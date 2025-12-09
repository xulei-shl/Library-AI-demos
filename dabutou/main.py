"""
主程序入口
负责协调各个模块完成爬取任务
支持CiNii和WorldCat两个爬虫的独立运行和批量运行
"""
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List
import time

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.utils.logger_config import get_logger, LoggerConfig
from src.core.keyword_processor import KeywordProcessor
from src.scrapers.cinii_scraper import CiNiiScraper
from src.core.worldcat_app import WorldCatApp
from src.utils.excel_reader import ExcelReader
from src.utils.excel_writer import ExcelWriter


class BookScraperApp:
    """图书爬虫应用程序（CiNii专用）"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = get_logger('BookScraperApp', self.config.get('log_dir', 'logs'))
        self.keyword_processor = KeywordProcessor()
        self.setup_scraper()

    def setup_scraper(self):
        """设置爬虫实例"""
        # CiNii爬虫
        scraper_config = self.config.get('cinii', {})
        self.scraper = CiNiiScraper(scraper_config)

    def process_excel(self, excel_path: str, isbn_col: str = 'ISBN', title_col: str = '题名',
                     sheet_name: str = 0, real_time_save: bool = True) -> bool:
        """
        处理Excel文件
        Args:
            excel_path: Excel文件路径
            isbn_col: ISBN列名
            title_col: 题名列名
            sheet_name: 工作表名称或索引
            real_time_save: 是否实时保存
        Returns:
            是否成功完成
        """
        try:
            self.logger.info(f"开始处理Excel文件: {excel_path}")

            # 初始化读写器
            reader = ExcelReader(excel_path)
            writer = ExcelWriter(excel_path)

            # 获取行数据迭代器
            rows_iterator = reader.get_rows_with_keywords(isbn_col, title_col, sheet_name)

            total_rows = 0
            successful_rows = 0
            failed_rows = 0

            # 处理每一行数据
            for row_index, row_data in rows_iterator:
                total_rows += 1
                self.logger.info(f"处理第 {row_index + 1} 行 (总计 {total_rows} 行)")

                try:
                    # 提取关键词列表（支持多个ISBN分别搜索）
                    keywords_list = self.keyword_processor.extract_keywords_list(
                        row_data.get(isbn_col, ''),
                        row_data.get(title_col, '')
                    )

                    if not keywords_list:
                        self.logger.warning(f"第 {row_index + 1} 行: 没有有效的关键词")
                        result = {
                            'row_index': row_index,
                            'keyword_type': 'none',
                            'keyword_value': '',
                            'success': False,
                            'error_message': '没有有效的关键词',
                            'libraries': [],
                            'libraries_count': 0,
                            'original_isbn': row_data.get(isbn_col, ''),
                            'original_title': row_data.get(title_col, '')
                        }
                    else:
                        # 合并所有关键词的搜索结果
                        all_libraries = []
                        all_search_urls = []
                        all_detail_urls = []
                        keyword_type = keywords_list[0][0]  # 使用第一个关键词的类型
                        keyword_value = '; '.join([kw[1] for kw in keywords_list])  # 显示所有搜索的关键词

                        for kw_type, kw_value in keywords_list:
                            self.logger.debug(f"搜索关键词: {kw_value} (类型: {kw_type})")
                            # 执行爬取
                            scraping_result = self.scraper.scrape(kw_value)

                            if scraping_result.success:
                                all_libraries.extend(scraping_result.libraries)
                                if scraping_result.search_url:
                                    all_search_urls.append(scraping_result.search_url)
                                if scraping_result.detail_url:
                                    all_detail_urls.append(scraping_result.detail_url)
                                self.logger.info(f"关键词 '{kw_value}' 成功获取 {len(scraping_result.libraries)} 个图书馆")
                            else:
                                self.logger.warning(f"关键词 '{kw_value}' 爬取失败 - {scraping_result.error_message}")

                        # 去重图书馆列表
                        unique_libraries = list(dict.fromkeys(all_libraries))  # 保持顺序的去重

                        # 构建结果字典
                        result = {
                            'row_index': row_index,
                            'keyword_type': keyword_type,
                            'keyword_value': keyword_value,
                            'success': len(unique_libraries) > 0,
                            'error_message': '' if len(unique_libraries) > 0 else '所有关键词都未找到相关图书',
                            'libraries': unique_libraries,
                            'libraries_count': len(unique_libraries),
                            'original_isbn': row_data.get(isbn_col, ''),
                            'original_title': row_data.get(title_col, ''),
                            'search_url': '; '.join(all_search_urls) if all_search_urls else None,
                            'detail_url': '; '.join(all_detail_urls) if all_detail_urls else None
                        }

                        if len(unique_libraries) > 0:
                            successful_rows += 1
                            self.logger.info(f"第 {row_index + 1} 行: 合并后获取 {len(unique_libraries)} 个图书馆")
                        else:
                            failed_rows += 1

                    # 实时保存结果
                    if real_time_save:
                        writer.write_single_row_result(row_index, result, sheet_name)

                    # 添加进度信息
                    if total_rows % 10 == 0:
                        self.logger.info(f"进度: {total_rows} 行已处理, 成功: {successful_rows}, 失败: {failed_rows}")

                except Exception as e:
                    failed_rows += 1
                    self.logger.error(f"处理第 {row_index + 1} 行时发生错误: {str(e)}")

                    # 保存错误结果
                    if real_time_save:
                        error_result = {
                            'row_index': row_index,
                            'keyword_type': '',
                            'keyword_value': '',
                            'success': False,
                            'error_message': str(e),
                            'libraries': [],
                            'libraries_count': 0,
                            'original_isbn': row_data.get(isbn_col, ''),
                            'original_title': row_data.get(title_col, '')
                        }
                        writer.write_single_row_result(row_index, error_result, sheet_name)

            # 输出统计信息
            self.logger.info(f"处理完成! 总计: {total_rows} 行, 成功: {successful_rows}, 失败: {failed_rows}")
            return True

        except Exception as e:
            self.logger.error(f"处理Excel文件失败: {str(e)}")
            return False

    def run(self, excel_path: str, **kwargs) -> bool:
        """
        运行爬虫程序
        Args:
            excel_path: Excel文件路径
            **kwargs: 其他参数
        Returns:
            是否成功完成
        """
        start_time = time.time()

        try:
            success = self.process_excel(excel_path, **kwargs)

            elapsed_time = time.time() - start_time
            self.logger.info(f"程序执行完成, 耗时: {elapsed_time:.2f} 秒")

            return success

        except KeyboardInterrupt:
            self.logger.info("程序被用户中断")
            return False
        except Exception as e:
            self.logger.error(f"程序执行失败: {str(e)}")
            return False


def interactive_main():
    """交互式主程序"""
    print("=" * 60)
    print("           图书馆藏信息爬虫系统")
    print("=" * 60)
    print("支持的爬虫:")
    print("  1. CiNii (日本学术信息检索系统)")
    print("  2. WorldCat (全球图书馆联合目录)")
    print("  3. 全部爬虫 (依次运行CiNii和WorldCat)")
    print("=" * 60)

    while True:
        try:
            choice = input("\n请选择要运行的爬虫 (1/2/3, 输入 'q' 退出): ").strip()

            if choice.lower() in ['q', 'quit', 'exit']:
                print("程序退出")
                break

            if choice not in ['1', '2', '3']:
                print("无效选择，请输入 1, 2, 3 或 q")
                continue

            # 获取Excel文件路径
            excel_path = input("请输入Excel文件路径: ").strip()
            if not excel_path:
                print("Excel文件路径不能为空")
                continue

            # 检查文件是否存在
            path = Path(excel_path)
            if not path.exists():
                print(f"Excel文件不存在: {excel_path}")
                continue

            # 获取列名信息
            isbn_col = input("请输入ISBN列名 (默认: ISBN): ").strip() or 'ISBN'
            title_col = input("请输入题名列名 (默认: 题名): ").strip() or '题名'

            # 获取日志级别
            log_level = input("请输入日志级别 (DEBUG/INFO/WARNING/ERROR, 默认: INFO): ").strip() or 'INFO'
            if log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
                log_level = 'INFO'

            # 设置日志
            log_dir = 'logs'
            LoggerConfig.setup_root_logger(log_level)
            logger = get_logger('main', log_dir, log_level)

            # 配置参数
            config = {
                'log_dir': log_dir,
                'cinii': {
                    'timeout': 30,
                    'delay': 2,
                    'max_retries': 3
                },
                'worldcat': {
                    'headless': False,
                    'timeout': 30000,
                    'delay_range': [2, 5],
                    'max_retries': 3
                }
            }

            # 根据选择运行不同的爬虫
            if choice == '1':
                # 运行CiNii爬虫
                logger.info("开始运行CiNii爬虫...")
                app = BookScraperApp(config)
                success = app.run(
                    excel_path,
                    isbn_col=isbn_col,
                    title_col=title_col,
                    real_time_save=True
                )

            elif choice == '2':
                # 运行WorldCat爬虫
                logger.info("开始运行WorldCat爬虫...")
                print("\n🌐 准备启动WorldCat爬虫...")
                print("注意：如果需要登录，程序会暂停等待您完成登录操作")

                app = WorldCatApp(config)
                success = app.run(
                    excel_path=excel_path,
                    isbn_col=isbn_col,
                    title_col=title_col,
                    output_mode='both'  # 同时生成独立文件和更新原文件
                )

            elif choice == '3':
                # 运行全部爬虫
                logger.info("开始运行全部爬虫...")

                # 先运行CiNii
                logger.info("第一步: 运行CiNii爬虫")
                cinii_app = BookScraperApp(config)
                cinii_success = cinii_app.run(
                    excel_path,
                    isbn_col=isbn_col,
                    title_col=title_col,
                    real_time_save=True
                )

                # 再运行WorldCat
                logger.info("第二步: 运行WorldCat爬虫")
                print("\n🌐 开始第二步：WorldCat爬虫...")
                print("注意：如果需要登录，程序会暂停等待您完成登录操作")

                worldcat_app = WorldCatApp(config)
                worldcat_success = worldcat_app.run(
                    excel_path=excel_path,
                    isbn_col=isbn_col,
                    title_col=title_col,
                    output_mode='both'
                )

                success = cinii_success and worldcat_success

            # 显示结果
            if success:
                print("\n✅ 程序执行成功!")
                if choice == '3':
                    print("CiNii和WorldCat爬虫均已成功完成")
            else:
                print("\n❌ 程序执行失败!")
                logger.error("程序执行失败")

            # 询问是否继续
            continue_choice = input("\n是否继续运行其他爬虫? (y/n): ").strip().lower()
            if continue_choice not in ['y', 'yes', '是']:
                break

        except KeyboardInterrupt:
            print("\n\n程序被用户中断")
            break
        except Exception as e:
            print(f"\n发生错误: {str(e)}")
            logger.error(f"交互式程序出错: {str(e)}")
            continue


def main():
    """主函数 - 支持命令行模式和交互式模式"""
    parser = argparse.ArgumentParser(description='图书馆藏信息爬虫')
    parser.add_argument('excel_path', nargs='?', help='Excel文件路径 (交互模式下可选)')
    parser.add_argument('--mode', choices=['interactive', 'cli'], default='interactive',
                       help='运行模式: interactive(交互式) 或 cli(命令行)')
    parser.add_argument('--scraper', choices=['cinii', 'worldcat', 'all'],
                       help='选择爬虫: cinii, worldcat, all (仅CLI模式)')
    parser.add_argument('--isbn-col', default='ISBN', help='ISBN列名 (默认: ISBN)')
    parser.add_argument('--title-col', default='题名', help='题名列名 (默认: 题名)')
    parser.add_argument('--sheet-name', default=0, help='工作表名称或索引 (默认: 0)')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='日志级别 (默认: INFO)')
    parser.add_argument('--log-dir', default='logs', help='日志目录 (默认: logs)')
    parser.add_argument('--no-real-time-save', action='store_true', help='禁用实时保存')
    parser.add_argument('--output-mode', choices=['separate', 'update', 'both'], default='both',
                       help='WorldCat输出模式 (separate/update/both, 默认: both)')

    args = parser.parse_args()

    # 如果是交互式模式
    if args.mode == 'interactive':
        interactive_main()
        return

    # CLI模式需要检查必要的参数
    if not args.excel_path:
        print("CLI模式需要指定Excel文件路径")
        sys.exit(1)

    if not args.scraper:
        print("CLI模式需要指定爬虫类型 (--scraper)")
        sys.exit(1)

    # 设置日志
    LoggerConfig.setup_root_logger(args.log_level)
    logger = get_logger('main', args.log_dir, args.log_level)

    # 检查Excel文件
    excel_path = Path(args.excel_path)
    if not excel_path.exists():
        logger.error(f"Excel文件不存在: {excel_path}")
        sys.exit(1)

    # 配置参数
    config = {
        'log_dir': args.log_dir,
        'cinii': {
            'timeout': 30,
            'delay': 2,
            'max_retries': 3
        },
        'worldcat': {
            'headless': False,
            'timeout': 30000,
            'delay_range': [2, 5],
            'max_retries': 3
        }
    }

    try:
        if args.scraper in ['cinii', 'all']:
            # 运行CiNii爬虫
            logger.info("运行CiNii爬虫...")
            cinii_app = BookScraperApp(config)
            cinii_success = cinii_app.run(
                str(excel_path),
                isbn_col=args.isbn_col,
                title_col=args.title_col,
                sheet_name=args.sheet_name,
                real_time_save=not args.no_real_time_save
            )

        if args.scraper in ['worldcat', 'all']:
            # 运行WorldCat爬虫
            logger.info("运行WorldCat爬虫...")
            worldcat_app = WorldCatApp(config)
            worldcat_success = worldcat_app.run(
                excel_path=str(excel_path),
                isbn_col=args.isbn_col,
                title_col=args.title_col,
                output_mode=args.output_mode
            )

        # 判断整体成功状态
        if args.scraper == 'cinii':
            success = cinii_success
        elif args.scraper == 'worldcat':
            success = worldcat_success
        else:  # all
            success = cinii_success and worldcat_success

        if success:
            logger.info("程序执行成功")
            sys.exit(0)
        else:
            logger.error("程序执行失败")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("程序被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()