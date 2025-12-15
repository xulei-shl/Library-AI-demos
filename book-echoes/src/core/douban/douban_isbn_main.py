#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
豆瓣 ISBN API 模块主程序

通过 ISBN 直接调用豆瓣 API 获取图书信息的独立模块。
与原有豆瓣模块（豆瓣链接解析 + Subject API）互不干扰。

流程：FOLIO ISBN 获取 → 豆瓣 ISBN API → 评分过滤
"""

import os
import sys
import argparse
from pathlib import Path

# 添加项目根目录
current_dir = Path(__file__).absolute().parent.parent.parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from src.utils.config_manager import get_config_manager
from src.utils.logger import get_logger
from src.core.douban.pipelines.douban_isbn_api_pipeline import (
    DoubanIsbnApiPipeline,
    DoubanIsbnApiPipelineOptions,
)

logger = get_logger(__name__)


def validate_excel_file(file_path: str) -> bool:
    """验证 Excel 文件."""
    if not file_path:
        print("错误: 请提供 Excel 文件路径")
        return False

    if not os.path.exists(file_path):
        print(f"错误: 文件不存在 - {file_path}")
        return False

    try:
        import pandas as pd
        df = pd.read_excel(file_path)
        if len(df) == 0:
            print("错误: Excel 文件为空")
            return False
        return True
    except Exception as e:
        print(f"错误: 无法读取 Excel 文件 - {e}")
        return False


def run_command(args):
    """执行 ISBN API 流水线."""
    if not validate_excel_file(args.excel_file):
        return 1

    # 加载配置
    config_manager = get_config_manager()
    full_config = config_manager.get_config()
    douban_config = config_manager.get_douban_config()
    isbn_api_config = douban_config.get("isbn_api", {})
    
    # 读取评分过滤配置
    rating_filter_config = full_config.get("rating_filter", {})
    dynamic_filter_enabled = rating_filter_config.get("dynamic_filter_enabled", True)

    # 构建流水线选项
    options = DoubanIsbnApiPipelineOptions(
        excel_file=args.excel_file,
        barcode_column=args.barcode_column,
        isbn_column=args.isbn_column,
        # 反爬配置：命令行参数 > 配置文件 > 默认值
        max_concurrent=args.max_concurrent or isbn_api_config.get("max_concurrent", 2),
        qps=args.qps or isbn_api_config.get("qps", 0.5),
        timeout=args.timeout or isbn_api_config.get("timeout", 15),
        # 数据库配置
        disable_database=args.disable_database,
        force_update=args.force_update,
        db_path=args.db_path,
        # 保存配置
        save_interval=args.save_interval,
        # 报告配置
        generate_report=not args.disable_report,
        # 评分过滤配置：优先使用配置文件中的设置
        enable_rating_filter=dynamic_filter_enabled and not args.disable_rating_filter,
    )

    # 从配置文件加载随机延迟和批次冷却配置
    random_delay = isbn_api_config.get("random_delay", {})
    if random_delay.get("enabled", True):
        options.random_delay_min = random_delay.get("min", 1.5)
        options.random_delay_max = random_delay.get("max", 3.5)

    batch_cooldown = isbn_api_config.get("batch_cooldown", {})
    if batch_cooldown.get("enabled", True):
        options.batch_cooldown_interval = batch_cooldown.get("interval", 20)
        options.batch_cooldown_min = batch_cooldown.get("min", 30)
        options.batch_cooldown_max = batch_cooldown.get("max", 60)

    # 重试配置
    retry_config = isbn_api_config.get("retry", {})
    options.retry_max_times = retry_config.get("max_times", 3)
    options.retry_backoff = retry_config.get("backoff", [2, 5, 10])

    # 打印配置信息
    print("=" * 60)
    print("豆瓣 ISBN API 模块")
    print("流程: FOLIO ISBN → 豆瓣 ISBN API → 评分过滤")
    print("=" * 60)
    print(f"源文件: {args.excel_file}")
    print(f"条码列: {options.barcode_column}")
    print(f"ISBN列: {options.isbn_column}")
    print(f"并发数: {options.max_concurrent}")
    print(f"QPS: {options.qps}")
    print(f"数据库: {'禁用' if options.disable_database else '启用'}")
    
    # 显示评分过滤状态，考虑配置文件中的动态过滤设置
    rating_filter_status = "启用"
    if not dynamic_filter_enabled:
        rating_filter_status = "配置禁用"
    elif not options.enable_rating_filter:
        rating_filter_status = "命令行禁用"
    
    print(f"评分过滤: {rating_filter_status}")
    print(f"  - 配置文件 dynamic_filter_enabled: {dynamic_filter_enabled}")
    print(f"  - 命令行 enable_rating_filter: {options.enable_rating_filter}")
    print("=" * 60)

    # 执行流水线
    pipeline = DoubanIsbnApiPipeline()
    try:
        output_file, stats = pipeline.run(options)
        print("")
        print("✅ ISBN API 流程完成")
        print(f"   输出文件: {output_file}")
        print(f"   总记录数: {stats.get('total_records', 0)}")
        print(f"   有效ISBN: {stats.get('valid_isbn_count', 0)}")
        print(f"   成功获取: {stats.get('api_success_count', 0)}")
        print(f"   未找到: {stats.get('api_failed_count', 0)}")
        print(f"   候选图书: {stats.get('candidate_count', 0)}")
        if stats.get('report_file'):
            print(f"   报告文件: {stats['report_file']}")
        return 0
    except Exception as e:
        print(f"❌ ISBN API 流程失败: {e}")
        logger.error(f"ISBN API 流程失败: {e}", exc_info=True)
        return 1


def show_help():
    """显示帮助信息."""
    print("""
🎯 豆瓣 ISBN API 模块

📋 说明:
  通过 ISBN 直接调用豆瓣移动版 API 获取图书信息。
  无需经过爬虫搜索获取链接的步骤，速度更快。

📖 用法:
  python douban_isbn_main.py run --excel-file <文件路径> [选项]

🔧 主要选项:
  --excel-file FILE       Excel 文件路径 (必需)
  --barcode-column NAME   条码列名 (默认: 书目条码)
  --isbn-column NAME      ISBN 列名 (默认: ISBN)
  --max-concurrent N      最大并发数 (默认: 2)
  --qps N                 每秒请求数 (默认: 0.5)
  --timeout N             请求超时秒数 (默认: 15)
  --save-interval N       保存间隔条数 (默认: 10)

数据库选项:
  --disable-database      禁用数据库功能
  --force-update          强制更新所有数据
  --db-path PATH          数据库文件路径

其他选项:
  --disable-report        禁用报告生成
  --disable-rating-filter 禁用评分过滤

📝 示例:
  # 基本用法
  python douban_isbn_main.py run --excel-file "数据.xlsx"

  # 禁用数据库
  python douban_isbn_main.py run --excel-file "数据.xlsx" --disable-database

  # 自定义并发和 QPS
  python douban_isbn_main.py run --excel-file "数据.xlsx" --max-concurrent 3 --qps 0.3

💡 配置文件:
  可在 config/setting.yaml 中配置 douban.isbn_api 部分

⚠️ 注意事项:
  1. 建议使用较低的 QPS (0.5 以下) 避免触发反爬
  2. 程序会自动添加随机延迟和批次冷却
  3. 此模块与原有豆瓣模块互不干扰
""")


def main():
    """主函数."""
    parser = argparse.ArgumentParser(
        description='豆瓣 ISBN API 模块 - 通过 ISBN 直接获取图书信息',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        'command',
        choices=['run', 'help'],
        help='执行的命令',
    )

    # Excel 文件参数
    parser.add_argument(
        '--excel-file',
        help='Excel 文件路径 (必需)',
    )
    parser.add_argument(
        '--barcode-column',
        default='书目条码',
        help='条码列名 (默认: 书目条码)',
    )
    parser.add_argument(
        '--isbn-column',
        default='ISBN',
        help='ISBN 列名 (默认: ISBN)',
    )

    # 反爬配置
    parser.add_argument(
        '--max-concurrent',
        type=int,
        help='最大并发数 (默认从配置文件读取，否则为 2)',
    )
    parser.add_argument(
        '--qps',
        type=float,
        help='每秒请求数 (默认从配置文件读取，否则为 0.5)',
    )
    parser.add_argument(
        '--timeout',
        type=float,
        help='请求超时秒数 (默认从配置文件读取，否则为 15)',
    )
    parser.add_argument(
        '--save-interval',
        type=int,
        default=10,
        help='保存间隔条数 (默认: 10)',
    )

    # 数据库配置
    parser.add_argument(
        '--disable-database',
        action='store_true',
        help='禁用数据库功能',
    )
    parser.add_argument(
        '--force-update',
        action='store_true',
        help='强制更新所有数据',
    )
    parser.add_argument(
        '--db-path',
        help='数据库文件路径',
    )

    # 其他配置
    parser.add_argument(
        '--disable-report',
        action='store_true',
        help='禁用报告生成',
    )
    parser.add_argument(
        '--disable-rating-filter',
        action='store_true',
        help='禁用评分过滤',
    )

    args = parser.parse_args()

    if args.command == 'help':
        show_help()
        return 0

    if args.command == 'run':
        if not args.excel_file:
            print("错误: 请使用 --excel-file 指定 Excel 文件路径")
            return 1
        return run_command(args)

    return 0


if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) > 1:
        exit_code = main()
        sys.exit(exit_code)
    else:
        # 无参数时显示简洁的帮助
        print("豆瓣 ISBN API 模块")
        print("=" * 40)
        print("执行 ISBN API 流程:")
        print("   python douban_isbn_main.py run --excel-file <文件>")
        print("")
        print("查看详细帮助:")
        print("   python douban_isbn_main.py help")
        print("")
