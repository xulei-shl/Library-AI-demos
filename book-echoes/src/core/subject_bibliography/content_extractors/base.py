"""全文提取器抽象基类"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseContentExtractor(ABC):
    """全文提取器抽象基类"""
    
    @abstractmethod
    def extract(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取全文
        
        Args:
            article: 包含 source, title, link, content 等字段的字典
            
        Returns:
            包含以下字段的字典:
            - full_text: 提取的全文内容
            - extract_status: 提取状态 (success/failed/skipped)
            - extract_error: 错误信息(如有)
        """
        pass
    
    @abstractmethod
    def can_handle(self, source_name: str) -> bool:
        """
        判断是否能处理该RSS源
        
        Args:
            source_name: RSS源名称
            
        Returns:
            True 如果能处理该源，否则 False
        """
        pass
