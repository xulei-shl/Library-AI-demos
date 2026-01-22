"""
图片下载器模块
负责下载豆瓣封面图片
支持并发下载以提升性能
使用 Playwright 访问豆瓣页面并下载图片
"""

import os
import time
import threading
from typing import Dict, Tuple, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ImageDownloader:
    """图片下载器类"""

    def __init__(self, config: Dict):
        """
        初始化图片下载器

        Args:
            config: 配置字典
        """
        self.config = config.get('image_download', {})
        self.timeout = self.config.get('timeout', 30000)
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay = self.config.get('retry_delay', 2)
        self.user_agent = self.config.get(
            'user_agent',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        self.url_replacements = self.config.get('url_replacements', [])
        self.supported_formats = self.config.get('supported_formats', ['jpg', 'png', 'jpeg'])
        self.headless = self.config.get('headless', True)

        # 并发下载配置(性能优化)
        self.max_concurrent_downloads = self.config.get('max_concurrent_downloads', 2)
        self.download_delay = self.config.get('download_delay', 0.5)

        # Playwright 浏览器实例（线程本地存储）
        self._thread_local = threading.local()

    def _get_browser(self) -> Optional[Browser]:
        """
        获取当前线程的浏览器实例（如果不存在则创建）

        Returns:
            Optional[Browser]: 浏览器实例
        """
        if hasattr(self._thread_local, 'browser') and self._thread_local.browser:
            return self._thread_local.browser

        try:
            pw = sync_playwright().start()
            self._thread_local.playwright = pw
            self._thread_local.browser = pw.chromium.launch(headless=self.headless)
            logger.debug(f"线程 {threading.current_thread().name} 的浏览器实例已启动")
            return self._thread_local.browser
        except Exception as e:
            logger.error(f"启动浏览器失败：{e}")
            return None

    def _close_browser(self) -> None:
        """关闭当前线程的浏览器实例"""
        if hasattr(self._thread_local, 'browser') and self._thread_local.browser:
            try:
                self._thread_local.browser.close()
                self._thread_local.browser = None
            except Exception as e:
                logger.warning(f"关闭浏览器时发生错误：{e}")

        if hasattr(self._thread_local, 'playwright') and self._thread_local.playwright:
            try:
                self._thread_local.playwright.stop()
                self._thread_local.playwright = None
            except Exception as e:
                logger.warning(f"关闭Playwright时发生错误：{e}")

    def __del__(self):
        """析构函数，确保浏览器实例被关闭"""
        self._close_browser()

    def extract_image_url_from_douban_page(self, douban_url: str) -> Optional[str]:
        """
        使用 Playwright 从豆瓣图书页面提取大图链接

        Args:
            douban_url: 豆瓣图书页面URL

        Returns:
            Optional[str]: 大图链接，失败返回None
        """
        if not douban_url or not douban_url.strip():
            return None

        browser = self._get_browser()
        if not browser:
            return None

        page = None
        try:
            page = browser.new_page(user_agent=self.user_agent)
            page.goto(douban_url, timeout=self.timeout, wait_until='networkidle')

            # 提取 #mainpic a.nbg 的 href 属性
            image_url = page.evaluate("""
                () => {
                    const mainpic = document.querySelector('#mainpic a.nbg');
                    return mainpic ? mainpic.href : null;
                }
            """)

            if image_url:
                logger.debug(f"从豆瓣页面提取到大图链接：{image_url}")
                return image_url

            logger.warning(f"豆瓣页面未找到封面图片：{douban_url}")
            return None

        except Exception as e:
            logger.error(f"解析豆瓣页面时发生错误：{e}")
            return None
        finally:
            if page:
                try:
                    page.close()
                except Exception:
                    pass

    def download_cover_image(
        self, url: str, output_path: str, douban_url: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        使用 Playwright 下载封面图片

        Args:
            url: 图片URL
            output_path: 输出路径（不含扩展名）
            douban_url: 豆瓣图书页面URL（用于提取真实图片URL）

        Returns:
            Tuple[bool, str]: (是否成功, 实际保存路径)
        """
        # 优先使用豆瓣页面提取真实图片URL
        if douban_url:
            extracted_url = self.extract_image_url_from_douban_page(douban_url)
            if extracted_url:
                url = extracted_url
            else:
                logger.warning("从豆瓣页面提取图片失败，使用原URL尝试下载")

        if not url or not url.strip():
            logger.error("图片URL为空")
            return False, ""

        # 处理豆瓣URL
        processed_url = self.process_douban_url(url)

        logger.debug(f"下载封面图片：{processed_url}")

        # 尝试下载
        for retry_count in range(self.max_retries):
            browser = self._get_browser()
            if not browser:
                logger.error("浏览器实例不可用")
                return False, ""

            page = None
            try:
                page = browser.new_page()
                # 访问图片URL
                response = page.goto(processed_url, timeout=self.timeout)

                if not response or response.status != 200:
                    logger.warning(
                        f"下载失败，状态码：{response.status if response else 'None'}，"
                        f"重试 {retry_count + 1}/{self.max_retries}"
                    )
                    time.sleep(self.retry_delay * (retry_count + 1))
                    continue

                # 获取图片二进制数据
                image_bytes = response.body()

                # 检测图片格式
                image_format = self.detect_image_format(image_bytes)

                if not image_format:
                    logger.error("无法识别图片格式")
                    return False, ""

                # 构建完整路径
                full_path = f"{output_path}.{image_format}"

                # 确保输出目录存在
                output_dir = os.path.dirname(full_path)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)

                # 保存图片
                with open(full_path, 'wb') as f:
                    f.write(image_bytes)

                logger.debug(f"封面图片下载成功：{full_path}")
                return True, full_path

            except PlaywrightTimeoutError:
                logger.warning(
                    f"网络请求超时，{self.retry_delay * (retry_count + 1)}秒后重试 "
                    f"({retry_count + 1}/{self.max_retries})"
                )
                time.sleep(self.retry_delay * (retry_count + 1))

            except Exception as e:
                logger.warning(
                    f"下载失败：{e}，重试 {retry_count + 1}/{self.max_retries}"
                )
                time.sleep(self.retry_delay * (retry_count + 1))

            finally:
                if page:
                    try:
                        page.close()
                    except Exception:
                        pass

        logger.error(f"封面图片下载失败（已重试{self.max_retries}次）：{processed_url}")
        return False, ""

    def process_douban_url(self, url: str) -> str:
        """
        处理豆瓣图片URL（替换为大图）

        Args:
            url: 原始URL

        Returns:
            str: 处理后的URL
        """
        processed_url = url

        # 应用URL替换规则
        for replacement in self.url_replacements:
            old = replacement.get('old', '')
            new = replacement.get('new', '')
            if old and old in processed_url:
                processed_url = processed_url.replace(old, new)
                logger.debug(f"替换URL：{old} -> {new}")

        return processed_url

    def detect_image_format(self, content: bytes) -> str:
        """
        检测图片格式（通过魔数）

        Args:
            content: 图片二进制数据

        Returns:
            str: 图片格式（jpg/png/jpeg），无法识别返回空字符串
        """
        if not content or len(content) < 8:
            return ""

        # PNG魔数：89 50 4E 47 0D 0A 1A 0A
        if content[:8] == b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A':
            return 'png'

        # JPEG魔数：FF D8 FF
        if content[:3] == b'\xFF\xD8\xFF':
            return 'jpg'

        # 如果无法通过魔数识别，返回默认格式
        logger.warning("无法通过魔数识别图片格式，使用默认格式jpg")
        return 'jpg'

    def download_covers_batch(
        self, download_tasks: List[Tuple[str, str, Optional[str]]]
    ) -> List[Tuple[bool, str, str]]:
        """
        批量并发下载封面图片(性能优化)

        Args:
            download_tasks: 下载任务列表,每个任务为(url, output_path, douban_url)元组

        Returns:
            List[Tuple[bool, str, str]]: 结果列表,每个结果为(是否成功, 输出路径, URL)
        """
        if not download_tasks:
            return []

        logger.info(f"开始批量下载 {len(download_tasks)} 张封面图片(并发数:{self.max_concurrent_downloads})...")

        results = []
        completed_count = 0

        # 使用线程池并发下载
        with ThreadPoolExecutor(max_workers=self.max_concurrent_downloads) as executor:
            # 提交所有下载任务
            future_to_task = {}
            for url, output_path, douban_url in download_tasks:
                future = executor.submit(self._download_single_with_delay, url, output_path, douban_url)
                future_to_task[future] = (url, output_path)

            # 收集结果
            for future in as_completed(future_to_task):
                url, output_path = future_to_task[future]
                try:
                    success, actual_path = future.result()
                    results.append((success, actual_path, url))
                    completed_count += 1

                    if success:
                        logger.debug(f"下载成功 ({completed_count}/{len(download_tasks)}): {url}")
                    else:
                        logger.warning(f"下载失败 ({completed_count}/{len(download_tasks)}): {url}")

                except Exception as e:
                    logger.error(f"下载异常: {url}, 错误: {e}")
                    results.append((False, "", url))
                    completed_count += 1

        # 关闭所有线程的浏览器实例
        self._cleanup_all_browsers()

        success_count = sum(1 for success, _, _ in results if success)
        logger.info(f"批量下载完成: 成功 {success_count}/{len(download_tasks)} 张")

        return results

    def _download_single_with_delay(
        self, url: str, output_path: str, douban_url: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        下载单张图片(带延迟,避免反爬)

        Args:
            url: 图片URL
            output_path: 输出路径
            douban_url: 豆瓣图书页面URL

        Returns:
            Tuple[bool, str]: (是否成功, 实际保存路径)
        """
        # 添加随机延迟,避免触发反爬
        if self.download_delay > 0:
            import random
            delay = self.download_delay + random.uniform(0, 0.3)
            time.sleep(delay)

        return self.download_cover_image(url, output_path, douban_url)

    def _cleanup_all_browsers(self) -> None:
        """清理所有浏览器资源"""
        self._close_browser()
