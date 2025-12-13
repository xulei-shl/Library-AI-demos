#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全量书目数据过滤脚本 - 主入口

独立运行的数据过滤脚本，用于批量处理图书馆书目 Excel 数据。
根据配置的过滤规则（索书号、题名关键词）筛选数据，并输出符合条件和被过滤的数据集。

使用示例:
    python src/scripts/data_filter.py
    python src/scripts/data_filter.py --config config/data_filter.yaml
    python src/scripts/data_filter.py --output-dir runtime/outputs/custom_dir
    python src/scripts/data_filter.py --files data/books_2023.xlsx data/books_2024.xlsx
    python src/scripts/data_filter.py --log-level DEBUG
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import get_logger, LoggerManager
from src.scripts.data_filter_runner import DataFilterRunner

logger = get_logger(__name__)


def parse_arguments() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="全量书目数据过滤脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s                                    # 使用默认配置
  %(prog)s --config custom_config.yaml        # 指定配置文件
  %(prog)s --output-dir custom_output         # 指定输出目录
  %(prog)s --files file1.xlsx file2.xlsx     # 指定输入文件
  %(prog)s --log-level DEBUG                 # 设置日志级别
        """
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default="config/data_filter.yaml",
        help="配置文件路径（默认: config/data_filter.yaml）"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        help="输出目录（覆盖配置文件）"
    )
    
    parser.add_argument(
        "--files",
        nargs="+",
        help="输入 Excel 文件列表（覆盖配置文件）"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别（覆盖配置文件）"
    )
    
    return parser.parse_args()


def main() -> None:
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_arguments()
        
        # 初始化日志系统
        LoggerManager.init()
        
        logger.info("=" * 50)
        logger.info("全量书目数据过滤脚本启动")
        logger.info("=" * 50)
        
        # 创建运行器并执行
        runner = DataFilterRunner(args.config)
        runner.run(
            output_dir=args.output_dir,
            excel_files=args.files,
            log_level=args.log_level
        )
        
        logger.info("=" * 50)
        logger.info("全量书目数据过滤脚本执行完成")
        logger.info("=" * 50)
        
    except FileNotFoundError as e:
        logger.error(f"文件未找到: {e}")
        sys.exit(1)
    except Exception as e:
        import traceback
        logger.error(f"执行过程中发生错误: {e}")
        logger.error(f"错误详情: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()