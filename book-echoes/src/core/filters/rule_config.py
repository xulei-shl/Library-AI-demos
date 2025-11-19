"""
筛选器注册表 - 支持动态新增筛选规则
"""

from typing import Dict, Any, List, Type
from .base_filter import BaseFilter
from .hot_books_filter import HotBooksFilter
from .title_keywords_filter import TitleKeywordsFilter
from .call_number_filter import CallNumberFilter
from .column_value_filter import ColumnValueFilter
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FilterRegistry:
    """筛选器注册表 - 支持动态新增筛选规则"""
    
    _filters = {}
    
    @classmethod
    def register(cls, filter_type: str, filter_class: Type[BaseFilter]):
        """注册新的筛选器类型"""
        cls._filters[filter_type] = filter_class
        logger.info(f"注册筛选器类型: {filter_type}")
    
    @classmethod
    def create_filter(cls, filter_type: str, config: Dict[str, Any]) -> BaseFilter:
        """根据类型创建筛选器实例"""
        if filter_type not in cls._filters:
            raise ValueError(f"未知的筛选器类型: {filter_type}")
        
        filter_class = cls._filters[filter_type]
        return filter_class(config)
    
    @classmethod
    def get_available_filters(cls) -> List[str]:
        """获取所有可用的筛选器类型"""
        return list(cls._filters.keys())
    
    @classmethod
    def init_default_filters(cls):
        """初始化默认的筛选器类型"""
        # 注册所有内置筛选器
        cls.register('hot_books', HotBooksFilter)
        cls.register('title_keywords', TitleKeywordsFilter)
        cls.register('call_number', CallNumberFilter)
        cls.register('column_value', ColumnValueFilter)
        
        logger.info(f"已注册 {len(cls._filters)} 种筛选器类型: {list(cls._filters.keys())}")


# 初始化默认筛选器
FilterRegistry.init_default_filters()