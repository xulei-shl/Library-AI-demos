"""Big Think全文提取器"""

from typing import Dict, Any
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
from .base import BaseContentExtractor
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BigThinkExtractor(BaseContentExtractor):
    """Big Think全文提取器
    
    策略: 使用无头浏览器从link爬取全文
    """
    
    def __init__(self):
        self.timeout = 30000  # 30秒超时
        self.headless = True
    
    def can_handle(self, source_name: str) -> bool:
        """判断是否能处理该RSS源"""
        return "big think" in source_name.lower() or "bigthink" in source_name.lower()
    
    def extract(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用无头浏览器提取全文
        
        Args:
            article: 文章字典,需包含 link 字段
            
        Returns:
            包含 full_text, extract_status, extract_error 的字典
        """
        result = {
            "full_text": "",
            "extract_status": "failed",
            "extract_error": ""
        }
        
        link = article.get("link", "")
        if not link:
            result["extract_status"] = "skipped"
            result["extract_error"] = "link字段为空"
            return result
        
        try:
            with sync_playwright() as p:
                # 启动浏览器
                browser = p.chromium.launch(headless=self.headless)
                page = browser.new_page()
                
                # 访问页面
                logger.info(f"正在访问: {link}")
                page.goto(link, timeout=self.timeout)
                
                # 等待主要内容加载 - 等待prose容器
                page.wait_for_selector("div.prose", timeout=self.timeout)
                
                # 获取页面HTML
                html = page.content()
                browser.close()
                
                # 解析HTML
                soup = BeautifulSoup(html, "html.parser")
                
                # 提取文章正文 - 定位prose容器
                prose_div = soup.find("div", class_="prose")
                if not prose_div:
                    result["extract_error"] = "未找到prose容器"
                    return result
                
                # 移除广告和无关元素
                # 1. 移除订阅框 (bt-block bt-inp)
                for ad_block in prose_div.find_all("div", class_="bt-block"):
                    ad_block.decompose()
                
                # 2. 移除广告位 (advertising)
                for ad in prose_div.find_all("div", class_="advertising"):
                    ad.decompose()
                
                # 3. 移除标签区域
                for tags_div in prose_div.find_all("div", class_="border-t"):
                    tags_div.decompose()
                
                # 4. 移除script和style标签
                for tag in prose_div(["script", "style"]):
                    tag.decompose()
                
                # 提取纯文本
                text = prose_div.get_text(separator="\n", strip=True)
                
                # 清理多余空行
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                full_text = "\n".join(lines)
                
                if full_text:
                    result["full_text"] = full_text
                    result["extract_status"] = "success"
                    logger.info(f"成功提取文章: {article.get('title')} (长度: {len(full_text)})")
                else:
                    result["extract_error"] = "提取的文本为空"
        
        except PlaywrightTimeout as e:
            result["extract_error"] = f"页面加载超时: {e}"
            logger.error(f"提取失败(超时): {link}")
        except Exception as e:
            result["extract_error"] = str(e)
            logger.error(f"提取失败: {link}, 错误: {e}")
        
        return result
