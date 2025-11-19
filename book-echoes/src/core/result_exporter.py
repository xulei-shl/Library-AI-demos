"""
结果输出器

生成结构化的分析结果Excel文件，包含多工作表支持和格式化，
保持原始数据的完整性，添加统计摘要和可视化信息。
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import os

from src.utils.logger import get_logger
from src.core.statistics import BorrowingStatistics

logger = get_logger(__name__)


class ResultExporter:
    """结果导出器类"""
    
    def __init__(self, output_dir: str = "runtime/outputs"):
        """
        初始化结果导出器
        
        Args:
            output_dir: 输出目录路径
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成时间戳
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        logger.info(f"结果导出器初始化完成，输出目录: {self.output_dir}")
    
    def export_to_excel(self, 
                       data: pd.DataFrame,
                       filename: Optional[str] = None,
                       include_summary: bool = True,
                       include_statistics: bool = True) -> str:
        """
        导出数据到Excel文件
        
        Args:
            data: 要导出的数据
            filename: 文件名，None则自动生成
            include_summary: 是否包含摘要工作表
            include_statistics: 是否包含统计工作表
            
        Returns:
            str: 导出的文件路径
        """
        if filename is None:
            filename = f"月归还数据统计结果_{self.timestamp}.xlsx"
        
        file_path = self.output_dir / filename
        
        logger.info(f"开始导出Excel文件: {file_path}")
        
        try:
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # 主数据工作表
                self._write_main_data_sheet(data, writer)
                
                # 统计摘要工作表
                if include_summary:
                    self._write_summary_sheet(data, writer)
                
                # 详细统计工作表
                if include_statistics:
                    self._write_statistics_sheet(data, writer)
                
                # 处理信息工作表
                self._write_process_info_sheet(writer)
            
            logger.info(f"Excel文件导出成功: {file_path}")
            return str(file_path)
            
        except Exception as e:
            error_msg = f"导出Excel文件失败: {str(e)}"
            logger.error(error_msg, extra={"file_path": str(file_path)})
            raise ValueError(error_msg) from e
    
    def export_filtered_out_data(self, 
                                filtered_out_data: pd.DataFrame,
                                filter_results: Dict[str, Any],
                                filename: Optional[str] = None) -> str:
        """
        导出被过滤掉的数据到独立的Excel文件
        
        Args:
            filtered_out_data: 被过滤掉的数据
            filter_results: 各筛选器的结果信息
            filename: 文件名，None则自动生成
            
        Returns:
            str: 导出的文件路径
        """
        if filename is None:
            filename = f"被过滤数据_{self.timestamp}.xlsx"
        
        file_path = self.output_dir / filename
        
        logger.info(f"开始导出被过滤数据Excel文件: {file_path}")
        
        if filtered_out_data.empty:
            # 如果没有被过滤的数据，创建一个包含说明的空文件
            try:
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    empty_data = pd.DataFrame([["没有数据被过滤", ""]], columns=['说明', '详情'])
                    empty_data.to_excel(writer, sheet_name='被过滤数据', index=False)
                    self._write_filtered_data_info_sheet(filter_results, writer)
                
                logger.info(f"被过滤数据Excel文件导出成功（无数据）: {file_path}")
                return str(file_path)
            except Exception as e:
                error_msg = f"导出被过滤数据Excel文件失败: {str(e)}"
                logger.error(error_msg, extra={"file_path": str(file_path)})
                raise ValueError(error_msg) from e
        
        try:
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # 被过滤数据工作表
                self._write_filtered_out_data_sheet(filtered_out_data, writer)
                
                # 过滤信息工作表
                self._write_filtered_data_info_sheet(filter_results, writer)
                
                # 处理信息工作表
                self._write_process_info_sheet(writer)
            
            logger.info(f"被过滤数据Excel文件导出成功: {file_path}")
            return str(file_path)
            
        except Exception as e:
            error_msg = f"导出被过滤数据Excel文件失败: {str(e)}"
            logger.error(error_msg, extra={"file_path": str(file_path)})
            raise ValueError(error_msg) from e
    
    def _write_filtered_out_data_sheet(self, data: pd.DataFrame, writer):
        """写入被过滤数据工作表"""
        # 确保有过滤时间戳（从data_filter.py添加的列）
        final_data = data.copy()
        
        # 重新排列列顺序，将关键列放在前面
        key_columns = ['索书号', '清理后索书号', '题名', '过滤原因', '过滤时间']
        ordered_columns = []
        
        # 添加关键列
        for col in key_columns:
            if col in final_data.columns:
                ordered_columns.append(col)
        
        # 添加剩余列
        for col in final_data.columns:
            if col not in ordered_columns:
                ordered_columns.append(col)
        
        # 重新排列所有列
        available_columns = [col for col in ordered_columns if col in final_data.columns]
        final_data = final_data[available_columns]
        
        final_data.to_excel(writer, sheet_name='被过滤数据', index=False)
        
        logger.info(f"被过滤数据工作表写入完成，包含 {len(final_data)} 行 x {len(available_columns)} 列")
        
        # 打印列信息用于调试
        logger.info(f"被过滤数据包含列: {available_columns}")
        if '过滤原因' in available_columns:
            logger.info("✅ 成功包含过滤原因列")
        else:
            logger.warning("⚠️ 未找到过滤原因列")
    
    def _write_filtered_data_info_sheet(self, filter_results: Dict[str, Any], writer):
        """写入过滤信息工作表"""
        filter_info = []
        filter_info.append(['=== 过滤信息概览 ===', ''])
        filter_info.append(['过滤时间', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        filter_info.append(['过滤模块', '智能降噪筛选器（最终版）'])
        filter_info.append(['', ''])
        
        # 统计各筛选器结果
        filter_info.append(['=== 各筛选器执行结果 ===', ''])
        for filter_name, result in filter_results.items():
            status = result.get('status', 'unknown')
            excluded_count = result.get('excluded_count', 0)
            description = result.get('description', 'N/A')
            
            status_icon = "✅" if status == 'completed' else "❌" if status == 'error' else "⚠️"
            filter_info.append([f'{status_icon} {filter_name}', ''])
            filter_info.append(['  描述', description])
            filter_info.append(['  排除数量', f'{excluded_count} 条记录'])
            
            if result.get('patterns_count'):
                filter_info.append(['  模式数量', str(result['patterns_count'])])
            
            if result.get('target_column'):
                filter_info.append(['  目标列', result['target_column']])
            
            if result.get('threshold'):
                filter_info.append(['  筛选阈值', str(result['threshold'])])
            
            if result.get('excluded_ratio'):
                filter_info.append(['  排除比例', f"{result['excluded_ratio']:.2%}"])
            
            filter_info.append(['', ''])
        
        # 总体统计
        filter_info.append(['=== 总体统计 ===', ''])
        total_excluded = sum(result.get('excluded_count', 0) for result in filter_results.values())
        filter_info.append(['总排除数量', f'{total_excluded} 条记录'])
        
        # 排除原因分析（如果有足够信息）
        filter_info.append(['', ''])
        filter_info.append(['=== 排除原因分析 ===', ''])
        for filter_name, result in filter_results.items():
            if result.get('excluded_count', 0) > 0:
                filter_info.append([f'{filter_name}', f"{result['excluded_count']} 条记录被此筛选器排除"])
        
        info_df = pd.DataFrame(filter_info, columns=['项目', '值'])
        info_df.to_excel(writer, sheet_name='过滤信息', index=False)
        
        logger.info("过滤信息工作表写入完成")
    
    def _write_main_data_sheet(self, data: pd.DataFrame, writer):
        """写入主数据工作表"""
        # 选择要显示的列，原始列优先，统计列在后
        original_columns = [col for col in data.columns if col not in BorrowingStatistics().new_columns]
        statistic_columns = [col for col in data.columns if col in BorrowingStatistics().new_columns]
        
        # 确保索书号相关列在前面
        key_columns = ['索书号', '清理后索书号', '题名']
        ordered_columns = []
        
        for col in key_columns:
            if col in original_columns:
                ordered_columns.append(col)
                original_columns.remove(col)
        
        # 添加其余原始列
        ordered_columns.extend(original_columns)
        # 最后添加统计列
        ordered_columns.extend(statistic_columns)
        
        # 重新排列数据
        available_columns = [col for col in ordered_columns if col in data.columns]
        final_data = data[available_columns].copy()
        
        # 写入主数据工作表
        final_data.to_excel(writer, sheet_name='主数据', index=False)
        
        logger.info(f"主数据工作表写入完成，包含 {len(final_data)} 行 x {len(available_columns)} 列")
    
    def _write_summary_sheet(self, data: pd.DataFrame, writer):
        """写入统计摘要工作表"""
        # 获取统计摘要
        calculator = BorrowingStatistics()
        summary = calculator.get_statistics_summary(data)
        
        # 创建摘要数据
        summary_data = []
        
        # 基本信息
        summary_data.append(['=== 基本信息 ===', ''])
        for key, value in summary.items():
            if key == "统计数据":
                continue
            summary_data.append([key, str(value)])
        
        # 统计数据
        if "统计数据" in summary:
            summary_data.append(['', ''])
            summary_data.append(['=== 统计数据 ===', ''])
            for col_name, col_stats in summary["统计数据"].items():
                summary_data.append([f'{col_name}:', ''])
                for stat_key, stat_value in col_stats.items():
                    summary_data.append([f'  {stat_key}', str(stat_value)])
                summary_data.append(['', ''])
        
        # 创建DataFrame并写入
        summary_df = pd.DataFrame(summary_data, columns=['项目', '值'])
        summary_df.to_excel(writer, sheet_name='统计摘要', index=False)
        
        logger.info("统计摘要工作表写入完成")
    
    def _write_statistics_sheet(self, data: pd.DataFrame, writer):
        """写入详细统计工作表"""
        # 按索书号分组的详细统计
        if '清理后索书号' in data.columns and '近三个月总次数' in data.columns:
            # 索书号级别统计
            call_number_stats = data.groupby('清理后索书号').agg({
                '近三个月总次数': 'first',
                '第一个月借阅次数': 'first',
                '第二个月借阅次数': 'first',
                '第三个月借阅次数': 'first',
                '借阅人数': 'first',  # 借阅人数
                '索书号': 'count'  # 原始记录数
            }).rename(columns={'索书号': '原始记录数'}).reset_index()
            
            # 按总借阅次数降序排序
            call_number_stats = call_number_stats.sort_values('近三个月总次数', ascending=False)
            
            call_number_stats.to_excel(writer, sheet_name='索书号统计', index=False)
            
            # 借阅次数分布统计
            if '近三个月总次数' in data.columns:
                distribution_stats = data['近三个月总次数'].value_counts().sort_index().reset_index()
                distribution_stats.columns = ['借阅次数', '索书号数量']
                distribution_stats.to_excel(writer, sheet_name='次数分布', index=False)
            
            logger.info("详细统计工作表写入完成")
    
    def _write_process_info_sheet(self, writer):
        """写入处理信息工作表"""
        process_info = [
            ['=== 数据处理信息 ===', ''],
            ['处理时间', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['处理模块', '智能降噪筛选器（最终版）'],
            ['版本', 'v2.0.0'],
            ['', ''],
            ['=== 处理步骤 ===', ''],
            ['1. 数据加载', '读取原始数据文件'],
            ['2. 数据清洗', '筛选中文图书，标准化索书号'],
            ['3. 智能筛选', '应用多个筛选规则进行数据过滤'],
            ['4. 结果输出', '生成筛选后数据和被过滤数据'],
            ['', ''],
            ['=== 新增功能 ===', ''],
            ['被过滤数据导出', '将所有被过滤的记录保存到独立Excel文件'],
            ['过滤原因记录', '每条被过滤的数据都记录具体的过滤原因'],
            ['过滤信息记录', '详细记录每个筛选器的执行情况'],
            ['排除原因分析', '分析数据被排除的具体原因'],
            ['', ''],
            ['=== 筛选规则说明 ===', ''],
            ['规则A', '热门书排除（借阅≥阈值次数）'],
            ['规则B-题名', '题名关键词排除'],
            ['规则B-索书号', '索书号和CLC号模式排除'],
            ['规则C-附加信息', '附加信息9位数字格式校验'],
            ['规则C-备注', '备注列排除指定关键词'],
            ['规则C-类型', '类型/册数列排除指定内容'],
            ['', ''],
            ['=== 筛选器类型说明 ===', ''],
            ['热门图书筛选', '根据借阅频率筛选热门图书'],
            ['题名关键词筛选', '根据题名包含的关键词进行筛选'],
            ['索书号筛选', '根据索书号模式进行筛选'],
            ['列值筛选', '根据特定列的值范围进行筛选']
        ]
        
        info_df = pd.DataFrame(process_info, columns=['项目', '说明'])
        info_df.to_excel(writer, sheet_name='处理信息', index=False)
        
        logger.info("处理信息工作表写入完成")
    
    def export_summary_report(self, data: pd.DataFrame, output_file: Optional[str] = None) -> str:
        """
        导出摘要报告
        
        Args:
            data: 处理后的数据
            output_file: 输出文件路径
            
        Returns:
            str: 导出的文件路径
        """
        if output_file is None:
            output_file = self.output_dir / f"月归还数据统计报告_{self.timestamp}.txt"
        
        try:
            calculator = BorrowingStatistics()
            summary = calculator.get_statistics_summary(data)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=" * 50 + "\n")
                f.write("月归还数据统计分析报告\n")
                f.write("=" * 50 + "\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"数据总量: {summary.get('数据总量', 0)} 条记录\n")
                f.write("\n")
                
                # 基本统计
                f.write("1. 基本统计信息\n")
                f.write("-" * 30 + "\n")
                for key, value in summary.items():
                    if key == "统计数据":
                        continue
                    f.write(f"{key}: {value}\n")
                
                # 统计数据
                if "统计数据" in summary:
                    f.write("\n2. 详细统计数据\n")
                    f.write("-" * 30 + "\n")
                    for col_name, col_stats in summary["统计数据"].items():
                        f.write(f"\n{col_name}:\n")
                        for stat_key, stat_value in col_stats.items():
                            f.write(f"  {stat_key}: {stat_value}\n")
                
                # 借阅次数分布
                if "借阅次数分布" in summary:
                    f.write("\n3. 借阅次数分布（前10）\n")
                    f.write("-" * 30 + "\n")
                    for times, count in summary["借阅次数分布"].items():
                        f.write(f"借阅{times}次: {count}个索书号\n")
            
            logger.info(f"摘要报告导出成功: {output_file}")
            return str(output_file)
            
        except Exception as e:
            error_msg = f"导出摘要报告失败: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
    
    def get_output_files(self) -> List[str]:
        """
        获取所有输出文件列表
        
        Returns:
            List[str]: 输出文件路径列表
        """
        if not self.output_dir.exists():
            return []
        
        files = []
        for file_path in self.output_dir.glob("*"):
            if file_path.is_file():
                files.append(str(file_path))
        
        return sorted(files)


def export_borrowing_analysis_results(data: pd.DataFrame,
                                     output_dir: str = "runtime/outputs") -> Dict[str, str]:
    """
    便捷函数：导出借阅分析结果
    
    Args:
        data: 处理后的数据
        output_dir: 输出目录
        
    Returns:
        Dict[str, str]: 输出文件字典 {'excel': Excel文件路径, 'report': 报告文件路径}
    """
    exporter = ResultExporter(output_dir)
    
    # 导出Excel文件
    excel_file = exporter.export_to_excel(data)
    
    # 导出摘要报告
    report_file = exporter.export_summary_report(data)
    
    return {
        'excel': excel_file,
        'report': report_file
    }


if __name__ == "__main__":
    # 测试结果导出器
    from src.core.data_loader import load_monthly_return_data
    from src.core.data_cleaner import clean_monthly_return_data
    from src.core.statistics import calculate_borrowing_stats
    from src.utils.time_utils import filter_recent_three_months_borrowing_data
    
    try:
        # 加载数据并处理
        print("正在处理数据...")
        original_data = load_monthly_return_data()
        cleaned_data = clean_monthly_return_data(original_data)
        recent_data, _ = filter_recent_three_months_borrowing_data(cleaned_data)
        final_data = calculate_borrowing_stats(recent_data)
        
        print(f"处理完成，数据量: {len(final_data)} 条")
        
        # 导出结果
        print("正在导出结果...")
        output_files = export_borrowing_analysis_results(final_data)
        
        print("导出完成:")
        for file_type, file_path in output_files.items():
            print(f"  {file_type}: {file_path}")
        
        # 列出所有输出文件
        exporter = ResultExporter()
        all_files = exporter.get_output_files()
        print(f"\n输出目录所有文件:")
        for file_path in all_files:
            print(f"  {file_path}")
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")