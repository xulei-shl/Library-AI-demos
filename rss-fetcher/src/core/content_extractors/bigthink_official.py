"""Big Think官方RSS全文提取器"""

from typing import Dict, Any
from bs4 import BeautifulSoup
from .base import BaseContentExtractor
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BigThinkOfficialExtractor(BaseContentExtractor):
    """Big Think官方RSS全文提取器
    
    策略: 直接从 content 字段解析HTML获取全文
    """
    
    def can_handle(self, source_name: str) -> bool:
        """判断是否能处理该RSS源"""
        # 优先匹配包含"-官方"后缀的Big Think源
        source_lower = source_name.lower()
        return ("big think-官方" in source_lower or 
                "bigthink-官方" in source_lower or
                ("big think" in source_lower and "-官方" in source_lower))
    
    def extract(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        从content字段提取全文
        
        Args:
            article: 文章字典，需包含 content 字段
            
        Returns:
            包含 full_text, extract_status, extract_error 的字典
        """
        result = {
            "full_text": "",
            "extract_status": "failed",
            "extract_error": ""
        }
        
        try:
            content = article.get("content", "")
            
            if not content:
                result["extract_status"] = "skipped"
                result["extract_error"] = "content字段为空"
                logger.warning(f"文章 '{article.get('title')}' 的content字段为空")
                return result
            
            # 使用 BeautifulSoup 解析HTML内容
            soup = BeautifulSoup(content, "html.parser")
            
            # 移除图片标签但保留alt文本信息
            for img in soup.find_all("img"):
                alt_text = img.get("alt", "")
                if alt_text:
                    # 用alt文本替换图片
                    img.replace_with(f"[图片: {alt_text}]")
                else:
                    img.decompose()
            
            # 移除script和style标签
            for tag in soup(["script", "style"]):
                tag.decompose()
            
            # 移除注释
            for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith("<!--")):
                comment.extract()
            
            # 处理链接，保留链接文本但移除链接本身
            for link in soup.find_all("a"):
                link_text = link.get_text(strip=True)
                link.replace_with(link_text)
            
            # 处理强调标签，保留文本
            for em_tag in soup.find_all(["em", "strong", "b", "i"]):
                em_tag.replace_with(em_tag.get_text())
            
            # 处理引用标签
            for quote in soup.find_all(["blockquote", "q"]):
                quote_text = quote.get_text(strip=True)
                quote.replace_with(f'"{quote_text}"')
            
            # 处理标题标签，保留文本
            for header in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
                header_text = header.get_text(strip=True)
                header.replace_with(f"\n{header_text}\n")
            
            # 处理段落标签
            for p in soup.find_all("p"):
                p_text = p.get_text(strip=True)
                if p_text:  # 只保留非空段落
                    p.replace_with(f"{p_text}\n")
            
            # 提取纯文本
            text = soup.get_text()
            
            # 清理多余的空行和空白
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            full_text = "\n".join(lines)
            
            # 进一步清理：移除多余的空行
            import re
            full_text = re.sub(r'\n\s*\n\s*\n', '\n\n', full_text)
            
            if full_text and len(full_text.strip()) > 100:  # 至少100字符才认为提取成功
                result["full_text"] = full_text
                result["extract_status"] = "success"
                logger.info(f"成功提取文章全文: {article.get('title')} (长度: {len(full_text)})")
            else:
                result["extract_status"] = "failed"
                result["extract_error"] = "提取的文本为空或过短"
                logger.warning(f"提取的文本为空或过短: {article.get('title')}")
        
        except Exception as e:
            result["extract_status"] = "failed"
            result["extract_error"] = str(e)
            logger.error(f"提取全文失败: {article.get('title')}, 错误: {e}")
        
        return result