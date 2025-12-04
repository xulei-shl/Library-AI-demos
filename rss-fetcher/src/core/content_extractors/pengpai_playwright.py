"""澎湃网站Playwright抓取文章全文提取器"""

import re
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from src.core.content_extractors.base import BaseContentExtractor
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PengpaiPlaywrightExtractor(BaseContentExtractor):
    """澎湃网站Playwright抓取文章全文提取器"""
    
    def can_handle(self, source_name: str) -> bool:
        """判断是否能处理指定的源"""
        # 支持通过名称匹配
        if "pengpai_playwright" in source_name.lower():
            return True
        
        # 支持通过内容匹配
        return "澎湃" in source_name and ("playwright" in source_name.lower() or "手机端" in source_name)
    
    def extract(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """提取澎湃文章全文"""
        url = article.get("link", "")
        if not url:
            return self._create_error_result("URL为空")
        
        try:
            logger.info(f"开始提取澎湃文章: {article.get('title', 'Unknown')}")
            
            # 使用Playwright获取页面内容
            html_content = self._fetch_article_html(url)
            if not html_content:
                return self._create_error_result("无法获取文章HTML内容")
            
            # 解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取正文内容
            content = self._extract_content(soup)
            
            # 确保content是字符串类型
            if content is None or (isinstance(content, float) and str(content) == 'nan'):
                content = ""
            content = str(content)
            
            result = {
                "full_text": content,
                "extract_status": "success" if content else "failed",
                "extract_error": None if content else "内容为空"
            }
            
            logger.info(f"成功提取文章全文，字符数: {len(content)}")
            return result
            
        except Exception as e:
            error_msg = f"提取失败: {str(e)}"
            logger.error(error_msg)
            return self._create_error_result(error_msg)
    
    def _fetch_article_html(self, url: str) -> str:
        """使用Playwright获取文章HTML内容"""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
                    viewport={"width": 375, "height": 667}
                )
                page = context.new_page()
                
                try:
                    # 访问文章页面
                    page.goto(url, timeout=30000)
                    page.wait_for_load_state("networkidle", timeout=30000)
                    
                    # 获取页面HTML
                    html_content = page.content()
                    logger.debug(f"成功获取文章页面HTML: {url} (长度: {len(html_content)})")
                    return html_content
                    
                except PlaywrightTimeoutError:
                    logger.warning(f"文章页面加载超时: {url}")
                    return ""
                except Exception as e:
                    logger.error(f"访问文章页面失败: {url}, 错误: {e}")
                    return ""
                finally:
                    browser.close()
        
        except Exception as e:
            logger.error(f"初始化Playwright失败: {e}")
            return ""
    

    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """根据澎湃手机端HTML结构提取文章正文内容"""
        try:
            # 查找文章内容容器
            # 根据用户提供的HTML结构：.index_cententWrapBox__bh0OY > .index_cententWrap__Jv8jK
            content_container = soup.select_one(".index_cententWrapBox__bh0OY .index_cententWrap__Jv8jK")
            
            if not content_container:
                # 备用选择器
                content_container = soup.select_one(".index_cententWrapBox__bh0OY")
            
            if not content_container:
                logger.warning("未找到文章内容容器")
                return "无法提取内容：未找到文章内容容器"
            
            # 移除不需要的元素
            for unwanted in content_container.select('script, style, .index_animation__S6WSF'):
                unwanted.decompose()
            
            # 处理图片元素
            for img in content_container.find_all("img"):
                alt_text = img.get("alt", "")
                if alt_text:
                    # 创建文本节点来替代图片
                    img.replace_with(f"[图片: {alt_text}]")
                else:
                    img.decompose()
            
            # 处理图片描述段落（class="image_desc"）
            for img_desc in content_container.find_all("p", class_="image_desc"):
                # 保留图片描述文本
                desc_text = img_desc.get_text(strip=True)
                if desc_text:
                    img_desc.replace_with(f"\n{desc_text}\n")
            
            # 提取纯文本
            text = content_container.get_text(separator="\n", strip=True)
            
            # 清理多余的空行
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            full_text = "\n".join(lines)
            
            if full_text and len(str(full_text)) > 50:  # 确保内容足够长
                logger.debug(f"成功提取正文内容，长度: {len(str(full_text))}")
                return str(full_text)
            else:
                logger.warning("提取的正文内容过短或为空")
                return "无法提取内容：内容过短"
                
        except Exception as e:
            logger.error(f"提取正文内容失败: {e}")
            return f"无法提取内容：{str(e)}"
    
    def _extract_author(self, soup: BeautifulSoup) -> str:
        """提取作者信息"""
        author_selectors = [
            '.author',
            '.writer',
            '[class*="author"]',
            '[class*="writer"]'
        ]
        
        for selector in author_selectors:
            author_elem = soup.select_one(selector)
            if author_elem:
                author = author_elem.get_text().strip()
                if author:
                    return author
        
        return ""
    
    def _extract_publish_time(self, soup: BeautifulSoup, fallback_time: str = "") -> str:
        """提取发布时间"""
        time_selectors = [
            '.time',
            '.publish_time',
            '[class*="time"]',
            '[class*="date"]'
        ]
        
        for selector in time_selectors:
            time_elem = soup.select_one(selector)
            if time_elem:
                time_text = time_elem.get_text().strip()
                if time_text:
                    return time_text
        
        return fallback_time or ""
    
    def _extract_tags(self, soup: BeautifulSoup) -> list:
        """提取标签"""
        tags = []
        tag_selectors = [
            '.tag',
            '.keyword',
            '[class*="tag"]',
            '[class*="keyword"]'
        ]
        
        for selector in tag_selectors:
            tag_elems = soup.select(selector)
            for tag_elem in tag_elems:
                tag_text = tag_elem.get_text().strip()
                if tag_text and tag_text not in tags:
                    tags.append(tag_text)
        
        return tags
    
    def _create_error_result(self, error_msg: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            "full_text": "",
            "title": "",
            "author": "",
            "publish_date": "",
            "tags": [],
            "extract_status": "failed",
            "extract_error": error_msg
        }