"""
字段转换器模块
提供灵活的字段转换功能,支持不同模板使用不同的字段处理规则
"""

from typing import Optional, Dict, Any
from abc import ABC, abstractmethod


class FieldTransformer(ABC):
    """字段转换器基类"""
    
    @abstractmethod
    def transform(self, value: Any, **kwargs) -> str:
        """
        转换字段值
        
        Args:
            value: 原始字段值
            **kwargs: 额外参数
            
        Returns:
            str: 转换后的字符串
        """
        pass


class DirectTransformer(FieldTransformer):
    """直接转换器 - 直接返回字段值"""
    
    def transform(self, value: Any, **kwargs) -> str:
        """直接返回值"""
        if value is None:
            return kwargs.get('default', '')
        return str(value).strip()


class FirstAuthorTransformer(FieldTransformer):
    """第一作者转换器 - 提取第一个作者并添加后缀"""
    
    def transform(self, value: Any, **kwargs) -> str:
        """
        提取第一个作者
        
        Args:
            value: 作者字段值 (可能包含多个作者,用分隔符分隔)
            **kwargs: 
                - separator: 分隔符,默认为 '/'
                - suffix: 后缀,默认为 ' 等'
                - default: 默认值,默认为 ''
        
        Returns:
            str: 第一个作者 + 后缀 (如果有多个作者)
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            return kwargs.get('default', '')
        
        value_str = str(value).strip()
        separator = kwargs.get('separator', '/')
        suffix = kwargs.get('suffix', ' 等')
        
        # 分割作者
        authors = [a.strip() for a in value_str.split(separator) if a.strip()]
        
        if not authors:
            return kwargs.get('default', '')
        
        # 如果只有一个作者,直接返回
        if len(authors) == 1:
            return authors[0]
        
        # 多个作者,返回第一个 + 后缀
        return authors[0] + suffix


class MainTitleOnlyTransformer(FieldTransformer):
    """主标题转换器 - 只返回主标题,不包含副标题"""
    
    def transform(self, value: Any, **kwargs) -> str:
        """
        返回主标题
        
        Args:
            value: 标题字段值
            **kwargs:
                - default: 默认值,默认为 ''
        
        Returns:
            str: 主标题
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            return kwargs.get('default', '')
        
        return str(value).strip()


class FullTitleTransformer(FieldTransformer):
    """完整标题转换器 - 返回主标题 + 副标题"""
    
    def transform(self, value: Any, **kwargs) -> str:
        """
        返回完整标题 (主标题 + 副标题)
        
        Args:
            value: 主标题字段值
            **kwargs:
                - subtitle: 副标题值
                - separator: 分隔符,默认为 ' : '
                - default: 默认值,默认为 ''
        
        Returns:
            str: 完整标题
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            return kwargs.get('default', '')
        
        main_title = str(value).strip()
        subtitle = kwargs.get('subtitle')
        
        # 如果没有副标题,只返回主标题
        if subtitle is None or (isinstance(subtitle, str) and not subtitle.strip()):
            return main_title
        
        separator = kwargs.get('separator', ' : ')
        return f"{main_title}{separator}{str(subtitle).strip()}"


class FieldTransformerFactory:
    """字段转换器工厂类"""
    
    # 转换器类型映射
    _transformers = {
        'direct': DirectTransformer,
        'first_author': FirstAuthorTransformer,
        'main_title_only': MainTitleOnlyTransformer,
        'full_title': FullTitleTransformer,
    }
    
    @classmethod
    def create(cls, transformer_type: str) -> FieldTransformer:
        """
        创建字段转换器
        
        Args:
            transformer_type: 转换器类型
            
        Returns:
            FieldTransformer: 字段转换器实例
            
        Raises:
            ValueError: 不支持的转换器类型
        """
        transformer_class = cls._transformers.get(transformer_type)
        if transformer_class is None:
            raise ValueError(f"不支持的转换器类型: {transformer_type}")
        
        return transformer_class()
    
    @classmethod
    def register(cls, transformer_type: str, transformer_class: type):
        """
        注册自定义转换器
        
        Args:
            transformer_type: 转换器类型名称
            transformer_class: 转换器类
        """
        cls._transformers[transformer_type] = transformer_class
