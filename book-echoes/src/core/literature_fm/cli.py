"""
Literature_FM 模块统一 CLI 入口
支持交互式菜单和子命令两种方式
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
root_dir = Path(__file__).absolute().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.utils.logger import get_logger
from src.core.literature_fm.literature_fm_orchestrator import LiteratureFMPipeline
from src.core.literature_fm.theme_generator import ThemeGenerator
from src.core.literature_fm.query_translator import QueryTranslator

logger = get_logger(__name__)


class LiteratureFMCLI:
    """Literature_FM 模块 CLI"""

    def __init__(self):
        self.pipeline = LiteratureFMPipeline()
        self.config = self.pipeline.config

    def run_interactive(self):
        """交互式菜单模式"""
        while True:
            print("\n" + "=" * 60)
            print("Literature_FM 模块 - 功能菜单")
            print("=" * 60)
            print("1. LLM 打标 (Phase 2)")
            print("2. 生成策划主题 (Phase 2.5)")
            print("3. 查询意图转换 (Phase 2.6)")
            print("4. 情境主题检索 (Phase 3)")
            print("5. 数据库向量化")
            print("6. 候选图书 LLM 筛选 (Phase 3.5)")
            print("0. 退出")
            print("=" * 60)

            choice = input("\n请选择功能 [0-6]: ").strip()

            if choice == '1':
                self._cmd_llm_tagging()
            elif choice == '2':
                self._cmd_theme_generation()
            elif choice == '3':
                self._cmd_query_translation()
            elif choice == '4':
                self._cmd_theme_shelf()
            elif choice == '5':
                self._cmd_vectorize()
            elif choice == '6':
                self._cmd_candidate_filter()
            elif choice == '0':
                print("再见！")
                break
            else:
                print("✗ 无效选择，请重试")

    def _cmd_theme_generation(self):
        """主题生成命令（交互式）"""
        print("\n【文学策划主题生成】")
        print("1. 随机生成")
        print("2. 基于关键词生成")

        mode = input("\n请选择模式 [1-2]: ").strip()

        if mode == '1':
            count_input = input("生成数量 (默认5): ").strip()
            count = int(count_input) if count_input.isdigit() else 5
            self._generate_themes(direction="", count=count)
        elif mode == '2':
            direction = input("请输入策划方向/关键词: ").strip()
            count_input = input("生成数量 (默认5): ").strip()
            count = int(count_input) if count_input.isdigit() else 5
            self._generate_themes(direction=direction, count=count)
        else:
            print("✗ 无效选择")

    def _generate_themes(self, direction: str, count: int):
        """执行主题生成"""
        try:
            # 检查功能是否启用
            theme_gen_config = self.config.get('theme_generation', {})
            if not theme_gen_config.get('enabled', False):
                print("\n✗ 主题生成功能未启用，请在配置文件中设置 theme_generation.enabled = true")
                return

            generator = ThemeGenerator(theme_gen_config)
            result = generator.generate_themes(direction=direction, count=count)

            if result['success']:
                print(f"\n✓ 主题生成成功！")
                print(f"  - 数量: {result['count']}")
                print(f"  - 文件: {result['output_file']}")

                # 打印主题预览
                print("\n主题预览:")
                for i, theme in enumerate(result['themes'], 1):
                    print(f"\n{i}. {theme['theme_name']}")
                    print(f"   {theme['slogan']}")
            else:
                print(f"\n✗ 生成失败: {result.get('error', '未知错误')}")

        except Exception as e:
            logger.error(f"主题生成异常: {e}", exc_info=True)
            print(f"\n✗ 异常: {str(e)}")

    def _cmd_llm_tagging(self):
        """LLM 打标命令"""
        success = self.pipeline.run_llm_tagging()
        if success:
            print("\n✓ LLM 打标完成")
        else:
            print("\n✗ LLM 打标失败")

    def _cmd_query_translation(self):
        """查询意图转换命令（交互式）"""
        print("\n【查询意图转换】")
        print("1. 从 Excel 文件转换（筛选候选状态为'通过'的主题）")
        print("2. 从 JSON 文件转换")
        print("3. 手动输入单个主题")

        mode = input("\n请选择模式 [1-3]: ").strip()

        if mode == '1':
            file_path = input("请输入 Excel 文件路径: ").strip()
            if not file_path:
                print("✗ 文件路径不能为空")
                return
            self._translate_from_excel(file_path)
        elif mode == '2':
            file_path = input("请输入 JSON 文件路径: ").strip()
            if not file_path:
                print("✗ 文件路径不能为空")
                return
            self._translate_from_json(file_path)
        elif mode == '3':
            self._translate_single_theme()
        else:
            print("✗ 无效选择")

    def _translate_from_excel(self, file_path: str):
        """从 Excel 文件转换"""
        try:
            translator = QueryTranslator(self.config)
            print(f"\n正在读取 Excel: {file_path}")

            result = translator.translate_from_excel(
                excel_path=file_path,
                status_column="候选状态",
                status_value="通过"
            )

            if result['success']:
                print(f"\n✓ 转换成功！")
                print(f"  - 处理数量: {result['processed']}")
                print(f"  - 输出文件: {result['output_file']}")

                # 预览第一个结果
                if result['results']:
                    first = result['results'][0]
                    print(f"\n预览第一个结果:")
                    print(f"  主题: {first['original_theme']['theme_name']}")
                    print(f"  关键词: {first.get('search_keywords', [])}")
                    print(f"  过滤条件: {len(first.get('filter_conditions', []))} 条")
            else:
                print(f"\n✗ 转换失败: {result.get('error', '未知错误')}")

        except Exception as e:
            logger.error(f"Excel 转换异常: {e}", exc_info=True)
            print(f"\n✗ 异常: {str(e)}")

    def _translate_from_json(self, file_path: str):
        """从 JSON 文件转换"""
        try:
            translator = QueryTranslator(self.config)
            print(f"\n正在读取 JSON: {file_path}")

            result = translator.translate_from_json(file_path)

            if result['success']:
                print(f"\n✓ 转换成功！")
                print(f"  - 处理数量: {result['processed']}")
                print(f"  - 输出文件: {result['output_file']}")

                # 预览第一个结果
                if result['results']:
                    first = result['results'][0]
                    print(f"\n预览第一个结果:")
                    print(f"  主题: {first['original_theme']['theme_name']}")
                    print(f"  关键词: {first.get('search_keywords', [])}")
                    print(f"  过滤条件: {len(first.get('filter_conditions', []))} 条")
            else:
                print(f"\n✗ 转换失败: {result.get('error', '未知错误')}")

        except Exception as e:
            logger.error(f"JSON 转换异常: {e}", exc_info=True)
            print(f"\n✗ 异常: {str(e)}")

    def _translate_single_theme(self):
        """手动输入单个主题转换"""
        print("\n【单个主题转换】")
        theme_name = input("主题名称: ").strip()
        slogan = input("副标题/推荐语: ").strip()
        description = input("情境描述: ").strip()
        target_vibe = input("预期氛围: ").strip()

        if not theme_name or not description:
            print("✗ 主题名称和情境描述不能为空")
            return

        try:
            translator = QueryTranslator(self.config)
            print(f"\n正在转换主题: {theme_name}")

            result = translator.translate_theme(
                theme_name=theme_name,
                slogan=slogan,
                description=description,
                target_vibe=target_vibe
            )

            if not result.get('is_fallback'):
                print(f"\n✓ 转换成功！")
                print(f"  关键词: {result.get('search_keywords', [])}")
                print(f"  过滤条件: {len(result.get('filter_conditions', []))} 条")
                print(f"  合成查询: {result.get('synthetic_query', '')[:100]}...")
            else:
                print(f"\n⚠ 转换使用兜底结果")
                print(f"  错误: {result.get('error', '')}")

        except Exception as e:
            logger.error(f"单主题转换异常: {e}", exc_info=True)
            print(f"\n✗ 异常: {str(e)}")

    def _cmd_theme_shelf(self):
        """情境主题检索命令（混合检索 + RRF融合）"""
        print("\n【情境主题检索（混合检索）】")
        print("请选择输入方式:")
        print("1. 自然语言主题（将自动调用QueryTranslator转换）")
        print("2. 已转换的JSON文件（QueryTranslator的输出）")

        choice = input("\n请选择 [1-2]: ").strip()

        if choice == '1':
            self._theme_shelf_from_text()
        elif choice == '2':
            self._theme_shelf_from_json()
        else:
            print("✗ 无效选择")

    def _theme_shelf_from_text(self):
        """从自然语言主题进行检索"""
        theme_text = input("\n请输入情境主题描述: ").strip()

        if not theme_text:
            print("✗ 主题描述不能为空")
            return

        try:
            # 先调用QueryTranslator转换
            translator = QueryTranslator(self.config)
            print(f"\n正在转换查询意图...")

            result = translator.translate_theme(
                theme_name=theme_text[:30],  # 使用前30字符作为主题名
                slogan="",
                description=theme_text,
                target_vibe=""
            )

            if result.get('is_fallback'):
                print(f"\n⚠ 查询转换使用兜底结果: {result.get('error', '')}")

            # 使用转换后的查询进行检索
            translated_queries = [result]
            self._run_hybrid_search(translated_queries)

        except Exception as e:
            logger.error(f"主题检索异常: {e}", exc_info=True)
            print(f"\n✗ 异常: {str(e)}")

    def _theme_shelf_from_json(self):
        """从JSON文件进行检索"""
        import json

        file_path = input("\n请输入JSON文件路径: ").strip()

        if not file_path:
            print("✗ 文件路径不能为空")
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 支持两种格式
            if 'queries' in data:
                # QueryTranslator的输出格式
                translated_queries = data['queries']
            else:
                # 直接是查询列表
                translated_queries = data if isinstance(data, list) else [data]

            print(f"\n加载了 {len(translated_queries)} 个查询")
            self._run_hybrid_search(translated_queries)

        except FileNotFoundError:
            print(f"✗ 文件不存在: {file_path}")
        except json.JSONDecodeError as e:
            print(f"✗ JSON格式错误: {str(e)}")
        except Exception as e:
            logger.error(f"JSON加载异常: {e}", exc_info=True)
            print(f"\n✗ 异常: {str(e)}")

    def _run_hybrid_search(self, translated_queries: list):
        """执行混合检索"""
        try:
            result = self.pipeline.generate_theme_shelf(
                translated_queries=translated_queries
            )

            if result['success']:
                print(f"\n✓ 混合检索成功！")
                print(f"  - 主题数量: {len(result['themes'])}")
                print(f"  - 总推荐书籍: {result['total_books']}")
                print(f"  - 输出文件: {result['output_file']}")

                # 打印每个主题的统计
                for theme_result in result['themes']:
                    theme = theme_result['theme']
                    stats = theme_result['stats']
                    print(f"\n  主题: {theme.get('theme_name', '')}")
                    print(f"    向量召回: {stats['vector_count']} 本")
                    print(f"    BM25召回: {stats['bm25_count']} 本")
                    print(f"    最终推荐: {stats['final_count']} 本")
            else:
                print(f"\n✗ 检索失败: {result.get('error', '未知错误')}")

        except Exception as e:
            logger.error(f"混合检索异常: {e}", exc_info=True)
            print(f"\n✗ 异常: {str(e)}")

    def _theme_shelf_from_json_file(self, file_path: str):
        """从JSON文件进行检索（命令行参数调用）"""
        import json

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 支持两种格式
            if 'queries' in data:
                translated_queries = data['queries']
            else:
                translated_queries = data if isinstance(data, list) else [data]

            print(f"加载了 {len(translated_queries)} 个查询")
            self._run_hybrid_search(translated_queries)

        except FileNotFoundError:
            print(f"✗ 文件不存在: {file_path}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"✗ JSON格式错误: {str(e)}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"JSON加载异常: {e}", exc_info=True)
            print(f"✗ 异常: {str(e)}")
            sys.exit(1)

    def _theme_shelf_from_text_direct(self, theme_text: str):
        """从自然语言主题进行检索（命令行参数调用）"""
        try:
            translator = QueryTranslator(self.config)
            print(f"正在转换查询意图...")

            result = translator.translate_theme(
                theme_name=theme_text[:30],
                slogan="",
                description=theme_text,
                target_vibe=""
            )

            if result.get('is_fallback'):
                print(f"⚠ 查询转换使用兜底结果: {result.get('error', '')}")

            translated_queries = [result]
            self._run_hybrid_search(translated_queries)

        except Exception as e:
            logger.error(f"主题检索异常: {e}", exc_info=True)
            print(f"✗ 异常: {str(e)}")
            sys.exit(1)

    def _cmd_vectorize(self):
        """数据库向量化命令"""
        from src.core.literature_fm.db_vectorizer import (
            vectorize_database, get_vectorize_status, clear_vector_collection
        )

        print("\n【数据库向量化】")
        print("1. 查看向量化状态")
        print("2. 清空旧数据（破坏性操作）")
        print("3. 重新向量化")

        choice = input("\n请选择 [1-3]: ").strip()

        if choice == '1':
            status = get_vectorize_status()
            print("\n" + "="*50)
            print("向量化状态")
            print("="*50)
            print(f"  已打标总数: {status['total_tagged']}")
            print(f"  已向量化: {status['vectorized']}")
            print(f"  待向量化: {status['pending']}")
            print(f"  失败: {status['failed']}")
            print(f"  进度: {status['progress']}%")
            print("="*50)

        elif choice == '2':
            print("\n【清空向量数据库】")
            print("⚠️  警告：此操作将删除所有向量数据，不可恢复！")
            confirm = input("\n确认清空? 请输入 'YES_I_CONFIRM': ").strip()

            if confirm == "YES_I_CONFIRM":
                if clear_vector_collection():
                    print("\n✓ 向量数据库已清空")
                else:
                    print("\n✗ 清空失败，请查看日志")
            else:
                print("已取消")

        elif choice == '3':
            print("\n【重新向量化】")
            batch_input = input("批次大小 (默认50): ").strip()
            batch_size = int(batch_input) if batch_input.isdigit() else 50

            confirm = input(f"\n确认开始向量化 (批次={batch_size})? [y/N]: ").strip().lower()

            if confirm == 'y':
                stats = vectorize_database(batch_size=batch_size)
                print(f"\n✓ 向量化完成")
                print(f"  - 总处理: {stats['total']} 本")
                print(f"  - 成功: {stats['success']}")
                print(f"  - 失败: {stats['failed']}")
                print(f"  - 跳过: {stats['skipped']}")
            else:
                print("已取消")

        else:
            print("✗ 无效选择")

    def _cmd_candidate_filter(self):
        """候选图书 LLM 筛选命令"""
        print("\n【候选图书 LLM 筛选（Phase 3.5）】")
        file_path = input("请输入候选图书 Excel 文件路径: ").strip()

        if not file_path:
            print("✗ 文件路径不能为空")
            return

        self._filter_candidates_from_excel(file_path)

    def _filter_candidates_from_excel(self, file_path: str):
        """从 Excel 筛选候选图书"""
        try:
            from src.core.literature_fm.candidate_filter import CandidateFilter

            filter_config = self.config.get('candidate_filter', {})
            if not filter_config.get('enabled', False):
                print("\n✗ 候选筛选功能未启用，请在配置文件中设置 candidate_filter.enabled = true")
                return

            filter_instance = CandidateFilter(filter_config)
            print(f"\n正在读取 Excel: {file_path}")

            result = filter_instance.filter_from_excel(file_path)

            if result['success']:
                print(f"\n✓ 筛选完成！")
                print(f"  - 处理数量: {result['processed']}")
                print(f"  - 通过筛选: {result['passed']}")
                print(f"  - 分组数量: {result['groups']}")
                print(f"  - 输出文件: {result['output_file']}")
            else:
                print(f"\n✗ 筛选失败: {result.get('error', '未知错误')}")

        except Exception as e:
            logger.error(f"候选筛选异常: {e}", exc_info=True)
            print(f"\n✗ 异常: {str(e)}")


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description='Literature_FM 模块 CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 交互式菜单
    python cli.py

    # 生成主题（随机）
    python cli.py theme-gen --random --count 5

    # 生成主题（关键词）
    python cli.py theme-gen --direction "冬日治愈" --count 3

    # 查询意图转换（Excel）
    python cli.py query-trans --excel themes.xlsx

    # 查询意图转换（JSON）
    python cli.py query-trans --json themes.json

    # LLM 打标
    python cli.py tag

    # 情境主题检索
    python cli.py shelf --theme "冬日暖阳，窝在沙发里阅读"
        """
    )

    parser.add_argument(
        'command',
        nargs='?',
        choices=['interactive', 'theme-gen', 'query-trans', 'tag', 'shelf', 'vectorize'],
        help='子命令（不指定则进入交互式菜单）'
    )

    # 主题生成参数
    parser.add_argument('--random', action='store_true', help='随机生成主题')
    parser.add_argument('--direction', type=str, help='策划方向/关键词')
    parser.add_argument('--count', type=int, default=5, help='生成数量')

    # 查询转换参数
    parser.add_argument('--excel', type=str, help='Excel 文件路径（查询转换）')
    parser.add_argument('--json', type=str, help='JSON 文件路径（查询转换）')
    parser.add_argument('--status-col', type=str, default='候选状态', help='状态列名（Excel）')
    parser.add_argument('--status-val', type=str, default='通过', help='状态值（Excel）')

    # 书架生成参数
    parser.add_argument('--theme', type=str, help='情境主题描述')
    parser.add_argument('--query-json', type=str, help='已转换的JSON文件路径')

    args = parser.parse_args()
    cli = LiteratureFMCLI()

    # 路由到对应功能
    if args.command == 'theme-gen':
        direction = "" if args.random else (args.direction or "")
        cli._generate_themes(direction=direction, count=args.count)
    elif args.command == 'query-trans':
        if args.excel:
            cli._translate_from_excel(args.excel)
        elif args.json:
            cli._translate_from_json(args.json)
        else:
            print("✗ 请使用 --excel 或 --json 参数指定输入文件")
            sys.exit(1)
    elif args.command == 'tag':
        cli._cmd_llm_tagging()
    elif args.command == 'shelf':
        # 支持两种输入方式
        if args.query_json:
            # 从JSON文件加载已转换的查询
            cli._theme_shelf_from_json_file(args.query_json)
        elif args.theme:
            # 从自然语言主题转换并检索
            cli._theme_shelf_from_text_direct(args.theme)
        else:
            print("✗ 请使用 --theme 或 --query-json 参数指定输入")
            sys.exit(1)
    elif args.command == 'vectorize':
        cli._cmd_vectorize()
    else:
        # 默认进入交互式菜单
        cli.run_interactive()


if __name__ == "__main__":
    main()
