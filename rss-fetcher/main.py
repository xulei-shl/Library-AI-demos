#!/usr/bin/env python3
"""RSS文章定时爬取与LLM分析 - 主入口程序

程序主入口，提供简单易用的命令行接口，支持按月聚合文章数据。

使用示例:
    # 完整流程运行(按默认阶段)
    python main.py

    # 日常自动运行（按最新文件处理）
    python main.py --stage fetch
    python main.py --stage extract
    python main.py --stage filter
    python main.py --stage summary    
    python main.py --stage analysis
    python main.py --stage cross --score-threshold 70

    # 手动指定输入文件
    python main.py --stage extract --input runtime/outputs/2025-12.xlsx
    python main.py --stage filter --input runtime/outputs/2025-12.xlsx
    
    python main.py --stage summary --input runtime/outputs/2025-12.xlsx    
    python main.py --stage analysis --input runtime/outputs/2025-12.xlsx    
    python main.py --stage cross --input runtime/outputs/2025-12.xlsx

    python main.py --stage all        # 执行完整流程

    # 历史数据或仅获取RSS
    python main.py --stage fetch --input runtime/outputs/2025-11.xlsx

    # 显示帮助信息
    python main.py --help
"""

import argparse
import sys
import os
from datetime import datetime
from typing import Optional

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.pipeline import run_pipeline, SubjectBibliographyPipeline
from src.utils.logger import get_logger

logger = get_logger(__name__)


def setup_args_parser() -> argparse.ArgumentParser:
    """设置命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="RSS文章定时爬取与LLM分析系统 - 按月聚合版本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s                          # 运行完整流程
  %(prog)s --stage fetch            # 仅运行RSS获取阶段
  %(prog)s --stage extract          # 仅运行全文解析阶段
  %(prog)s --stage filter           # 仅运行文章过滤阶段
  %(prog)s --stage summary          # 仅运行文章总结阶段
  %(prog)s --stage analysis         # 仅运行深度分析阶段
  %(prog)s --stage cross            # 仅运行文章交叉主题分析阶段
  %(prog)s --stage extract --input runtime/outputs/2025-12.xlsx
  %(prog)s --stage filter --input runtime/outputs/2025-12.xlsx
  %(prog)s --stage summary --input runtime/outputs/2025-12.xlsx
  %(prog)s --stage analysis --input runtime/outputs/2025-12.xlsx
  %(prog)s --stage cross --input runtime/outputs/2025-12.xlsx
  %(prog)s --stage cross --score-threshold 70  # 自定义评分阈值
        """
    )
    
    parser.add_argument(
        "--stage",
        type=str,
        default="all",
        choices=["fetch", "extract", "filter", "summary", "analysis", "cross", "all"],
        help="""运行阶段:
  fetch     - 阶段1: RSS获取 (按月聚合)
  extract   - 阶段2: 全文解析 (基于月文件)
  filter    - 阶段3: 文章过滤 (基于月文件)
  summary   - 阶段4: 文章总结 (基于过滤结果)
  analysis  - 阶段5: 深度分析 (基于总结结果)
  cross     - 阶段6: 文章交叉主题分析 (基于月文件)
  all       - 完整流程 (默认)"""
    )
    
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="输入文件路径 (用于阶段2、3及summary阶段，例如: runtime/outputs/2025-12.xlsx)"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default="config/subject_bibliography.yaml",
        help="配置文件路径 (默认: config/subject_bibliography.yaml)"
    )
    
    parser.add_argument(
        "--score-threshold",
        type=int,
        default=None,
        help="交叉分析的评分筛选阈值(仅对cross有效)，如果不指定则使用配置文件中的默认值"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 2.0.0 - 按月聚合版本"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true", 
        help="启用详细日志输出"
    )
    
    return parser


def validate_environment() -> bool:
    """验证运行环境是否准备就绪"""
    logger.info("验证运行环境...")
    
    # 检查配置文件
    config_path = "config/subject_bibliography.yaml"
    if not os.path.exists(config_path):
        logger.error(f"配置文件不存在: {config_path}")
        logger.error("请确保配置文件存在并正确配置")
        return False
    
    # 检查输出目录
    output_dir = "runtime/outputs"
    try:
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"输出目录准备就绪: {output_dir}")
    except Exception as e:
        logger.error(f"无法创建输出目录 {output_dir}: {e}")
        return False
    
    # 检查日志目录
    log_dir = "runtime/logs"
    try:
        os.makedirs(log_dir, exist_ok=True)
        logger.info(f"日志目录准备就绪: {log_dir}")
    except Exception as e:
        logger.error(f"无法创建日志目录 {log_dir}: {e}")
        return False
    
    logger.info("运行环境验证完成")
    return True


def print_startup_banner():
    """打印启动横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                RSS文章爬取与LLM分析系统                      ║
║                     按月聚合版本 v2.0.0                      ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def main():
    """主函数"""
    # 打印启动横幅
    print_startup_banner()
    
    # 解析命令行参数
    parser = setup_args_parser()
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("已启用详细日志模式")
    
    # 验证运行环境
    if not validate_environment():
        logger.error("环境验证失败，程序退出")
        return 1
    
    # 记录启动信息
    start_time = datetime.now()
    logger.info(f"程序启动时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"运行阶段: {args.stage}")
    
    if args.input:
        logger.info(f"指定输入文件: {args.input}")
    
    try:
        # 执行pipeline
        run_pipeline(stage=args.stage, input_file=args.input, score_threshold=args.score_threshold)
        
        # 记录完成信息
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"程序执行完成，耗时: {duration}")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("用户中断执行")
        return 130
        
    except Exception as e:
        logger.error(f"程序执行失败: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)