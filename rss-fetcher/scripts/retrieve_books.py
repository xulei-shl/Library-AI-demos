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
    python scripts/retrieve_books.py --query-file scripts/query-samples.txt --min-rating 8

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

from src.core.book_vectorization.output_formatter import OutputFormatter
from src.core.book_vectorization.query_assets import build_query_package_from_md
from src.core.book_vectorization.retriever import BookRetriever
from src.core.book_vectorization.json_parser import JsonParser
from src.core.book_vectorization.excel_exporter import ExcelExporter
from src.core.book_vectorization.theme_screener import ThemeScreener
from src.core.book_vectorization.excel_enhancer import ExcelEnhancer
from src.core.book_vectorization.recommendation_writer import RecommendationWriter
from src.utils.config_manager import ConfigManager
from src.utils.logger import get_logger
from src.utils.llm.client import UnifiedLLMClient

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
        "多查询检索 - 从Markdown文件生成多个子查询",
        "Excel导出 - 从JSON结果导出完整书籍信息到Excel",
        "大模型主题筛选 - 基于文章主题分析报告筛选书籍",
        "大模型推荐导语 - 根据文章分析报告和筛选书籍生成推荐导语"
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
    args.disable_llm_fallback = False
    args.disable_exact_match = False
    
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
            
        args.per_query_top_k = int(get_user_input("每个子查询候选数量", "15"))
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
    
    elif mode_choice == 3:  # Excel导出
        print("\n📊 Excel导出模式")
        
        json_file_path = get_user_input("请输入JSON结果文件路径", required=True)
        if not Path(json_file_path).exists():
            print(f"❌ 文件不存在: {json_file_path}")
            return None
        
        # 执行Excel导出
        try:
            # 初始化JSON解析器
            json_parser = JsonParser()
            book_ids = json_parser.extract_book_ids(json_file_path)
            
            if not book_ids:
                print("❌ 未能从JSON文件中提取到任何书籍ID")
                return None
            
            print(f"✅ 成功提取到{len(book_ids)}个书籍ID")
            
            # 初始化Excel导出器
            config_manager = ConfigManager(args.config)
            db_config = config_manager.get('database', {})
            excel_config = config_manager.get('excel_export', {})
            
            excel_exporter = ExcelExporter(db_config, excel_config)
            
            # 使用配置文件中的默认路径和文件名格式
            from datetime import datetime
            timestamp = datetime.now().strftime(excel_config.get('timestamp_format', '%Y%m%d_%H%M%S'))
            filename_template = excel_config.get('filename_template', 'books_full_info_{timestamp}')
            default_filename = filename_template.format(timestamp=timestamp)
            
            # 构建完整输出路径
            default_directory = Path(excel_config.get('default_directory', 'runtime/outputs/excel'))
            default_excel_path = default_directory / f"{default_filename}.xlsx"
            
            # 询问用户是否使用默认路径
            print(f"默认输出路径: {default_excel_path}")
            use_default_path = get_user_yes_no("是否使用默认输出路径?", default=True)
            
            if not use_default_path:
                excel_path = get_user_input("请输入自定义Excel输出路径", required=True)
            else:
                excel_path = str(default_excel_path)
            
            # 导出Excel
            output_file = excel_exporter.export_books_to_excel(book_ids, excel_path)
            print(f"✅ Excel导出完成: {output_file}")
            
            # 关闭资源
            excel_exporter.close()
            
            return None  # Excel导出模式不需要继续执行检索
            
        except Exception as e:
            print(f"❌ Excel导出失败: {e}")
            logger.error(f"Excel导出失败: {e}")
            return None
            
    elif mode_choice == 4:  # 大模型主题筛选
        print("\n🤖 大模型主题筛选模式")
        
        article_report_path = get_user_input("请输入文章主题分析报告文件路径", required=True)
        if not Path(article_report_path).exists():
            print(f"❌ 文件不存在: {article_report_path}")
            return None
            
        excel_path = get_user_input("请输入图书元数据Excel文件路径", required=True)
        if not Path(excel_path).exists():
            print(f"❌ 文件不存在: {excel_path}")
            return None
        
        # 执行主题筛选
        try:
            print("\n🔄 开始执行大模型主题筛选...")
            
            # 读取文章主题分析报告
            with open(article_report_path, 'r', encoding='utf-8') as f:
                article_report = f.read()
            
            print(f"✅ 成功读取文章主题分析报告: {len(article_report)} 字符")
            
            # 初始化Excel增强器
            excel_enhancer = ExcelEnhancer(excel_path)
            
            # 加载书籍数据
            books_data = excel_enhancer.load_books_data()
            print(f"✅ 成功加载{len(books_data)}本书籍数据")
            
            # 初始化LLM客户端和主题筛选器
            llm_client = UnifiedLLMClient()
            theme_screener = ThemeScreener(llm_client, {})
            
            # 批量评估书籍
            print("\n🔍 开始批量评估书籍...")
            results = theme_screener.evaluate_books_batch(article_report, books_data)
            
            # 统计结果
            selected_count = sum(1 for r in results if r.get("is_selected", False))
            success_count = sum(1 for r in results if r.get("llm_status") == "success")
            
            print(f"\n📊 筛选结果统计:")
            print(f"  总书籍数: {len(books_data)}")
            print(f"  评估成功: {success_count}")
            print(f"  通过筛选: {selected_count}")
            print(f"  筛选通过率: {selected_count/len(books_data)*100:.1f}%")
            
            # 添加评估结果到Excel
            print("\n📝 正在将评估结果添加到Excel文件...")
            enhanced_excel_path = excel_enhancer.add_evaluation_results(results)
            
            # 生成摘要报告
            failed_books = excel_enhancer.get_failed_books()
            if failed_books:
                summary_path = excel_enhancer.create_summary_report()
                if summary_path:  # 检查是否成功生成报告
                    print(f"⚠️ 有{len(failed_books)}本书籍评估失败，已生成摘要报告: {summary_path}")
                else:
                    print(f"⚠️ 有{len(failed_books)}本书籍评估失败，但摘要报告生成失败")
            
            print(f"✅ 主题筛选完成，增强后的Excel文件: {enhanced_excel_path}")
            
            return None  # 主题筛选模式不需要继续执行检索
            
        except Exception as e:
            print(f"❌ 主题筛选失败: {e}")
            logger.error(f"主题筛选失败: {e}")
            return None
            
    elif mode_choice == 5:  # 大模型推荐导语
        print("\n✍️ 大模型推荐导语模式")
        
        article_report_path = get_user_input("请输入文章分析报告文件路径", required=True)
        if not Path(article_report_path).exists():
            print(f"❌ 文件不存在: {article_report_path}")
            return None
            
        excel_path = get_user_input("请输入图书元数据Excel文件路径", required=True)
        if not Path(excel_path).exists():
            print(f"❌ 文件不存在: {excel_path}")
            return None
        
        # 执行推荐导语生成
        try:
            print("\n🔄 开始生成推荐导语...")
            
            # 初始化推荐导语生成器
            llm_client = UnifiedLLMClient()
            recommendation_writer = RecommendationWriter(llm_client, {})
            
            # 生成推荐导语
            recommendation_path = recommendation_writer.generate_recommendation(
                article_report_path, excel_path
            )
            
            print(f"✅ 推荐导语生成完成: {recommendation_path}")
            
            return None
            
        except Exception as e:
            print(f"❌ 推荐导语生成失败: {e}")
            logger.error(f"推荐导语生成失败: {e}")
            return None
    
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
        print(f"返回数量: {args.final_top_k}")
    else:
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
    parser.add_argument(
        '--disable-llm-fallback',
        action='store_true',
        help='禁用 Markdown 解析失败时的 LLM 兜底流程'
    )
    parser.add_argument(
        '--disable-exact-match',
        action='store_true',
        help='禁用关键词/书名精确匹配分支（仅在精确匹配开启时生效）'
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


def _print_text_results(results: List[Dict], extra_field_name: str = None):
    """打印文本检索结果。

    Args:
        results: 检索返回的书籍结果列表。
        extra_field_name: 可选的额外字段名（用于精确匹配标注）。
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
        fused = item.get('fused_score')
        fused_str = f"{fused:.4f}" if fused is not None else ''
        extra_info = item.get(extra_field_name, '') if extra_field_name else ''
        title = item.get('title', '未知')
        print(f"[{idx}] 📚 {title}{extra_info}")
        detail = f"👤 作者: {item.get('author', '未知')} | ⭐ 评分: {item.get('rating', '未知')}"
        if fused_str:
            detail += f" | 🎯 融合: {fused_str}"
        detail += f" | 相似度: {similarity_str}"
        print(f"    {detail}")
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


def _run_multi_query_flow(args: argparse.Namespace, retriever: BookRetriever, output_formatter: OutputFormatter) -> Dict:
    """执行 Markdown → 多子查询 → 融合 → 可选 rerank 的完整流程。"""

    if not args.from_md:
        raise ValueError('多查询模式必须提供 --from-md')

    print("🔄 正在解析Markdown文件并生成子查询...")
    query_package = build_query_package_from_md(
        args.from_md,
        enable_llm_fallback=not getattr(args, "disable_llm_fallback", False),
    )
    # 若 CLI 要求禁用精确匹配，则设置标记，供检索器读取
    query_package.disable_exact_match = getattr(args, "disable_exact_match", False)

    logger.info(
        "已解析 Markdown(origin=%s): primary=%s, tags=%s, insight=%s, books=%s",
        query_package.origin,
        len(query_package.primary),
        len(query_package.tags),
        len(query_package.insight),
        len(query_package.books),
    )
    if query_package.origin == "llm_recovered":
        print("⚠️ Markdown 结构未匹配，已调用 LLM 兜底生成查询")
        latency = query_package.metadata.get("llm_latency_ms")
        if latency:
            print(f"    ⏱️ LLM 耗时: {latency} ms")

    print("🔍 正在执行多轮检索与融合...")
    logger.info(
        "开始多查询检索: md=%s, per_query_top_k=%s, final_top_k=%s, min_rating=%s, rerank=%s, disable_exact_match=%s",
        args.from_md,
        args.per_query_top_k,
        args.final_top_k,
        args.min_rating,
        args.enable_rerank,
        getattr(args, "disable_exact_match", False),
    )
    results = retriever.search_multi_query(
        query_package=query_package,
        min_rating=args.min_rating,
        per_query_top_k=args.per_query_top_k,
        rerank=args.enable_rerank,
        final_top_k=args.final_top_k,
    )
    exact_hits = sum(1 for item in results if item.get('match_source'))
    logger.info(
        "多查询检索完成: total_results=%s, exact_match_hits=%s, rerank=%s",
        len(results),
        exact_hits,
        args.enable_rerank,
    )
    # 精确命中标注
    for item in results:
        source = item.get('match_source')
        if source:
            item['display_source'] = f" ({({'title': '标题', 'author': '作者', 'custom_keywords': '关键词'}.get(source, source))}精确命中)"
        else:
            item['display_source'] = ''
    _print_text_results(results, extra_field_name='display_source')
    
    if args.enable_rerank:
        print("✨ 已完成 SiliconFlow Reranker 重排序")
    
    # 构建元数据并保存结果
    metadata = {
        'mode': 'multi',
        'from_md': args.from_md,
        'query_package_origin': query_package.origin,
        'enable_rerank': args.enable_rerank,
        'disable_exact_match': getattr(args, 'disable_exact_match', False),
        'min_rating': args.min_rating,
        'per_query_top_k': args.per_query_top_k,
        'final_top_k': args.final_top_k
    }
    saved_files = _save_results_if_enabled(output_formatter, results, metadata)
    
    # 询问是否执行Excel导出
    if get_user_yes_no("是否执行完整元数据检索并导出Excel文件?"):
        try:
            print("\n📊 开始执行完整元数据检索和Excel导出...")
            
            # 从保存的JSON文件中提取book_id
            json_file_path = None
            if saved_files and 'json' in saved_files:
                json_file_path = saved_files['json']
            else:
                # 如果没有保存JSON文件，直接从结果中提取book_id
                book_ids = []
                for item in results:
                    if 'book_id' in item:
                        book_ids.append(item['book_id'])
                
                if not book_ids:
                    print("❌ 未能从检索结果中提取到任何书籍ID")
                    return {
                        'mode': 'multi',
                        'results': results,
                        'from_md': args.from_md,
                        'query_package': query_package.as_dict(),
                        'query_package_origin': query_package.origin,
                        'query_package_metadata': dict(query_package.metadata),
                        'enable_rerank': args.enable_rerank,
                        'disable_exact_match': getattr(args, 'disable_exact_match', False),
                    }
                
                # 使用配置文件中的默认路径和文件名格式
                from datetime import datetime
                config_manager = ConfigManager(args.config)
                excel_config = config_manager.get('excel_export', {})
                
                timestamp = datetime.now().strftime(excel_config.get('timestamp_format', '%Y%m%d_%H%M%S'))
                filename_template = excel_config.get('filename_template', 'books_full_info_{timestamp}')
                default_filename = filename_template.format(timestamp=timestamp)
                
                # 构建完整输出路径
                default_directory = Path(excel_config.get('default_directory', 'runtime/outputs/excel'))
                default_excel_path = default_directory / f"{default_filename}.xlsx"
                
                # 初始化Excel导出器
                db_config = config_manager.get('database', {})
                excel_exporter = ExcelExporter(db_config, excel_config)
                
                # 导出Excel
                output_file = excel_exporter.export_books_to_excel(book_ids, str(default_excel_path))
                print(f"✅ Excel导出完成: {output_file}")
                
                # 关闭资源
                excel_exporter.close()
                
                return {
                    'mode': 'multi',
                    'results': results,
                    'from_md': args.from_md,
                    'query_package': query_package.as_dict(),
                    'query_package_origin': query_package.origin,
                    'query_package_metadata': dict(query_package.metadata),
                    'enable_rerank': args.enable_rerank,
                    'disable_exact_match': getattr(args, 'disable_exact_match', False),
                    'excel_export_path': output_file
                }
            
            # 如果有保存的JSON文件，使用JSON解析器
            if json_file_path:
                json_parser = JsonParser()
                book_ids = json_parser.extract_book_ids(json_file_path)
                
                if not book_ids:
                    print("❌ 未能从JSON文件中提取到任何书籍ID")
                    return {
                        'mode': 'multi',
                        'results': results,
                        'from_md': args.from_md,
                        'query_package': query_package.as_dict(),
                        'query_package_origin': query_package.origin,
                        'query_package_metadata': dict(query_package.metadata),
                        'enable_rerank': args.enable_rerank,
                        'disable_exact_match': getattr(args, 'disable_exact_match', False),
                    }
                
                print(f"✅ 成功提取到{len(book_ids)}个书籍ID")
                
                # 初始化Excel导出器
                config_manager = ConfigManager(args.config)
                db_config = config_manager.get('database', {})
                excel_config = config_manager.get('excel_export', {})
                
                excel_exporter = ExcelExporter(db_config, excel_config)
                
                # 使用配置文件中的默认路径和文件名格式
                from datetime import datetime
                timestamp = datetime.now().strftime(excel_config.get('timestamp_format', '%Y%m%d_%H%M%S'))
                filename_template = excel_config.get('filename_template', 'books_full_info_{timestamp}')
                default_filename = filename_template.format(timestamp=timestamp)
                
                # 构建完整输出路径
                default_directory = Path(excel_config.get('default_directory', 'runtime/outputs/excel'))
                default_excel_path = default_directory / f"{default_filename}.xlsx"
                
                # 询问用户是否使用默认路径
                print(f"默认输出路径: {default_excel_path}")
                use_default_path = get_user_yes_no("是否使用默认输出路径?", default=True)
                
                if not use_default_path:
                    excel_path = get_user_input("请输入自定义Excel输出路径", required=True)
                else:
                    excel_path = str(default_excel_path)
                
                # 导出Excel
                output_file = excel_exporter.export_books_to_excel(book_ids, excel_path)
                print(f"✅ Excel导出完成: {output_file}")
                
                # 关闭资源
                excel_exporter.close()
                
                return {
                    'mode': 'multi',
                    'results': results,
                    'from_md': args.from_md,
                    'query_package': query_package.as_dict(),
                    'query_package_origin': query_package.origin,
                    'query_package_metadata': dict(query_package.metadata),
                    'enable_rerank': args.enable_rerank,
                    'disable_exact_match': getattr(args, 'disable_exact_match', False),
                    'excel_export_path': output_file
                }
                
        except Exception as e:
            print(f"❌ Excel导出失败: {e}")
            logger.error(f"Excel导出失败: {e}")
    
    return {
        'mode': 'multi',
        'results': results,
        'from_md': args.from_md,
        'query_package': query_package.as_dict(),
        'query_package_origin': query_package.origin,
        'query_package_metadata': dict(query_package.metadata),
        'enable_rerank': args.enable_rerank,
        'disable_exact_match': getattr(args, 'disable_exact_match', False),
    }


def _save_results_if_enabled(output_formatter: OutputFormatter, results: List[Dict], metadata: Dict) -> Dict:
    """如果启用了输出功能，则保存检索结果
    
    Args:
        output_formatter: 输出格式化器实例
        results: 检索结果列表
        metadata: 元数据字典
        
    Returns:
        Dict: 保存的文件路径字典，格式为 {format_name: file_path}
    """
    saved_files = {}
    try:
        saved_files = output_formatter.save_results(results, metadata)
        if saved_files:
            print("\n📄 检索结果已保存到文件:")
            for format_name, file_path in saved_files.items():
                print(f"  {format_name.upper()}: {file_path}")
            print()
    except Exception as e:
        logger.error(f"保存检索结果时发生错误: {e}")
        print(f"\n⚠️ 保存检索结果失败: {e}")
    
    return saved_files


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

    # 初始化检索器
    retriever = BookRetriever(config_path=args.config)
    
    # 初始化输出格式化器
    config_manager = ConfigManager(args.config)
    output_config = config_manager.get('output', {})
    output_formatter = OutputFormatter(output_config)
    
    try:
        if args.category:
            logger.info(f"执行分类检索: category={args.category}, top_k={args.top_k}")
            results = retriever.search_by_category(args.category.upper(), top_k=args.top_k)
            _print_category_results(results)
            
            # 构建元数据并保存结果
            metadata = {
                'mode': 'category',
                'category': args.category.upper(),
                'top_k': args.top_k
            }
            _save_results_if_enabled(output_formatter, results, metadata)
            
            return {
                'mode': 'category',
                'results': results,
                'category': args.category.upper()
            }

        query_mode = args.query_mode
        if args.from_md:
            query_mode = 'multi'

        if query_mode == 'multi':
            return _run_multi_query_flow(args, retriever, output_formatter)
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
            
            # 构建元数据并保存结果
            metadata = {
                'mode': 'single',
                'query': query_text,
                'top_k': args.top_k,
                'min_rating': args.min_rating
            }
            _save_results_if_enabled(output_formatter, results, metadata)
            
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
