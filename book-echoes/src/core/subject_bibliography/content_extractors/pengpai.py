"""澎湃思想市场全文提取器"""

from typing import Dict, Any
from bs4 import BeautifulSoup
from .base import BaseContentExtractor
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PengpaiExtractor(BaseContentExtractor):
    """澎湃思想市场全文提取器
    
    策略: 直接从 content 字段解析HTML获取全文
    """
    
    def can_handle(self, source_name: str) -> bool:
        """判断是否能处理该RSS源"""
        return "澎湃" in source_name or "pengpai" in source_name.lower()
    
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
            
            # 使用 BeautifulSoup 清理 HTML 标签
            soup = BeautifulSoup(content, "html.parser")
            
            # 移除 script 和 style 标签
            for tag in soup(["script", "style"]):
                tag.decompose()
            
            # 提取纯文本
            text = soup.get_text(separator="\n", strip=True)
            
            # 清理多余的空行
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            full_text = "\n".join(lines)
            
            if full_text:
                result["full_text"] = full_text
                result["extract_status"] = "success"
                logger.info(f"成功提取文章全文: {article.get('title')} (长度: {len(full_text)})")
            else:
                result["extract_status"] = "failed"
                result["extract_error"] = "提取的文本为空"
                logger.warning(f"提取的文本为空: {article.get('title')}")
        
        except Exception as e:
            result["extract_status"] = "failed"
            result["extract_error"] = str(e)
            logger.error(f"提取全文失败: {article.get('title')}, 错误: {e}")
        
        return result
