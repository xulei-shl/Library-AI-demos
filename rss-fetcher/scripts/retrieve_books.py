#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图书向量检索工具 - 支持命令行和交互式模式

使用方式:
    # 交互式模式（推荐新手使用）
    python scripts/retrieve_books.py --interactive

    # 传统命令行模式
    # 文本相似度检索
    python scripts/retrieve_books.py --query "网络亚文化中的身份表演与情感部落" --top-k 5

    # 从文件读取查询文本
    python scripts/retrieve_books.py --query-file samples/query.txt --min-rating 8

    # 根据分类编号查看高评分图书
    python scripts/retrieve_books.py --category H --top-k 5

    # Markdown → 多子查询检索 → 可选 rerank
    python scripts/retrieve_books.py --query-mode multi \
        --from-md runtime/outputs/cross_analysis/20251211_091043_*.md \
        --per-query-top-k 20 --final-top-k 15 --enable-rerank --min-rating 8
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# 添加项目根目录到 Python 路径，确保脚本可独立运行
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载 .env 中的环境变量（如果存在）
try:
    from dotenv import load_dotenv

    env_file = Path(__file__).parent.parent / 'config' / '.env'
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass

from src.core.book_vectorization.query_assets import build_query_package_from_md
from src.core.book_vectorization.retriever import BookRetriever
from src.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_CONFIG_PATH = 'config/book_vectorization.yaml'
SEPARATOR = '=' * 60


def print_welcome():
    """打印欢迎信息"""
    print(SEPARATOR)
    print("📚 图书向量检索工具 - 交互式模式")
    print(SEPARATOR)
    print("🎯 欢迎使用图书检索工具！请选择您需要的检索方式")
    print()


def get_user_input(prompt: str, default: str = None, required: bool = True) -> str:
    """获取用户输入，带默认值和验证"""
    if default:
        full_prompt = f"{prompt} (默认: {default}): "
    else:
        full_prompt = f"{prompt}: "
    
    while True:
        user_input = input(full_prompt).strip()
        if not user_input and default:
            return default
        if not user_input and required:
            print("⚠️  此项为必填项，请输入有效内容")
            continue
        return user_input


def get_user_choice(prompt: str, options: List[str]) -> int:
    """获取用户单选"""
    print(f"\n{prompt}")
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")
    
    while True:
        choice_input = input("请选择 (输入数字): ").strip()
        try:
            choice = int(choice_input) - 1
            if 0 <= choice < len(options):
                return choice
            else:
                print("⚠️  请输入有效的选项编号")
        except ValueError:
            print("⚠️  请输入有效的数字")


def get_user_yes_no(prompt: str, default: bool = False) -> bool:
    """获取用户是/否选择"""
    default_str = "Y/n" if default else "y/N"
    while True:
        user_input = input(f"{prompt} ({default_str}): ").strip().lower()
        if not user_input:
            return default
        if user_input in ['y', 'yes', '是', '1']:
            return True
        elif user_input in ['n', 'no', '否', '0']:
            return False
        else:
            print("⚠️  请输入 y(是) 或 n(否)")


def interactive_mode():
    """交互式模式主函数"""
    print_welcome()
    
    # 第一步：选择检索模式
    search_modes = [
        "文本检索 - 根据关键词搜索相似书籍",
        "分类检索 - 按索书号分类浏览高评分书籍",
        "多查询检索 - 从Markdown文件生成多个子查询"
    ]
    
    mode_choice = get_user_choice("请选择检索模式", search_modes)
    
    # 构建参数
    args = argparse.Namespace()
    args.config = DEFAULT_CONFIG_PATH
    args.query = None
    args.query_file = None
    args.category = None
    args.top_k = 5
    args.min_rating = None
    args.query_mode = 'single'
    args.from_md = None
    args.per_query_top_k = None
    args.enable_rerank = False
    args.final_top_k = None
    
    if mode_choice == 0:  # 文本检索
        print("\n🔍 文本检索模式")
        
        # 查询方式选择
        query_modes = ["直接输入文本", "从文件读取"]
        query_mode_choice = get_user_choice("请选择查询文本来源", query_modes)
        
        if query_mode_choice == 0:
            args.query = get_user_input("请输入搜索关键词", required=True)
        else:
            print("\n📁 文件读取模式")
            args.query_file = get_user_input("请输入文件路径", required=True)
            # 验证文件存在
            if not Path(args.query_file).exists():
                print(f"❌ 文件不存在: {args.query_file}")
                return None
        
        # 高级参数
        args.top_k = int(get_user_input("返回结果数量", "5"))
        args.min_rating = get_user_input("最低豆瓣评分过滤(可选)", None, required=False)
        if args.min_rating:
            try:
                args.min_rating = float(args.min_rating)
            except ValueError:
                print("⚠️  评分格式不正确，将忽略此设置")
                args.min_rating = None
        
        args.query_mode = 'single'
        
    elif mode_choice == 1:  # 分类检索
        print("\n📂 分类检索模式")
        
        # 显示常见分类
        categories = [
            "A - 马克思主义、哲学、宗教",
            "B - 社会科学总论", 
            "C - 政治、法律",
            "D - 军事",
            "E - 经济",
            "F - 文化、科学、教育、体育",
            "G - 语言、文字",
            "H - 文学",
            "I - 艺术",
            "J - 历史、地理",
            "K - 综合性图书",
            "N - 自然科学总论",
            "O - 数理科学和化学",
            "P - 天文学、地球科学",
            "Q - 生物科学",
            "R - 医药、卫生",
            "S - 农业科学",
            "T - 工业技术",
            "U - 交通运输",
            "V - 航空、航天",
            "X - 环境科学、安全科学",
            "Z - 综合性图书"
        ]
        
        print("\n常见分类说明:")
        for cat in categories:
            print(f"  {cat}")
        
        args.category = get_user_input("请输入索书号首字母 (如: H)", required=True).upper()
        args.top_k = int(get_user_input("返回结果数量", "10"))
        
    elif mode_choice == 2:  # 多查询检索
        print("\n🔄 多查询检索模式")
        
        args.from_md = get_user_input("请输入Markdown文件路径", required=True)
        if not Path(args.from_md).exists():
            print(f"❌ 文件不存在: {args.from_md}")
            return None
            
        args.per_query_top_k = int(get_user_input("每个子查询候选数量", "20"))
        args.final_top_k = int(get_user_input("最终返回结果数量", "15"))
        args.min_rating = get_user_input("最低豆瓣评分过滤(可选)", None, required=False)
        if args.min_rating:
            try:
                args.min_rating = float(args.min_rating)
            except ValueError:
                print("⚠️  评分格式不正确，将忽略此设置")
                args.min_rating = None
        
        # 是否启用Rerank
        if get_user_yes_no("是否启用高级重排序功能?"):
            args.enable_rerank = True
            print("✨ 将使用 SiliconFlow Reranker 进行结果重排序")
        else:
            args.enable_rerank = False
        
        args.query_mode = 'multi'
    
    # 确认参数
    print("\n📋 参数确认")
    print("=" * 40)
    if hasattr(args, 'query') and args.query:
        print(f"检索文本: {args.query}")
    if hasattr(args, 'query_file') and args.query_file:
        print(f"查询文件: {args.query_file}")
    if args.category:
        print(f"分类检索: {args.category}")
    if args.from_md:
        print(f"Markdown文件: {args.from_md}")
        print(f"启用重排序: {'是' if args.enable_rerank else '否'}")
    print(f"返回数量: {args.top_k}")
    if args.min_rating:
        print(f"最低评分: {args.min_rating}")
    print("=" * 40)
    
    if not get_user_yes_no("确认开始检索?"):
        print("已取消检索")
        return None
    
    return args


def build_parser() -> argparse.ArgumentParser:
    """构建命令行解析器。

    Returns:
        argparse.ArgumentParser: 参数解析器实例。
    """
    parser = argparse.ArgumentParser(
        description='图书向量检索工具 - 支持命令行和交互式模式',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  交互式模式（推荐）:
    python scripts/retrieve_books.py --interactive
  
  文本检索:
    python scripts/retrieve_books.py --query "人工智能与伦理"
  从文件加载查询:
    python scripts/retrieve_books.py --query-file samples/query.txt
  分类检索:
    python scripts/retrieve_books.py --category H --top-k 5
  高级多查询:
    python scripts/retrieve_books.py --query-mode multi --from-md file.md --enable-rerank
        """
    )

    parser.add_argument(
        '--interactive',
        action='store_true',
        help='启动交互式模式，提供友好的菜单界面（推荐新手使用）'
    )
    parser.add_argument(
        '--config',
        type=str,
        default=DEFAULT_CONFIG_PATH,
        help='配置文件路径（默认: config/book_vectorization.yaml）'
    )
    parser.add_argument(
        '--query',
        type=str,
        help='直接提供的查询文本（仅文本检索模式使用）'
    )
    parser.add_argument(
        '--query-file',
        type=str,
        help='包含查询文本的文件路径（UTF-8 编码）'
    )
    parser.add_argument(
        '--category',
        type=str,
        help='分类检索使用的索书号首字母（例如: H 表示语言类）'
    )
    parser.add_argument(
        '--top-k',
        type=int,
        default=5,
        help='返回的结果数量（默认: 5）'
    )
    parser.add_argument(
        '--min-rating',
        type=float,
        default=None,
        help='文本检索时的最低豆瓣评分过滤值（可选）'
    )
    parser.add_argument(
        '--query-mode',
        choices=['single', 'multi'],
        default='single',
        help='检索模式：single 为单文本检索，multi 为多子查询融合'
    )
    parser.add_argument(
        '--from-md',
        type=str,
        help='多查询模式下，交叉分析 Markdown 文件路径'
    )
    parser.add_argument(
        '--per-query-top-k',
        type=int,
        default=None,
        help='多查询模式下单个子查询的候选数量（默认使用配置）'
    )
    parser.add_argument(
        '--enable-rerank',
        action='store_true',
        help='启用 SiliconFlow reranker 对融合结果重排序'
    )
    parser.add_argument(
        '--final-top-k',
        type=int,
        default=None,
        help='多查询模式下融合阶段最终返回的候选数量（默认使用配置）'
    )

    return parser


def _resolve_query_text(query: Optional[str], query_file: Optional[str]) -> str:
    """解析查询文本来源。

    Args:
        query: 直接传入的查询文本。
        query_file: 包含查询文本的文件路径。

    Returns:
        str: 去除首尾空白后的查询文本。

    Raises:
        FileNotFoundError: 当提供的文件不存在时抛出。
        ValueError: 当既未提供文本又未提供文件或内容为空时抛出。
    """
    if query:
        return query.strip()

    if query_file:
        file_path = Path(query_file)
        if not file_path.exists():
            raise FileNotFoundError(f"查询文件不存在: {query_file}")
        content = file_path.read_text(encoding='utf-8').strip()
        if not content:
            raise ValueError('查询文件内容为空')
        return content

    raise ValueError('必须提供 --query 或 --query-file 之一')


def _print_text_results(results: List[Dict]):
    """打印文本检索结果。

    Args:
        results: 检索返回的书籍结果列表。
    """
    print(SEPARATOR)
    print('📖 文本相似度检索结果')
    print(SEPARATOR)
    if not results:
        print('😔 未找到匹配书籍，请尝试调整查询或降低评分过滤。')
        return

    for idx, item in enumerate(results, start=1):
        similarity = item.get('similarity_score')
        similarity_str = f"{similarity:.4f}" if similarity is not None else 'N/A'
        print(f"[{idx}] 📚 {item.get('title', '未知')}")
        print(f"    👤 作者: {item.get('author', '未知')} | ⭐ 评分: {item.get('rating', '未知')} | 🎯 相似度: {similarity_str}")
        print(f"    🏷️  索书号: {item.get('call_no', '-')}")
        summary = item.get('summary', '')
        if summary:
            preview = summary[:120].replace('\n', ' ')
            print(f"    📝 简介: {preview}{'...' if len(summary) > 120 else ''}")
        print(f"    🆔 embedding_id: {item.get('embedding_id', '-')}")
        print('-' * 50)


def _print_category_results(results: List[Dict]):
    """打印分类检索结果。

    Args:
        results: 分类检索得到的书籍列表。
    """
    print(SEPARATOR)
    print('📂 分类检索结果')
    print(SEPARATOR)
    if not results:
        print('😔 该分类暂无完成向量化的高评分书籍。')
        return

    for idx, item in enumerate(results, start=1):
        print(f"[{idx}] 📚 {item.get('douban_title', '未知')}")
        print(f"    👤 作者: {item.get('douban_author', '未知')} | ⭐ 评分: {item.get('douban_rating', '未知')}")
        print(f"    🏷️  索书号: {item.get('call_no', '-')} | 📅 年份: {item.get('douban_pub_year', '-')}")
        print('-' * 50)


def _run_multi_query_flow(args: argparse.Namespace, retriever: BookRetriever) -> Dict:
    """执行 Markdown → 多子查询 → 融合 → 可选 rerank 的完整流程。"""

    if not args.from_md:
        raise ValueError('多查询模式必须提供 --from-md')

    print("🔄 正在解析Markdown文件并生成子查询...")
    query_package = build_query_package_from_md(args.from_md)
    logger.info(
        "已解析 Markdown: primary=%s, tags=%s, insight=%s, books=%s",
        len(query_package.primary),
        len(query_package.tags),
        len(query_package.insight),
        len(query_package.books),
    )

    print("🔍 正在执行多轮检索与融合...")
    results = retriever.search_multi_query(
        query_package=query_package,
        min_rating=args.min_rating,
        per_query_top_k=args.per_query_top_k,
        rerank=args.enable_rerank,
        final_top_k=args.final_top_k,
    )
    _print_text_results(results)
    
    if args.enable_rerank:
        print("✨ 已完成 SiliconFlow Reranker 重排序")
    
    return {
        'mode': 'multi',
        'results': results,
        'from_md': args.from_md,
        'query_package': query_package.as_dict(),
        'enable_rerank': args.enable_rerank,
    }


def run_cli(args: argparse.Namespace) -> Dict:
    """执行检索逻辑并输出结果。

    Args:
        args: 解析后的命令行参数。

    Returns:
        Dict: 包含检索模式与结果的上下文字典。

    Raises:
        ValueError: 当 top_k 非正数或缺少查询文本时抛出。
    """
    if args.top_k <= 0:
        raise ValueError('参数 --top-k 必须为正整数')
    if args.final_top_k is not None and args.final_top_k <= 0:
        raise ValueError('参数 --final-top-k 必须为正整数')

    retriever = BookRetriever(config_path=args.config)
    try:
        if args.category:
            logger.info(f"执行分类检索: category={args.category}, top_k={args.top_k}")
            results = retriever.search_by_category(args.category.upper(), top_k=args.top_k)
            _print_category_results(results)
            return {
                'mode': 'category',
                'results': results,
                'category': args.category.upper()
            }

        query_mode = args.query_mode
        if args.from_md:
            query_mode = 'multi'

        if query_mode == 'multi':
            return _run_multi_query_flow(args, retriever)
        else:
            # 单文本检索模式
            query_text = _resolve_query_text(args.query, args.query_file)
            logger.info(f"执行文本检索: query={query_text[:50]}..., top_k={args.top_k}")
            results = retriever.search_by_text(
                query_text=query_text,
                top_k=args.top_k,
                min_rating=args.min_rating
            )
            _print_text_results(results)
            return {
                'mode': 'single',
                'results': results,
                'query': query_text,
                'top_k': args.top_k,
                'min_rating': args.min_rating
            }

    except Exception as e:
        logger.error(f"检索过程中发生错误: {e}")
        raise


def main():
    """主函数"""
    parser = build_parser()
    args = parser.parse_args()

    # 交互式模式
    if args.interactive:
        try:
            interactive_args = interactive_mode()
            if interactive_args is None:
                return
            # 使用交互式模式的参数执行检索
            run_cli(interactive_args)
        except KeyboardInterrupt:
            print("\n\n👋 已取消操作，再见！")
        except Exception as e:
            print(f"\n❌ 交互式模式发生错误: {e}")
            logger.error(f"交互式模式错误: {e}")
    else:
        # 命令行模式
        try:
            run_cli(args)
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            logger.error(f"命令行模式错误: {e}")
            sys.exit(1)


if __name__ == '__main__':
    main()