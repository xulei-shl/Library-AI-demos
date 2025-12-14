#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全量书目数据过滤脚本 - 数据过滤运行器

负责协调整个过滤流程，包括配置加载、文件处理、结果保存和统计输出。
"""

import os
import yaml
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

import pandas as pd

from src.utils.logger import get_logger
from src.scripts.data_filter_types import (
    DataFilterConfig,
    InputConfig,
    FilterConfig,
    OutputConfig,
    FilterResult,
    FilterStatistics
)
from src.scripts.data_filter_engine import DataFilterEngine

logger = get_logger(__name__)


class DataFilterRunner:
    """数据过滤运行器"""
    
    def __init__(self, config_path: str):
        """
        初始化运行器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.engine = DataFilterEngine(self.config)
        self.logger = get_logger(__name__)
        self.statistics = FilterStatistics()
    
    def run(self, 
            output_dir: Optional[str] = None, 
            excel_files: Optional[List[str]] = None,
            log_level: Optional[str] = None) -> None:
        """
        执行完整的过滤流程
        
        Args:
            output_dir: 覆盖配置文件的输出目录
            excel_files: 覆盖配置文件的输入文件列表
            log_level: 覆盖配置文件的日志级别
        """
        # 应用命令行参数覆盖
        if output_dir:
            self.config.output.output_dir = output_dir
        if excel_files:
            self.config.input.excel_files = excel_files
        if log_level:
            # 确保logging配置是字典类型
            if not isinstance(self.config.logging, dict):
                self.config.logging = {}
            self.config.logging['level'] = log_level
        
        self.logger.info("开始数据过滤任务")
        self.logger.info(f"加载配置文件: {self.config}")
        
        # 处理所有文件
        results = self._process_all_files()
        
        # 合并结果
        merged_df = self._merge_results(results) if self.config.output.merge_passed_data else None
        
        # 保存结果
        self._save_results(results, merged_df)
        
        # 生成并保存报告
        self._generate_and_save_report(results, merged_df)
        
        # 输出统计报告
        self._print_statistics()
        
        self.logger.info("数据过滤任务完成")
    
    def _load_config(self, config_path: str) -> DataFilterConfig:
        """加载配置文件"""
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                raise FileNotFoundError(f"配置文件不存在: {config_path}")
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            # 转换为配置对象
            input_config = InputConfig(**config_data['input'])
            filter_config = FilterConfig(**config_data['filters'])
            output_config = OutputConfig(**config_data['output'])
            
            logging_config = config_data.get('logging', {})
            # 确保日志配置是字典类型
            if not isinstance(logging_config, dict):
                logging_config = {}
                
            extensions_config = config_data.get('extensions', {})
            # 确保扩展配置是字典类型
            if not isinstance(extensions_config, dict):
                extensions_config = {}
                
            return DataFilterConfig(
                input=input_config,
                filters=filter_config,
                output=output_config,
                logging=logging_config,
                extensions=extensions_config
            )
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            raise
    
    def _process_all_files(self) -> List[FilterResult]:
        """处理所有文件"""
        results = []
        excel_files = self._resolve_excel_files()
        
        self.logger.info(f"开始处理 {len(excel_files)} 个文件")
        
        for i, excel_file in enumerate(excel_files, 1):
            self.logger.info(f"处理文件 {i}/{len(excel_files)}: {excel_file}")
            
            try:
                result = self.engine.process_file(excel_file)
                results.append(result)
                
                # 添加到统计
                self.statistics.add_file_result(result)
                
                # 保存单个文件结果
                self._save_single_file_result(result)
            except Exception as e:
                # 单个文件处理失败，记录错误但继续处理其他文件
                self.logger.error(f"处理文件失败: {excel_file}, 错误: {e}")
                # 创建一个空的结果对象，确保统计信息正确
                empty_result = FilterResult(
                    source_file=excel_file,
                    passed_data=pd.DataFrame(),
                    filtered_data=pd.DataFrame(),
                    passed_count=0,
                    filtered_count=0,
                    filter_reasons={"处理失败": 1}
                )
                results.append(empty_result)
                self.statistics.add_file_result(empty_result)
        
        return results
    
    def _resolve_excel_files(self) -> List[str]:
        """解析Excel文件列表，支持目录扫描"""
        excel_files = []
        
        for path_str in self.config.input.excel_files:
            path = Path(path_str)
            
            if not path.exists():
                self.logger.warning(f"路径不存在: {path_str}")
                continue
                
            if path.is_file():
                # 直接是文件
                if self._is_excel_file(path):
                    excel_files.append(str(path))
                else:
                    self.logger.warning(f"不是Excel文件: {path_str}")
            elif path.is_dir():
                # 是目录，扫描目录下的所有Excel文件
                if self.config.input.scan_directories:
                    self.logger.info(f"扫描目录: {path_str}")
                    found_files = self._scan_directory_for_excel(path)
                    excel_files.extend(found_files)
                    self.logger.info(f"在目录 {path_str} 中找到 {len(found_files)} 个Excel文件")
                else:
                    self.logger.warning(f"路径是目录但未启用目录扫描: {path_str}")
            else:
                self.logger.warning(f"无效路径: {path_str}")
        
        if not excel_files:
            self.logger.warning("未找到任何可处理的Excel文件")
            
        return excel_files
    
    def _is_excel_file(self, path: Path) -> bool:
        """检查是否为Excel文件"""
        return path.suffix.lower() in ['.xlsx', '.xls']
    
    def _scan_directory_for_excel(self, directory: Path) -> List[str]:
        """扫描目录中的所有Excel文件"""
        excel_files = []
        
        try:
            for file_path in directory.iterdir():
                if file_path.is_file() and self._is_excel_file(file_path):
                    excel_files.append(str(file_path))
        except Exception as e:
            self.logger.error(f"扫描目录失败: {directory}, 错误: {e}")
            
        return excel_files
    
    def _save_single_file_result(self, result: FilterResult) -> None:
        """保存单个文件的过滤结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(self.config.output.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存符合条件的数据
        if not result.passed_data.empty:
            passed_filename = self.config.output.filename_template['passed'].format(timestamp=timestamp)
            passed_path = output_dir / passed_filename
            result.passed_data.to_excel(passed_path, index=False)
            self.logger.info(f"保存符合条件数据: {passed_path}")
        
        # 保存被过滤的数据
        if not result.filtered_data.empty:
            filtered_filename = self.config.output.filename_template['filtered'].format(timestamp=timestamp)
            filtered_path = output_dir / filtered_filename
            result.filtered_data.to_excel(filtered_path, index=False)
            self.logger.info(f"保存被过滤数据: {filtered_path}")
    
    def _merge_results(self, results: List[FilterResult]) -> pd.DataFrame:
        """合并所有符合条件的数据"""
        if not results:
            return pd.DataFrame()
        
        passed_dataframes = []
        for result in results:
            if not result.passed_data.empty:
                df = result.passed_data.copy()
                
                # 添加来源文件列
                if self.config.output.add_source_file_column:
                    df[self.config.output.source_file_column] = Path(result.source_file).name
                
                passed_dataframes.append(df)
        
        if not passed_dataframes:
            self.logger.warning("没有符合条件的数据可合并")
            return pd.DataFrame()
        
        # 合并所有数据
        merged_df = pd.concat(passed_dataframes, ignore_index=True)
        
        # 重命名列名
        column_mapping = {
            '标识号': 'ISBN',
            '题名': '书名'
        }
        
        # 只重命名存在的列
        existing_columns = set(merged_df.columns)
        valid_mapping = {old: new for old, new in column_mapping.items() if old in existing_columns}
        
        if valid_mapping:
            merged_df = merged_df.rename(columns=valid_mapping)
            renamed_columns = ', '.join([f"{old} -> {new}" for old, new in valid_mapping.items()])
            self.logger.info(f"重命名列: {renamed_columns}")
        
        self.logger.info(f"合并所有符合条件数据: {len(merged_df)} 行")
        
        return merged_df
    
    def _save_results(self, results: List[FilterResult], merged_df: Optional[pd.DataFrame]) -> None:
        """保存所有结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(self.config.output.output_dir)
        
        # 保存合并结果
        if merged_df is not None and not merged_df.empty:
            merged_filename = self.config.output.filename_template['merged'].format(timestamp=timestamp)
            merged_path = output_dir / merged_filename
            merged_df.to_excel(merged_path, index=False)
            self.logger.info(f"保存合并结果: {merged_path}")
    
    def _print_statistics(self) -> None:
        """打印统计信息"""
        if not self.config.logging.get('verbose_stats', True):
            return
        
        self.logger.info("\n========== 统计报告 ==========")
        self.logger.info(self.statistics.get_summary())
        
        # 打印过滤原因分布
        if self.statistics.filter_reason_distribution:
            self.logger.info("\n过滤原因分布:")
            total_filtered = self.statistics.total_filtered
            for reason, count in sorted(self.statistics.filter_reason_distribution.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total_filtered * 100) if total_filtered > 0 else 0
                self.logger.info(f"  - {reason}: {count} ({percentage:.1f}%)")
        
        # 打印各文件统计
        if self.config.logging.get('verbose_stats', True) and self.statistics.file_statistics:
            self.logger.info("\n各文件统计:")
            for file_stat in self.statistics.file_statistics:
                self.logger.info(f"  {file_stat}")
        
        self.logger.info("==============================")
    
    def _generate_and_save_report(self, results: List[FilterResult], merged_df: Optional[pd.DataFrame]) -> None:
        """生成并保存详细报告
        
        Args:
            results: 所有文件的过滤结果
            merged_df: 合并后的数据
        """
        try:
            # 生成报告内容
            report_content = self.statistics.generate_report(self._get_config_dict())
            
            # 保存报告到文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path(self.config.output.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            report_filename = f"过滤报告_{timestamp}.txt"
            report_path = output_dir / report_filename
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            self.logger.info(f"过滤报告已保存: {report_path}")
            
        except Exception as e:
            self.logger.error(f"生成或保存报告时出错: {e}")
    
    def _get_config_dict(self) -> Dict:
        """获取配置字典，用于报告生成
        
        Returns:
            Dict: 配置字典
        """
        config_dict = {
            'input': {
                'excel_files': self.config.input.excel_files,
                'required_columns': self.config.input.required_columns,
                'scan_directories': self.config.input.scan_directories
            },
            'filters': {
                'call_number_rules': self.config.filters.call_number_rules,
                'title_keywords_rules': self.config.filters.title_keywords_rules,
                'field_mapping': self.config.filters.field_mapping,
                'null_handling': self.config.filters.null_handling,
                'logic': self.config.filters.logic
            },
            'output': {
                'output_dir': self.config.output.output_dir,
                'merge_passed_data': self.config.output.merge_passed_data,
                'add_source_file_column': self.config.output.add_source_file_column
            }
        }
        
        return config_dict