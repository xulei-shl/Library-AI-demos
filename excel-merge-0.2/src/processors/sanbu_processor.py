"""
三部文件处理器
处理文件名包含"三部"的Excel文件，在默认逻辑基础上对特定列进行赋值
"""
import pandas as pd

from .base_processor import BaseProcessor
from ..utils.logger import logger
from ..utils.config_mapper import ConfigMapper


class SanbuProcessor(BaseProcessor):
    """三部文件处理器"""
    
    def get_file_type(self) -> str:
        """
        获取文件类型标识符
        
        Returns:
            文件类型标识符
        """
        return 'sanbu'
    
    def can_handle(self, filename: str) -> bool:
        """
        判断是否能处理指定的文件
        
        Args:
            filename: 文件名
            
        Returns:
            文件名包含"三部"时返回True
        """
        can_handle = "三部" in filename
        if can_handle:
            logger.info(f"SanbuProcessor: 检测到三部文件: {filename}")
        return can_handle
    def process_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        三部文件数据处理逻辑（不需要特殊处理，配置化处理已在基类中完成）
        
        Args:
            df: 已经过配置化处理的DataFrame
            
        Returns:
            处理后的DataFrame
        """
        try:
            logger.info("SanbuProcessor: 开始三部文件数据处理")
            
            # 记录原始数据信息
            original_rows = len(df)
            logger.info(f"SanbuProcessor: 原始数据行数: {original_rows}")
            
            # 三部文件的具体处理逻辑（如果有的话）
            # 目前三部文件不需要特殊处理，只需要配置化映射和默认值填充
            
            logger.info("SanbuProcessor: 三部文件数据处理完成")
            return df
            
        except Exception as e:
            logger.exception(f"SanbuProcessor: 数据处理失败: {str(e)}")
            return df
