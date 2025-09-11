"""
馆藏业务统计表处理器
处理文件名包含"馆藏业务统计表"的Excel文件
"""
import pandas as pd
from typing import Dict

from .base_processor import BaseProcessor
from ..config.settings import FILE_PATTERNS
from ..utils.logger import logger


class YibuProcessor(BaseProcessor):
    """馆藏业务统计表文件处理器"""
    
    def can_handle(self, filename: str) -> bool:
        """
        判断是否能处理指定的文件
        
        Args:
            filename: 文件名
            
        Returns:
            是否能处理该文件
        """
        pattern = FILE_PATTERNS.get('yibu', '')
        can_handle = pattern in filename
        
        if can_handle:
            logger.info(f"YibuProcessor: 识别到一部馆藏业务统计表文件: {filename}")
        
        return can_handle
    
    def get_file_type(self) -> str:
        """
        获取文件类型标识符
        
        Returns:
            文件类型标识符
        """
        return 'yibu'
    
    def process_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理一部馆藏业务统计表数据
        
        Args:
            df: 已经过配置化处理的DataFrame
            
        Returns:
            处理后的DataFrame
        """
        try:
            logger.info("YibuProcessor: 开始处理一部馆藏业务统计表数据")
            
            # 记录原始数据信息
            original_rows = len(df)
            logger.info(f"YibuProcessor: 原始数据行数: {original_rows}")
            
            # 一部文件的具体处理逻辑（如果有的话）
            # 目前一部文件不需要特殊处理，只需要配置化映射
            
            logger.info("YibuProcessor: 一部馆藏业务统计表数据处理完成")
            return df
            
        except Exception as e:
            logger.exception(f"YibuProcessor: 数据处理失败: {str(e)}")
            return df