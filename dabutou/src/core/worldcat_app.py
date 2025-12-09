"""
WorldCat爬虫应用程序
独立的WorldCat爬虫应用，与CiNii应用保持独立
"""
import sys
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger_config import get_logger
from src.scrapers.worldcat_scraper import WorldCatScraper, WorldCatResult
from src.utils.worldcat_excel_handler import WorldCatExcelHandler
from src.core.keyword_processor import KeywordProcessor


class WorldCatApp:
    """WorldCat爬虫应用程序"""

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化WorldCat应用
        Args:
            config: 配置参数
        """
        self.config = config or {}
        self.logger = get_logger('WorldCatApp', self.config.get('log_dir', 'logs'))
        self.keyword_processor = KeywordProcessor()
        self.setup_scraper()

    def setup_scraper(self):
        """设置爬虫实例"""
        scraper_config = self.config.get('worldcat', {})
        self.scraper = WorldCatScraper(scraper_config)

    def process_excel(self, excel_path: str,
                     isbn_col: str = 'ISBN',
                     title_col: str = '题名',
                     sheet_name: str = 0,
                     output_mode: str = 'separate') -> bool:
        """
        处理Excel文件
        Args:
            excel_path: Excel文件路径
            isbn_col: ISBN列名
            title_col: 题名列名
            sheet_name: 工作表名称或索引
            output_mode: 输出模式 ('separate' | 'update' | 'both')
        Returns:
            是否成功完成
        """
        try:
            self.logger.info(f"开始处理Excel文件: {excel_path}")

            # 初始化Excel处理器
            excel_handler = WorldCatExcelHandler(excel_path)

            # 启动浏览器
            if not self.scraper.start_browser():
                self.logger.error("启动浏览器失败")
                return False

            # 检查并确保WorldCat登录状态
            if not self.scraper.login():
                self.logger.error("WorldCat系统登录失败")
                return False

            self.logger.info("WorldCat系统登录成功，准备开始检索")

            # 采用main.py的逐行处理模式
            total_rows = 0
            successful_rows = 0
            failed_rows = 0
            row_results = []  # 存储每行的处理结果
            worldcat_results = []  # 存储WorldCat结果，用于生成独立的Excel文件

            # 逐行处理Excel数据
            for row_index, row_data in excel_handler.get_excel_data_iterator():
                total_rows += 1
                self.logger.info(f"正在处理第 {row_index + 1}/{total_rows} 行")

                try:
                    # 提取ISBN和题名
                    isbn_value = str(row_data.get(isbn_col, '')).strip()
                    title_value = str(row_data.get(title_col, '')).strip()

                    # 使用keyword_processor提取关键词列表（支持多个ISBN分别提取）
                    keywords_list = self.keyword_processor.extract_keywords_list(isbn_value, title_value)

                    if not keywords_list:
                        self.logger.warning(f"第 {row_index + 1} 行: 没有有效的关键词")
                        row_result = {
                            'row_index': row_index,
                            'keyword_type': 'none',
                            'keyword_value': '',
                            'success': False,
                            'error_message': '没有有效的关键词',
                            'libraries': [],
                            'libraries_count': 0,
                            'original_isbn': isbn_value,
                            'original_title': title_value
                        }
                        row_results.append(row_result)
                        failed_rows += 1
                        continue

                    # 合并所有关键词的搜索结果
                    all_libraries = []
                    keyword_type = keywords_list[0][0]  # 使用第一个关键词的类型
                    keyword_value = '; '.join([kw[1] for kw in keywords_list])  # 显示所有搜索的关键词

                    for kw_type, kw_value in keywords_list:
                        self.logger.debug(f"搜索关键词: {kw_value} (类型: {kw_type})")
                        # 执行爬取
                        scraping_result = self.scraper.scrape(kw_value)

                        if scraping_result.success:
                            all_libraries.extend(scraping_result.libraries)
                            self.logger.info(f"关键词 '{kw_value}' 成功获取 {len(scraping_result.libraries)} 个图书馆")
                        else:
                            self.logger.warning(f"关键词 '{kw_value}' 爬取失败 - {scraping_result.error_message}")

                    # 去重图书馆列表
                    unique_libraries = list(dict.fromkeys(all_libraries))  # 保持顺序的去重

                    # 构建行结果
                    row_result = {
                        'row_index': row_index,
                        'keyword_type': keyword_type,
                        'keyword_value': keyword_value,
                        'success': len(unique_libraries) > 0,
                        'error_message': '' if len(unique_libraries) > 0 else '所有关键词都未找到相关图书',
                        'libraries': unique_libraries,
                        'libraries_count': len(unique_libraries),
                        'original_isbn': isbn_value,
                        'original_title': title_value
                    }

                    row_results.append(row_result)

                    if len(unique_libraries) > 0:
                        successful_rows += 1
                        self.logger.info(f"第 {row_index + 1} 行: 合并后获取 {len(unique_libraries)} 个图书馆")
                    else:
                        failed_rows += 1
                        self.logger.warning(f"第 {row_index + 1} 行: 未找到相关图书")

                except Exception as e:
                    self.logger.error(f"处理第 {row_index + 1} 行时出错: {str(e)}")
                    row_result = {
                        'row_index': row_index,
                        'keyword_type': 'error',
                        'keyword_value': '',
                        'success': False,
                        'error_message': str(e),
                        'libraries': [],
                        'libraries_count': 0,
                        'original_isbn': isbn_value,
                        'original_title': title_value
                    }
                    row_results.append(row_result)
                    failed_rows += 1

                # 添加延时避免被反爬虫机制检测
                time.sleep(2)

            # 统计结果
            self.logger.info(f"处理完成: 总计 {total_rows} 行, 成功 {successful_rows} 行, 失败 {failed_rows} 行")

            # 根据输出模式保存结果
            if output_mode in ['update', 'both']:
                try:
                    updated_file = excel_handler.update_original_excel_with_row_results(row_results)
                    self.logger.info(f"已更新原始Excel文件: {updated_file}")
                except Exception as e:
                    self.logger.error(f"更新原始Excel文件失败: {str(e)}")

            if output_mode in ['separate', 'both']:
                # 将行结果转换为WorldCatResult格式
                for row_result in row_results:
                    # 创建WorldCatResult对象
                    worldcat_result = WorldCatResult(
                        search_term=row_result['keyword_value'],
                        success=row_result['success'],
                        libraries=row_result['libraries'],
                        libraries_count=row_result['libraries_count'],
                        error_message=row_result['error_message'] if not row_result['success'] else None
                    )
                    worldcat_results.append(worldcat_result)

                try:
                    output_file = excel_handler.save_results(
                        results=worldcat_results,
                        isbn_col=isbn_col,
                        title_col=title_col,
                        include_original_data=True
                    )
                    self.logger.info(f"已保存WorldCat结果到独立文件: {output_file}")
                except Exception as e:
                    self.logger.error(f"保存独立结果文件失败: {str(e)}")

            return successful_rows > 0

        except Exception as e:
            self.logger.error(f"处理Excel文件失败: {str(e)}")
            return False

        finally:
            # 确保浏览器关闭
            self.scraper.close_browser()

    def process_single_search(self, search_term: str, output_file: str = None) -> bool:
        """
        处理单个搜索词
        Args:
            search_term: 搜索词
            output_file: 输出文件路径（可选）
        Returns:
            是否成功完成
        """
        try:
            self.logger.info(f"开始处理单个搜索词: {search_term}")

            # 启动浏览器
            if not self.scraper.start_browser():
                self.logger.error("启动浏览器失败")
                return False

            # 检查并确保WorldCat登录状态
            if not self.scraper.login():
                self.logger.error("WorldCat系统登录失败")
                return False

            self.logger.info("WorldCat系统就绪，开始执行搜索")

            # 执行单次爬取
            result = self.scraper.scrape(search_term)

            # 保存结果
            if output_file:
                self.scraper.save_results_to_excel([result], output_file)
                self.logger.info(f"结果已保存到: {output_file}")

            # 输出结果
            if result.success:
                self.logger.info(f"搜索成功: {search_term}")
                self.logger.info(f"找到 {result.libraries_count} 个海外图书馆")
                for library in result.libraries:
                    self.logger.info(f"  - {library}")
            else:
                self.logger.warning(f"搜索失败: {search_term}")
                self.logger.warning(f"错误信息: {result.error_message}")

            return result.success

        except Exception as e:
            self.logger.error(f"处理单个搜索词失败: {str(e)}")
            return False

        finally:
            # 确保浏览器关闭
            self.scraper.close_browser()

    def interactive_search(self):
        """交互式搜索模式"""
        self.logger.info("进入交互式搜索模式")

        # 启动浏览器
        if not self.scraper.start_browser():
            self.logger.error("启动浏览器失败")
            return

        try:
            # 检查并确保WorldCat登录状态
            if not self.scraper.login():
                self.logger.error("WorldCat系统登录失败")
                return

            self.logger.info("WorldCat系统就绪，进入交互式搜索模式")

            while True:
                try:
                    # 获取用户输入
                    search_term = input("\n请输入搜索词（输入 'quit' 或 'exit' 退出）: ").strip()

                    if search_term.lower() in ['quit', 'exit', 'q']:
                        break

                    if not search_term:
                        continue

                    # 执行搜索
                    self.logger.info(f"正在搜索: {search_term}")
                    result = self.scraper.scrape(search_term)

                    # 显示结果
                    if result.success:
                        print(f"\n✅ 搜索成功: {search_term}")
                        print(f"找到 {result.libraries_count} 个海外图书馆:")
                        for i, library in enumerate(result.libraries, 1):
                            print(f"  {i}. {library}")
                    else:
                        print(f"\n❌ 搜索失败: {search_term}")
                        print(f"错误信息: {result.error_message}")

                except KeyboardInterrupt:
                    print("\n\n用户中断搜索")
                    break
                except Exception as e:
                    self.logger.error(f"搜索过程中出错: {str(e)}")
                    continue

        finally:
            # 确保浏览器关闭
            self.scraper.close_browser()
            self.logger.info("交互式搜索模式结束")

    def run(self, excel_path: str = None, search_term: str = None,
            mode: str = 'batch', **kwargs) -> bool:
        """
        运行WorldCat爬虫程序
        Args:
            excel_path: Excel文件路径（批量模式）
            search_term: 搜索词（单次模式）
            mode: 运行模式 ('batch' | 'single' | 'interactive')
            **kwargs: 其他参数
        Returns:
            是否成功完成
        """
        start_time = time.time()

        try:
            success = False

            if mode == 'batch' and excel_path:
                # 批量模式
                success = self.process_excel(excel_path, **kwargs)
            elif mode == 'single' and search_term:
                # 单次模式
                success = self.process_single_search(search_term, **kwargs)
            elif mode == 'interactive':
                # 交互模式
                self.interactive_search()
                success = True
            else:
                self.logger.error("无效的运行模式或缺少必要参数")
                return False

            elapsed_time = time.time() - start_time
            self.logger.info(f"程序执行完成, 耗时: {elapsed_time:.2f} 秒")

            return success

        except KeyboardInterrupt:
            self.logger.info("程序被用户中断")
            return False
        except Exception as e:
            self.logger.error(f"程序执行失败: {str(e)}")
            return False