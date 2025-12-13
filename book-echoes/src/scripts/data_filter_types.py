#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全量书目数据过滤脚本 - 数据类型定义

包含配置类和结果类的定义，遵循设计文档规范。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Literal, Optional
import pandas as pd


@dataclass
class InputConfig:
    """输入配置"""
    excel_files: List[str]
    required_columns: List[str]


@dataclass
class FilterConfig:
    """过滤规则配置"""
    call_number_rules: str
    title_keywords_rules: str
    field_mapping: Dict[str, str]
    null_handling: Dict[str, Literal["filter", "keep"]]
    logic: Literal["OR", "AND"]


@dataclass
class OutputConfig:
    """输出配置"""
    output_dir: str
    filename_template: Dict[str, str]
    add_filter_reason: bool
    filter_reason_column: str
    merge_passed_data: bool
    add_source_file_column: bool
    source_file_column: str


@dataclass
class DataFilterConfig:
    """总配置"""
    input: InputConfig
    filters: FilterConfig
    output: OutputConfig
    logging: Dict
    extensions: Dict


@dataclass
class FilterResult:
    """单个文件的过滤结果"""
    source_file: str                    # 来源文件路径
    passed_data: pd.DataFrame           # 符合条件的数据
    filtered_data: pd.DataFrame         # 被过滤的数据
    passed_count: int                   # 符合条件数量
    filtered_count: int                 # 被过滤数量
    filter_reasons: Dict[str, int]      # 过滤原因统计 {"索书号匹配": 10, "题名关键词": 5}


@dataclass
class FilterStatistics:
    """过滤统计信息"""
    total_files: int = 0                # 总处理文件数
    total_rows: int = 0                 # 总数据行数
    total_passed: int = 0               # 符合条件总数
    total_filtered: int = 0             # 被过滤总数
    filter_reason_distribution: Dict[str, int] = field(default_factory=dict)  # 过滤原因分布
    file_statistics: List[Dict[str, int]] = field(default_factory=list)  # 各文件统计
    
    def add_file_result(self, result: FilterResult) -> None:
        """添加单个文件的过滤结果到统计中"""
        self.total_files += 1
        self.total_rows += result.passed_count + result.filtered_count
        self.total_passed += result.passed_count
        self.total_filtered += result.filtered_count
        
        # 累加过滤原因分布
        for reason, count in result.filter_reasons.items():
            if reason in self.filter_reason_distribution:
                self.filter_reason_distribution[reason] += count
            else:
                self.filter_reason_distribution[reason] = count
        
        # 添加文件统计
        total_rows = result.passed_count + result.filtered_count
        pass_rate = (result.passed_count / total_rows * 100) if total_rows > 0 else 0.0
        self.file_statistics.append({
            "文件": result.source_file,
            "总行数": total_rows,
            "符合条件": result.passed_count,
            "被过滤": result.filtered_count,
            "通过率": f"{pass_rate:.1f}%"
        })
    
    def get_passed_rate(self) -> float:
        """获取通过率"""
        if self.total_rows == 0:
            return 0.0
        return (self.total_passed / self.total_rows) * 100
    
    def get_summary(self) -> str:
        """获取统计摘要"""
        return (
            f"总处理文件数: {self.total_files}\n"
            f"总数据行数: {self.total_rows}\n"
            f"符合条件: {self.total_passed} ({self.get_passed_rate():.1f}%)\n"
            f"被过滤: {self.total_filtered} ({100 - self.get_passed_rate():.1f}%)"
        )