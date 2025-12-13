#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全量书目数据过滤脚本 - 数据过滤引擎

负责应用过滤规则到数据，并生成过滤结果。
复用现有的 CallNumberMatcher 和 TitleKeywordsMatcher 组件。
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from src.utils.logger import get_logger
from src.utils.rule_file_parser import (
    CallNumberMatcher, 
    TitleKeywordsMatcher,
    RuleFileParser
)
from src.scripts.data_filter_types import (
    DataFilterConfig, 
    FilterResult
)

logger = get_logger(__name__)


class DataFilterEngine:
    """数据过滤引擎"""
    
    def __init__(self, config: DataFilterConfig):
        """
        初始化过滤引擎
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.logger = get_logger(__name__)
        
        # 加载过滤规则
        self.call_number_matcher = CallNumberMatcher(
            RuleFileParser.load_call_number_rules(config.filters.call_number_rules)
        )
        self.title_matcher = TitleKeywordsMatcher(
            RuleFileParser.load_title_keywords(config.filters.title_keywords_rules)
        )
        
        self.logger.info(f"初始化过滤引擎完成: {self.call_number_matcher.get_rules_summary()}")
        self.logger.info(f"加载题名关键词: {self.title_matcher.get_keywords_count()} 条")
    
    def process_file(self, excel_path: str) -> FilterResult:
        """
        处理单个 Excel 文件
        
        Args:
            excel_path: Excel 文件路径
            
        Returns:
            FilterResult 过滤结果
        """
        try:
            self.logger.info(f"开始处理文件: {excel_path}")
            
            # 读取 Excel 数据
            df = self._read_excel(excel_path)
            if df is None or df.empty:
                self.logger.warning(f"文件为空或读取失败: {excel_path}")
                return FilterResult(
                    source_file=excel_path,
                    passed_data=pd.DataFrame(),
                    filtered_data=pd.DataFrame(),
                    passed_count=0,
                    filtered_count=0,
                    filter_reasons={"文件为空或读取失败": 1}
                )
            
            self.logger.info(f"读取数据: {len(df)} 行")
            
            # 验证必需列
            if not self._validate_columns(df):
                self.logger.error(f"文件缺少必需列，跳过处理: {excel_path}")
                return FilterResult(
                    source_file=excel_path,
                    passed_data=pd.DataFrame(),
                    filtered_data=pd.DataFrame(),
                    passed_count=0,
                    filtered_count=0,
                    filter_reasons={"文件缺少必需列": 1}
                )
            
            # 应用过滤规则
            filter_mask, filter_reasons = self._apply_filters(df)
            
            # 添加过滤原因列
            filtered_df = self._add_filter_reason_column(df, filter_reasons)
            
            # 分离数据
            passed_df = df[~filter_mask].copy()  # 符合条件的数据
            filtered_df = filtered_df[filter_mask].copy()  # 被过滤的数据
            
            # 统计过滤原因
            reason_counts = self._count_filter_reasons(filter_reasons[filter_mask])
            
            result = FilterResult(
                source_file=excel_path,
                passed_data=passed_df,
                filtered_data=filtered_df,
                passed_count=len(passed_df),
                filtered_count=len(filtered_df),
                filter_reasons=reason_counts
            )
            
            self.logger.info(f"过滤结果: 符合条件 {result.passed_count} 行, 被过滤 {result.filtered_count} 行")
            return result
            
        except Exception as e:
            # 捕获所有未处理的异常，确保程序不会因单个文件处理失败而中断
            self.logger.error(f"处理文件时发生未预期的错误: {excel_path}, 错误: {e}")
            import traceback
            self.logger.debug(f"错误详情: {traceback.format_exc()}")
            
            return FilterResult(
                source_file=excel_path,
                passed_data=pd.DataFrame(),
                filtered_data=pd.DataFrame(),
                passed_count=0,
                filtered_count=0,
                filter_reasons={"处理过程中发生错误": 1}
            )
    
    def _read_excel(self, excel_path: str) -> Optional[pd.DataFrame]:
        """读取 Excel 文件"""
        try:
            file_path = Path(excel_path)
            if not file_path.exists():
                self.logger.warning(f"文件不存在: {excel_path}")
                return None
            
            # 使用 pandas 读取 Excel
            df = pd.read_excel(excel_path)
            return df
        except Exception as e:
            self.logger.error(f"读取 Excel 文件失败: {excel_path}, 错误: {e}")
            return None
    
    def _validate_columns(self, df: pd.DataFrame) -> bool:
        """验证必需列是否存在"""
        required_columns = self.config.input.required_columns
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            self.logger.error(f"缺少必需列: {missing_columns}")
            return False
        
        return True
    
    def _apply_filters(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """
        应用过滤规则
        
        Args:
            df: 输入 DataFrame
            
        Returns:
            (filter_mask, filter_reasons) 过滤掩码和原因
        """
        try:
            # 获取字段映射
            call_number_col = self.config.filters.field_mapping.get("call_number", "索书号")
            title_col = self.config.filters.field_mapping.get("title", "题名")
            
            # 检查列是否存在
            if call_number_col not in df.columns:
                self.logger.warning(f"数据中不存在索书号列: {call_number_col}")
                call_number_col = None
            if title_col not in df.columns:
                self.logger.warning(f"数据中不存在题名列: {title_col}")
                title_col = None
            
            # 初始化过滤掩码和原因
            filter_mask = pd.Series(False, index=df.index)
            filter_reasons = pd.Series("", index=df.index)
            
            # 1. 处理空值
            if call_number_col and title_col:
                null_mask, null_reasons = self._handle_null_values(df, call_number_col, title_col)
                filter_mask |= null_mask
                filter_reasons = self._merge_reasons(filter_reasons, null_reasons)
            
            # 2. 应用索书号规则
            if call_number_col and self.call_number_matcher.has_rules:
                try:
                    call_number_mask = self.call_number_matcher.apply(df[call_number_col])
                    call_number_reasons = pd.Series(
                        f"索书号匹配排除规则",
                        index=df.index
                    )
                    filter_mask |= call_number_mask
                    filter_reasons = self._merge_reasons(filter_reasons, call_number_reasons, call_number_mask)
                except Exception as e:
                    self.logger.error(f"应用索书号规则时出错: {e}")
            
            # 3. 应用题名关键词规则
            if title_col and self.title_matcher.has_keywords:
                try:
                    title_mask = self.title_matcher.apply(df[title_col])
                    title_reasons = pd.Series(
                        f"题名包含排除关键词",
                        index=df.index
                    )
                    filter_mask |= title_mask
                    filter_reasons = self._merge_reasons(filter_reasons, title_reasons, title_mask)
                except Exception as e:
                    self.logger.error(f"应用题名关键词规则时出错: {e}")
            
            return filter_mask, filter_reasons
            
        except Exception as e:
            self.logger.error(f"应用过滤规则时发生错误: {e}")
            # 返回空过滤结果，确保所有数据都通过
            return pd.Series(False, index=df.index), pd.Series("", index=df.index)
    
    def _handle_null_values(self, df: pd.DataFrame, call_number_col: str, title_col: str) -> Tuple[pd.Series, pd.Series]:
        """处理空值"""
        null_mask = pd.Series(False, index=df.index)
        null_reasons = pd.Series("", index=df.index)
        
        # 处理索书号为空
        if self.config.filters.null_handling.get("call_number") == "filter":
            call_number_null_mask = df[call_number_col].isna() | (df[call_number_col] == "")
            null_mask |= call_number_null_mask
            null_reasons = self._merge_reasons(null_reasons, pd.Series("索书号为空", index=df.index), call_number_null_mask)
        
        # 处理题名为空
        if self.config.filters.null_handling.get("title") == "filter":
            title_null_mask = df[title_col].isna() | (df[title_col] == "")
            null_mask |= title_null_mask
            null_reasons = self._merge_reasons(null_reasons, pd.Series("题名为空", index=df.index), title_null_mask)
        
        return null_mask, null_reasons
    
    def _merge_reasons(self, base_reasons: pd.Series, new_reasons: pd.Series, mask: Optional[pd.Series] = None) -> pd.Series:
        """合并过滤原因"""
        if mask is None:
            mask = pd.Series(True, index=base_reasons.index)
        
        merged = base_reasons.copy()
        for idx in merged.index:
            if mask[idx]:
                if merged[idx] and new_reasons[idx]:
                    merged[idx] = f"{merged[idx]}; {new_reasons[idx]}"
                elif new_reasons[idx]:
                    merged[idx] = new_reasons[idx]
        
        return merged
    
    def _add_filter_reason_column(self, df: pd.DataFrame, reasons: pd.Series) -> pd.DataFrame:
        """添加过滤原因列"""
        result_df = df.copy()
        if self.config.output.add_filter_reason:
            result_df[self.config.output.filter_reason_column] = reasons
        return result_df
    
    def _count_filter_reasons(self, reasons: pd.Series) -> Dict[str, int]:
        """统计过滤原因"""
        reason_counts = {}
        
        for reason in reasons:
            if not reason:
                continue
                
            # 分割多个原因
            for part in reason.split(";"):
                part = part.strip()
                if part:
                    if part in reason_counts:
                        reason_counts[part] += 1
                    else:
                        reason_counts[part] = 1
        
        return reason_counts