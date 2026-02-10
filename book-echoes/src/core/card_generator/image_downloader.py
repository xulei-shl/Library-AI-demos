"""
图片下载器模块
负责下载豆瓣封面图片
使用 Playwright 访问豆瓣页面并下载图片

稳定性设计：
- 顺序下载，不使用并发
- 单一浏览器实例
- 非无头模式便于调试
- 支持 requests 备用方案
"""

import os
import time
from typing import Dict, Tuple, List, Optional
import requests
from playwright.sync_api import sync_playwright, Browser, Page
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
        # 配置中的 timeout 单位是秒，需要转换为毫秒
        self.timeout = self.config.get('timeout', 30) * 1000
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay = self.config.get('retry_delay', 2)
        self.user_agent = self.config.get(
            'user_agent',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        self.url_replacements = self.config.get('url_replacements', [])
        self.supported_formats = self.config.get('supported_formats', ['jpg', 'png', 'jpeg'])
        # 默认非无头模式，便于调试
        self.headless = self.config.get('headless', False)

        # Playwright 实例
        self._playwright = None
        self._browser = None
        self._stealth_enabled = self.config.get('enable_stealth', True)

    def _get_browser(self) -> Optional[Browser]:
        """
        获取浏览器实例（如果不存在则创建）

        Returns:
            Optional[Browser]: 浏览器实例
        """
        if self._browser is not None:
            return self._browser

        try:
            self._playwright = sync_playwright().start()

            # 浏览器启动参数 - 增强反爬虫措施
            browser_args = [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-features=IsolateOrigins,site-per-process',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
            ]

            self._browser = self._playwright.chromium.launch(
                headless=self.headless,
                args=browser_args
            )

            logger.info(f"浏览器实例已启动（headless={self.headless}, stealth={self._stealth_enabled}）")
            return self._browser
        except Exception as e:
            logger.error(f"启动浏览器失败：{e}")
            return None

    def _close_browser(self) -> None:
        """关闭浏览器实例"""
        if self._browser:
            try:
                self._browser.close()
                logger.debug("浏览器实例已关闭")
            except Exception as e:
                logger.warning(f"关闭浏览器时发生错误：{e}")
            finally:
                self._browser = None

        if self._playwright:
            try:
                self._playwright.stop()
                logger.debug("Playwright 实例已停止")
            except Exception as e:
                logger.warning(f"关闭Playwright时发生错误：{e}")
            finally:
                self._playwright = None

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
            # 创建页面上下文
            page = browser.new_page(user_agent=self.user_agent)

            # 添加初始化脚本，隐藏 webdriver 特征
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en']
                });
                window.chrome = {
                    runtime: {}
                };
            """)

            # 访问豆瓣页面
            page.goto(douban_url, timeout=self.timeout, wait_until='domcontentloaded')

            # 添加短暂延迟，模拟人类操作
            time.sleep(1)

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
        下载封面图片

        逻辑：
        1. 如果有豆瓣 URL，用 Playwright 访问页面提取图片链接
        2. 使用 requests 直接下载图片

        Args:
            url: 图片URL
            output_path: 输出路径（不含扩展名）
            douban_url: 豆瓣图书页面URL（用于提取真实图片URL）

        Returns:
            Tuple[bool, str]: (是否成功, 实际保存路径)
        """
        # 步骤1：如果有豆瓣 URL，用 Playwright 访问页面提取图片链接
        if douban_url:
            extracted_url = self.extract_image_url_from_douban_page(douban_url)
            if extracted_url:
                url = extracted_url
                logger.debug(f"从豆瓣页面提取到图片链接：{url}")
            else:
                logger.warning(f"从豆瓣页面提取图片失败：{douban_url}，使用原 URL")

        # 检查 URL 是否有效
        if not url or not url.strip():
            logger.error("图片URL为空")
            return False, ""

        # 处理豆瓣URL（小图转大图）
        processed_url = self.process_douban_url(url)
        logger.debug(f"准备下载图片：{processed_url}")

        # 步骤2：使用 requests 直接下载图片
        for retry_count in range(self.max_retries):
            success, actual_path = self._download_with_requests(processed_url, output_path)
            if success:
                return True, actual_path

            logger.warning(
                f"下载失败，{self.retry_delay * (retry_count + 1)}秒后重试 "
                f"({retry_count + 1}/{self.max_retries})"
            )
            time.sleep(self.retry_delay * (retry_count + 1))

        logger.error(f"图片下载失败（已重试{self.max_retries}次）：{processed_url}")
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

    def _download_with_requests(self, url: str, output_path: str) -> Tuple[bool, str]:
        """
        使用 requests 库直接下载图片（备用方案，绕过反爬虫）

        Args:
            url: 图片URL
            output_path: 输出路径（不含扩展名）

        Returns:
            Tuple[bool, str]: (是否成功, 实际保存路径)
        """
        try:
            headers = {
                'User-Agent': self.user_agent,
                'Referer': 'https://book.douban.com/',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
            }

            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                image_bytes = response.content

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

                logger.info(f"使用 requests 下载成功：{full_path}")
                return True, full_path
            else:
                logger.warning(f"requests 下载失败，状态码：{response.status_code}")
                return False, ""

        except Exception as e:
            logger.warning(f"requests 下载异常：{e}")
            return False, ""

    def download_covers_batch(
        self, download_tasks: List[Tuple[str, str, Optional[str]]]
    ) -> List[Tuple[bool, str, str]]:
        """
        批量顺序下载封面图片（稳定性优先）

        Args:
            download_tasks: 下载任务列表,每个任务为(url, output_path, douban_url)元组

        Returns:
            List[Tuple[bool, str, str]]: 结果列表,每个结果为(是否成功, 输出路径, URL)
        """
        if not download_tasks:
            return []

        logger.info(f"开始顺序下载 {len(download_tasks)} 张封面图片...")

        # 预先启动浏览器（所有任务共用）
        browser = self._get_browser()
        if not browser:
            logger.error("无法启动浏览器实例")
            return [(False, "", url) for _, _, url in download_tasks]

        results = []
        success_count = 0

        for index, (url, output_path, douban_url) in enumerate(download_tasks, 1):
            try:
                success, actual_path = self.download_cover_image(url, output_path, douban_url)
                results.append((success, actual_path, url))

                if success:
                    success_count += 1
                    logger.info(f"下载成功 ({index}/{len(download_tasks)}): {url}")
                else:
                    logger.warning(f"下载失败 ({index}/{len(download_tasks)}): {url}")

            except Exception as e:
                logger.error(f"下载异常 ({index}/{len(download_tasks)}): {url}, 错误: {e}")
                results.append((False, "", url))

        # 批量下载完成，关闭浏览器实例
        self._close_browser()

        logger.info(f"顺序下载完成: 成功 {success_count}/{len(download_tasks)} 张")
        return results


def main():
    """
    独立测试函数 - 便于测试图片下载功能

    使用方法:
        python -m src.core.card_generator.image_downloader
    """
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description='测试图片下载器')
    parser.add_argument('--url', type=str, help='图片URL')
    parser.add_argument('--douban-url', type=str, help='豆瓣图书页面URL（可选）')
    parser.add_argument('--output', type=str, help='输出路径（不含扩展名）')

    args = parser.parse_args()

    # 如果没有提供参数，使用默认测试数据
    if not args.url:
        # 默认测试：下载一本书的封面
        test_douban_url = "https://book.douban.com/subject/27071823/"
        test_output = f"test_output/test_cover_{int(time.time())}"
        print(f"使用测试参数:")
        print(f"  豆瓣URL: {test_douban_url}")
        print(f"  输出路径: {test_output}")
        douban_url = test_douban_url
        output = test_output
        url = None
    else:
        url = args.url
        douban_url = args.douban_url
        output = args.output or f"test_output/test_cover_{int(time.time())}"

    # 创建输出目录
    output_dir = Path(output).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # 配置
    config = {
        'image_download': {
            'timeout': 30,  # 秒
            'max_retries': 3,
            'retry_delay': 2,
            'headless': False,  # 非无头模式，便于调试
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'url_replacements': [
                {'old': '/s/', 'new': '/l/'},
                {'old': '/ssq/', 'new': '/ll/'}
            ],
            'supported_formats': ['jpg', 'png', 'jpeg']
        }
    }

    # 创建下载器
    downloader = ImageDownloader(config)

    try:
        # 下载图片
        print(f"\n开始下载封面图片...")
        success, actual_path = downloader.download_cover_image(url, output, douban_url)

        if success:
            print(f"\n✓ 下载成功!")
            print(f"  保存路径: {actual_path}")
            return 0
        else:
            print(f"\n✗ 下载失败!")
            return 1

    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # 清理资源
        downloader._close_browser()


if __name__ == '__main__':
    exit(main())
