"""提取器工厂类"""

from typing import Optional, List
from .base import BaseContentExtractor
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ExtractorFactory:
    """提取器工厂类，负责管理和分发提取器"""
    
    _extractors: List[BaseContentExtractor] = []
    
    @classmethod
    def register(cls, extractor_class):
        """
        注册提取器
        
        Args:
            extractor_class: 提取器类(非实例)
        """
        try:
            instance = extractor_class()
            cls._extractors.append(instance)
            logger.info(f"已注册提取器: {extractor_class.__name__}")
        except Exception as e:
            logger.error(f"注册提取器 {extractor_class.__name__} 失败: {e}")
    
    @classmethod
    def get_extractor(cls, source_name: str) -> Optional[BaseContentExtractor]:
        """
        根据RSS源名称获取对应的提取器
        
        Args:
            source_name: RSS源名称
            
        Returns:
            对应的提取器实例，如果没有找到则返回 None
        """
        for extractor in cls._extractors:
            if extractor.can_handle(source_name):
                logger.debug(f"为源 '{source_name}' 选择提取器: {extractor.__class__.__name__}")
                return extractor
        
        logger.warning(f"未找到适合源 '{source_name}' 的提取器")
        return None
    
    @classmethod
    def list_extractors(cls) -> List[str]:
        """
        列出所有已注册的提取器
        
        Returns:
            提取器类名列表
        """
        return [extractor.__class__.__name__ for extractor in cls._extractors]
