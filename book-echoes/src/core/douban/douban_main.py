#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
豆瓣模块主程序

基于新的异步处理逻辑的简洁高效主程序：
1. 统一使用新的异步处理器
2. 简化配置管理和命令行接口
3. 优化用户体验和错误处理
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, Any

# 立即添加项目根目录
current_dir = Path(__file__).absolute().parent.parent.parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import logging

# 导入配置和工具
from src.utils.config_manager import get_config_manager
from src.utils.logger import get_logger
from src.core.douban.isbn_processor_config import get_config, get_config_for_data_size, load_config_from_yaml
from src.core.douban.pipelines import (
    FolioIsbnPipeline,
    FolioIsbnPipelineOptions,
    DoubanRatingPipeline,
    DoubanRatingPipelineOptions,
    PipelineRunner,
    PipelineExecutionOptions,
)

logger = get_logger(__name__)


def load_effective_config(command_args=None, excel_file_path=None):
    """
    获取有效的ISBN处理配置

    Args:
        command_args: 命令行参数
        excel_file_path: Excel文件路径

    Returns:
        配置对象
    """
    config_manager = get_config_manager()
    douban_config = config_manager.get_douban_config()
    isbn_config = douban_config.get('isbn_processor', {})

    # 优先从配置文件加载
    config = load_config_from_yaml(isbn_config)

    # 如果自动模式且提供了Excel文件，根据数据量选择
    if config and isbn_config.get('strategy') == 'auto' and excel_file_path:
        try:
            import pandas as pd
            data = pd.read_excel(excel_file_path)
            data_size = len(data)
            config = get_config_for_data_size(data_size)
            logger.info(f"自动选择配置: {config.name} (数据量: {data_size}条)")
        except Exception as e:
            logger.warning(f"读取Excel失败，使用默认配置: {e}")

    # 命令行参数覆盖（如果指定了config_name）
    if command_args and command_args.config_name:
        config = get_config(command_args.config_name)
        logger.info(f"使用命令行指定配置: {config.name}")

    return config


def validate_excel_file(file_path: str) -> bool:
    """验证Excel文件"""
    if not file_path:
        print("错误: 请提供Excel文件路径")
        return False
    
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在 - {file_path}")
        return False
    
    try:
        import pandas as pd
        df = pd.read_excel(file_path)
        if len(df) == 0:
            print("错误: Excel文件为空")
            return False
        return True
    except Exception as e:
        print(f"错误: 无法读取Excel文件 - {e}")
        return False


def show_performance_estimate(excel_file_path: str, config_name: str = "balanced"):
    """显示性能估算"""
    try:
        import pandas as pd
        from src.core.douban.isbn_processor_config import estimate_performance, get_config

        data = pd.read_excel(excel_file_path)
        data_size = len(data)

        # 检查config_name是否为中文显示名，是则转换为英文键
        actual_config_name = config_name
        if config_name in ["保守配置", "平衡配置", "激进配置", "紧急配置"]:
            name_mapping = {
                "保守配置": "conservative",
                "平衡配置": "balanced",
                "激进配置": "aggressive",
                "紧急配置": "emergency"
            }
            actual_config_name = name_mapping.get(config_name, config_name)

        config = get_config(actual_config_name)
        estimate = estimate_performance(config, data_size)

        print(f"📊 性能估算 (数据量: {data_size}条)")
        print(f"   预计处理时间: {estimate['total_time_hours']:.1f}小时")
        print(f"   预计吞吐量: {estimate['throughput_items_per_hour']:.0f}条/小时")
        print(f"   性能提升: {estimate['speed_improvement']:.1f}倍")
        print(f"   预估成功率: {estimate['estimated_success_rate']*100:.0f}%")

    except Exception as e:
        logger.warning(f"性能估算失败: {e}")


def process_isbn_command(args):
    """处理ISBN命令"""
    if not validate_excel_file(args.excel_file):
        return

    # 获取配置
    config = load_effective_config(args, args.excel_file) or get_config("balanced")

    db_config_preview = {}
    if not args.disable_database:
        config_manager = get_config_manager()
        douban_config = config_manager.get_douban_config()
        db_config_preview = douban_config.get('database', {}).copy()
        if args.force_update:
            db_config_preview.setdefault('refresh_strategy', {})['force_update'] = True
        if args.db_path:
            db_config_preview['db_path'] = args.db_path

    print("ISBN 流水线启动")
    print(f"源文件: {args.excel_file}")
    print(f"配置方案: {config.name}")
    print(f"数据库功能: {'启用' if not args.disable_database else '禁用'}")
    if not args.disable_database:
        stale_days = db_config_preview.get('refresh_strategy', {}).get('stale_days', 30)
        print(f"   刷新策略: {stale_days}天")

    if not args.quiet:
        show_performance_estimate(args.excel_file, config.name)

    pipeline = FolioIsbnPipeline()
    options = FolioIsbnPipelineOptions(
        excel_file=args.excel_file,
        barcode_column=args.barcode_column,
        isbn_column=args.output_column,
        config_name=args.config_name,
        username=args.username,
        password=args.password,
        disable_database=args.disable_database,
        force_update=args.force_update,
        db_path=args.db_path,
        retry_failed=not getattr(args, "disable_retry", False),
        limit_rows=5 if args.test else None,
        save_interval=args.save_interval,
    )

    try:
        output_file, stats = pipeline.run(options)
        print(f"\n✅ FOLIO 流程完成 -> {output_file}")
        print(f"   总记录数: {stats.get('total_records')}")
        print(f"   成功获取: {stats.get('success_count')}")
        print(f"   获取失败: {stats.get('failed_count')}")
        print(f"   成功率: {stats.get('success_rate', 0):.2f}%")
    except Exception as e:
        print(f"❌ ISBN 流程失败: {e}")
        logger.error(f"ISBN流程失败: {e}")


def douban_rating_command(args):
    """豆瓣评分命令 - 仅执行豆瓣流水线"""
    if not validate_excel_file(args.excel_file):
        return

    print("豆瓣评分流水线启动")
    print(f"源文件: {args.excel_file}")
    print("描述: 仅执行豆瓣评分阶段")
    print(f"配置方案: {args.config_name or '默认'}")
    print(f"数据库功能: {'启用' if not args.disable_database else '禁用'}")

    pipeline = DoubanRatingPipeline()
    options = DoubanRatingPipelineOptions(
        excel_file=args.excel_file,
        barcode_column=args.barcode_column,
        isbn_column=args.isbn_column or "ISBN",
        status_column=args.status_column,
        link_column=args.link_column,
        config_name=args.config_name,
        username=args.username,
        password=args.password,
        disable_database=args.disable_database,
        force_update=args.force_update,
        db_path=args.db_path,
        enable_isbn_resolution=args.enable_isbn_resolution,
        generate_report=not args.disable_report,
        enable_db_stage=not getattr(args, "skip_db_stage", False),
        enable_link_stage=not getattr(args, "skip_link_stage", False),
        enable_subject_stage=not getattr(args, "skip_subject_stage", False),
        save_interval=getattr(args, "douban_save_interval", 15),
        force_db_stage=getattr(args, "force_db_stage", False),
    )

    try:
        output_file, stats = pipeline.run(options)
        if stats.get("paused_after_link"):
            partial_file = stats.get("partial_file") or output_file
            print("ℹ 豆瓣流程已在链接阶段后按用户指令暂停，未生成最终 Excel 或报告")
            print(f"   已保留 partial 文件: {partial_file}")
            print("   稍后再次运行 `douban-rating` 命令即可继续执行 Subject API 阶段")
        else:
            print("✅ 豆瓣流程完成")
            print(f"   输出文件: {output_file}")
            if stats.get('report_file'):
                print(f"   报告路径: {stats['report_file']}")
            print(f"   成功条数: {stats.get('success_douban_count')}")
            print(f"   失败条数: {stats.get('failed_douban_count')}")
    except Exception as e:
        print(f"❌ 豆瓣流程失败: {e}")
        logger.error(f"豆瓣流程失败: {e}")


def run_full_pipeline_command(args):
    """串行执行 FOLIO -> 豆瓣"""
    if not validate_excel_file(args.excel_file):
        return

    folio_opts = FolioIsbnPipelineOptions(
        excel_file=args.excel_file,
        barcode_column=args.barcode_column,
        isbn_column=args.output_column,
        config_name=args.config_name,
        username=args.username,
        password=args.password,
        disable_database=args.disable_database,
        force_update=args.force_update,
        db_path=args.db_path,
        retry_failed=not getattr(args, "disable_retry", False),
        limit_rows=None,
        save_interval=args.save_interval,
    )

    douban_opts = DoubanRatingPipelineOptions(
        excel_file=args.excel_file,
        barcode_column=args.barcode_column,
        isbn_column=args.isbn_column or "ISBN",
        status_column=args.status_column,
        link_column=args.link_column,
        config_name=args.config_name,
        username=args.username,
        password=args.password,
        disable_database=args.disable_database,
        force_update=args.force_update,
        db_path=args.db_path,
        enable_isbn_resolution=args.enable_isbn_resolution,
        generate_report=not args.disable_report,
        force_db_stage=getattr(args, "force_db_stage", False),
        enable_db_stage=not getattr(args, "skip_db_stage", False),
        enable_link_stage=not getattr(args, "skip_link_stage", False),
        enable_subject_stage=not getattr(args, "skip_subject_stage", False),
        save_interval=getattr(args, "douban_save_interval", 15),
    )

    runner = PipelineRunner()
    try:
        results = runner.run_full_pipeline(
            PipelineExecutionOptions(
                excel_file=args.excel_file,
                folio_options=folio_opts,
                douban_options=douban_opts,
            )
        )
        folio_output = results["folio"]["output"]
        douban_output = results["douban"]["output"]
        print("\n✅ 串行流水线完成")
        print(f"   FOLIO 输出: {folio_output}")
        print(f"   豆瓣输出: {douban_output}")
        report_path = results["douban"]["stats"].get("report_file")
        if report_path:
            print(f"   豆瓣报告: {report_path}")
    except Exception as e:
        print(f"❌ 串行流水线失败: {e}")
        logger.error(f"串行流水线失败: {e}")


def list_modules():
    """列出模块状态"""
    print("📋 豆瓣模块状态")
    print("=" * 40)
    print("✅ Folio ISBN 流水线: 启用")
    print("✅ 豆瓣评分流水线: 启用")
    print("➡️  pipeline_runner: 支持串行编排")
    print("")


def show_help():
    """显示帮助信息"""
    print("""
🎯 豆瓣模块串行流水线

📋 可用命令:
  isbn           - 仅执行 FOLIO ISBN 流程
  douban-rating  - 仅执行豆瓣评分流程
  full           - 顺序执行 FOLIO -> 豆瓣
  list           - 列出模块状态
  help           - 显示帮助

🔧 常用选项:
  --excel-file FILE       Excel 文件路径 (必需)
  --barcode-column NAME   条码列 (默认: 书目条码)
  --output-column NAME    ISBN 输出列 (默认: ISBN)
  --isbn-column NAME      豆瓣阶段使用的 ISBN 列 (默认: ISBN)
  --status-column NAME    豆瓣阶段状态列 (默认: 处理状态)
  --config-name NAME      指定配置方案
  --username/--password   覆盖 FOLIO 登录
  --disable-database      仅使用 Excel，不写入数据库
  --force-update          忽略过期策略，强制刷新

📝 示例:
  python douban_main.py isbn --excel-file 数据.xlsx
  python douban_main.py douban-rating --excel-file 数据.xlsx --disable-database
  python douban_main.py full --excel-file 数据.xlsx
""")
def show_help():
    """显示帮助信息"""
    print("""
🎯 豆瓣模块主程序 - 异步处理版本

📋 可用命令:
  isbn         - 执行ISBN异步获取 (推荐)
  douban-rating - 执行ISBN获取+豆瓣评分同步处理 (推荐)
  list         - 列出模块状态
  help         - 显示帮助信息

📖 ISBN异步处理用法:
  python douban_main.py isbn --excel-file <文件路径> [选项]

🎭 豆瓣评分处理用法:
  python douban_main.py douban-rating --excel-file <文件路径> [选项]

🔧 主要选项:
  --excel-file FILE       Excel文件路径 (必需)
  --barcode-column NAME   条码列名 (默认: 书目条码)
  --output-column NAME    输出ISBN列名 (默认: ISBN号)
  --isbn-column NAME      ISBN列名 (用于豆瓣评分，默认: ISBN号)
  --config-name NAME      配置方案 (默认: balanced)
                          可选: conservative/balanced/aggressive/emergency
  --username USER         FOLIO用户名 (可选，默认从配置读取)
  --password PASS         FOLIO密码 (可选，默认从配置读取)
  --test                  测试模式 (仅处理前5条记录)
  --quiet                 安静模式 (减少输出信息)

数据库选项:
  --disable-database      禁用数据库功能（仅爬取和更新Excel）
  --force-update          强制更新所有数据（忽略时间限制）
  --db-path PATH          数据库文件路径（可选，默认从配置读取）

📝 示例:
  # ISBN异步模式 (推荐，高性能)
  python douban_main.py isbn --excel-file "数据.xlsx"

  # 豆瓣评分处理模式 (推荐，高性能)
  python douban_main.py douban-rating --excel-file "数据.xlsx"

  # 启用数据库功能的豆瓣评分处理
  python douban_main.py douban-rating --excel-file "数据.xlsx"

  # 禁用数据库功能
  python douban_main.py douban-rating --excel-file "数据.xlsx" --disable-database

  # 强制更新所有数据（忽略时间限制）
  python douban_main.py douban-rating --excel-file "数据.xlsx" --force-update

🎛️ 智能配置:
  • 自动模式: 根据数据量自动选择最佳配置
  • 预设配置: 保守/平衡/激进/紧急四种方案
  • 配置文件: config/setting.yaml -> douban.isbn_processor
  • 性能提升: 异步模式比同步模式快5-15倍

📊 性能对比:
  异步模式: ~0.7-1.3秒/条，5-15倍性能提升 (推荐)
  同步模式: ~6.6秒/条，稳定可靠 (兼容)

💡 配置示例 (config/setting.yaml):
  douban:
    isbn_processor:
      strategy: "preset"        # preset/custom/auto
      preset: "balanced"        # balanced/aggressive/emergency

📝 示例:
  # ISBN异步模式 (推荐，高性能)
  python douban_main.py isbn --excel-file "数据.xlsx"

  # 豆瓣评分处理模式 (推荐，高性能)
  python douban_main.py douban-rating --excel-file "数据.xlsx"

  # 测试模式 (先测试5条记录)
  python douban_main.py isbn --excel-file "数据.xlsx" --test

  # 指定配置方案
  python douban_main.py isbn --excel-file "数据.xlsx" --config-name aggressive

  # 断点续传 (后续功能)
  python douban_main.py isbn --excel-file "数据.xlsx" --resume-from 500

🔍 更多信息:
  • 配置文件: config/setting.yaml
  • 模块文档: docs/模块3-豆瓣评分/
  • 配置详解: src/core/douban/isbn_processor_config.py
""")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='豆瓣模块主程序 - 异步处理版本',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('command',
                       choices=['isbn', 'douban-rating', 'full', 'list', 'help'],
                       help='执行的命令')
    
    # ISBN命令参数
    parser.add_argument('--excel-file',
                       help='Excel文件路径 (用于ISBN处理)')
    parser.add_argument('--barcode-column',
                       default='书目条码',
                       help='条码列名')
    parser.add_argument('--output-column',
                       default='ISBN',
                       help='输出ISBN列名')
    parser.add_argument('--save-interval',
                       type=int,
                       default=25,
                       help='ISBN流程保存间隔（秒），0 表示仅结束保存')
    parser.add_argument('--disable-retry',
                       action='store_true',
                       help='跳过ISBN失败重试')
    parser.add_argument('--config-name',
                       choices=['test', 'small', 'production', 'conservative', 'balanced', 'aggressive', 'emergency'],
                       help='配置方案')
    parser.add_argument('--username',
                       help='FOLIO用户名')
    parser.add_argument('--password',
                       help='FOLIO密码')
    parser.add_argument('--test',
                       action='store_true',
                       help='测试模式 (仅处理前5条记录)')
    parser.add_argument('--quiet',
                       action='store_true',
                       help='安静模式 (减少输出)')
    # 豆瓣阶段参数
    parser.add_argument('--isbn-column',
                       default='ISBN',
                       help='ISBN列名 (用于豆瓣评分)')
    parser.add_argument('--status-column',
                       default='处理状态',
                       help='状态列名 (用于豆瓣评分)')
    parser.add_argument('--link-column',
                       help='豆瓣链接列名 (默认读取配置)')
    parser.add_argument('--disable-report',
                       action='store_true',
                       help='禁用豆瓣报告生成')
    parser.add_argument('--enable-isbn-resolution',
                       action='store_true',
                       help='在豆瓣阶段允许补救ISBN（默认关闭）')
    parser.add_argument('--skip-db-stage',
                       action='store_true',
                       help='跳过数据库查重阶段')
    parser.add_argument('--force-db-stage',
                       action='store_true',
                       help='在恢复模式下也强制执行数据库阶段')
    parser.add_argument('--skip-link-stage',
                       action='store_true',
                       help='跳过豆瓣链接解析阶段')
    parser.add_argument('--skip-subject-stage',
                       action='store_true',
                       help='跳过Subject API 阶段')
    parser.add_argument('--douban-save-interval',
                       type=int,
                       default=15,
                       help='豆瓣流水线持久化间隔(秒)')


    # 数据库相关参数
    parser.add_argument('--disable-database',
                       action='store_true',
                       help='禁用数据库功能（仅爬取和更新Excel）')
    parser.add_argument('--force-update',
                       action='store_true',
                       help='强制更新所有数据（忽略时间限制）')
    parser.add_argument('--db-path',
                       help='数据库文件路径（可选，默认从配置读取）')
    args = parser.parse_args()
    
    try:
        if args.command == 'isbn':
            process_isbn_command(args)
        elif args.command == 'douban-rating':
            douban_rating_command(args)
        elif args.command == 'full':
            run_full_pipeline_command(args)
        elif args.command == 'list':
            list_modules()
        elif args.command == 'help':
            show_help()

    except Exception as e:
        print(f"程序执行失败: {str(e)}")
        logger.error(f"主程序执行失败: {e}")


if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) > 1:
        main()
    else:
        # 无参数时显示简洁的帮助
        print("豆瓣模块串行流水线")
        print("=" * 40)
        print("FOLIO ISBN 流程")
        print("   python douban_main.py isbn --excel-file <文件>")
        print("")
        print("豆瓣评分流程")
        print("   python douban_main.py douban-rating --excel-file <文件>")
        print("")
        print("串行执行 FOLIO -> 豆瓣")
        print("   python douban_main.py full --excel-file <文件>")
        print("")
        print("查看模块状态")
        print("   python douban_main.py list")
        print("")
        print("查看详细帮助")
        print("   python douban_main.py help")
        print("")
        print("无参数时执行此模式")



