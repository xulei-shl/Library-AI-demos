"""
二部文件处理器
处理文件名包含"二部"的Excel文件，进行时间筛选
"""
import pandas as pd
from datetime import datetime
from typing import Dict, Optional, Tuple
import re

from .base_processor import BaseProcessor
from ..config.settings import FILE_PATTERNS, BUSINESS_TIME_COLUMN
from ..utils.logger import logger
from ..utils.config_mapper import ConfigMapper


class ErbuProcessor(BaseProcessor):
    """二部文件处理器"""
    
    def _parse_date_robust(self, date_value) -> Optional[Tuple[int, int]]:
        """
        鲁棒的日期解析函数，支持多种日期格式
        
        Args:
            date_value: 日期值（可能是字符串、日期对象、Excel序列号等）
            
        Returns:
            (年, 月) 元组，解析失败返回None
        """
        if pd.isna(date_value):
            return None
        
        # 模式1: Excel序列号格式（数字类型）
        if isinstance(date_value, (int, float)) and not pd.isna(date_value):
            try:
                # Excel序列号转换为日期（Excel起始日期是1900-01-01）
                parsed_date = pd.to_datetime(date_value, origin='1899-12-30', unit='D')
                return (parsed_date.year, parsed_date.month)
            except:
                pass
        
        date_str = str(date_value).strip()
        
        # 模式2: 中文格式 "2025年8月", "2025年08月"
        chinese_pattern = r'(\d{4})年(\d{1,2})月?'
        match = re.search(chinese_pattern, date_str)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            return (year, month)
        
        # 模式3: 标准日期格式，尝试用pandas解析
        try:
            parsed_date = pd.to_datetime(date_value, errors='raise')
            return (parsed_date.year, parsed_date.month)
        except:
            pass
        
        # 模式4: 其他可能的格式 "2025/8", "2025-08"
        slash_pattern = r'(\d{4})[/-](\d{1,2})'
        match = re.search(slash_pattern, date_str)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            return (year, month)
        
        return None
    
    def get_file_type(self) -> str:
        """
        获取文件类型标识符
        
        Returns:
            文件类型标识符
        """
        return 'erbu'
    
    def can_handle(self, filename: str) -> bool:
        """
        判断是否能处理指定的文件
        
        Args:
            filename: 文件名
            
        Returns:
            是否能处理该文件
        """
        pattern = FILE_PATTERNS.get('erbu', '')
        can_handle = pattern in filename
        
        if can_handle:
            logger.info(f"ErbuProcessor: 识别到二部文件: {filename}")
        
        return can_handle
    def process_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理二部文件数据，基于配置筛选当年上个月的记录
        
        Args:
            df: 已经过配置化处理的DataFrame
            
        Returns:
            处理后的DataFrame
        """
        try:
            logger.info("ErbuProcessor: 开始处理二部文件数据")
            
            # 记录原始数据信息
            original_rows = len(df)
            logger.info(f"ErbuProcessor: 原始数据行数: {original_rows}")
            
            # 检查是否启用时间筛选
            config = ConfigMapper.get_processing_config('erbu')
            if not config.get('enable_time_filtering', True):
                logger.info("ErbuProcessor: 时间筛选已禁用，跳过筛选")
                return df
            
            # 检查业务时间列是否存在
            if BUSINESS_TIME_COLUMN not in df.columns:
                logger.warning(f"ErbuProcessor: 未找到业务时间列 '{BUSINESS_TIME_COLUMN}'，跳过时间筛选")
                logger.debug(f"ErbuProcessor: 可用列名: {list(df.columns)}")
                return df
            
            # 获取上个月的年月
            current_date = datetime.now()
            if current_date.month == 1:
                # 当前是1月，上个月是去年12月
                target_year = current_date.year - 1
                target_month = 12
            else:
                # 其他月份，直接减1
                target_year = current_date.year
                target_month = current_date.month - 1
            logger.info(f"ErbuProcessor: 筛选条件 - 上个月: {target_year}年{target_month}月")
            
            # 使用鲁棒的日期解析
            df_copy = df.copy()
            parsed_dates = []
            valid_mask = []
            
            for idx, date_value in enumerate(df_copy[BUSINESS_TIME_COLUMN]):
                parsed = self._parse_date_robust(date_value)
                parsed_dates.append(parsed)
                valid_mask.append(parsed is not None)
                
                # 记录解析结果用于调试
                if idx < 5:  # 只记录前5条
                    if parsed:
                        logger.debug(f"ErbuProcessor: 日期解析成功 '{date_value}' -> {parsed[0]}年{parsed[1]}月")
                    else:
                        logger.debug(f"ErbuProcessor: 日期解析失败 '{date_value}'")
            
            # 统计解析结果
            valid_count = sum(valid_mask)
            invalid_count = len(df_copy) - valid_count
            
            if invalid_count > 0:
                logger.warning(f"ErbuProcessor: 发现 {invalid_count} 条无效日期记录，将被排除")
            
            logger.info(f"ErbuProcessor: 日期解析完成，有效记录: {valid_count}/{len(df_copy)}")
            
            # 应用时间筛选条件
            time_mask = []
            for i, parsed in enumerate(parsed_dates):
                if parsed is None:
                    time_mask.append(False)
                else:
                    year, month = parsed
                    matches = (year == target_year and month == target_month)
                    time_mask.append(matches)
            
            # 筛选数据
            df_filtered = df[time_mask].copy()  # 确保返回DataFrame
            filtered_rows = len(df_filtered)
            
            logger.info(f"ErbuProcessor: 时间筛选完成，从 {original_rows} 行筛选出 {filtered_rows} 行")
            
            if filtered_rows == 0:
                logger.warning("ErbuProcessor: 筛选后无数据，请检查业务时间列格式和当前日期")
                # 显示一些样本数据用于调试
                sample_data = df_copy[BUSINESS_TIME_COLUMN].head(10).tolist()
                logger.debug(f"ErbuProcessor: 样本业务时间数据: {sample_data}")
                
                # 显示解析后的年月分布
                year_month_counts = {}
                for parsed in parsed_dates:
                    if parsed:
                        key = f"{parsed[0]}年{parsed[1]}月"
                        year_month_counts[key] = year_month_counts.get(key, 0) + 1
                
                if year_month_counts:
                    logger.info(f"ErbuProcessor: 数据中的年月分布: {year_month_counts}")
            
            # 确保返回的是DataFrame类型
            return df_filtered if isinstance(df_filtered, pd.DataFrame) else df
            
        except Exception as e:
            logger.exception(f"ErbuProcessor: 数据处理失败: {str(e)}")
            return df