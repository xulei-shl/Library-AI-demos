"""
新书零借阅流程管理器

负责协调整个新书零借阅筛选流程。
"""

import time
from pathlib import Path
from datetime import datetime
import pandas as pd
from typing import Optional

from src.utils.logger import get_logger
from src.utils.config_manager import get_config
from src.utils.time_utils import get_timestamp
from src.core.data_loader import load_new_books_data, load_borrowing_data_4months
from src.core.data_filter import BookFilterFinal
from .preprocessor import preprocess_new_books_data
from .filter import ZeroBorrowingFilter

logger = get_logger(__name__)


def run_new_sleeping_pipeline() -> bool:
    """
    运行新书零借阅完整流程
    
    流程步骤：
    1. 加载新书验收数据
    2. 加载近四月借阅数据
    3. 数据预处理（列重命名）
    4. 零借阅筛选
    5. 常规过滤（题名、分类号）
    6. 输出结果
    
    Returns:
        bool: 是否成功
    """
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("开始新书零借阅（睡美人）筛选流程")
    logger.info("=" * 60)
    
    try:
        # 步骤1: 加载新书验收数据
        logger.info("步骤1: 加载新书验收数据")
        new_books_data = load_new_books_data()
        logger.info(f"新书验收数据加载完成: {len(new_books_data)} 条记录")
        
        # 步骤2: 加载近四月借阅数据
        logger.info("步骤2: 加载近四月借阅数据")
        borrowing_data = load_borrowing_data_4months()
        logger.info(f"近四月借阅数据加载完成: {len(borrowing_data)} 条记录")
        
        # 步骤3: 数据预处理
        logger.info("步骤3: 数据预处理（列重命名）")
        preprocessed_data = preprocess_new_books_data(new_books_data)
        logger.info(f"数据预处理完成: {len(preprocessed_data)} 条记录")
        
        # 步骤4: 零借阅筛选
        logger.info("步骤4: 零借阅筛选")
        zero_filter = ZeroBorrowingFilter()
        zero_borrowing_books, borrowed_books, zero_stats = zero_filter.filter_zero_borrowing_books(
            preprocessed_data,
            borrowing_data
        )
        logger.info(f"零借阅筛选完成: {len(zero_borrowing_books)} 条零借阅记录")
        
        # 步骤5: 常规过滤（题名、分类号等）
        logger.info("步骤5: 常规过滤（题名、分类号）")
        filter_engine = BookFilterFinal()
        filtered_data, excluded_data, filter_summary = filter_engine.filter_books(zero_borrowing_books)
        logger.info(f"常规过滤完成: {len(filtered_data)} 条记录通过筛选")
        
        # 步骤6: 输出结果
        logger.info("步骤6: 输出结果")
        output_files = export_new_sleeping_results(
            filtered_data,
            excluded_data,
            borrowed_books,
            zero_stats,
            filter_summary
        )
        
        # 计算处理时间
        end_time = time.time()
        processing_time = end_time - start_time
        
        # 输出最终统计
        logger.info("=" * 60)
        logger.info("新书零借阅筛选流程完成")
        logger.info("=" * 60)
        logger.info(f"处理时间: {processing_time:.2f} 秒")
        logger.info(f"新书验收数据量: {len(new_books_data)} 条")
        logger.info(f"近四月借阅数据量: {len(borrowing_data)} 条")
        logger.info(f"零借阅图书数量: {len(zero_borrowing_books)} 条")
        logger.info(f"常规过滤后数量: {len(filtered_data)} 条")
        logger.info(f"输出文件数量: {len(output_files)} 个")
        
        for file_type, file_path in output_files.items():
            logger.info(f"  {file_type}: {file_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"新书零借阅筛选流程失败: {str(e)}", exc_info=True)
        return False


def export_new_sleeping_results(
    filtered_data: pd.DataFrame,
    excluded_data: pd.DataFrame,
    borrowed_books: pd.DataFrame,
    zero_stats: dict,
    filter_summary: dict
) -> dict:
    """
    导出新书零借阅筛选结果
    
    Args:
        filtered_data: 筛选后的数据
        excluded_data: 被过滤的数据
        borrowed_books: 有借阅的图书
        zero_stats: 零借阅统计信息
        filter_summary: 过滤汇总信息
        
    Returns:
        dict: 输出文件路径字典
    """
    from src.core.result_exporter import ResultExporter
    
    # 获取输出目录
    outputs_dir = Path(get_config('paths.outputs_dir', 'runtime/outputs'))
    outputs_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成时间戳
    timestamp = get_timestamp()
    
    output_files = {}
    
    try:
        # 在筛选数据中添加标识列
        filtered_data_copy = filtered_data.copy()
        
        # 添加评选批次 (默认为当前月)
        target_month = get_config('statistics.target_month', None)
        if not target_month:
            target_month = datetime.now().strftime('%Y-%m')
            
        filtered_data_copy.insert(0, '评选批次', target_month)
        filtered_data_copy.insert(1, '数据来源', '新书零借阅')
        
        # 1. 输出零借阅筛选结果（通过常规过滤的）
        # 使用统一的文件名前缀，以便后续模块自动识别
        excel_file = outputs_dir / f"数据筛选结果_{timestamp}.xlsx"
        filtered_data_copy.to_excel(excel_file, index=False)
        output_files['零借阅筛选结果'] = str(excel_file)
        logger.info(f"零借阅筛选结果已保存到: {excel_file} (数据来源: 新书零借阅)")
        
        # 2. 输出被过滤的数据
        if not excluded_data.empty:
            excluded_excel_file = outputs_dir / f"新书零借阅_被过滤数据_{timestamp}.xlsx"
            exporter = ResultExporter(str(outputs_dir))
            try:
                excluded_file_path = exporter.export_filtered_out_data(
                    excluded_data,
                    filter_summary.get('filter_results', {}),
                    f"新书零借阅_被过滤数据_{timestamp}.xlsx"
                )
                output_files['被过滤数据'] = excluded_file_path
                logger.info(f"被过滤数据已保存到: {excluded_file_path}")
            except Exception as e:
                logger.warning(f"使用ResultExporter导出被过滤数据失败，尝试简单导出: {e}")
                excluded_data.to_excel(excluded_excel_file, index=False)
                output_files['被过滤数据'] = str(excluded_excel_file)
                logger.info(f"被过滤数据已保存到（简单模式）: {excluded_excel_file}")
        
        # 3. 输出有借阅的图书（供参考）
        if not borrowed_books.empty:
            borrowed_excel_file = outputs_dir / f"新书_有借阅图书_{timestamp}.xlsx"
            borrowed_books.to_excel(borrowed_excel_file, index=False)
            output_files['有借阅图书'] = str(borrowed_excel_file)
            logger.info(f"有借阅图书已保存到: {borrowed_excel_file}")
        
        # 4. 生成统计报告
        report_file = outputs_dir / f"新书零借阅筛选报告_{timestamp}.txt"
        report_content = generate_report(
            filtered_data,
            excluded_data,
            borrowed_books,
            zero_stats,
            filter_summary
        )
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        output_files['筛选报告'] = str(report_file)
        logger.info(f"筛选报告已保存到: {report_file}")
        
        return output_files
        
    except Exception as e:
        logger.error(f"导出结果失败: {str(e)}")
        return output_files


def generate_report(
    filtered_data: pd.DataFrame,
    excluded_data: pd.DataFrame,
    borrowed_books: pd.DataFrame,
    zero_stats: dict,
    filter_summary: dict
) -> str:
    """
    生成筛选报告
    
    Args:
        filtered_data: 筛选后的数据
        excluded_data: 被过滤的数据
        borrowed_books: 有借阅的图书
        zero_stats: 零借阅统计信息
        filter_summary: 过滤汇总信息
        
    Returns:
        str: 报告内容
    """
    report = []
    report.append("=" * 60)
    report.append("新书零借阅（睡美人）筛选报告")
    report.append("=" * 60)
    report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # 零借阅筛选统计
    report.append("一、零借阅筛选统计")
    report.append("-" * 60)
    for key, value in zero_stats.items():
        report.append(f"{key}: {value}")
    report.append("")
    
    # 常规过滤统计
    if filter_summary:
        report.append("二、常规过滤统计")
        report.append("-" * 60)
        report.append(f"原始数据: {filter_summary.get('original_count', 0)} 条")
        report.append(f"筛选后数据: {filter_summary.get('filtered_count', 0)} 条")
        report.append(f"被过滤数据: {filter_summary.get('excluded_count', 0)} 条")
        report.append(f"总排除数量: {filter_summary.get('total_excluded', 0)} 条")
        report.append(f"排除比例: {filter_summary.get('exclusion_ratio', 0):.2%}")
        report.append("")
        
        # 各筛选器详情
        if filter_summary.get('filter_results'):
            report.append("三、各筛选器详情")
            report.append("-" * 60)
            for filter_name, result in filter_summary['filter_results'].items():
                status = result.get('status', 'unknown')
                excluded_count = result.get('excluded_count', 0)
                exclusion_ratio = result.get('excluded_ratio', 0.0)
                report.append(f"\n{filter_name}:")
                report.append(f"  状态: {status}")
                report.append(f"  排除数量: {excluded_count} 条")
                report.append(f"  排除比例: {exclusion_ratio:.2%}")
                if result.get('patterns_count'):
                    report.append(f"  模式数量: {result['patterns_count']}")
                if result.get('target_column'):
                    report.append(f"  目标列: {result['target_column']}")
                elif result.get('target_columns'):
                    report.append(f"  目标列: {', '.join(result['target_columns'])}")
                if result.get('reason'):
                    report.append(f"  备注: {result['reason']}")
            report.append("")
    
    # 最终结果统计
    report.append("四、最终结果统计")
    report.append("-" * 60)
    report.append(f"零借阅筛选结果: {len(filtered_data)} 条")
    report.append(f"有借阅图书: {len(borrowed_books)} 条")
    report.append(f"被过滤数据: {len(excluded_data)} 条")
    report.append("")
    
    # 分类统计（如果有索书号列）
    if '索书号' in filtered_data.columns:
        report.append("五、分类统计（零借阅筛选结果）")
        report.append("-" * 60)
        filtered_data_copy = filtered_data.copy()
        filtered_data_copy['分类号'] = filtered_data_copy['索书号'].astype(str).str[0]
        category_counts = filtered_data_copy['分类号'].value_counts()
        for category, count in category_counts.head(20).items():
            report.append(f"{category}: {count} 条")
        report.append("")
    
    report.append("=" * 60)
    report.append("报告结束")
    report.append("=" * 60)
    
    return "\n".join(report)
