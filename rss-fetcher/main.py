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


def interactive_mode():
    """交互式菜单模式"""
    while True:
        print("\n" + "="*60)
        print("                RSS文章爬取与LLM分析系统")
        print("                     按月聚合版本 v2.0.0")
        print("="*60)
        print("\n请选择要执行的功能：")
        print("1. 完整流程 (all) - 执行所有阶段")
        print("2. RSS获取 (fetch) - 获取RSS源文章")
        print("3. 全文解析 (extract) - 解析文章全文内容")
        print("4. 文章过滤 (filter) - 根据规则过滤文章")
        print("5. 文章总结 (summary) - 生成文章摘要")
        print("6. 深度分析 (analysis) - 对文章进行深度分析")
        print("7. 交叉主题分析 (cross) - 文章间交叉分析")
        print("8. 查看帮助信息")
        print("9. 退出程序")
        print("="*60)
        
        try:
            choice = input("\n请输入选项 (1-9): ").strip()

            if choice == '1':
                run_interactive_stage('all')
            elif choice == '2':
                run_interactive_stage('fetch')
            elif choice == '3':
                run_interactive_stage('extract')
            elif choice == '4':
                run_interactive_stage('filter')
            elif choice == '5':
                run_interactive_stage('summary')
            elif choice == '6':
                run_interactive_stage('analysis')
            elif choice == '7':
                run_interactive_stage('cross')
            elif choice == '8':
                show_help()
            elif choice == '9':
                print("\n感谢使用，再见！")
                break
            else:
                print("\n❌ 无效选项，请输入 1-9 之间的数字")
                
        except KeyboardInterrupt:
            print("\n\n用户中断，退出程序")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")


def run_interactive_stage(stage: str, quick_mode: bool = False):
    """交互式执行指定阶段

    Args:
        stage: 要执行的阶段名称
        quick_mode: 是否使用快速模式（减少确认步骤）
    """
    print(f"\n🚀 准备执行阶段: {stage}")

    # 添加调试日志
    logger.debug(f"开始交互式执行阶段: {stage}, 快速模式: {quick_mode}")

    # 使用默认配置直接执行
    input_file = None
    config_file = "config/subject_bibliography.yaml"
    score_threshold = None

    # 记录执行信息
    logger.info(f"使用默认配置执行阶段: {stage}")
    logger.info(f"配置文件: {config_file}")
    logger.info(f"输入文件: {'默认文件' if input_file is None else input_file}")
    logger.info(f"评分阈值: {'默认值' if score_threshold is None else score_threshold}")

    # 显示执行信息
    print(f"📋 使用默认配置执行:")
    print(f"   阶段: {stage}")
    print(f"   输入文件: 默认文件")
    print(f"   配置文件: {config_file}")
    if stage == 'cross':
        print(f"   评分阈值: 默认值")

    try:
        print(f"\n🎯 开始执行阶段: {stage}")
        run_pipeline(
            stage=stage,
            input_file=input_file,
            score_threshold=score_threshold
        )
        print(f"\n✅ 阶段 '{stage}' 执行完成!")
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        logger.error(f"交互式执行失败: {e}", exc_info=True)


def show_help():
    """显示帮助信息"""
    print("\n" + "="*60)
    print("                    帮助信息")
    print("="*60)
    print("\n📖 各阶段说明:")
    print("1. 完整流程 (all) - 按顺序执行所有阶段，从RSS获取到交叉分析")
    print("2. RSS获取 (fetch) - 从配置的RSS源获取最新文章")
    print("3. 全文解析 (extract) - 下载并解析文章的完整内容")
    print("4. 文章过滤 (filter) - 使用LLM对文章进行质量筛选")
    print("5. 文章总结 (summary) - 为通过筛选的文章生成摘要")
    print("6. 深度分析 (analysis) - 对文章进行深度主题分析")
    print("7. 交叉主题分析 (cross) - 分析文章间的主题关联性")
    print("\n📁 文件说明:")
    print("- 输入文件通常位于: runtime/outputs/YYYY-MM.xlsx")
    print("- 配置文件默认: config/subject_bibliography.yaml")
    print("- 日志文件位于: runtime/logs/")
    print("\n💡 使用提示:")
    print("- 大部分阶段支持使用默认文件，无需手动指定")
    print("- 启用详细日志可以看到更多执行信息")
    print("- 按 Ctrl+C 可以随时中断执行")
    print("="*60)


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
    # 解析命令行参数
    parser = setup_args_parser()
    args = parser.parse_args()
    
    # 添加日志验证使用模式
    logger.info("=== 启动模式分析 ===")
    logger.info(f"命令行参数数量: {len(sys.argv)}")
    logger.info(f"完整命令: {' '.join(sys.argv)}")
    
    # 检测是否为交互式启动（无参数）
    if len(sys.argv) == 1:
        logger.info("检测到无参数启动，启用交互式模式")
        # 打印启动横幅
        print_startup_banner()
        
        # 验证运行环境
        if not validate_environment():
            logger.error("环境验证失败，程序退出")
            return 1
        
        # 进入交互式模式
        interactive_mode()
        return 0
    elif len(sys.argv) == 2 and sys.argv[1] in ['-h', '--help']:
        logger.info("检测到帮助请求，可以提供交互式帮助选项")
        # 打印启动横幅
        print_startup_banner()
        # 显示帮助后直接返回
        parser.print_help()
        return 0
    else:
        logger.info("检测到命令行参数，使用传统模式")
    
    # 传统命令行模式
    # 打印启动横幅
    print_startup_banner()
    
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