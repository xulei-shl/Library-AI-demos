"""
数据合并核心模块
负责数据对齐、合并和格式转换
"""
import pandas as pd
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from ..utils.logger import logger
from ..utils.excel_utils import ExcelUtils
from ..config.settings import (
    TARGET_FILE_PATH, EXCEL_SHEET_NAME, 
    BUSINESS_TIME_COLUMN, BUSINESS_TIME_FORMAT, STATISTICS_CONFIG
)


class DataMerger:
    """数据合并器"""
    
    def __init__(self):
        self.target_file_path = Path(TARGET_FILE_PATH)
        logger.debug("DataMerger: 初始化数据合并器")
    
    def get_target_columns(self) -> Optional[List[str]]:
        """
        获取目标文件的列结构（原始列名）
        
        Returns:
            目标文件的原始列名列表，如果获取失败返回None
        """
        try:
            logger.info(f"DataMerger: 获取目标文件列结构: {self.target_file_path}")
            
            if not self.target_file_path.exists():
                logger.error(f"DataMerger: 目标文件不存在: {self.target_file_path}")
                return None
            
            columns = ExcelUtils.get_excel_columns(self.target_file_path, EXCEL_SHEET_NAME)
            if columns:
                logger.info(f"DataMerger: 目标文件列数: {len(columns)}")
                logger.debug(f"DataMerger: 目标文件列名: {columns}")
            
            return columns
            
        except Exception as e:
            logger.exception(f"DataMerger: 获取目标文件列结构失败: {str(e)}")
            return None
    
    def align_columns_by_position(self, source_df: pd.DataFrame, target_columns: List[str], file_type: str = 'default') -> pd.DataFrame:
        """
        基于列位置进行数据对齐，支持位置映射
        
        Args:
            source_df: 源数据DataFrame
            target_columns: 目标文件的原始列名列表
            file_type: 文件类型，用于确定特殊映射规则
            
        Returns:
            对齐后的DataFrame
        """
        try:
            logger.info(f"DataMerger: 开始基于位置的列对齐处理 - 文件类型: {file_type}")
            
            aligned_df = pd.DataFrame()
            matched_columns = 0
            missing_columns = []
            
            # 获取源文件的列名
            source_columns = list(source_df.columns)
            logger.debug(f"DataMerger: 源数据列名: {source_columns}")
            logger.debug(f"DataMerger: 目标数据列名: {target_columns}")
            
            # 特殊处理：I列（索引8）的位置映射
            for i, target_col in enumerate(target_columns):
                source_col = None
                
                # 检查是否是目标文件的第I列（索引8）
                if i == 8:  # I列位置
                    logger.debug(f"DataMerger: 处理目标I列位置 (索引8): {target_col}")
                    
                    # 根据文件类型确定源列
                    if file_type == 'yibu':
                        # 一部：源文件的I列（索引8）-> 目标文件的I列（索引8）
                        if len(source_columns) > 8:
                            source_col = source_columns[8]
                            logger.info(f"DataMerger: 一部文件 - 源I列({source_col}) -> 目标I列({target_col})")
                    elif file_type == 'erbu':
                        # 二部：源文件的H列（索引7）-> 目标文件的I列（索引8）
                        if len(source_columns) > 7:
                            source_col = source_columns[7]
                            logger.info(f"DataMerger: 二部文件 - 源H列({source_col}) -> 目标I列({target_col})")
                    elif file_type == 'sanbu':
                        # 三部：源文件的"数量"列 -> 目标文件的I列（索引8）
                        if '数量' in source_columns:
                            source_col = '数量'
                            logger.info(f"DataMerger: 三部文件 - 源数量列 -> 目标I列({target_col})")
                else:
                    # 非I列位置，尝试按列名匹配
                    if target_col in source_columns:
                        source_col = target_col
                        logger.debug(f"DataMerger: 列名直接匹配: {source_col} -> {target_col}")
                
                # 复制数据
                if source_col and source_col in source_df.columns:
                    aligned_df[target_col] = source_df[source_col].copy()
                    matched_columns += 1
                    logger.debug(f"DataMerger: 列映射成功: {source_col} -> {target_col}")
                else:
                    aligned_df[target_col] = None
                    missing_columns.append(target_col)
                    logger.debug(f"DataMerger: 列缺失: {target_col}")
            
            logger.info(f"DataMerger: 基于位置的列对齐完成 - 匹配: {matched_columns}, 缺失: {len(missing_columns)}")
            if missing_columns:
                logger.debug(f"DataMerger: 缺失的列: {missing_columns}")
            
            return aligned_df
            
        except Exception as e:
            logger.exception(f"DataMerger: 基于位置的列对齐失败: {str(e)}")
            return source_df
        """
        将源数据按目标文件的列结构对齐（基于动态映射匹配，保持目标列名）
        
        Args:
            source_df: 源数据DataFrame
            target_columns: 目标文件的原始列名列表
            
        Returns:
            对齐后的DataFrame
        """
        try:
            logger.info("DataMerger: 开始列对齐处理")
            
            # 对源数据和目标数据的列名都应用动态映射
            source_columns = list(source_df.columns)
            mapped_source_columns = ExcelUtils.apply_column_mapping(source_columns, 'default')
            mapped_target_columns = ExcelUtils.apply_column_mapping(target_columns, 'default')
            
            logger.debug(f"DataMerger: 源数据原始列名: {source_columns}")
            logger.debug(f"DataMerger: 源数据映射后列名: {mapped_source_columns}")
            logger.debug(f"DataMerger: 目标数据原始列名: {target_columns}")
            logger.debug(f"DataMerger: 目标数据映射后列名: {mapped_target_columns}")
            
            # 创建源列名映射字典：映射后列名 -> 原始列名
            source_mapping = {}
            for original, mapped in zip(source_columns, mapped_source_columns):
                if mapped not in source_mapping:
                    source_mapping[mapped] = original
                else:
                    # 如果有多个原始列映射到同一个标准列名，记录警告
                    logger.warning(f"DataMerger: 多个源列映射到同一标准列名 '{mapped}': {source_mapping[mapped]}, {original}")
            
            aligned_df = pd.DataFrame()
            matched_columns = 0
            missing_columns = []
            
            # 按目标文件的列顺序创建新DataFrame，使用目标文件的原始列名
            for i, target_col in enumerate(target_columns):
                mapped_target_col = mapped_target_columns[i]
                
                if mapped_target_col in source_mapping:
                    # 找到匹配的源列，使用原始列名获取数据，但保持目标列的原始名称
                    original_source_col = source_mapping[mapped_target_col]
                    aligned_df[target_col] = source_df[original_source_col]
                    matched_columns += 1
                    logger.debug(f"DataMerger: 列匹配成功: {original_source_col} -> {target_col} (通过映射: {mapped_target_col})")
                else:
                    aligned_df[target_col] = None
                    missing_columns.append(target_col)
            
            logger.info(f"DataMerger: 列对齐完成 - 匹配: {matched_columns}, 缺失: {len(missing_columns)}")
            if missing_columns:
                logger.debug(f"DataMerger: 缺失的列: {missing_columns}")
            
            return aligned_df
            
        except Exception as e:
            logger.exception(f"DataMerger: 列对齐失败: {str(e)}")
            return source_df
    
    def format_business_time_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        将业务时间列设置为脚本运行时的上个月
        
        Args:
            df: 要处理的DataFrame
            
        Returns:
            格式转换后的DataFrame
        """
        try:
            # 使用回退机制查找业务时间列
            business_time_col = ExcelUtils.find_column_by_name_or_letter(
                df,
                STATISTICS_CONFIG['business_time_column'],
                STATISTICS_CONFIG.get('business_time_column_letter')
            )
            
            if not business_time_col:
                logger.debug(f"DataMerger: 未找到业务时间列 '{STATISTICS_CONFIG['business_time_column']}'，跳过格式转换")
                return df
            
            logger.info("DataMerger: 开始设置业务时间为上个月")
            
            df_copy = df.copy()
            
            # 获取当前日期
            now = datetime.now()
            
            # 计算上个月，正确处理跨年情况
            if now.month == 1:
                # 如果是1月，上个月是去年12月
                prev_month = 12
                prev_year = now.year - 1
            else:
                # 其他月份，直接减1
                prev_month = now.month - 1
                prev_year = now.year
            
            # 格式化为 "YYYY年M月" 文本格式
            business_time_text = f"{prev_year}年{prev_month}月"
            
            # 将业务时间列的所有行都赋值为上个月
            df_copy[business_time_col] = business_time_text
            
            logger.info(f"DataMerger: 业务时间已设置为 '{business_time_text}'，共 {len(df_copy)} 条记录")
            
            return df_copy
            
        except Exception as e:
            logger.exception(f"DataMerger: 业务时间设置失败: {str(e)}")
            return df
    
    def merge_data(self, processed_data_list: List[tuple]) -> Optional[pd.DataFrame]:
        """
        合并多个处理后的DataFrame
        
        Args:
            processed_data_list: 包含(DataFrame, file_type)元组的列表
            
        Returns:
            合并后的DataFrame，如果合并失败返回None
        """
        try:
            if not processed_data_list:
                logger.warning("DataMerger: 没有数据需要合并")
                return None
            
            logger.info(f"DataMerger: 开始合并 {len(processed_data_list)} 个数据集")
            
            # 获取目标文件列结构
            target_columns = self.get_target_columns()
            if not target_columns:
                logger.error("DataMerger: 无法获取目标文件列结构，合并失败")
                return None
            
            aligned_data_list = []
            total_rows = 0
            
            # 对每个数据集进行列对齐
            for i, (df, file_type) in enumerate(processed_data_list):
                if df is not None and not df.empty:
                    # 使用基于位置的对齐方法
                    aligned_df = self.align_columns_by_position(df, target_columns, file_type)
                    aligned_data_list.append(aligned_df)
                    total_rows += len(aligned_df)
                    logger.debug(f"DataMerger: 数据集 {i+1} ({file_type}) 对齐完成，行数: {len(aligned_df)}")
            
            if not aligned_data_list:
                logger.warning("DataMerger: 没有有效数据可合并")
                return None
            
            # 合并所有数据
            merged_df = pd.concat(aligned_data_list, ignore_index=True)
            logger.info(f"DataMerger: 数据合并完成，总行数: {len(merged_df)}")
            
            # 格式化业务时间列
            formatted_df = self.format_business_time_column(merged_df)
            
            return formatted_df
            
        except Exception as e:
            logger.exception(f"DataMerger: 数据合并失败: {str(e)}")
            return None
    
    def append_to_target_file(self, merged_df: pd.DataFrame) -> bool:
        """
        将合并后的数据追加到目标文件
        
        Args:
            merged_df: 合并后的DataFrame
            
        Returns:
            是否追加成功
        """
        try:
            if merged_df is None or merged_df.empty:
                logger.warning("DataMerger: 没有数据需要追加到目标文件")
                return False
            
            logger.info(f"DataMerger: 开始追加数据到目标文件，行数: {len(merged_df)}")
            
            # 追加数据到目标文件
            success = ExcelUtils.append_to_excel_file(
                merged_df, 
                self.target_file_path, 
                EXCEL_SHEET_NAME
            )
            
            if success:
                logger.info("DataMerger: 数据追加成功")
            else:
                logger.error("DataMerger: 数据追加失败")
            
            return success
            
        except Exception as e:
            logger.exception(f"DataMerger: 追加数据到目标文件失败: {str(e)}")
            return False