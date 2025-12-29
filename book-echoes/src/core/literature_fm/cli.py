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
from src.core.literature_fm.pipeline import LiteratureFMPipeline
from src.core.literature_fm.theme_generator import ThemeGenerator

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
            print("3. 情境主题书架 (Phase 3)")
            print("4. 数据库向量化")
            print("0. 退出")
            print("=" * 60)

            choice = input("\n请选择功能 [0-4]: ").strip()

            if choice == '1':
                self._cmd_llm_tagging()
            elif choice == '2':
                self._cmd_theme_generation()
            elif choice == '3':
                self._cmd_theme_shelf()
            elif choice == '4':
                self._cmd_vectorize()
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

    def _cmd_theme_shelf(self):
        """情境主题书架命令"""
        theme_text = input("\n请输入情境主题描述: ").strip()

        if not theme_text:
            print("✗ 主题描述不能为空")
            return

        result = self.pipeline.generate_theme_shelf(
            theme_text=theme_text,
            use_vector=True,
            vector_weight=0.5,
            randomness=0.2
        )

        if result['success']:
            print(f"\n✓ 书架生成成功！")
            print(f"  - 推荐数量: {result['stats']['final_count']}")
            print(f"  - 输出文件: {result['output_file']}")
        else:
            print(f"\n✗ 生成失败: {result.get('error', '未知错误')}")

    def _cmd_vectorize(self):
        """数据库向量化命令"""
        from .db_vectorizer import vectorize_database

        print("\n【数据库向量化】")
        confirm = input("确认开始向量化? [y/N]: ").strip().lower()

        if confirm == 'y':
            stats = vectorize_database()
            print(f"\n✓ 向量化完成")
            print(f"  - 成功: {stats['success']}")
            print(f"  - 失败: {stats['failed']}")
        else:
            print("已取消")


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

    # LLM 打标
    python cli.py tag

    # 情境主题书架
    python cli.py shelf --theme "冬日暖阳，窝在沙发里阅读"
        """
    )

    parser.add_argument(
        'command',
        nargs='?',
        choices=['interactive', 'theme-gen', 'tag', 'shelf', 'vectorize'],
        help='子命令（不指定则进入交互式菜单）'
    )

    # 主题生成参数
    parser.add_argument('--random', action='store_true', help='随机生成主题')
    parser.add_argument('--direction', type=str, help='策划方向/关键词')
    parser.add_argument('--count', type=int, default=5, help='生成数量')

    # 书架生成参数
    parser.add_argument('--theme', type=str, help='情境主题描述')

    args = parser.parse_args()
    cli = LiteratureFMCLI()

    # 路由到对应功能
    if args.command == 'theme-gen':
        direction = "" if args.random else (args.direction or "")
        cli._generate_themes(direction=direction, count=args.count)
    elif args.command == 'tag':
        cli._cmd_llm_tagging()
    elif args.command == 'shelf':
        if not args.theme:
            print("✗ 请使用 --theme 参数指定主题描述")
            sys.exit(1)
        cli.pipeline.generate_theme_shelf(theme_text=args.theme)
    elif args.command == 'vectorize':
        cli._cmd_vectorize()
    else:
        # 默认进入交互式菜单
        cli.run_interactive()


if __name__ == "__main__":
    main()
