"""
图片下载器模块
负责下载豆瓣封面图片
支持并发下载以提升性能
"""

import os
import time
from typing import Dict, Tuple, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
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
        self.timeout = self.config.get('timeout', 30)
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay = self.config.get('retry_delay', 2)
        self.user_agent = self.config.get(
            'user_agent',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        self.url_replacements = self.config.get('url_replacements', [])
        self.supported_formats = self.config.get('supported_formats', ['jpg', 'png', 'jpeg'])
        
        # 并发下载配置(性能优化)
        self.max_concurrent_downloads = self.config.get('max_concurrent_downloads', 2)
        self.download_delay = self.config.get('download_delay', 0.5)  # 下载间隔,避免反爬


    def download_cover_image(
        self, url: str, output_path: str
    ) -> Tuple[bool, str]:
        """
        下载封面图片

        Args:
            url: 图片URL
            output_path: 输出路径（不含扩展名）

        Returns:
            Tuple[bool, str]: (是否成功, 实际保存路径)
        """
        if not url or not url.strip():
            logger.error("图片URL为空")
            return False, ""

        # 处理豆瓣URL
        processed_url = self.process_douban_url(url)

        logger.debug(f"下载封面图片：{processed_url}")

        # 尝试下载
        for retry_count in range(self.max_retries):
            try:
                # 发送请求
                headers = {'User-Agent': self.user_agent}
                response = requests.get(
                    processed_url,
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=True
                )

                # 检查状态码
                if response.status_code != 200:
                    logger.warning(
                        f"下载失败，状态码：{response.status_code}，"
                        f"重试 {retry_count + 1}/{self.max_retries}"
                    )
                    time.sleep(self.retry_delay * (retry_count + 1))
                    continue

                # 检测图片格式
                image_format = self.detect_image_format(response.content)

                if not image_format:
                    logger.error("无法识别图片格式")
                    return False, ""

                # 构建完整路径
                full_path = f"{output_path}.{image_format}"

                # 保存图片
                with open(full_path, 'wb') as f:
                    f.write(response.content)

                logger.debug(f"封面图片下载成功：{full_path}")
                return True, full_path

            except requests.exceptions.Timeout:
                logger.warning(
                    f"网络请求超时，{self.retry_delay * (retry_count + 1)}秒后重试 "
                    f"({retry_count + 1}/{self.max_retries})"
                )
                time.sleep(self.retry_delay * (retry_count + 1))

            except requests.exceptions.RequestException as e:
                logger.warning(
                    f"网络请求失败：{e}，重试 {retry_count + 1}/{self.max_retries}"
                )
                time.sleep(self.retry_delay * (retry_count + 1))

            except Exception as e:
                logger.error(f"下载封面图片时发生错误：{e}")
                return False, ""

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
        self, download_tasks: List[Tuple[str, str]]
    ) -> List[Tuple[bool, str, str]]:
        """
        批量并发下载封面图片(性能优化)
        
        Args:
            download_tasks: 下载任务列表,每个任务为(url, output_path)元组
        
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
            for url, output_path in download_tasks:
                future = executor.submit(self._download_single_with_delay, url, output_path)
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
        
        success_count = sum(1 for success, _, _ in results if success)
        logger.info(f"批量下载完成: 成功 {success_count}/{len(download_tasks)} 张")
        
        return results
    
    def _download_single_with_delay(self, url: str, output_path: str) -> Tuple[bool, str]:
        """
        下载单张图片(带延迟,避免反爬)
        
        Args:
            url: 图片URL
            output_path: 输出路径
        
        Returns:
            Tuple[bool, str]: (是否成功, 实际保存路径)
        """
        # 添加随机延迟,避免触发反爬
        if self.download_delay > 0:
            import random
            delay = self.download_delay + random.uniform(0, 0.3)
            time.sleep(delay)
        
        return self.download_cover_image(url, output_path)
