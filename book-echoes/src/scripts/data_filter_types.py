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
    excel_files: List[str]  # 可以是文件路径或目录路径
    required_columns: List[str]
    scan_directories: bool = False  # 是否扫描目录中的Excel文件


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
    
    def generate_report(self, config: Optional[Dict] = None) -> str:
        """生成详细的过滤报告
        
        Args:
            config: 配置信息，用于报告中显示配置详情
            
        Returns:
            str: 格式化的报告文本
        """
        from datetime import datetime
        import pandas as pd
        
        report = []
        report.append("=" * 60)
        report.append("全量书目数据过滤报告")
        report.append("=" * 60)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 总体统计
        report.append("总体统计:")
        report.append(f"  处理文件数: {self.total_files}")
        report.append(f"  总数据行数: {self.total_rows}")
        report.append(f"  符合条件: {self.total_passed} ({self.get_passed_rate():.1f}%)")
        report.append(f"  被过滤: {self.total_filtered} ({100 - self.get_passed_rate():.1f}%)")
        report.append("")
        
        # 过滤原因分布
        if self.filter_reason_distribution:
            report.append("过滤原因分布:")
            total_filtered = self.total_filtered
            for reason, count in sorted(self.filter_reason_distribution.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total_filtered * 100) if total_filtered > 0 else 0
                report.append(f"  - {reason}: {count} ({percentage:.1f}%)")
            report.append("")
        
        # 各文件统计详情
        if self.file_statistics:
            report.append("各文件处理详情:")
            for file_stat in self.file_statistics:
                file_name = file_stat.get("文件", "未知文件")
                total_rows = file_stat.get("总行数", 0)
                passed_count = file_stat.get("符合条件", 0)
                filtered_count = file_stat.get("被过滤", 0)
                pass_rate = file_stat.get("通过率", "0.0%")
                
                report.append(f"  文件: {file_name}")
                report.append(f"    总行数: {total_rows}")
                report.append(f"    符合条件: {passed_count}")
                report.append(f"    被过滤: {filtered_count}")
                report.append(f"    通过率: {pass_rate}")
                report.append("")
        
        # 配置信息（如果提供）
        if config:
            report.append("配置信息:")
            
            # 输入配置
            input_config = config.get('input', {})
            excel_files = input_config.get('excel_files', [])
            report.append(f"  输入文件数: {len(excel_files)}")
            if len(excel_files) <= 5:  # 只显示前5个文件路径
                for file_path in excel_files:
                    report.append(f"    - {file_path}")
            else:
                for file_path in excel_files[:3]:
                    report.append(f"    - {file_path}")
                report.append(f"    - ... 还有 {len(excel_files) - 3} 个文件")
            
            required_columns = input_config.get('required_columns', [])
            report.append(f"  必需列: {', '.join(required_columns)}")
            
            # 过滤配置
            filters_config = config.get('filters', {})
            call_number_rules = filters_config.get('call_number_rules', '')
            title_keywords_rules = filters_config.get('title_keywords_rules', '')
            
            if call_number_rules:
                report.append(f"  索书号规则文件: {call_number_rules}")
            if title_keywords_rules:
                report.append(f"  题名关键词规则文件: {title_keywords_rules}")
            
            null_handling = filters_config.get('null_handling', {})
            report.append(f"  空值处理: 索书号={null_handling.get('call_number', 'N/A')}, 题名={null_handling.get('title', 'N/A')}")
            report.append(f"  过滤逻辑: {filters_config.get('logic', 'N/A')}")
            
            # 输出配置
            output_config = config.get('output', {})
            output_dir = output_config.get('output_dir', '')
            if output_dir:
                report.append(f"  输出目录: {output_dir}")
            
            merge_passed = output_config.get('merge_passed_data', False)
            add_source = output_config.get('add_source_file_column', False)
            report.append(f"  合并结果: {'是' if merge_passed else '否'}")
            report.append(f"  添加来源文件列: {'是' if add_source else '否'}")
            
            report.append("")
        
        # 报告结束
        report.append("=" * 60)
        
        return "\n".join(report)