"""
处理器工厂模块
根据文件名创建对应的处理器实例
"""
from typing import Optional

from .base_processor import BaseProcessor
from .yibu_processor import YibuProcessor
from .erbu_processor import ErbuProcessor
from .sanbu_processor import SanbuProcessor
from .default_processor import DefaultProcessor
from ..utils.logger import logger


class ProcessorFactory:
    """处理器工厂类"""
    
    # 处理器类列表，按优先级排序（越靠前优先级越高）
    PROCESSOR_CLASSES = [
        YibuProcessor,
        ErbuProcessor,
        SanbuProcessor,
        DefaultProcessor  # 默认处理器放在最后，作为兜底
    ]
    
    @classmethod
    def create_processor(cls, filename: str) -> Optional[BaseProcessor]:
        """
        根据文件名创建对应的处理器
        
        Args:
            filename: 文件名
            
        Returns:
            对应的处理器实例，如果创建失败返回None
        """
        try:
            logger.debug(f"ProcessorFactory: 为文件 '{filename}' 创建处理器")
            
            # 遍历处理器类，找到第一个能处理该文件的处理器
            for processor_class in cls.PROCESSOR_CLASSES:
                processor = processor_class()
                if processor.can_handle(filename):
                    logger.info(f"ProcessorFactory: 选择处理器 {processor_class.__name__} 处理文件 '{filename}'")
                    return processor
            
            # 理论上不会到达这里，因为DefaultProcessor总是返回True
            logger.error(f"ProcessorFactory: 无法为文件 '{filename}' 找到合适的处理器")
            return None
            
        except Exception as e:
            logger.exception(f"ProcessorFactory: 创建处理器失败，文件: {filename}, 错误: {str(e)}")
            return None
    
    @classmethod
    def get_available_processors(cls) -> list:
        """
        获取所有可用的处理器类
        
        Returns:
            处理器类列表
        """
        return cls.PROCESSOR_CLASSES.copy()