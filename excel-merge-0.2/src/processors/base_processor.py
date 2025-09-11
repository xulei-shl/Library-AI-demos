"""
处理器基类模块
定义所有文件处理器的通用接口
"""
from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Optional
from pathlib import Path

from ..utils.logger import logger
from ..utils.config_mapper import ConfigMapper


class BaseProcessor(ABC):
    """文件处理器抽象基类"""
    
    def __init__(self):
        self.processor_name = self.__class__.__name__
        logger.debug(f"初始化处理器: {self.processor_name}")
    
    @abstractmethod
    def can_handle(self, filename: str) -> bool:
        """
        判断是否能处理指定的文件
        
        Args:
            filename: 文件名
            
        Returns:
            是否能处理该文件
        """
        pass
    
    @abstractmethod
    def get_file_type(self) -> str:
        """
        获取文件类型标识符
        
        Returns:
            文件类型标识符（如 'yibu', 'erbu', 'sanbu', 'default'）
        """
        pass
    
    @abstractmethod
    def process_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理数据的核心逻辑（在应用配置化映射和默认值后执行）
        
        Args:
            df: 已经过配置化处理的DataFrame
            
        Returns:
            处理后的DataFrame
        """
        pass
    
    def get_column_mapping(self) -> Dict[str, str]:
        """
        获取列名映射关系（已废弃，由配置文件管理）
        
        Returns:
            空字典（保持向后兼容）
        """
        logger.warning(f"{self.processor_name}: get_column_mapping方法已废弃，请使用配置文件管理列映射")
        return {}
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        验证数据有效性
        
        Args:
            df: 要验证的DataFrame
            
        Returns:
            数据是否有效
        """
        try:
            if df is None or df.empty:
                logger.warning(f"{self.processor_name}: 数据为空")
                return False
            
            logger.info(f"{self.processor_name}: 数据验证通过，行数: {len(df)}, 列数: {len(df.columns)}")
            return True
            
        except Exception as e:
            logger.exception(f"{self.processor_name}: 数据验证失败: {str(e)}")
            return False
    
    def apply_config_mapping(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        应用基于配置的列映射和数据处理
        
        Args:
            df: 原始DataFrame
            
        Returns:
            应用配置后的DataFrame
        """
        try:
            file_type = self.get_file_type()
            logger.info(f"{self.processor_name}: 开始应用配置映射，文件类型: {file_type}")
            
            # 1. 应用数据清洗
            df_cleaned = ConfigMapper.apply_data_cleaning(df, file_type)
            
            # 2. 应用列映射
            df_mapped, applied_mapping = ConfigMapper.apply_column_mapping(df_cleaned, file_type)
            
            if applied_mapping:
                mapped_info = ', '.join([f"{k}->{v}" for k, v in applied_mapping.items()])
                logger.info(f"{self.processor_name}: 应用列映射: {mapped_info}")
            
            # 3. 应用默认值填充
            df_with_defaults = ConfigMapper.apply_default_values(df_mapped, file_type)
            
            logger.info(f"{self.processor_name}: 配置映射完成")
            return df_with_defaults
            
        except Exception as e:
            logger.exception(f"{self.processor_name}: 配置映射失败: {str(e)}")
            return df
    
    def execute(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        执行完整的数据处理流程
        
        Args:
            df: 原始数据DataFrame
            
        Returns:
            处理后的DataFrame或None（如果处理失败）
        """
        try:
            logger.info(f"{self.processor_name}: 开始处理数据")
            
            # 数据验证
            if not self.validate_data(df):
                return None
            
            # 应用基于配置的映射和处理
            df_processed_config = self.apply_config_mapping(df)
            
            # 执行具体处理逻辑
            df_processed = self.process_data(df_processed_config)
            
            # 最终验证
            if not self.validate_data(df_processed):
                return None
            
            logger.info(f"{self.processor_name}: 数据处理完成")
            return df_processed
            
        except Exception as e:
            logger.exception(f"{self.processor_name}: 数据处理失败: {str(e)}")
            return None