"""
配置映射工具模块
提供基于配置的列映射、默认值填充和动态模式匹配功能
"""
import re
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from ..config.settings import (
    COLUMN_MAPPINGS, DYNAMIC_COLUMN_PATTERNS, DEFAULT_VALUES, 
    DATA_PROCESSING_CONFIG, FILE_PATTERNS
)
from ..utils.logger import logger


class ConfigMapper:
    """配置映射器，基于配置文件进行数据映射和处理"""
    
    # 定义标准列名列表，用于默认直通逻辑验证
    STANDARD_COLUMNS = {
        "馆藏编号", "文献类型", "二级分类", "编目状态", "上游来源", 
        "业务类型", "下游去向", "统计来源", "批次编号", "总表数据修订说明",
        "统计人", "单位", "业务时间", "部门", "馆藏地", "内容", "I"
    }
    
    @staticmethod
    def get_file_type_from_name(filename: str) -> str:
        """
        根据文件名确定文件类型
        
        Args:
            filename: 文件名
            
        Returns:
            文件类型标识符
        """
        for file_type, pattern in FILE_PATTERNS.items():
            if pattern in filename:
                logger.debug(f"ConfigMapper: 文件 '{filename}' 匹配类型 '{file_type}'")
                return file_type
        
        logger.debug(f"ConfigMapper: 文件 '{filename}' 使用默认类型")
        return 'default'
    
    @staticmethod
    def get_column_mapping(file_type: str) -> Dict[str, str]:
        """
        获取指定文件类型的列映射配置
        
        Args:
            file_type: 文件类型
            
        Returns:
            列映射字典
        """
        mapping = {}
        
        # 1. 首先加载全局映射 (*)
        global_mapping = COLUMN_MAPPINGS.get("*", {})
        mapping.update(global_mapping)
        
        # 2. 然后加载文件类型特定的映射，覆盖全局配置
        file_mapping = COLUMN_MAPPINGS.get(file_type, {})
        mapping.update(file_mapping)
        
        logger.debug(f"ConfigMapper: 文件类型 '{file_type}' 的列映射规则数量: {len(mapping)}")
        return mapping
    
    @staticmethod
    def get_dynamic_patterns(file_type: str) -> Dict[str, str]:
        """
        获取指定文件类型的动态模式配置
        
        Args:
            file_type: 文件类型
            
        Returns:
            动态模式字典
        """
        patterns = {}
        
        # 1. 首先加载全局动态模式 (*)
        global_patterns = DYNAMIC_COLUMN_PATTERNS.get("*", {})
        patterns.update(global_patterns)
        
        # 2. 然后加载文件类型特定的动态模式，覆盖全局配置
        file_patterns = DYNAMIC_COLUMN_PATTERNS.get(file_type, {})
        patterns.update(file_patterns)
        
        logger.debug(f"ConfigMapper: 文件类型 '{file_type}' 的动态模式数量: {len(patterns)}")
        return patterns
    
    @staticmethod
    def get_default_values(file_type: str) -> Dict[str, Any]:
        """
        获取指定文件类型的默认值配置
        
        Args:
            file_type: 文件类型
            
        Returns:
            默认值字典
        """
        defaults = {}
        
        # 1. 首先加载全局默认值 (*)
        global_defaults = DEFAULT_VALUES.get("*", {})
        defaults.update(global_defaults)
        
        # 2. 然后加载文件类型特定的默认值，覆盖全局配置
        file_defaults = DEFAULT_VALUES.get(file_type, {})
        defaults.update(file_defaults)
        
        logger.debug(f"ConfigMapper: 文件类型 '{file_type}' 的默认值数量: {len(defaults)}")
        return defaults
    
    @staticmethod
    def get_processing_config(file_type: str) -> Dict[str, Any]:
        """
        获取指定文件类型的数据处理配置
        
        Args:
            file_type: 文件类型
            
        Returns:
            处理配置字典
        """
        config = {}
        
        # 1. 首先加载全局处理配置 (*)
        global_config = DATA_PROCESSING_CONFIG.get("*", {})
        config.update(global_config)
        
        # 2. 然后加载文件类型特定的处理配置，覆盖全局配置
        file_config = DATA_PROCESSING_CONFIG.get(file_type, {})
        config.update(file_config)
        
        logger.debug(f"ConfigMapper: 文件类型 '{file_type}' 的处理配置: {config}")
        return config
    
    @staticmethod
    def apply_column_mapping(df: pd.DataFrame, file_type: str) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """
        基于配置应用智能列映射（支持默认直通逻辑）
        
        映射优先级：
        1. 特定文件类型的显式配置映射
        2. 全局显式配置映射 
        3. 动态模式匹配
        4. 默认直通逻辑（源列名与标准列名相同时自动匹配）
        
        Args:
            df: 原始DataFrame
            file_type: 文件类型
            
        Returns:
            (映射后的DataFrame, 实际应用的映射字典)
        """
        try:
            if df.empty:
                logger.warning("ConfigMapper: 数据为空，跳过列映射")
                return df, {}
            
            # 获取列映射配置
            column_mapping = ConfigMapper.get_column_mapping(file_type)
            dynamic_patterns = ConfigMapper.get_dynamic_patterns(file_type)
            
            # 应用智能列映射策略
            applied_mapping = {}
            final_mapping = {}
            default_passthrough_count = 0
            
            for col in df.columns:
                mapped_col = col  # 默认保持原列名
                mapping_reason = "保持原名"
                
                # 1. 优先级1：尝试精确配置映射
                if col in column_mapping:
                    mapped_col = column_mapping[col]
                    applied_mapping[col] = mapped_col
                    mapping_reason = "配置映射"
                    logger.debug(f"ConfigMapper: {mapping_reason} '{col}' -> '{mapped_col}'")
                    
                # 2. 优先级2：尝试动态模式匹配
                elif dynamic_patterns:
                    pattern_matched = False
                    for pattern, target_col in dynamic_patterns.items():
                        if re.match(pattern, str(col)):
                            mapped_col = target_col
                            applied_mapping[col] = mapped_col
                            mapping_reason = f"动态匹配(模式: {pattern})"
                            pattern_matched = True
                            logger.debug(f"ConfigMapper: {mapping_reason} '{col}' -> '{mapped_col}'")
                            break
                    
                    # 3. 优先级3：默认直通逻辑（仅当未匹配到动态模式时）
                    if not pattern_matched and col in ConfigMapper.STANDARD_COLUMNS:
                        # 源列名是标准列名，直接使用（这是默认直通逻辑）
                        mapped_col = col
                        default_passthrough_count += 1
                        mapping_reason = "默认直通"
                        logger.debug(f"ConfigMapper: {mapping_reason} '{col}' -> '{mapped_col}' (标准列名)")
                
                # 4. 优先级4：如果没有动态模式配置，直接应用默认直通逻辑
                else:
                    if col in ConfigMapper.STANDARD_COLUMNS:
                        # 源列名是标准列名，直接使用（这是默认直通逻辑）
                        mapped_col = col
                        default_passthrough_count += 1
                        mapping_reason = "默认直通"
                        logger.debug(f"ConfigMapper: {mapping_reason} '{col}' -> '{mapped_col}' (标准列名)")
                
                final_mapping[col] = mapped_col
            
            # 应用映射
            df_mapped = df.rename(columns=final_mapping)
            
            # 记录映射统计
            total_columns = len(df.columns)
            config_mappings = len(applied_mapping)
            
            logger.info(f"ConfigMapper: 列映射完成 - 总列数: {total_columns}, "
                       f"配置映射: {config_mappings}, 默认直通: {default_passthrough_count}, "
                       f"保持原名: {total_columns - config_mappings - default_passthrough_count}")
            
            if applied_mapping:
                logger.info(f"ConfigMapper: 应用的配置映射: {dict(list(applied_mapping.items())[:5])}{'...' if len(applied_mapping) > 5 else ''}")
            
            return df_mapped, applied_mapping
            
        except Exception as e:
            logger.exception(f"ConfigMapper: 列映射失败: {str(e)}")
            return df, {}
    
    @staticmethod
    def apply_default_values(df: pd.DataFrame, file_type: str) -> pd.DataFrame:
        """
        基于配置应用默认值填充
        
        Args:
            df: DataFrame
            file_type: 文件类型
            
        Returns:
            填充默认值后的DataFrame
        """
        try:
            if df.empty:
                logger.warning("ConfigMapper: 数据为空，跳过默认值填充")
                return df
            
            # 获取默认值配置
            default_values = ConfigMapper.get_default_values(file_type)
            
            if not default_values:
                logger.debug(f"ConfigMapper: 文件类型 '{file_type}' 无默认值配置")
                return df
            
            df_copy = df.copy()
            filled_count = 0
            
            for column, default_value in default_values.items():
                if column in df_copy.columns:
                    # 查找需要填充的行（空值或空字符串）
                    mask = df_copy[column].isna() | (df_copy[column].astype(str).str.strip() == '')
                    fill_count = mask.sum()
                    
                    if fill_count > 0:
                        df_copy.loc[mask, column] = default_value
                        filled_count += fill_count
                        logger.info(f"ConfigMapper: 为列 '{column}' 填充 {fill_count} 个默认值 '{default_value}'")
                else:
                    # 如果列不存在，创建新列并填充默认值
                    df_copy[column] = default_value
                    filled_count += len(df_copy)
                    logger.info(f"ConfigMapper: 创建新列 '{column}' 并填充默认值 '{default_value}'")
            
            if filled_count > 0:
                logger.info(f"ConfigMapper: 总计填充 {filled_count} 个默认值")
            else:
                logger.debug("ConfigMapper: 未进行默认值填充")
            
            return df_copy
            
        except Exception as e:
            logger.exception(f"ConfigMapper: 默认值填充失败: {str(e)}")
            return df
    
    @staticmethod
    def apply_data_cleaning(df: pd.DataFrame, file_type: str) -> pd.DataFrame:
        """
        基于配置应用数据清洗
        
        Args:
            df: DataFrame
            file_type: 文件类型
            
        Returns:
            清洗后的DataFrame
        """
        try:
            if df.empty:
                logger.warning("ConfigMapper: 数据为空，跳过数据清洗")
                return df
            
            # 获取处理配置
            config = ConfigMapper.get_processing_config(file_type)
            
            if not config.get("enable_default_cleaning", True):
                logger.debug(f"ConfigMapper: 文件类型 '{file_type}' 已禁用默认数据清洗")
                return df
            
            df_cleaned = df.copy()
            original_rows = len(df_cleaned)
            
            # 移除完全空白的行
            if config.get("remove_empty_rows", True):
                df_cleaned = df_cleaned.dropna(how='all')
                empty_removed = original_rows - len(df_cleaned)
                if empty_removed > 0:
                    logger.info(f"ConfigMapper: 移除 {empty_removed} 个完全空白行")
            
            # 移除空白字符行
            if config.get("remove_whitespace_rows", True) and not df_cleaned.empty:
                def is_empty_row(row):
                    str_row = row.astype(str)
                    non_nan_values = str_row[str_row != 'nan']
                    if len(non_nan_values) == 0:
                        return True
                    return non_nan_values.str.strip().eq('').all()
                
                empty_mask = df_cleaned.apply(is_empty_row, axis=1)
                df_cleaned = df_cleaned[~empty_mask].copy()  # 确保返回DataFrame
                
                whitespace_removed = len(df_cleaned) - (original_rows - (original_rows - len(df_cleaned)))
                if whitespace_removed > 0:
                    logger.info(f"ConfigMapper: 移除 {abs(whitespace_removed)} 个空白字符行")
            
            final_rows = len(df_cleaned)
            total_removed = original_rows - final_rows
            
            if total_removed > 0:
                logger.info(f"ConfigMapper: 数据清洗完成，从 {original_rows} 行清洗到 {final_rows} 行")
            else:
                logger.debug("ConfigMapper: 数据清洗完成，无行被移除")
            
            # 确保返回的是DataFrame类型
            return df_cleaned if isinstance(df_cleaned, pd.DataFrame) else df
            
        except Exception as e:
            logger.exception(f"ConfigMapper: 数据清洗失败: {str(e)}")
            return df