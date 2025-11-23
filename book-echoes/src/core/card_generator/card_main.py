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
            'library_card_failed_count': 0
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
            logger.info("=" * 60)
            logger.info("启动并行任务:")
            logger.info("  任务1: 图书卡片生成")
            logger.info("  任务2: 推荐结果数据库写入")
            if self.library_card_enabled:
                logger.info("  任务3: 图书馆借书卡生成")
            logger.info("=" * 60)

            # 使用ThreadPoolExecutor并行执行
            max_workers = 3 if self.library_card_enabled else 2
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 任务1: 图书卡片生成（使用线程安全的converter）
                card_future = executor.submit(self._generate_cards_task, filtered_df)
                
                # 任务2: 推荐结果数据库写入
                db_future = executor.submit(self._write_recommendation_results_task, df)
                
                # 任务3: 图书馆借书卡生成（如果启用，使用线程安全的converter）
                library_card_future = None
                if self.library_card_enabled:
                    library_card_future = executor.submit(self._generate_library_cards_task, filtered_df)

                # 等待任务完成
                card_result = card_future.result()
                db_result = db_future.result()
                library_card_result = library_card_future.result() if library_card_future else 0

            logger.info("=" * 60)
            logger.info("并行任务执行完成")
            logger.info(f"  任务1结果: {'成功' if card_result else '失败'}")
            logger.info(f"  任务2结果: 写入 {db_result} 条记录")
            if self.library_card_enabled:
                logger.info(f"  任务3结果: 成功生成 {library_card_result} 张借书卡")
            logger.info("=" * 60)

            # 8. 生成汇总报告
            elapsed_time = time.time() - start_time
            report = self.generate_summary_report(excel_path, elapsed_time)
            logger.info("\n" + report)

            # 9. 保存报告
            report_path = os.path.join(
                self.config.get('output', {}).get('base_dir', 'runtime/outputs'),
                f'card_generation_report_{time.strftime("%Y%m%d_%H%M%S")}.txt'
            )
            self.save_report(report, report_path)

            # 10. 返回结果
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

    def _write_recommendation_results_task(self, df: pd.DataFrame) -> int:
        """
        任务2: 推荐结果数据库写入任务(在独立线程中执行)

        Args:
            df: 完整的DataFrame(包含所有数据)

        Returns:
            int: 成功写入的记录数
        """
        try:
            logger.info("[任务2] 开始写入推荐结果到数据库...")
            task_start = time.time()

            # 获取完整配置(包含fields_mapping)
            config_manager = get_config_manager()
            full_config = config_manager.get_config()

            # 创建写入器
            writer = RecommendationResultsWriter(full_config)

            # 写入数据(只写入初评结果为"通过"的记录)
            success_count = writer.write_recommendation_results(df)

            task_time = time.time() - task_start
            logger.info(f"[任务2] 推荐结果写入完成,成功 {success_count} 条,耗时: {task_time:.2f}秒")
            return success_count

        except Exception as e:
            logger.error(f"[任务2] 推荐结果写入任务异常: {e}", exc_info=True)
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

    def generate_summary_report(self, excel_path: str, elapsed_time: float) -> str:
        """
        生成汇总报告

        Args:
            excel_path: Excel文件路径
            elapsed_time: 执行时间（秒）

        Returns:
            str: 汇总报告文本
        """
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
            f"  失败记录: {self.stats['failed_count']} 条",
            f"  警告记录: {self.stats['warning_count']} 条",
        ]
        
        # 添加借书卡统计（如果启用）
        if self.library_card_enabled:
            lines.extend([
                "",
                "借书卡生成结果：",
                f"  成功生成: {self.stats['library_card_success_count']} 张借书卡",
                f"  失败记录: {self.stats['library_card_failed_count']} 条",
            ])
        
        lines.append("")

        # 失败详情
        if self.stats['failed_records']:
            lines.append("失败详情：")
            for i, record in enumerate(self.stats['failed_records'][:20], 1):
                lines.append(f"  {i}. 书目条码：{record['barcode']}，原因：{record['reason']}")
            if len(self.stats['failed_records']) > 20:
                lines.append(f"  ... 还有 {len(self.stats['failed_records']) - 20} 条失败记录")
            lines.append("")

        # 警告详情
        if self.stats['warning_records']:
            lines.append("警告详情：")
            for i, record in enumerate(self.stats['warning_records'][:20], 1):
                lines.append(f"  {i}. 书目条码：{record['barcode']}，警告：{record['warning']}")
            if len(self.stats['warning_records']) > 20:
                lines.append(f"  ... 还有 {len(self.stats['warning_records']) - 20} 条警告记录")
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
