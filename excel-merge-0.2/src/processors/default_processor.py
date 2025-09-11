"""
默认文件处理器
处理不匹配特定模式的Excel文件
"""
import pandas as pd

from .base_processor import BaseProcessor
from ..utils.logger import logger


class DefaultProcessor(BaseProcessor):
    """默认文件处理器"""
    
    def get_file_type(self) -> str:
        """
        获取文件类型标识符
        
        Returns:
            文件类型标识符
        """
        return 'default'
    
    def can_handle(self, filename: str) -> bool:
        """
        默认处理器可以处理任何文件
        
        Args:
            filename: 文件名
            
        Returns:
            总是返回True
        """
        logger.info(f"DefaultProcessor: 使用默认处理器处理文件: {filename}")
        return True
    def process_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        默认数据处理逻辑（不需要特殊处理，配置化处理已在基类中完成）
        
        Args:
            df: 已经过配置化处理的DataFrame
            
        Returns:
            处理后的DataFrame
        """
        try:
            logger.info("DefaultProcessor: 开始默认数据处理")
            
            # 记录原始数据信息
            original_rows = len(df)
            logger.info(f"DefaultProcessor: 原始数据行数: {original_rows}")
            
            # 默认处理器不需要特殊处理，只需要配置化映射
            
            logger.info("DefaultProcessor: 默认数据处理完成")
            return df
            
        except Exception as e:
            logger.exception(f"DefaultProcessor: 数据处理失败: {str(e)}")
            return df