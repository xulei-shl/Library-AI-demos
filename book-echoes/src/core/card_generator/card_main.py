"""
图书卡片生成主程序
统筹整个卡片生成流程
"""

import os
import sys
import time
import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple, Optional
import pandas as pd

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, project_root)

import shutil

from src.utils.logger import get_logger
from src.utils.config_manager import get_config_manager
from src.core.card_generator.models import BookCardData
from src.core.card_generator.validator import DataValidator
from src.core.card_generator.directory_manager import DirectoryManager
from src.core.card_generator.image_downloader import ImageDownloader
from src.core.card_generator.qrcode_generator import QRCodeGenerator
from src.core.card_generator.html_generator import HTMLGenerator
from src.core.card_generator.html_to_image_converter import HTMLToImageConverter
from src.core.card_generator.recommendation_writer import RecommendationResultsWriter
from src.core.card_generator.library_card_models import LibraryCardData, BorrowerRecord
from src.core.card_generator.library_card_html_generator import LibraryCardHTMLGenerator

logger = get_logger(__name__)


class CardGeneratorModule:
    """图书卡片生成模块主类"""

    def __init__(self, config: Dict):
        """
        初始化模块

        Args:
            config: 配置字典
        """
        self.config = config
        self.validator = DataValidator(config)
        self.directory_manager = DirectoryManager(config)
        self.image_downloader = ImageDownloader(config)
        self.qrcode_generator = QRCodeGenerator(config)
        self.html_generator = HTMLGenerator(config)
        # 注意：不再在主线程创建html_to_image_converter，而是在各个任务线程中创建
        
        # 初始化图书馆借书卡生成器（如果启用）
        self.library_card_enabled = False
        library_card_config = config.get('library_card_generator', {})
        if library_card_config.get('enabled', False):
            self.library_card_enabled = True
            self.library_card_html_generator = LibraryCardHTMLGenerator(library_card_config)
            logger.info("图书馆借书卡生成器已启用")

        # 获取字段配置
        self.fields_config = config.get('fields', {})
        self.recommendation_column = self.fields_config.get('recommendation_column', '初评理由')
        self.recommendation_priority_column = self.fields_config.get('recommendation_priority_column', '人工推荐语')

        # 截取长度配置
        self.truncate_config = self.fields_config.get('truncate', {})

        # 重试配置
        retry_config = config.get('retry', {})
        self.max_retry_attempts = retry_config.get('max_attempts', 3)
        self.retry_delay = retry_config.get('delay_seconds', 2)
        
        # 统计信息
        self.stats = {
            'total_count': 0,
            'passed_count': 0,
            'success_count': 0,
            'failed_count': 0,
            'warning_count': 0,
            'failed_records': [],
            'warning_records': [],
            'library_card_success_count': 0,
            'library_card_failed_count': 0,
            'retry_success_count': 0,
            'retry_failed_records': [],
            'success_barcodes': []  # 成功生成卡片的条码列表
        }

    def run(self, excel_path: str) -> int:
        """
        主函数流程

        Args:
            excel_path: Excel文件路径

        Returns:
            int: 成功返回0，失败返回1
        """
        start_time = time.time()

        logger.info("=" * 60)
        logger.info("模块5: 图书卡片生成模块")
        logger.info("=" * 60)

        try:
            # 1. 验证Excel文件
            if not self.validator.validate_excel_file(excel_path):
                return 1

            # 2. 加载Excel数据
            logger.info(f"加载Excel文件：{excel_path}")
            df = pd.read_excel(excel_path)
            self.stats['total_count'] = len(df)

            # 3. 验证必填列
            required_columns = list(self.config.get('fields', {}).get('required', []))
            required_columns.append('书目条码')  # 添加书目条码为必填
            if self.recommendation_column:
                required_columns.append(self.recommendation_column)

            valid, missing_cols = self.validator.validate_required_columns(df, required_columns)
            if not valid:
                return 1

            # 4. 筛选通过的图书
            filtered_df = self.validator.filter_passed_books(df)
            self.stats['passed_count'] = len(filtered_df)
            self.stats['filter_source'] = self.validator.filter_source

            if len(filtered_df) == 0:
                logger.warning("警告：没有终评结果为'通过'的图书")
                return 0

            logger.info(f"开始处理 {len(filtered_df)} 本通过终评的图书...")

            # 5. 并行执行独立任务（每个任务使用独立的浏览器实例）
            # 注意：DB写入移到最后执行，确保只写入成功生成卡片的记录
            logger.info("=" * 60)
            logger.info("启动并行任务:")
            logger.info("  任务1: 图书卡片生成")
            if self.library_card_enabled:
                logger.info("  任务2: 图书馆借书卡生成")
            logger.info("=" * 60)

            # 使用ThreadPoolExecutor并行执行
            max_workers = 2 if self.library_card_enabled else 1
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 任务1: 图书卡片生成（使用线程安全的converter）
                card_future = executor.submit(self._generate_cards_task, filtered_df)

                # 任务2: 图书馆借书卡生成（如果启用，使用线程安全的converter）
                library_card_future = None
                if self.library_card_enabled:
                    library_card_future = executor.submit(self._generate_library_cards_task, filtered_df)

                # 等待任务完成
                card_result = card_future.result()
                library_card_result = library_card_future.result() if library_card_future else 0

            logger.info("=" * 60)
            logger.info("并行任务执行完成")
            logger.info(f"  任务1结果: {'成功' if card_result else '失败'}")
            if self.library_card_enabled:
                logger.info(f"  任务2结果: 成功生成 {library_card_result} 张借书卡")
            logger.info("=" * 60)

            # 6. 失败重试机制
            if self.stats['failed_records']:
                logger.info("=" * 60)
                logger.info(f"检测到 {len(self.stats['failed_records'])} 条失败记录，开始重试流程...")
                logger.info("=" * 60)
                self._retry_failed_records(filtered_df)

            # 7. 如果重试后仍有失败，清理失败记录并生成错误报告
            if self.stats['retry_failed_records']:
                # 清理失败记录的文件夹和Excel标记
                logger.info("=" * 60)
                logger.info("开始清理失败记录...")
                logger.info("=" * 60)
                self._cleanup_failed_records(excel_path, filtered_df)

                # 生成错误报告
                error_report_path = os.path.join(
                    self.config.get('output', {}).get('base_dir', 'runtime/outputs'),
                    f'card_generation_errors_{time.strftime("%Y%m%d_%H%M%S")}.txt'
                )
                self._generate_error_report(error_report_path)
                logger.error(f"重试后仍有 {len(self.stats['retry_failed_records'])} 条记录失败，错误报告已生成：{error_report_path}")

            # 8. 写入推荐结果到数据库（只写入成功生成卡片的记录）
            db_result = 0
            if self.stats['success_barcodes']:
                logger.info("=" * 60)
                logger.info("开始写入推荐结果到数据库...")
                logger.info("=" * 60)
                db_result = self._write_recommendation_results_task(df, self.stats['success_barcodes'])
                logger.info(f"数据库写入完成，成功写入 {db_result} 条记录")

            # 9. 生成汇总报告
            elapsed_time = time.time() - start_time
            report = self.generate_summary_report(excel_path, elapsed_time, db_result)
            logger.info("\n" + report)

            # 10. 保存报告
            report_path = os.path.join(
                self.config.get('output', {}).get('base_dir', 'runtime/outputs'),
                f'card_generation_report_{time.strftime("%Y%m%d_%H%M%S")}.txt'
            )
            self.save_report(report, report_path)

            # 11. 返回结果
            if self.stats['success_count'] > 0:
                logger.info("=" * 60)
                logger.info("[成功] 模块5执行完成!")
                logger.info(f"成功生成 {self.stats['success_count']} 张图书卡片")
                logger.info(f"成功写入 {db_result} 条推荐结果到数据库")
                logger.info("=" * 60)
                return 0
            else:
                logger.error("=" * 60)
                logger.error("[失败] 模块5执行失败!")
                logger.error("所有图书卡片生成均失败")
                logger.error("=" * 60)
                return 1

        except Exception as e:
            logger.critical(f"模块5执行异常：{e}", exc_info=True)
            return 1

        finally:
            # 浏览器实例由各个任务线程自行管理，无需在此关闭
            pass

    def _generate_cards_task(self, filtered_df: pd.DataFrame) -> bool:
        """
        任务1: 图书卡片生成任务(在独立线程中执行)

        Args:
            filtered_df: 筛选后的DataFrame

        Returns:
            bool: 是否成功
        """
        # 创建线程安全的HTML转图片转换器
        html_to_image_converter = HTMLToImageConverter(self.config, thread_safe=True)
        
        try:
            logger.info("[任务1] 开始生成图书卡片...")
            task_start = time.time()

            # 1. 批量并发下载封面图片(性能优化)
            logger.info("[任务1] 步骤1: 批量下载封面图片...")
            download_start = time.time()
            download_results = self.batch_download_covers(filtered_df)
            download_time = time.time() - download_start
            logger.info(f"[任务1] 封面图片下载完成,耗时: {download_time:.2f}秒")

            # 2. 启动浏览器实例
            logger.info("[任务1] 步骤2: 启动浏览器实例...")
            if not html_to_image_converter.start_browser():
                logger.error("[任务1] 浏览器启动失败,无法继续处理")
                return False

            # 3. 逐本生成卡片(封面图片已下载,跳过下载步骤)
            logger.info("[任务1] 步骤3: 生成卡片...")
            for index, row in filtered_df.iterrows():
                barcode = str(row.get('书目条码', 'Unknown')).strip()
                # 修复: 改为检查封面是否已存在，而不是下载结果
                output_paths = self.directory_manager.create_book_directory(barcode)
                if output_paths:
                    files_status = self.check_existing_files(output_paths)
                    cover_exists = files_status['cover_exists']
                else:
                    cover_exists = False
                self.process_single_book(row, html_to_image_converter, skip_cover_download=True, cover_downloaded=cover_exists)

            task_time = time.time() - task_start
            logger.info(f"[任务1] 图书卡片生成完成,耗时: {task_time:.2f}秒")
            return True

        except Exception as e:
            logger.error(f"[任务1] 图书卡片生成任务异常: {e}", exc_info=True)
            return False
        finally:
            # 关闭浏览器实例
            logger.info("[任务1] 关闭浏览器实例...")
            html_to_image_converter.stop_browser()

    def _write_recommendation_results_task(self, df: pd.DataFrame, success_barcodes: List[str] = None) -> int:
        """
        推荐结果数据库写入任务

        Args:
            df: 完整的DataFrame(包含所有数据)
            success_barcodes: 成功生成卡片的条码列表，如果为None则写入所有初评通过的记录

        Returns:
            int: 成功写入的记录数
        """
        try:
            logger.info("开始写入推荐结果到数据库...")
            task_start = time.time()

            # 获取完整配置(包含fields_mapping)
            config_manager = get_config_manager()
            full_config = config_manager.get_config()

            # 创建写入器
            writer = RecommendationResultsWriter(full_config)

            # 如果指定了成功条码列表，先过滤DataFrame
            if success_barcodes:
                # 只保留成功生成卡片的记录
                df_to_write = df[df['书目条码'].astype(str).str.strip().isin(success_barcodes)]
                logger.info(f"过滤后待写入记录数: {len(df_to_write)}")
            else:
                df_to_write = df

            # 写入数据(只写入初评结果为"通过"的记录)
            success_count = writer.write_recommendation_results(df_to_write)

            task_time = time.time() - task_start
            logger.info(f"推荐结果写入完成,成功 {success_count} 条,耗时: {task_time:.2f}秒")
            return success_count

        except Exception as e:
            logger.error(f"推荐结果写入任务异常: {e}", exc_info=True)
            return 0

    def _generate_library_cards_task(self, filtered_df: pd.DataFrame) -> int:
        """
        任务3: 图书馆借书卡生成任务(在独立线程中执行)
        
        Args:
            filtered_df: 筛选后的DataFrame
        
        Returns:
            int: 成功生成的借书卡数量
        """
        # 创建线程安全的HTML转图片转换器
        html_to_image_converter = HTMLToImageConverter(self.config, thread_safe=True)
        
        try:
            logger.info("[任务3] 开始生成图书馆借书卡...")
            task_start = time.time()
            
            # 启动浏览器实例
            logger.info("[任务3] 启动浏览器实例...")
            if not html_to_image_converter.start_browser():
                logger.error("[任务3] 浏览器启动失败,无法继续处理")
                return 0
            
            success_count = 0
            
            for index, row in filtered_df.iterrows():
                barcode = str(row.get('书目条码', 'Unknown')).strip()
                
                try:
                    # 提取图书数据
                    author = str(row.get('豆瓣作者', '')).strip() if pd.notna(row.get('豆瓣作者')) else ''
                    title = str(row.get('豆瓣书名', '')).strip() if pd.notna(row.get('豆瓣书名')) else str(row.get('书名', '')).strip()
                    call_no = str(row.get('索书号', '')).strip()
                    year = str(row.get('豆瓣出版年', '')).strip() if pd.notna(row.get('豆瓣出版年')) else ''
                    
                    # 提取副标题
                    subtitle = None
                    if pd.notna(row.get('豆瓣副标题')) and str(row.get('豆瓣副标题')).strip():
                        subtitle = str(row['豆瓣副标题']).strip()
                    
                    # 生成随机借阅记录
                    borrower_records = self.library_card_html_generator.generate_random_borrower_records()
                    
                    # 创建借书卡数据对象
                    library_card_data = LibraryCardData(
                        barcode=barcode,
                        author=author,
                        title=title,
                        call_no=call_no,
                        year=year,
                        borrower_records=borrower_records,
                        subtitle=subtitle
                    )
                    
                    # 验证数据
                    if not library_card_data.validate():
                        logger.warning(f"[任务3] 借书卡数据验证失败，书目条码：{barcode}")
                        self.stats['library_card_failed_count'] += 1
                        continue
                    
                    # 获取输出路径
                    output_paths = self.directory_manager.create_book_directory(barcode)
                    if not output_paths:
                        logger.warning(f"[任务3] 无法创建输出目录，书目条码：{barcode}")
                        self.stats['library_card_failed_count'] += 1
                        continue
                    
                    # 生成HTML（会自动添加-S后缀）
                    html_success, html_path = self.library_card_html_generator.generate_html(
                        library_card_data,
                        output_paths.html_file
                    )
                    
                    if not html_success:
                        logger.warning(f"[任务3] HTML生成失败，书目条码：{barcode}")
                        self.stats['library_card_failed_count'] += 1
                        continue
                    
                    # 转换为图片（需要添加-S后缀到输出路径）
                    image_output_path = output_paths.image_file.replace('.png', '-S.png')
                    image_success, image_path = html_to_image_converter.convert_html_to_image(
                        html_path,
                        image_output_path
                    )
                    
                    if not image_success:
                        logger.warning(f"[任务3] 图片生成失败，书目条码：{barcode}")
                        self.stats['library_card_failed_count'] += 1
                        continue
                    
                    success_count += 1
                    self.stats['library_card_success_count'] += 1
                    logger.debug(f"[任务3] 成功生成借书卡，书目条码：{barcode}")
                
                except Exception as e:
                    logger.error(f"[任务3] 处理借书卡时发生异常，书目条码：{barcode}，错误：{e}")
                    self.stats['library_card_failed_count'] += 1
                    continue
            
            task_time = time.time() - task_start
            logger.info(f"[任务3] 图书馆借书卡生成完成，成功 {success_count} 张，耗时: {task_time:.2f}秒")
            return success_count
        
        except Exception as e:
            logger.error(f"[任务3] 图书馆借书卡生成任务异常: {e}", exc_info=True)
            return 0
        finally:
            # 关闭浏览器实例
            logger.info("[任务3] 关闭浏览器实例...")
            html_to_image_converter.stop_browser()


    def batch_download_covers(self, filtered_df: pd.DataFrame) -> Dict[str, bool]:
        """
        批量并发下载所有封面图片
        
        Args:
            filtered_df: 筛选后的DataFrame
        
        Returns:
            Dict[str, bool]: 书目条码 -> 是否下载成功的映射
        """
        download_tasks = []
        barcode_to_task = {}
        download_results = {}  # 初始化结果字典
        
        # 准备下载任务
        for index, row in filtered_df.iterrows():
            barcode = str(row.get('书目条码', 'Unknown')).strip()
            
            # 提取图书数据
            book_data = self.extract_book_data(row)
            if not book_data:
                continue
            
            # 创建目录
            output_paths = self.directory_manager.create_book_directory(barcode)
            if not output_paths:
                continue
            
            # 检查封面是否已存在
            files_status = self.check_existing_files(output_paths)
            if not files_status['cover_exists']:
                # 需要下载
                download_tasks.append((book_data.cover_image_url, output_paths.cover_image))
                barcode_to_task[len(download_tasks) - 1] = barcode
            else:
                # 封面已存在,记录为成功
                download_results[barcode] = True
                logger.debug(f"封面图片已存在,跳过下载,书目条码:{barcode}")
        
        # 批量并发下载
        if download_tasks:
            results = self.image_downloader.download_covers_batch(download_tasks)
            
            # 构建结果映射(合并到已有结果中)
            for task_index, (success, actual_path, url) in enumerate(results):
                if task_index in barcode_to_task:
                    barcode = barcode_to_task[task_index]
                    download_results[barcode] = success
        
        return download_results

    def process_single_book(self, row: pd.Series, html_to_image_converter: HTMLToImageConverter,
                           skip_cover_download: bool = False, cover_downloaded: bool = True) -> bool:
        """
        处理单本图书

        Args:
            row: DataFrame行数据

        Returns:
            bool: 处理成功返回True，否则返回False
        """
        barcode = str(row.get('书目条码', 'Unknown')).strip()
        
        # 性能计时
        book_start_time = time.time()
        step_times = {}

        logger.debug(f"开始处理书目条码：{barcode}")

        try:
            # 1. 提取图书数据
            step_start = time.time()
            book_data = self.extract_book_data(row)
            step_times['数据提取'] = time.time() - step_start

            if not book_data:
                self.stats['failed_count'] += 1
                self.stats['failed_records'].append({
                    'barcode': barcode,
                    'reason': '数据提取失败或验证失败'
                })
                return False

            # 2. 创建目录结构
            step_start = time.time()
            output_paths = self.directory_manager.create_book_directory(barcode)
            step_times['创建目录'] = time.time() - step_start

            if not output_paths:
                self.stats['failed_count'] += 1
                self.stats['failed_records'].append({
                    'barcode': barcode,
                    'reason': '目录创建失败'
                })
                return False

            # 3. 检查已有文件，决定需要执行哪些操作
            step_start = time.time()
            files_status = self.check_existing_files(output_paths)
            step_times['检查文件'] = time.time() - step_start

            # 3.1 复制Logo文件（如果缺失）
            step_start = time.time()
            if not files_status['logo_complete']:
                if not self.directory_manager.copy_logo_files(output_paths.pic_dir):
                    self.stats['warning_count'] += 1
                    self.stats['warning_records'].append({
                        'barcode': barcode,
                        'warning': 'Logo文件复制失败'
                    })
            else:
                logger.info(f"Logo文件已存在，跳过复制，书目条码：{barcode}")
            step_times['复制Logo'] = time.time() - step_start

            # 4. 下载封面图片(如果不存在且未跳过下载)
            step_start = time.time()
            if skip_cover_download:
                # 批量下载模式:检查下载结果
                if not cover_downloaded:
                    self.stats['failed_count'] += 1
                    self.stats['failed_records'].append({
                        'barcode': barcode,
                        'reason': '封面图片下载失败(批量下载)'
                    })
                    return False
                logger.debug(f"封面图片已批量下载,书目条码:{barcode}")
            else:
                # 传统模式:逐个下载
                if not files_status['cover_exists']:
                    success, cover_path = self.image_downloader.download_cover_image(
                        book_data.cover_image_url,
                        output_paths.cover_image
                    )

                    if not success:
                        self.stats['failed_count'] += 1
                        self.stats['failed_records'].append({
                            'barcode': barcode,
                            'reason': '封面图片下载失败'
                        })
                        return False
                else:
                    logger.info(f"封面图片已存在，跳过下载，书目条码：{barcode}")
            step_times['下载封面'] = time.time() - step_start

            # 5. 生成二维码（如果不存在）
            step_start = time.time()
            if not files_status['qrcode_exists']:
                success, qr_path = self.qrcode_generator.generate_qrcode(
                    book_data.call_number,
                    output_paths.qrcode_image
                )

                if not success:
                    self.stats['failed_count'] += 1
                    self.stats['failed_records'].append({
                        'barcode': barcode,
                        'reason': '二维码生成失败'
                    })
                    return False
            else:
                logger.info(f"二维码已存在，跳过生成，书目条码：{barcode}")
            step_times['生成二维码'] = time.time() - step_start

            # 6. 生成HTML（总是生成以确保数据最新）
            step_start = time.time()
            success, html_path = self.html_generator.generate_html(
                book_data,
                output_paths.html_file
            )
            step_times['生成HTML'] = time.time() - step_start

            if not success:
                self.stats['failed_count'] += 1
                self.stats['failed_records'].append({
                    'barcode': barcode,
                    'reason': 'HTML生成失败'
                })
                return False

            # 7. HTML转图片（总是生成以确保与HTML同步）
            step_start = time.time()
            success, image_path = html_to_image_converter.convert_html_to_image(
                output_paths.html_file,
                output_paths.image_file
            )
            step_times['HTML转图片'] = time.time() - step_start

            if not success:
                self.stats['failed_count'] += 1
                self.stats['failed_records'].append({
                    'barcode': barcode,
                    'reason': 'HTML转图片失败'
                })
                return False

            # 8. 成功完成
            total_time = time.time() - book_start_time
            self.stats['success_count'] += 1
            self.stats['success_barcodes'].append(barcode)  # 记录成功的条码

            # 输出性能统计
            logger.info(f"成功生成卡片,书目条码:{barcode}, 总耗时:{total_time:.2f}秒")
            logger.debug(f"  步骤耗时: {', '.join([f'{k}:{v:.2f}s' for k, v in step_times.items()])}")

            return True

        except Exception as e:
            logger.error(f"处理图书时发生异常,书目条码:{barcode},错误:{e}", exc_info=True)
            self.stats['failed_count'] += 1
            self.stats['failed_records'].append({
                'barcode': barcode,
                'reason': f'异常:{str(e)}'
            })
            return False

    def check_existing_files(self, output_paths) -> Dict[str, bool]:
        """
        检查已有文件,判断哪些资源需要重新生成

        Args:
            output_paths: 输出路径集合

        Returns:
            Dict[str, bool]: 文件状态字典
                - cover_exists: 封面图片是否存在(cover.jpg 或 cover.png)
                - qrcode_exists: 二维码是否存在
                - logo_complete: Logo文件是否完整(三个文件都存在:logo_shl.png, logozi_shl.jpg, b.png)
        """
        # 检查封面图片(可能是 jpg 或 png)
        cover_jpg = f"{output_paths.cover_image}.jpg"
        cover_png = f"{output_paths.cover_image}.png"
        cover_exists = os.path.exists(cover_jpg) or os.path.exists(cover_png)

        # 检查二维码
        qrcode_exists = os.path.exists(output_paths.qrcode_image)

        # 检查Logo文件(需要三个文件都存在:logo_shl.png, logozi_shl.jpg, b.png)
        logo_shl = os.path.join(output_paths.pic_dir, 'logo_shl.png')
        logozi_shl = os.path.join(output_paths.pic_dir, 'logozi_shl.jpg')
        b_png = os.path.join(output_paths.pic_dir, 'b.png')
        logo_complete = os.path.exists(logo_shl) and os.path.exists(logozi_shl) and os.path.exists(b_png)

        return {
            'cover_exists': cover_exists,
            'qrcode_exists': qrcode_exists,
            'logo_complete': logo_complete
        }

    def _get_recommendation_text(self, row: pd.Series) -> Tuple[str, int]:
        """
        获取推荐语文本及对应的截取长度
        优先使用人工推荐语,如果不存在则使用默认推荐语

        Args:
            row: DataFrame行数据

        Returns:
            Tuple[str, int]: (推荐语文本, 截取长度)
        """
        # 1. 尝试优先列（人工推荐语）
        if self.recommendation_priority_column and self.recommendation_priority_column in row:
            val = row[self.recommendation_priority_column]
            if pd.notna(val) and str(val).strip():
                # 获取优先列的截取长度，默认为50
                length = self.truncate_config.get(self.recommendation_priority_column, 50)
                return str(val).strip(), length

        # 2. 使用默认列
        if self.recommendation_column in row:
            val = row[self.recommendation_column]
            if pd.notna(val):
                # 获取默认列的截取长度，默认为50
                length = self.truncate_config.get(self.recommendation_column, 50)
                return str(val).strip(), length
            
        return "", 50

    def extract_book_data(self, row: pd.Series) -> Optional[BookCardData]:
        """
        从Excel行数据提取图书卡片数据

        Args:
            row: DataFrame行数据

        Returns:
            Optional[BookCardData]: 图书卡片数据，失败返回None
        """
        try:
            # 书名处理（优先豆瓣书名）
            if pd.notna(row.get('豆瓣书名')) and str(row.get('豆瓣书名')).strip():
                title = str(row['豆瓣书名']).strip()
            else:
                title = str(row['书名']).strip() if pd.notna(row.get('书名')) else ""

            # 副标题处理
            subtitle = None
            if pd.notna(row.get('豆瓣副标题')) and str(row.get('豆瓣副标题')).strip():
                subtitle = str(row['豆瓣副标题']).strip()

            # 可选字段处理
            author = str(row['豆瓣作者']).strip() if pd.notna(row.get('豆瓣作者')) else None
            publisher = str(row['豆瓣出版社']).strip() if pd.notna(row.get('豆瓣出版社')) else None
            pub_year = str(row['豆瓣出版年']).strip() if pd.notna(row.get('豆瓣出版年')) else None

            # 获取推荐语和对应的截取长度
            rec_text, rec_length = self._get_recommendation_text(row)

            # 创建数据对象
            book_data = BookCardData(
                barcode=str(row['书目条码']).strip(),
                call_number=str(row['索书号']).strip(),
                douban_rating=float(row['豆瓣评分']),
                final_review_reason=rec_text,
                cover_image_url=str(row['豆瓣封面图片链接']).strip(),
                title=title,
                subtitle=subtitle,
                author=author,
                publisher=publisher,
                pub_year=pub_year,
                max_length=rec_length
            )

            # 验证数据
            if not book_data.validate():
                logger.warning(f"图书数据验证失败，书目条码：{book_data.barcode}")
                return None

            return book_data

        except Exception as e:
            logger.error(f"提取图书数据时发生错误：{e}")
            return None

    def generate_summary_report(self, excel_path: str, elapsed_time: float, db_result: int = 0) -> str:
        """
        生成汇总报告

        Args:
            excel_path: Excel文件路径
            elapsed_time: 执行时间（秒）
            db_result: 数据库写入成功记录数

        Returns:
            str: 汇总报告文本
        """
        # 按条码去重统计失败记录
        unique_failed_barcodes = set(r['barcode'] for r in self.stats['failed_records'])
        unique_failed_count = len(unique_failed_barcodes)

        # 按条码去重统计警告记录
        unique_warning_barcodes = set(r['barcode'] for r in self.stats['warning_records'])
        unique_warning_count = len(unique_warning_barcodes)

        lines = [
            "=" * 60,
            "模块5执行汇总报告",
            "=" * 60,
            "",
            "输入信息：",
            f"  Excel文件: {excel_path}",
            f"  总记录数: {self.stats['total_count']}",
            f"  筛选依据: {self.stats.get('filter_source', '未知')}",
            f"  终评通过数: {self.stats['passed_count']}",
            "",
            "执行结果：",
            f"  成功生成: {self.stats['success_count']} 张图书卡片",
            f"  失败记录: {unique_failed_count} 条",
            f"  警告记录: {unique_warning_count} 条",
            f"  数据库写入: {db_result} 条",
        ]

        # 添加重试统计（如果有重试）
        if self.stats['retry_success_count'] > 0 or self.stats['retry_failed_records']:
            unique_retry_failed = len(set(r['barcode'] for r in self.stats['retry_failed_records']))
            lines.extend([
                "",
                "重试结果：",
                f"  重试成功: {self.stats['retry_success_count']} 条",
                f"  重试后仍失败: {unique_retry_failed} 条",
            ])

        # 继续原有的统计
        lines.append("")

        # 添加借书卡统计（如果启用）
        if self.library_card_enabled:
            lines.extend([
                "",
                "借书卡生成结果：",
                f"  成功生成: {self.stats['library_card_success_count']} 张借书卡",
                f"  失败记录: {self.stats['library_card_failed_count']} 条",
            ])

        lines.append("")

        # 失败详情（按条码去重，每个条码只显示最后一次失败原因）
        if self.stats['failed_records']:
            # 去重：保留每个条码的最后一条记录
            seen_barcodes = {}
            for record in self.stats['failed_records']:
                seen_barcodes[record['barcode']] = record
            unique_failed_records = list(seen_barcodes.values())

            lines.append("失败详情：")
            for i, record in enumerate(unique_failed_records[:20], 1):
                lines.append(f"  {i}. 书目条码：{record['barcode']}，原因：{record['reason']}")
            if len(unique_failed_records) > 20:
                lines.append(f"  ... 还有 {len(unique_failed_records) - 20} 条失败记录")
            lines.append("")

        # 警告详情（按条码去重）
        if self.stats['warning_records']:
            # 去重：保留每个条码的最后一条记录
            seen_barcodes = {}
            for record in self.stats['warning_records']:
                seen_barcodes[record['barcode']] = record
            unique_warning_records = list(seen_barcodes.values())

            lines.append("警告详情：")
            for i, record in enumerate(unique_warning_records[:20], 1):
                lines.append(f"  {i}. 书目条码：{record['barcode']}，警告：{record['warning']}")
            if len(unique_warning_records) > 20:
                lines.append(f"  ... 还有 {len(unique_warning_records) - 20} 条警告记录")
            lines.append("")

        lines.append(f"执行时间: {elapsed_time:.2f} 秒")
        lines.append("=" * 60)

        return "\n".join(lines)

    def save_report(self, report: str, output_path: str) -> bool:
        """
        保存报告文件

        Args:
            report: 报告内容
            output_path: 输出路径

        Returns:
            bool: 保存成功返回True，否则返回False
        """
        try:
            # 确保目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            # 保存报告
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)

            logger.info(f"汇总报告已保存：{output_path}")
            return True

        except Exception as e:
            logger.error(f"保存报告失败：{output_path}，错误：{e}")
            return False

    def _retry_failed_records(self, filtered_df: pd.DataFrame) -> None:
        """
        对失败的记录进行重试
        
        Args:
            filtered_df: 筛选后的DataFrame
        """
        # 创建线程安全的HTML转图片转换器
        html_to_image_converter = HTMLToImageConverter(self.config, thread_safe=True)
        
        try:
            # 启动浏览器实例
            if not html_to_image_converter.start_browser():
                logger.error("[重试] 浏览器启动失败，无法进行重试")
                self.stats['retry_failed_records'] = self.stats['failed_records'].copy()
                return
            
            # 获取失败记录的条码列表
            failed_barcodes = {record['barcode'] for record in self.stats['failed_records']}
            
            # 筛选出失败的记录
            failed_df = filtered_df[filtered_df['书目条码'].astype(str).str.strip().isin(failed_barcodes)]
            
            logger.info(f"[重试] 准备重试 {len(failed_df)} 条失败记录，最大重试次数：{self.max_retry_attempts}")
            
            # 对每条失败记录进行重试
            for attempt in range(1, self.max_retry_attempts + 1):
                if not failed_barcodes:
                    break
                    
                logger.info(f"[重试] 第 {attempt}/{self.max_retry_attempts} 次重试，剩余 {len(failed_barcodes)} 条记录")
                
                # 当前轮次成功的条码
                current_success = set()
                
                for index, row in failed_df.iterrows():
                    barcode = str(row.get('书目条码', 'Unknown')).strip()
                    
                    # 跳过已经成功的记录
                    if barcode not in failed_barcodes:
                        continue
                    
                    logger.info(f"[重试] 第 {attempt} 次重试，书目条码：{barcode}")
                    
                    # 等待一段时间再重试
                    if self.retry_delay > 0:
                        time.sleep(self.retry_delay)
                    
                    # 重新处理
                    success = self.process_single_book(row, html_to_image_converter, skip_cover_download=False)
                    
                    if success:
                        current_success.add(barcode)
                        self.stats['retry_success_count'] += 1
                        # 从failed_records中移除该条码的所有记录
                        self.stats['failed_records'] = [
                            r for r in self.stats['failed_records'] if r['barcode'] != barcode
                        ]
                        self.stats['failed_count'] = len(self.stats['failed_records'])
                        logger.info(f"[重试] 成功，书目条码：{barcode}")
                    else:
                        # 清理重复的失败记录，只保留最新的一条
                        other_records = [r for r in self.stats['failed_records'] if r['barcode'] != barcode]
                        latest_record = [r for r in self.stats['failed_records'] if r['barcode'] == barcode][-1:]
                        self.stats['failed_records'] = other_records + latest_record
                        self.stats['failed_count'] = len(self.stats['failed_records'])
                        logger.warning(f"[重试] 第 {attempt} 次重试失败，书目条码：{barcode}")
                
                # 从失败列表中移除成功的记录
                failed_barcodes -= current_success
                
                if current_success:
                    logger.info(f"[重试] 第 {attempt} 次重试成功 {len(current_success)} 条记录")
            
            # 更新最终失败记录列表
            self.stats['retry_failed_records'] = [
                record for record in self.stats['failed_records']
                if record['barcode'] in failed_barcodes
            ]
            
            # 从原失败记录中移除重试成功的
            self.stats['failed_records'] = self.stats['retry_failed_records'].copy()
            
            if self.stats['retry_success_count'] > 0:
                logger.info(f"[重试] 重试完成，成功恢复 {self.stats['retry_success_count']} 条记录")
            
            if self.stats['retry_failed_records']:
                logger.warning(f"[重试] 重试完成，仍有 {len(self.stats['retry_failed_records'])} 条记录失败")
        
        except Exception as e:
            logger.error(f"[重试] 重试过程发生异常：{e}", exc_info=True)
            self.stats['retry_failed_records'] = self.stats['failed_records'].copy()
        
        finally:
            # 关闭浏览器实例
            logger.info("[重试] 关闭浏览器实例...")
            html_to_image_converter.stop_browser()
    
    def _generate_error_report(self, output_path: str) -> None:
        """
        生成详细的错误报告
        
        Args:
            output_path: 报告输出路径
        """
        try:
            lines = [
                "=" * 80,
                "图书卡片生成 - 错误报告",
                "=" * 80,
                "",
                f"生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "=" * 80,
                "重试统计信息",
                "=" * 80,
                f"最大重试次数：{self.max_retry_attempts}",
                f"重试成功数量：{self.stats['retry_success_count']}",
                f"最终失败数量：{len(self.stats['retry_failed_records'])}",
                "",
                "=" * 80,
                "失败记录详情",
                "=" * 80,
                ""
            ]
            
            for i, record in enumerate(self.stats['retry_failed_records'], 1):
                lines.append(f"{i}. 书目条码：{record['barcode']}")
                lines.append(f"   失败原因：{record['reason']}")
                lines.append("")
            
            lines.extend([
                "=" * 80,
                "建议处理方案",
                "=" * 80,
                "1. 检查失败原因，确认是否为数据问题（如封面链接失效、必填字段缺失等）",
                "2. 对于数据问题，请在Excel中修正后重新运行",
                "3. 对于网络问题，请检查网络连接后重新运行",
                "4. 对于浏览器问题，请检查Playwright是否正确安装",
                "=" * 80
            ])
            
            report_content = "\n".join(lines)
            
            # 确保目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # 保存报告
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            logger.info(f"错误报告已生成：{output_path}")

        except Exception as e:
            logger.error(f"生成错误报告失败：{e}", exc_info=True)

    def _cleanup_failed_records(self, excel_path: str, filtered_df: pd.DataFrame) -> None:
        """
        清理最终失败的记录：删除文件夹、清除Excel中的人工评选标记

        Args:
            excel_path: Excel文件路径
            filtered_df: 筛选后的DataFrame
        """
        if not self.stats['retry_failed_records']:
            return

        # 获取失败的条码列表（去重）
        failed_barcodes = set()
        for record in self.stats['retry_failed_records']:
            failed_barcodes.add(record['barcode'])

        logger.info(f"[清理] 需要清理 {len(failed_barcodes)} 条失败记录")

        # 1. 删除失败记录的文件夹
        deleted_folders = 0
        output_base_dir = self.config.get('output', {}).get('base_dir', 'runtime/outputs')
        cards_dir = os.path.join(output_base_dir, 'cards')

        for barcode in failed_barcodes:
            folder_path = os.path.join(cards_dir, barcode)
            if os.path.exists(folder_path):
                try:
                    shutil.rmtree(folder_path)
                    deleted_folders += 1
                    logger.debug(f"[清理] 已删除文件夹: {folder_path}")
                except Exception as e:
                    logger.warning(f"[清理] 删除文件夹失败: {folder_path}, 错误: {e}")

        logger.info(f"[清理] 已删除 {deleted_folders} 个失败记录的文件夹")

        # 2. 更新Excel文件，清除失败记录的人工评选标记
        try:
            # 读取原始Excel文件
            df = pd.read_excel(excel_path)

            # 获取人工评选列名
            filter_config = self.config.get('filter', {})
            manual_column = filter_config.get('force_column', '人工评选')

            if manual_column not in df.columns:
                logger.warning(f"[清理] Excel中未找到列 '{manual_column}'，跳过清除标记")
                return

            # 清除失败记录的人工评选标记
            updated_count = 0
            for barcode in failed_barcodes:
                mask = df['书目条码'].astype(str).str.strip() == barcode
                if mask.any():
                    df.loc[mask, manual_column] = ''
                    updated_count += 1
                    logger.debug(f"[清理] 已清除条码 {barcode} 的人工评选标记")

            # 保存更新后的Excel文件
            df.to_excel(excel_path, index=False)
            logger.info(f"[清理] 已更新Excel文件，清除 {updated_count} 条记录的人工评选标记")

        except Exception as e:
            logger.error(f"[清理] 更新Excel文件失败: {e}", exc_info=True)


def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(description='图书卡片生成模块')
    parser.add_argument(
        '--excel-file',
        type=str,
        required=True,
        help='模块4生成的终评结果Excel文件路径'
    )

    args = parser.parse_args()

    # 加载配置
    config_manager = get_config_manager()
    config = config_manager.get_config()
    card_config = config.get('card_generator', {})
    
    # 将 library_card_generator 配置合并到 card_config 中
    card_config['library_card_generator'] = config.get('library_card_generator', {})

    # 创建并运行模块
    module = CardGeneratorModule(card_config)
    exit_code = module.run(args.excel_file)

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
