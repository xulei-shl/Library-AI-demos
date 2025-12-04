"""Wikipedia每日首页文章全文提取器"""

from typing import Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
from .base import BaseContentExtractor
from src.utils.logger import get_logger

logger = get_logger(__name__)


class WikipediaExtractor(BaseContentExtractor):
    """Wikipedia每日首页文章全文提取器
    
    策略: 从content字段提取全文URL，然后爬取
    """
    
    def __init__(self):
        self.timeout = 30
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    
    def can_handle(self, source_name: str) -> bool:
        """判断是否能处理该RSS源"""
        return "wikipedia" in source_name.lower() or "维基" in source_name
    
    def _extract_article_url(self, content: str) -> Optional[str]:
        """从RSS content中提取Wikipedia文章URL
        
        Args:
            content: RSS的content字段HTML内容
            
        Returns:
            Wikipedia完整文章URL，如果未找到则返回None
        """
        try:
            soup = BeautifulSoup(content, "html.parser")
            
            # 查找所有链接
            links = soup.find_all("a", href=True)
            for link in links:
                href = link["href"]
                
                # 处理不同格式的Wikipedia链接
                if href.startswith("/wiki/"):
                    # 相对路径链接，如 /wiki/SMS_Pommern
                    article_name = href[6:]  # 移除 "/wiki/" 前缀
                    if article_name and ":" not in article_name.split("#")[0]:
                        full_url = f"https://en.wikipedia.org{href}"
                        logger.info(f"从相对路径找到Wikipedia文章URL: {full_url}")
                        return full_url
                
                elif "wikipedia.org/wiki/" in href:
                    # 完整Wikipedia链接，如 https://en.wikipedia.org/wiki/SMS_Pommern
                    # 提取 /wiki/ 后面的部分
                    wiki_part = href.split("/wiki/")[-1]
                    if ":" not in wiki_part.split("#")[0]:  # 排除锚点后的冒号
                        # 如果URL不完整，尝试构建完整URL
                        if not href.startswith("http"):
                            full_url = f"https://{href}" if "://" not in href else href
                        else:
                            full_url = href
                        logger.info(f"找到Wikipedia文章URL: {full_url}")
                        return full_url
                
                elif "wikipedia.org" in href and "/wiki/" in href:
                    # 其他形式的Wikipedia链接
                    article_part = href.split("/wiki/")[-1]
                    if article_part and ":" not in article_part.split("#")[0]:
                        # 构建标准Wikipedia URL
                        full_url = f"https://en.wikipedia.org/wiki/{article_part}"
                        logger.info(f"构建Wikipedia文章URL: {full_url}")
                        return full_url
            
            logger.warning("未在content中找到有效的Wikipedia文章链接")
            return None
        except Exception as e:
            logger.error(f"提取Wikipedia URL失败: {e}")
            return None
    
    def _fetch_article_content(self, url: str) -> Optional[Dict[str, str]]:
        """从Wikipedia URL爬取文章内容和标题
        
        Args:
            url: Wikipedia文章URL
            
        Returns:
            包含title和full_text的字典，如果爬取失败则返回None
        """
        try:
            logger.info(f"正在爬取Wikipedia文章: {url}")
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # 提取文章标题（从 h1 标签，id="firstHeading"）
            title_tag = soup.find("h1", {"id": "firstHeading"})
            article_title = title_tag.get_text(strip=True) if title_tag else ""
            
            if article_title:
                logger.info(f"提取到文章标题: {article_title}")
            else:
                logger.warning("未找到文章标题")
            
            # Wikipedia文章内容在 id="mw-content-text" 的div中
            content_div = soup.find("div", {"id": "mw-content-text"})
            if not content_div:
                logger.error("未找到Wikipedia文章内容容器 (id=mw-content-text)")
                return None
            
            # 找到文章主体部分（class="mw-parser-output"）
            parser_output = content_div.find("div", {"class": "mw-parser-output"})
            if not parser_output:
                logger.warning("未找到mw-parser-output，使用整个content_div")
                parser_output = content_div
            
            # 移除不需要的元素
            for unwanted in parser_output.find_all(["script", "style", "table", "div"], class_=["navbox", "infobox", "toc", "reflist", "reference"]):
                unwanted.decompose()
            
            # 只保留段落
            paragraphs = parser_output.find_all("p")
            
            # 提取文本
            texts = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                # 过滤掉空段落和过短的段落
                if text and len(text) > 20:
                    texts.append(text)
            
            if not texts:
                logger.error("未提取到有效段落")
                return None
            
            full_text = "\n\n".join(texts)
            logger.info(f"成功提取文章内容，长度: {len(full_text)} 字符")
            
            return {
                "title": article_title,
                "full_text": full_text
            }
        
        except requests.exceptions.Timeout:
            logger.error(f"请求超时: {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {url}, 错误: {e}")
            return None
        except Exception as e:
            logger.error(f"爬取Wikipedia内容失败: {url}, 错误: {e}")
            return None
    
    def extract(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        从content提取URL并爬取全文和标题
        
        Args:
            article: 文章字典，需包含 content 字段
            
        Returns:
            包含 title, full_text, extract_status, extract_error 的字典
        """
        result = {
            "full_text": "",
            "extract_status": "failed",
            "extract_error": ""
        }
        
        content = article.get("content", "")
        if not content:
            result["extract_status"] = "skipped"
            result["extract_error"] = "content字段为空"
            logger.warning(f"跳过文章（content为空）: {article.get('title')}")
            return result
        
        try:
            # 步骤1: 从content提取Wikipedia文章URL
            article_url = self._extract_article_url(content)
            if not article_url:
                result["extract_error"] = "未找到Wikipedia文章URL"
                logger.warning(f"未找到URL: {article.get('title')}")
                return result
            
            # 步骤2: 爬取文章内容和标题
            content_data = self._fetch_article_content(article_url)
            if not content_data:
                result["extract_error"] = "爬取文章内容失败或内容为空"
                return result
            
            # 提取标题和全文
            extracted_title = content_data.get("title", "")
            full_text = content_data.get("full_text", "")
            
            result["full_text"] = full_text
            result["extract_status"] = "success"
            
            # 如果提取到了真实标题，则更新title字段
            if extracted_title:
                result["title"] = extracted_title
                logger.info(f"✓ 成功提取Wikipedia文章: {extracted_title} (长度: {len(full_text)})")
            else:
                logger.info(f"✓ 成功提取Wikipedia文章: {article.get('title')} (长度: {len(full_text)})")
        
        except Exception as e:
            result["extract_error"] = str(e)
            logger.error(f"提取Wikipedia文章失败: {article.get('title')}, 错误: {e}")
        
        return result
