#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISBN异步批量处理器 - 精简版

基于简单爬虫逻辑的高效实现：
1. 多个浏览器实例并发处理
2. 单实例登录重用
3. 实时保存到Excel
4. 可配置并发参数
"""

import asyncio
import os
import random
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import pandas as pd
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError
from playwright.async_api import Error as PlaywrightError

# 添加项目路径
import sys
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from src.utils.logger import get_logger
from src.utils.config_manager import get_douban_config
from src.core.douban.isbn_processor_config import ProcessingConfig
from .exceptions import FolioNeedsRestart

logger = get_logger(__name__)

ISBN_ALLOWED_PATTERN = re.compile(r'^[0-9-]+$')


class AsyncBrowserWorker:
    """单个异步浏览器工作器"""

    def __init__(
        self,
        worker_id: int,
        username: str,
        password: str,
        base_url: str,
        *,
        min_delay: float = 0.5,
        max_delay: float = 2.0,
        retry_times: int = 3,
        request_timeout: int = 15,
        browser_startup_timeout: int = 180,
        page_navigation_timeout: int = 180,
    ):
        self.worker_id = worker_id
        self.username = username
        self.password = password
        self.base_url = base_url
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_logged_in = False
        self.playwright = None

        self.min_delay = max(0.1, min(min_delay, max_delay))
        self.max_delay = max(self.min_delay, max_delay)
        self.retry_times = max(1, retry_times)
        self.request_timeout_ms = max(1_000, int(request_timeout * 1000))
        self.browser_startup_timeout = max(30, browser_startup_timeout)
        self.page_navigation_timeout_ms = max(self.request_timeout_ms, int(page_navigation_timeout * 1000))
        # 每个工作器独占使用浏览器页，避免输入/点击时的并发冲突
        self._page_lock = asyncio.Lock()

    async def _adaptive_delay(self, multiplier: float = 1.0) -> None:
        """根据配置延迟，避免对目标站点请求过快"""
        base_delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(max(0.05, base_delay * max(multiplier, 0.1)))

    async def start(self) -> bool:
        """启动浏览器并登录"""
        try:
            logger.info(f"工作者{self.worker_id}: 启动浏览器..")

            async def _launch_and_login():
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.launch(
                    headless=False,
                    args=['--no-sandbox', '--disable-setuid-sandbox'],
                )
                self.context = await self.browser.new_context()
                self.page = await self.context.new_page()
                await self._login()
                logger.info(f"工作者{self.worker_id}: 启动完成")
                return True

            return await asyncio.wait_for(_launch_and_login(), timeout=self.browser_startup_timeout)

        except asyncio.TimeoutError:
            logger.error(f"工作者{self.worker_id}: 浏览器启动超时（>{self.browser_startup_timeout}s）")
            await self.close()
            return False
        except Exception as exc:
            logger.error(f"工作者{self.worker_id}: 启动失败 - {exc}")
            await self.close()
            return False

    async def _login(self) -> None:
        """执行登录操作"""
        try:
            logger.info(f"工作者{self.worker_id}: 开始登录..")
            await self.page.goto(
                self.base_url,
                wait_until='networkidle',
                timeout=self.page_navigation_timeout_ms,
            )

            await self.page.wait_for_selector('#input-username', timeout=self.request_timeout_ms)
            await self.page.fill('#input-username', self.username)

            await self.page.wait_for_selector('#input-password', timeout=self.request_timeout_ms)
            await self.page.fill('#input-password', self.password)

            await self.page.wait_for_selector('#clickable-login', timeout=self.request_timeout_ms)
            await self.page.click('#clickable-login')

            await self.page.wait_for_selector('.ant-input', timeout=self.page_navigation_timeout_ms)
            self.is_logged_in = True
            logger.info(f"工作者{self.worker_id}: 登录成功")

        except Exception as exc:
            logger.error(f"工作者{self.worker_id}: 登录失败 - {exc}")
            raise

    async def get_isbn(self, barcode: str) -> Optional[str]:
        """获取单个条码的ISBN"""
        async with self._page_lock:
            if not self.is_logged_in:
                logger.warning(f"工作者{self.worker_id}: 未登录状态，重新登录")
                await self._login()

            for attempt in range(self.retry_times):
                try:
                    logger.debug(f"工作者{self.worker_id}: 条码 {barcode} 第 {attempt + 1} 次尝试")
                    await self.page.fill('.ant-input', str(barcode))
                    await self.page.wait_for_selector('.ant-input-search-button', timeout=self.request_timeout_ms)
                    await self.page.click('.ant-input-search-button')

                    await self.page.wait_for_selector('tr.ant-descriptions-row', timeout=self.page_navigation_timeout_ms)
                    result_ready = await self._wait_for_barcode_update(str(barcode))
                    if not result_ready:
                        if attempt == self.retry_times - 1:
                            logger.warning(f"工作者{self.worker_id}: 条码 {barcode} 多次刷新失败")
                            return None
                        await self._adaptive_delay()
                        continue

                    data = {}
                    rows = await self.page.query_selector_all('tr.ant-descriptions-row')
                    for row in rows:
                        ths = await row.query_selector_all('th.ant-descriptions-item-label')
                        tds = await row.query_selector_all('td.ant-descriptions-item-content')
                        for i in range(min(len(ths), len(tds))):
                            key = (await ths[i].inner_text()).strip()
                            value = (await tds[i].inner_text()).strip()
                            if key in ['ISBN', 'ISBN/ISSN']:
                                data[key] = value

                    for field in ['ISBN', 'ISBN/ISSN']:
                        if field in data and data[field]:
                            isbn_value = data[field].strip()
                            if isbn_value and isbn_value not in ['/', '-', '']:
                                logger.debug(f"工作者{self.worker_id}: 条码 {barcode} -> ISBN: {isbn_value} (第{attempt + 1}次尝试)")
                                return isbn_value

                    if attempt == self.retry_times - 1:
                        logger.warning(f"工作者{self.worker_id}: 条码 {barcode} 重试上限仍未获取ISBN")
                        return None
                    await self._adaptive_delay()

                except TimeoutError as exc:
                    await self._handle_worker_restart(barcode, f"FOLIO 搜索超时: {exc}")
                except PlaywrightError as exc:
                    if self._should_restart_exception(exc):
                        await self._handle_worker_restart(barcode, f"FOLIO 浏览器异常: {exc}")
                    if attempt == self.retry_times - 1:
                        logger.error(f"工作者{self.worker_id}: Playwright错误导致失败 - {exc}")
                        return None
                    logger.warning(f"工作者{self.worker_id}: Playwright错误，准备重试 - {exc}")
                    await self._adaptive_delay(1.5)
                except Exception as exc:
                    if attempt == self.retry_times - 1:
                        logger.error(f"工作者{self.worker_id}: 获取条码 {barcode} 的ISBN失败 - {exc}")
                        return None
                    logger.warning(f"工作者{self.worker_id}: 条码 {barcode} 第 {attempt + 1} 次尝试出现问题 - {exc}")
                    await self._adaptive_delay(1.5)

            return None

    async def close(self) -> None:
        """关闭浏览器"""
        try:
            if self.page:
                await self.page.close()
                self.page = None
            if self.context:
                await self.context.close()
                self.context = None
            if self.browser:
                await self.browser.close()
                self.browser = None
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            self.is_logged_in = False
        except Exception as exc:
            logger.error(f"工作者{self.worker_id}: 关闭浏览器失败 - {exc}")
    async def _restart_browser(self) -> None:
        """整体重启浏览器并重新登录"""
        logger.warning(f"工作者{self.worker_id}: 正在重启FOLIO浏览器")
        await self.close()
        started = await self.start()
        if not started:
            raise RuntimeError(f"工作者{self.worker_id}: 浏览器重启失败")

    async def _handle_worker_restart(self, barcode: str, message: str) -> None:
        """执行浏览器重启并向上抛出需要重试的异常"""
        try:
            await self._restart_browser()
        finally:
            raise FolioNeedsRestart(message, barcode=barcode)

    def _should_restart_exception(self, exc: Exception) -> bool:
        """判断异常类型是否需要整体重启浏览器"""
        message = str(exc).lower()
        restart_markers = ['target closed', 'browser has been closed', 'context destroyed']
        return any(marker in message for marker in restart_markers)

    async def _wait_for_barcode_update(self, barcode: str, timeout: Optional[int] = None) -> bool:
        """等待详情面板刷新到指定条码，避免读取到上一次查询的数据"""
        if not self.page:
            return False
        timeout = timeout or self.page_navigation_timeout_ms

        try:
            await self.page.wait_for_function(
                """
                (targetBarcode) => {
                    const normalize = (text) =>
                        (text || '').trim().replace(/[\\s:：]/g, '');
                    const targetLabels = new Set([
                        '条码号',
                        '条码',
                        '馆藏条码',
                        '馆藏条码号'
                    ]);

                    const rows = document.querySelectorAll('tr.ant-descriptions-row');
                    for (const row of rows) {
                        const labels = row.querySelectorAll('th.ant-descriptions-item-label');
                        const contents = row.querySelectorAll('td.ant-descriptions-item-content');
                        for (let i = 0; i < Math.min(labels.length, contents.length); i++) {
                            const label = normalize(labels[i].textContent || '');
                            if (!targetLabels.has(label)) {
                                continue;
                            }
                            const content = contents[i] && contents[i].textContent
                                ? contents[i].textContent.trim()
                                : '';
                            if (content === targetBarcode) {
                                return true;
                            }
                        }
                    }
                    return false;
                }
                """,
                arg=str(barcode),
                timeout=timeout,
            )
            return True
        except TimeoutError:
            logger.warning(
                f"工作者{self.worker_id}: 条码 {barcode} 等待详情刷新超过 {timeout}ms"
            )
            return False


class ISBNAsyncProcessor:
    """ISBN异步处理器主类"""

    def __init__(self, max_concurrent: int = 2, save_interval: int = 25,
                 enable_database: bool = False, db_config: Dict = None,
                 processing_config: Optional[ProcessingConfig] = None):
        """初始化异步处理器"""

        self.processing_config = processing_config
        self.max_concurrent = (processing_config.max_concurrent
                                if processing_config else max_concurrent)
        self.save_interval = max(0, int(save_interval))
        self.database_enabled = enable_database
        self.db_config = db_config or {}
        self.batch_size = (processing_config.batch_size
                          if processing_config and processing_config.batch_size else 0)
        self.min_delay = processing_config.min_delay if processing_config else 0.5
        self.max_delay = processing_config.max_delay if processing_config else 2.0
        self.retry_times = processing_config.retry_times if processing_config else 3
        self.request_timeout = processing_config.timeout if processing_config else 15
        self.browser_startup_timeout = (processing_config.browser_startup_timeout
                                        if processing_config else 180)
        self.page_navigation_timeout = (processing_config.page_navigation_timeout
                                        if processing_config else 180)

        # 从配置文件获取默认值
        douban_config = get_douban_config()
        isbn_processor_conf = douban_config.get('isbn_processor', {}) if isinstance(douban_config, dict) else {}
        performance_conf = isbn_processor_conf.get('performance', {}) if isinstance(isbn_processor_conf, dict) else {}
        self.save_interval_seconds = max(0, int(performance_conf.get('save_interval_seconds', 180)))
        isbn_config = douban_config.get('isbn_resolver', {})

        self.username = isbn_config.get('username')
        self.password = isbn_config.get('password')
        self.base_url = isbn_config.get('base_url', "https://circ-folio.library.sh.cn/shlcirculation-query/literatureHistory")

        if not self.username or not self.password:
            raise ValueError("请在配置文件中设置FOLIO用户名和密码")

        self.workers: List[AsyncBrowserWorker] = []
        self.stats = {
            'total_processed': 0,
            'successful_isbn': 0,
            'failed_isbn': 0,
            'skipped_count': 0
        }

        # 创建异步锁防止并发写入冲突
        self.write_lock = asyncio.Lock()
        self._worker_assign_lock = asyncio.Lock()
        self._next_worker_index = 0
        # 结果存储（避免直接修改DataFrame）
        self.results_buffer = {}
        self._pending_indices: Set[int] = set()
        self._final_only_indices: Set[int] = set()
        self._last_flush_ts = time.monotonic()
        self._row_index_cache: Dict[str, int] = {}
        self._row_cache_column: Optional[str] = None
        self._db_result_cache: Dict[str, str] = {}
        self.output_column: Optional[str] = None
        self.barcode_column: Optional[str] = None

        # 初始化数据库组件（如果启用）
        self.db_manager = None
        self.data_checker = None
        if self.database_enabled:
            self._init_database_components()

        logger.info(
            f"ISBNAsyncProcessor初始化完成，并发数: {self.max_concurrent}, 保存间隔: {save_interval}, 数据库: {'启用' if enable_database else '禁用'}"
        )

    def _init_database_components(self):
        """初始化数据库组件"""
        try:
            from .database.database_manager import DatabaseManager
            from .database.data_checker import DataChecker

            # 获取数据库配置
            db_path = self.db_config.get('db_path', 'books_history.db')
            refresh_config = self.db_config.get('refresh_strategy', {})

            # 初始化数据库管理器
            self.db_manager = DatabaseManager(db_path)
            self.db_manager.init_database()

            # 初始化查重处理器
            self.data_checker = DataChecker(self.db_manager, refresh_config)

            logger.info("数据库组件初始化成功")

        except Exception as e:
            logger.error(f"初始化数据库组件失败: {e}")
            raise

    async def start_workers(self) -> bool:
        """启动所有工作器"""
        try:
            logger.info(f"启动 {self.max_concurrent} 个工作器...")

            # 创建工作器
            for i in range(self.max_concurrent):
                worker = AsyncBrowserWorker(
                    worker_id=i + 1,
                    username=self.username,
                    password=self.password,
                    base_url=self.base_url,
                    min_delay=self.min_delay,
                    max_delay=self.max_delay,
                    retry_times=self.retry_times,
                    request_timeout=self.request_timeout,
                    browser_startup_timeout=self.browser_startup_timeout,
                    page_navigation_timeout=self.page_navigation_timeout,
                )
                self.workers.append(worker)

            # 并发启动工作器
            tasks = [worker.start() for worker in self.workers]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            success_count = sum(1 for r in results if r is True)
            if success_count == 0:
                raise Exception("所有工作器启动失败")

            logger.info(f"成功启动 {success_count}/{self.max_concurrent} 个工作器")
            self._next_worker_index = 0
            return True

        except Exception as e:
            logger.error(f"启动工作器失败: {e}")
            await self.stop_workers()
            return False

    async def stop_workers(self):
        """停止所有工作器"""
        logger.info("停止所有工作器...")
        for worker in self.workers:
            await worker.close()
        self.workers.clear()
        self._next_worker_index = 0

    async def _processor_delay(self, multiplier: float = 1.0) -> None:
        """根据配置为调度过程添加轻量节流"""
        base_delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(max(0.05, base_delay * max(multiplier, 0.1)))

    async def _get_next_worker(self) -> AsyncBrowserWorker:
        """按顺序分配下一个工作器，避免某些实例长期空闲"""
        if not self.workers:
            raise RuntimeError("没有可用的浏览器工作器")
        async with self._worker_assign_lock:
            worker = self.workers[self._next_worker_index]
            self._next_worker_index = (self._next_worker_index + 1) % len(self.workers)
            return worker

    async def process_excel_file(self,
                                excel_file_path: str,
                                barcode_column: str = "书目条码",
                                output_column: str = "ISBN号",
                                retry_failed: bool = True) -> Tuple[str, Dict]:
        """
        批量处理Excel文件

        Args:
            excel_file_path: Excel文件路径
            barcode_column: 书目条码列名
            output_column: 输出ISBN列名
            retry_failed: 是否在第一轮处理完后重试失败的条码（默认True）

        Returns:
            Tuple[str, Dict]: (输出文件路径, 统计信息)
        """
        try:
            start_time = time.time()
            logger.info(f"开始异步批量处理: {excel_file_path}")

            # 读取Excel文件
            if not os.path.exists(excel_file_path):
                raise FileNotFoundError(f"Excel文件不存在: {excel_file_path}")

            df = pd.read_excel(excel_file_path)
            total_records = len(df)
            logger.info(f"读取到 {total_records} 条记录")

            # 检查必需的列
            if barcode_column not in df.columns:
                raise ValueError(f"Excel文件中不存在列 '{barcode_column}'")

            # 初始化输出列
            if output_column not in df.columns:
                df[output_column] = ""

            self.barcode_column = barcode_column
            self.output_column = output_column
            self._initialize_row_index_cache(df, barcode_column)

            valid_isbn_rows = self._collect_rows_with_valid_isbn(df, output_column)
            if valid_isbn_rows:
                logger.info(f"检测到 {len(valid_isbn_rows)} 条记录的ISBN列已存在合法值，将跳过后续处理")
                self.stats['skipped_count'] += len(valid_isbn_rows)

            pending_indices = [idx for idx in range(total_records) if idx not in valid_isbn_rows]
            pending_index_set = set(pending_indices)

            if not pending_indices:
                stats = {
                    'total_records': total_records,
                    'success_count': self.stats['successful_isbn'],
                    'failed_count': self.stats['failed_isbn'],
                    'skipped_count': self.stats['skipped_count'],
                    'success_rate': self.stats['successful_isbn'] / (total_records - self.stats['skipped_count']) * 100 if total_records > self.stats['skipped_count'] else 0,
                    'processing_time': time.time() - start_time,
                    'retry_enabled': retry_failed,
                    'failed_after_retry': 0
                }
                logger.info("所有记录的ISBN列均已包含合法值，无需继续处理")
                return excel_file_path, stats

            # ============================================================
            # 数据库查重（如果启用数据库功能）
            # ============================================================
            categories = None
            if self.database_enabled and self.data_checker:
                logger.info("=" * 80)
                logger.info("执行ISBN数据库查重...")
                logger.info("=" * 80)

                # 将DataFrame转换为字典列表
                excel_data = df.iloc[pending_indices].to_dict('records')

                # 执行ISBN查重分类(只检查isbn字段)
                categories = self.data_checker.check_and_categorize_isbn_books(excel_data)

                # 记录查重统计
                self.stats['existing_valid_count'] = len(categories['existing_valid'])
                self.stats['existing_stale_count'] = len(categories['existing_stale'])
                self.stats['new_count'] = len(categories['new'])

                logger.info(
                    f"ISBN查重完成: "
                    f"已有ISBN={self.stats['existing_valid_count']}, "
                    f"需爬取ISBN={self.stats['new_count']}"
                )

                # 处理已有ISBN数据（从数据库获取，不爬取）
                if categories['existing_valid']:
                    await self._process_existing_valid_books(
                        categories['existing_valid'], df, excel_file_path, output_column
                    )

            # ============================================================
            # 第一轮处理
            # ============================================================
            logger.info("=" * 80)
            logger.info("第一轮处理:批量获取ISBN")
            logger.info("=" * 80)

            # 需要处理的数据:只有新数据(ISBN查重不会产生existing_stale)
            data_to_process = []
            if categories:
                # ISBN查重只需要处理new分类的数据
                all_books_to_process = categories['new']

                # 从字典数据中提取barcode,然后查找对应的索引
                for book_data in all_books_to_process:
                    barcode = book_data.get('barcode') or book_data.get('书目条码')
                    if barcode:
                        # 查找barcode对应的Excel索引
                        index = self._find_row_index(df, barcode)
                        if index != -1 and index in pending_index_set:
                            data_to_process.append(index)

                logger.info(f"需要爬取ISBN的记录数: {len(data_to_process)} 条")
            else:
                # 所有待处理的数据都来自剩余索引
                data_to_process = pending_indices.copy()

            # ============================================================
            # 检查是否有需要爬取的数据
            # ============================================================
            if not data_to_process:
                logger.info("=" * 80)
                logger.info("无需爬取的数据,跳过浏览器启动和爬取流程")
                logger.info("=" * 80)
                
                # 生成统计信息
                stats = {
                    'total_records': total_records,
                    'success_count': self.stats['successful_isbn'],
                    'failed_count': self.stats['failed_isbn'],
                    'skipped_count': self.stats['skipped_count'],
                    'success_rate': 100.0 if total_records > 0 else 0,
                    'processing_time': time.time() - start_time,
                    'retry_enabled': retry_failed,
                    'failed_after_retry': 0
                }
                
                logger.info("=" * 80)
                logger.info("处理完成(无需爬取):")
                logger.info("=" * 80)
                logger.info(f"  总记录数: {stats['total_records']}")
                logger.info(f"  已有ISBN: {self.stats.get('existing_valid_count', 0)}")
                logger.info(f"  跳过记录: {stats['skipped_count']}")
                logger.info(f"  处理时间: {stats['processing_time']:.2f}秒")
                logger.info("=" * 80)
                
                return excel_file_path, stats

            # ============================================================
            # 启动工作器(只有在有需要爬取的数据时才启动)
            # ============================================================
            if not await self.start_workers():
                raise Exception("工作器启动失败")

            # 清空结果缓冲区
            self.results_buffer = {}
            self._pending_indices.clear()
            self._final_only_indices.clear()
            self._db_result_cache.clear()
            self._last_flush_ts = time.monotonic()

            skip_existing_isbn = categories is None
            failed_barcodes_first_round = await self._process_batch(
                df, excel_file_path, barcode_column, output_column, total_records,
                batch_name="第一轮", data_to_process_indices=data_to_process,
                skip_existing_with_value=skip_existing_isbn,
            )

            # ============================================================
            # 第二轮处理：重试失败的条码
            # ============================================================
            if retry_failed and failed_barcodes_first_round:
                logger.info("=" * 80)
                logger.info(f"第二轮处理：重试失败的条码（共 {len(failed_barcodes_first_round)} 条）")
                logger.info("=" * 80)

                # 重新处理失败的条码
                failed_barcodes_second_round = await self._process_failed_barcodes(
                    df, excel_file_path, failed_barcodes_first_round,
                    batch_name="第二轮"
                )

                # 记录最终统计
                retry_success_count = len(failed_barcodes_first_round) - len(failed_barcodes_second_round)
                logger.info(f"第二轮重试结果：")
                logger.info(f"  重试成功: {retry_success_count} 条")
                logger.info(f"  仍失败: {len(failed_barcodes_second_round)} 条")
            else:
                failed_barcodes_second_round = failed_barcodes_first_round
                if not retry_failed:
                    logger.info("已禁用失败条码重试功能")

            # 最终保存 - 保证所有缓冲结果落盘
            await self._maybe_flush_results(df, excel_file_path, force=True)

            # 生成统计信息
            stats = {
                'total_records': total_records,
                'success_count': self.stats['successful_isbn'],
                'failed_count': self.stats['failed_isbn'],
                'skipped_count': self.stats['skipped_count'],
                'success_rate': self.stats['successful_isbn'] / (total_records - self.stats['skipped_count']) * 100 if total_records > self.stats['skipped_count'] else 0,
                'processing_time': time.time() - start_time,
                'retry_enabled': retry_failed,
                'failed_after_retry': len(failed_barcodes_second_round)
            }

            logger.info("=" * 80)
            logger.info("异步批量处理完成:")
            logger.info("=" * 80)
            logger.info(f"  总记录数: {stats['total_records']}")
            logger.info(f"  成功获取: {stats['success_count']}")
            logger.info(f"  获取失败: {stats['failed_count']}")
            logger.info(f"  跳过记录: {stats['skipped_count']}")
            logger.info(f"  成功率: {stats['success_rate']:.2f}%")
            logger.info(f"  处理时间: {stats['processing_time']:.2f}秒")
            if retry_failed:
                logger.info(f"  重试后仍失败: {stats['failed_after_retry']} 条")
            logger.info("=" * 80)

            return excel_file_path, stats

        except Exception as e:
            logger.error(f"异步批量处理失败: {e}")
            raise
        finally:
            if 'df' in locals():
                try:
                    await self._maybe_flush_results(df, excel_file_path, force=True)
                except Exception as flush_error:
                    logger.error(f"清理阶段保存结果失败: {flush_error}")
            await self.stop_workers()

    async def _process_batch(self, df: pd.DataFrame, excel_file_path: str,
                           barcode_column: str, output_column: str, total_records: int,
                           batch_name: str = "处理", data_to_process_indices: List[int] = None,
                           skip_existing_with_value: bool = True) -> List[Tuple[int, str]]:
        """批量处理条码（第一轮或第二轮）"""
        failed_barcodes: List[Tuple[int, str]] = []

        semaphores = asyncio.Semaphore(self.max_concurrent)

        async def process_with_semaphore(index: int, barcode: str):
            async with semaphores:
                return await self._process_single_barcode_safe(index, barcode)

        tasks: List[Tuple[int, asyncio.Task]] = []
        for index, row in df.iterrows():
            if data_to_process_indices is not None and index not in data_to_process_indices:
                continue
            barcode = str(row[barcode_column]).strip()
            if not barcode or barcode == 'nan':
                self._stage_result(index, "跳过：空条码")
                self.stats['skipped_count'] += 1
                continue
            if skip_existing_with_value:
                current_value = df.at[index, output_column]
                if not pd.isna(current_value) and str(current_value).strip():
                    self._stage_result(index, str(current_value).strip())
                    self.stats['total_processed'] += 1
                    continue
            task = process_with_semaphore(index, barcode)
            tasks.append((index, task))

        logger.info(f"{batch_name}：开始并发处理{len(tasks)} 条记录..")
        if not tasks:
            return failed_barcodes

        async def _run_task_chunk(task_group: List[Tuple[int, asyncio.Task]]) -> int:
            results = await asyncio.gather(*[task for _, task in task_group], return_exceptions=True)
            for (index, _), result in zip(task_group, results):
                if isinstance(result, Exception):
                    logger.error(f"处理第 {index + 1} 条记录时发生异常: {result}")
                    result = "获取失败"
                self._stage_result(index, result)
                if result == "获取失败":
                    barcode = str(df.at[index, barcode_column]).strip()
                    failed_barcodes.append((index, barcode))
            await self._maybe_flush_results(df, excel_file_path)
            return len(task_group)

        processed_count = 0
        chunk_size = self.batch_size if self.batch_size and self.batch_size > 0 else len(tasks)
        chunk_size = max(1, chunk_size)
        for start_idx in range(0, len(tasks), chunk_size):
            chunk = tasks[start_idx:start_idx + chunk_size]
            processed_count += await _run_task_chunk(chunk)

        await self._maybe_flush_results(df, excel_file_path, force=True)
        logger.info(f"{batch_name}处理完成，失败 {len(failed_barcodes)} 条")
        return failed_barcodes

    async def _process_failed_barcodes(self, df: pd.DataFrame, excel_file_path: str,
                                     failed_barcodes: List[Tuple[int, str]],
                                     batch_name: str = "重试") -> List[Tuple[int, str]]:
        """
        重新处理失败的条码

        Args:
            df: DataFrame对象
            excel_file_path: Excel文件路径
            failed_barcodes: 失败的条码列表 [(index, barcode), ...]
            batch_name: 批次名称（用于日志）

        Returns:
            List[Tuple[int, str]]: 仍然失败的条码列表
        """
        still_failed = []

        # 创建信号量限制并发数
        semaphores = asyncio.Semaphore(self.max_concurrent)

        # 重新处理每个失败的条码
        for index, barcode in failed_barcodes:
            async with semaphores:
                logger.info(f"{batch_name}：重新处理条码 {barcode} (行 {index + 1})")

                # 再次获取ISBN
                isbn = await self._process_single_barcode_safe(index, barcode, is_retry=True)

                # 更新结果缓冲区
                self._stage_result(index, isbn)

                # 如果仍然失败，记录
                if isbn == "获取失败":
                    still_failed.append((index, barcode))

                # 等待一小段时间
                await self._processor_delay(0.5)

        await self._maybe_flush_results(df, excel_file_path, force=True)

        logger.info(f"{batch_name}重试完成，仍有 {len(still_failed)} 条失败")

        return still_failed

    async def _process_single_barcode_safe(self, index: int, barcode: str, is_retry: bool = False) -> str:
        """
        安全处理单个条码（使用结果缓冲区避免并发冲突）

        Args:
            index: 记录索引
            barcode: 条码值
            is_retry: 是否为重试操作（影响日志输出）

        Returns:
            str: 处理结果（ISBN号或"获取失败"）
        """
        try:
            # 选择工作器（轮询）
            worker = await self._get_next_worker()

            # 根据是否为重试生成不同的日志前缀
            log_prefix = "重试" if is_retry else "处理"
            logger.info(f"工作器 {worker.worker_id}: {log_prefix}第 {index + 1} 条记录: {barcode}")

            # 获取ISBN
            isbn = await worker.get_isbn(barcode)

            if isbn:
                self.stats['successful_isbn'] += 1
                logger.info(f"✓ 成功获取ISBN: {isbn}")
                result = isbn
            else:
                self.stats['failed_isbn'] += 1
                logger.warning(f"✗ 获取ISBN失败: {barcode}")
                result = "获取失败"

            self.stats['total_processed'] += 1

            # 等待一小段时间避免过快请求
            await self._processor_delay(0.5)

            return result

        except Exception as e:
            error_msg = f"错误: {str(e)[:50]}"
            logger.error(f"处理记录 {index + 1} 时出错: {str(e)}")
            self.stats['failed_isbn'] += 1
            self.stats['total_processed'] += 1
            return error_msg

    async def _process_single_barcode(self, index: int, barcode: str, df: pd.DataFrame,
                                     excel_file_path: str, output_column: str):
        """处理单个条码（保留以兼容旧版本）"""
        try:
            # 选择工作器（轮询）
            worker = await self._get_next_worker()

            logger.info(f"工作器 {worker.worker_id}: 处理第 {index + 1} 条记录: {barcode}")

            # 获取ISBN
            isbn = await worker.get_isbn(barcode)

            if isbn:
                df.at[index, output_column] = isbn
                self.stats['successful_isbn'] += 1
                logger.info(f"✓ 成功获取ISBN: {isbn}")
            else:
                df.at[index, output_column] = "获取失败"
                self.stats['failed_isbn'] += 1
                logger.warning(f"✗ 获取ISBN失败: {barcode}")

            self.stats['total_processed'] += 1

            # 立即保存到Excel
            await self._save_to_excel(df, excel_file_path, index + 1)

            # 等待一小段时间避免过快请求
            await self._processor_delay(0.5)

        except Exception as e:
            error_msg = f"处理记录 {index + 1} 时出错: {str(e)}"
            logger.error(error_msg)
            df.at[index, output_column] = f"错误: {str(e)[:50]}"
            self.stats['failed_isbn'] += 1
            await self._save_to_excel(df, excel_file_path, index + 1)

    async def _save_results_to_excel(self, df: pd.DataFrame, excel_file_path: str, processed_count: int, is_final: bool = False):
        """Write buffered results to Excel with atomic rename semantics."""
        if not self.output_column:
            logger.warning("输出列未设置，跳过保存请求")
            return

        async with self.write_lock:
            try:
                if is_final:
                    target_indices = list(self.results_buffer.keys())
                else:
                    target_indices = list(self._pending_indices)

                if not target_indices:
                    return

                for index in target_indices:
                    value = self.results_buffer.get(index)
                    if value is None:
                        continue
                    df.at[index, self.output_column] = value

                temp_file = excel_file_path.replace('.xlsx', f'_tmp_{int(time.time())}.xlsx')
                df.to_excel(temp_file, index=False, engine='openpyxl')

                if os.path.exists(excel_file_path):
                    os.remove(excel_file_path)
                os.rename(temp_file, excel_file_path)

                if is_final:
                    logger.info(f"[保存] 已写入 {len(target_indices)} 条记录到Excel（最终保存）")
                else:
                    logger.debug(f"[保存] 增量写入 {len(target_indices)} 条记录到Excel")

                if is_final:
                    self.results_buffer.clear()
                    self._pending_indices.clear()
                    self._final_only_indices.clear()
                else:
                    for index in target_indices:
                        self._pending_indices.discard(index)
                        self.results_buffer.pop(index, None)

            except Exception as e:
                logger.error(f"保存Excel失败: {e}")
                if 'temp_file' in locals() and os.path.exists(temp_file):
                    os.remove(temp_file)
    async def _save_batch_results(self, df: pd.DataFrame, excel_file_path: str, processed_count: int, is_final: bool = False):
        """批量保存所有结果到Excel（并发修复版）"""
        async with self.write_lock:
            try:
                # 原子性保存：先写临时文件，再重命名
                temp_file = excel_file_path.replace('.xlsx', f'_tmp_{int(time.time())}.xlsx')
                df.to_excel(temp_file, index=False, engine='openpyxl')

                # 重命名为最终文件
                if os.path.exists(excel_file_path):
                    os.remove(excel_file_path)
                os.rename(temp_file, excel_file_path)

                if is_final:
                    logger.info(f"[OK] 已保存全部 {processed_count} 条记录到Excel")
                else:
                    logger.debug(f"已保存 {processed_count} 条记录")

            except Exception as e:
                logger.error(f"保存Excel失败: {e}")
                # 清理临时文件
                temp_file = excel_file_path.replace('.xlsx', f'_tmp_{int(time.time())}.xlsx')
                if os.path.exists(temp_file):
                    os.remove(temp_file)

    async def _save_single_result(self, df: pd.DataFrame, excel_file_path: str, index: int, result: str):
        """保存单条记录到Excel（处理一条立即保存）"""
        async with self.write_lock:
            try:
                column = self.output_column or 'ISBN号'
                if column not in df.columns:
                    df[column] = ""

                df.at[index, column] = result

                # 原子性保存：先写临时文件，再重命名
                temp_file = excel_file_path.replace('.xlsx', f'_tmp_{int(time.time())}.xlsx')
                df.to_excel(temp_file, index=False, engine='openpyxl')

                # 重命名为最终文件
                if os.path.exists(excel_file_path):
                    os.remove(excel_file_path)
                os.rename(temp_file, excel_file_path)

                logger.info(f"✓ 已保存第 {index + 1} 条记录: {result}")

            except Exception as e:
                logger.error(f"保存单条记录失败: {e}")
                # 清理临时文件
                if 'temp_file' in locals() and os.path.exists(temp_file):
                    os.remove(temp_file)

    async def _save_to_excel(self, df: pd.DataFrame, excel_file_path: str, processed_count: int):
        """保存到Excel文件（保留以兼容旧版本）"""
        async with self.write_lock:
            try:
                # 原子性保存：先写临时文件，再重命名
                temp_file = excel_file_path + '.tmp'
                df.to_excel(temp_file, index=False)

                # 重命名为最终文件
                if os.path.exists(excel_file_path):
                    os.remove(excel_file_path)
                os.rename(temp_file, excel_file_path)

                logger.debug(f"已安全保存第 {processed_count} 条记录到Excel")

            except Exception as e:
                logger.warning(f"保存Excel失败: {e}")
                # 清理临时文件
                temp_file = excel_file_path + '.tmp'
                if os.path.exists(temp_file):
                    os.remove(temp_file)

    def _can_partial_flush(self, value: Optional[str]) -> bool:
        """Return True when a value can be flushed before最终保存."""
        if value is None:
            return False
        text = str(value).strip()
        if not text:
            return False
        return not text.startswith(("跳过", "获取失败", "错误"))

    def _stage_result(self, index: int, value: str):
        """Record a result and decide whether it can be flushed incrementally."""
        self.results_buffer[index] = value
        if self._can_partial_flush(value):
            self._final_only_indices.discard(index)
            self._pending_indices.add(index)
        else:
            self._pending_indices.discard(index)
            self._final_only_indices.add(index)

    async def _maybe_flush_results(self, df: pd.DataFrame, excel_file_path: str, *, force: bool = False):
        """Flush buffered results when thresholds are met."""
        if not self.results_buffer:
            return

        if force:
            await self._save_results_to_excel(df, excel_file_path, len(self.results_buffer), is_final=True)
            self._last_flush_ts = time.monotonic()
            return

        should_flush = False
        if self.save_interval > 0 and len(self._pending_indices) >= self.save_interval:
            should_flush = True
        elif self.save_interval <= 0 and self._pending_indices:
            # 在仅最终保存模式下依赖时间触发
            should_flush = False

        if not should_flush and self.save_interval_seconds > 0 and self._pending_indices:
            if (time.monotonic() - self._last_flush_ts) >= self.save_interval_seconds:
                should_flush = True

        if should_flush and self._pending_indices:
            await self._save_results_to_excel(df, excel_file_path, len(self._pending_indices), is_final=False)
            self._last_flush_ts = time.monotonic()

    # ============================================================================
    # 数据库相关方法
    # ============================================================================

    async def _process_existing_valid_books(self, valid_data: List[Dict], df: pd.DataFrame,
                                           excel_file_path: str, output_column: str):
        """处理已有有效数据（从数据库获取）"""
        logger.info(f"从数据库加载已有有效数据: {len(valid_data)} 条")
        if not valid_data:
            return

        deduped: Dict[str, Dict] = {}
        for book_data in valid_data:
            barcode = book_data.get('barcode') or book_data.get('书目条码')
            if not barcode:
                logger.warning(f"跳过缺少barcode的记录: {book_data}")
                continue
            barcode = str(barcode).strip()
            updated_at = (book_data.get('updated_at') or '').strip()
            existing = deduped.get(barcode)
            if existing:
                prev = (existing.get('updated_at') or '').strip()
                if updated_at and prev and updated_at <= prev:
                    continue
            deduped[barcode] = book_data

        try:
            for barcode, book_data in deduped.items():
                excel_index = self._find_row_index(df, barcode)
                if excel_index == -1:
                    logger.warning(f"在Excel中未找到条码 {barcode}，跳过")
                    continue

                isbn_value = (book_data.get('isbn') or book_data.get('ISBN') or '').strip()
                if not isbn_value:
                    continue

                updated_at = (book_data.get('updated_at') or '').strip()
                if output_column in df.columns:
                    existing_cell = df.at[excel_index, output_column]
                    existing_value = '' if pd.isna(existing_cell) else str(existing_cell).strip()
                else:
                    existing_value = ''
                cached_marker = self._db_result_cache.get(barcode)
                if existing_value == isbn_value and cached_marker == updated_at:
                    logger.debug(f"跳过重复回填: {barcode}")
                    continue

                df.at[excel_index, output_column] = isbn_value
                self._stage_result(excel_index, isbn_value)
                if updated_at:
                    self._db_result_cache[barcode] = updated_at

                self.stats['successful_isbn'] += 1
                self.stats['total_processed'] += 1

            await self._maybe_flush_results(df, excel_file_path, force=True)
            logger.info(f"已有有效数据处理完成: {len(deduped)} 条")

        except Exception as e:
            logger.error(f"处理已有有效数据失败: {e}")
            raise

    def _is_valid_isbn_value(self, value: Optional[str]) -> bool:
        """Return True if the given Excel cell contains a legal ISBN value."""
        if value is None:
            return False
        if isinstance(value, float) and pd.isna(value):
            return False
        text = str(value).strip()
        if not text or text.lower() == 'nan':
            return False
        if not ISBN_ALLOWED_PATTERN.fullmatch(text):
            return False
        return any(ch.isdigit() for ch in text)

    def _collect_rows_with_valid_isbn(self, df: pd.DataFrame, output_column: str) -> Set[int]:
        """Collect row indices whose ISBN column already contains a valid value."""
        if output_column not in df.columns:
            return set()
        valid_rows: Set[int] = set()
        for idx, cell in df[output_column].items():
            if self._is_valid_isbn_value(cell):
                valid_rows.add(idx)
        return valid_rows

    def _initialize_row_index_cache(self, df: pd.DataFrame, barcode_column: str) -> None:
        """预构建条码到行索引的映射，避免重复扫描。"""
        if barcode_column not in df.columns:
            self._row_index_cache = {}
            self._row_cache_column = None
            return

        cache: Dict[str, int] = {}
        duplicate_count = 0
        for idx, value in df[barcode_column].items():
            barcode = str(value).strip()
            if not barcode:
                continue
            if barcode in cache:
                duplicate_count += 1
                continue
            cache[barcode] = idx

        self._row_index_cache = cache
        self._row_cache_column = barcode_column
        if duplicate_count:
            logger.warning(f"条码列 {barcode_column} 中发现 {duplicate_count} 个重复条码，仅使用第一次出现的记录")

    def _find_row_index(self, df: pd.DataFrame, barcode: str) -> int:
        """根据barcode查找Excel行索引"""
        barcode_str = str(barcode).strip()
        if not barcode_str:
            return -1

        if self._row_index_cache and self._row_cache_column and self._row_cache_column in df.columns:
            cached = self._row_index_cache.get(barcode_str)
            if cached is not None:
                return cached

        barcode_column = None
        if self.barcode_column and self.barcode_column in df.columns:
            barcode_column = self.barcode_column
        elif 'barcode' in df.columns:
            barcode_column = 'barcode'
        elif '书目条码' in df.columns:
            barcode_column = '书目条码'
        else:
            logger.error("Excel中未找到barcode列")
            return -1

        for idx, row in df.iterrows():
            row_barcode = str(row[barcode_column]).strip()
            if row_barcode == barcode_str:
                if self._row_cache_column == barcode_column:
                    self._row_index_cache[barcode_str] = idx
                return idx

        return -1

    async def _batch_save_to_database(self, books_data: List[Dict], borrow_records_list: List[Dict],
                                     statistics_list: List[Dict]):
        """
        批量保存到数据库

        Args:
            books_data: books表数据列表
            borrow_records_list: borrow_records表数据列表
            statistics_list: borrow_statistics表数据列表
        """
        if not self.db_manager:
            logger.warning("数据库管理器未初始化，跳过保存")
            return

        try:
            logger.info(f"开始批量保存到数据库: {len(books_data)} 条books数据")

            batch_size = self.db_config.get('write_strategy', {}).get('batch_size', 100)
            self.db_manager.batch_save_data(books_data, borrow_records_list, statistics_list, batch_size)

            logger.info("批量保存到数据库完成")

        except Exception as e:
            logger.error(f"批量保存到数据库失败: {e}")
            raise

    async def _process_all_books_without_db(self, df: pd.DataFrame, excel_file_path: str,
                                           barcode_column: str, output_column: str, total_records: int):
        """
        降级处理：没有数据库功能时的原有逻辑

        Args:
            df: DataFrame对象
            excel_file_path: Excel文件路径
            barcode_column: 条码列名
            output_column: 输出列名
            total_records: 总记录数
        """
        logger.info("降级到原有处理逻辑（无数据库）")

        # 调用原有的_process_batch方法
        await self._process_batch(
            df, excel_file_path, barcode_column, output_column, total_records,
            batch_name="处理"
        )

# ============================================================================
# 便捷接口函数
# ============================================================================

def process_isbn_async(excel_file_path: str,
                      max_concurrent: int = 2,
                      save_interval: int = 25,
                      barcode_column: str = "书目条码",
                      output_column: str = "ISBN号",
                      username: str = None,
                      password: str = None,
                      retry_failed: bool = True,
                      enable_database: bool = False,
                      db_config: Dict = None,
                      processing_config: Optional[ProcessingConfig] = None) -> Tuple[str, Dict]:
    """
    异步处理ISBN的便捷接口函数

    Args:
        excel_file_path: Excel文件路径
        max_concurrent: 最大并发数（默认2，允许并发处理）
        save_interval: 保存间隔，1表示处理一条保存一次（默认）
        barcode_column: 书目条码列名
        output_column: 输出ISBN列名
        username: FOLIO系统用户名（可选）
        password: FOLIO系统密码（可选）
        retry_failed: 是否在第一轮处理完后重试失败的条码（默认True）
        enable_database: 是否启用数据库功能（默认False）
        db_config: 数据库配置字典（可选）

    Returns:
        Tuple[str, Dict]: (文件路径, 统计信息)
    """
    async def _process():
        # 创建处理器
        processor = ISBNAsyncProcessor(
            max_concurrent=max_concurrent,
            save_interval=save_interval,
            enable_database=enable_database,
            db_config=db_config,
            processing_config=processing_config,
        )

        # 如果提供了用户名和密码，更新配置
        if username and password:
            processor.username = username
            processor.password = password

        # 批量处理
        output_file, stats = await processor.process_excel_file(
            excel_file_path=excel_file_path,
            barcode_column=barcode_column,
            output_column=output_column,
            retry_failed=retry_failed
        )

        return output_file, stats

    return asyncio.run(_process())


if __name__ == "__main__":
    # 测试代码
    async def test_async_processor():
        """测试异步处理器"""
        test_excel = "runtime/outputs/月归还数据筛选结果_20251101_183318.xlsx"

        if not os.path.exists(test_excel):
            logger.error(f"测试文件不存在: {test_excel}")
            return

        try:
            # 显示性能估算
            import pandas as pd
            df_test = pd.read_excel(test_excel)
            data_size = len(df_test)
            estimated_time = data_size * 1.5 / 3600  # 估算1.5秒/条
            logger.info(f"数据量: {data_size} 条，预计处理时间: {estimated_time:.1f} 小时")

            # 执行处理
            output_file, stats = await process_isbn_async(
                excel_file_path=test_excel,
                max_concurrent=3,
                barcode_column="书目条码",
                output_column="ISBN号"
            )

            logger.info(f"处理完成，结果: {output_file}")
            logger.info(f"处理统计: {stats}")

        except Exception as e:
            logger.error(f"测试失败: {str(e)}")

    # 运行测试
    asyncio.run(test_async_processor())
