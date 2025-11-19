"""
HTML转图片转换器模块
负责将HTML卡片转换为PNG图片
"""

import os
import time
from typing import Dict, Tuple, Optional
from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class HTMLToImageConverter:
    """HTML转图片转换器类"""

    def __init__(self, config: Dict):
        """
        初始化转换器

        Args:
            config: 配置字典
        """
        self.config = config.get('html_to_image', {})
        self.headless = self.config.get('headless', True)
        self.viewport_width = self.config.get('viewport_width', 1200)
        self.viewport_height = self.config.get('viewport_height', 800)
        self.device_scale_factor = self.config.get('device_scale_factor', 2)
        self.image_format = self.config.get('image_format', 'png')
        self.quality = self.config.get('quality', 90)
        self.full_page = self.config.get('full_page', False)
        self.clip_element = self.config.get('clip_element', True)
        self.border_radius = self.config.get('border_radius', 8)
        self.timeout = self.config.get('timeout', 60000)
        self.wait_time = self.config.get('wait_time', 2000)
        
        # 浏览器实例复用(性能优化)
        self.playwright = None
        self.browser = None

    def start_browser(self) -> bool:
        """
        启动浏览器实例(复用模式)
        
        Returns:
            bool: 启动成功返回True,否则返回False
        """
        if self.browser is not None:
            logger.debug("浏览器实例已存在,无需重复启动")
            return True
        
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=self.headless)
            logger.info("浏览器实例已启动(复用模式)")
            return True
        except Exception as e:
            logger.error(f"启动浏览器失败：{e}")
            return False
    
    def stop_browser(self) -> None:
        """
        关闭浏览器实例
        """
        if self.browser:
            try:
                self.browser.close()
                self.browser = None
                logger.info("浏览器实例已关闭")
            except Exception as e:
                logger.warning(f"关闭浏览器时发生错误：{e}")
        
        if self.playwright:
            try:
                self.playwright.stop()
                self.playwright = None
            except Exception as e:
                logger.warning(f"关闭Playwright时发生错误：{e}")
    
    def convert_html_to_image(
        self, html_path: str, output_path: str
    ) -> Tuple[bool, str]:
        """
        转换HTML为图片

        Args:
            html_path: HTML文件路径
            output_path: 输出图片路径

        Returns:
            Tuple[bool, str]: (是否成功, 输出路径)
        """
        if not os.path.exists(html_path):
            logger.error(f"HTML文件不存在：{html_path}")
            return False, ""

        page = None
        try:
            # 确保浏览器已启动
            if self.browser is None:
                if not self.start_browser():
                    return False, ""
            
            # 只创建新页面,不启动新浏览器
            page = self.browser.new_page(
                viewport={
                    'width': self.viewport_width,
                    'height': self.viewport_height
                },
                device_scale_factor=self.device_scale_factor
            )

            # 加载HTML页面
            if not self.load_html_page(page, html_path):
                return False, ""

            # 等待渲染完成
            self.wait_for_rendering(page)

            # 应用圆角效果（如果需要）
            if self.border_radius > 0:
                self.apply_border_radius(page)

            # 截图
            if self.take_screenshot(page, output_path):
                logger.debug(f"HTML转图片成功：{output_path}")
                return True, output_path
            else:
                return False, ""

        except Exception as e:
            logger.error(f"HTML转图片失败：{html_path}，错误：{e}")
            return False, ""

        finally:
            # 只关闭页面,不关闭浏览器
            if page:
                try:
                    page.close()
                except Exception as e:
                    logger.warning(f"关闭页面时发生错误：{e}")

    def load_html_page(self, page: Page, html_path: str) -> bool:
        """
        加载HTML页面

        Args:
            page: Playwright页面对象
            html_path: HTML文件路径

        Returns:
            bool: 加载成功返回True，否则返回False
        """
        try:
            # 转换为file://协议的URL
            if os.path.isabs(html_path):
                file_url = f"file:///{html_path.replace(os.sep, '/')}"
            else:
                abs_path = os.path.abspath(html_path)
                file_url = f"file:///{abs_path.replace(os.sep, '/')}"

            logger.debug(f"加载HTML页面：{file_url}")

            # 加载页面
            page.goto(file_url, timeout=self.timeout, wait_until='networkidle')

            return True

        except PlaywrightTimeoutError:
            logger.error(f"加载HTML页面超时：{html_path}")
            return False

        except Exception as e:
            logger.error(f"加载HTML页面失败：{html_path}，错误：{e}")
            return False

    def wait_for_rendering(self, page: Page) -> None:
        """
        等待页面渲染完成

        Args:
            page: Playwright页面对象
        """
        try:
            # 先等待网络空闲(本地HTML文件通常很快)
            page.wait_for_load_state('networkidle', timeout=self.timeout)
            
            # 只在配置了额外等待时间时才等待(性能优化)
            if self.wait_time > 0:
                time.sleep(self.wait_time / 1000.0)

        except Exception as e:
            logger.warning(f"等待页面渲染时发生警告:{e}")

    def take_screenshot(self, page: Page, output_path: str) -> bool:
        """
        截图并保存

        Args:
            page: Playwright页面对象
            output_path: 输出路径

        Returns:
            bool: 截图成功返回True，否则返回False
        """
        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            # 截图选项
            screenshot_options = {
                'path': output_path,
                'type': self.image_format,
                'full_page': self.full_page,
            }

            # 如果是jpg格式，添加质量参数
            if self.image_format == 'jpeg':
                screenshot_options['quality'] = self.quality

            # 如果需要裁剪元素
            if self.clip_element:
                # 按优先级尝试多个选择器
                selectors_to_try = [
                    '.library-card',      # 当前模板使用的类名
                    '.book-card',         # 备用类名
                    'body > div:first-child',  # 第一个div元素
                    '.card',              # 通用卡片类
                    '[class*="max-w"]',   # 包含max-w的元素
                    'main',               # main标签
                ]

                element_found = False
                for selector in selectors_to_try:
                    try:
                        element = page.query_selector(selector)
                        if element:
                            box = element.bounding_box()
                            if box:
                                screenshot_options['clip'] = box
                                screenshot_options['full_page'] = False
                                logger.debug(f"使用元素 {selector} 的边界进行截图")
                                element_found = True
                                break
                    except Exception as e:
                        logger.debug(f"尝试选择器 {selector} 失败: {e}")
                        continue

                if not element_found:
                    logger.warning("未找到任何可用的卡片元素，使用全页截图")

            # 执行截图
            page.screenshot(**screenshot_options)

            return True

        except Exception as e:
            logger.error(f"截图失败：{output_path}，错误：{e}")
            return False

    def apply_border_radius(self, page: Page) -> bool:
        """
        应用圆角效果

        Args:
            page: Playwright页面对象

        Returns:
            bool: 应用成功返回True，否则返回False
        """
        try:
            # 按优先级尝试多个选择器
            selectors_to_try = [
                '.library-card',      # 当前模板使用的类名
                '.book-card',         # 备用类名
                'body > div:first-child',  # 第一个div元素
                '.card',              # 通用卡片类
            ]

            for selector in selectors_to_try:
                try:
                    # 检查元素是否存在
                    element = page.query_selector(selector)
                    if element:
                        # 通过JavaScript添加圆角样式
                        page.evaluate(f"""
                            () => {{
                                const card = document.querySelector('{selector}');
                                if (card) {{
                                    card.style.borderRadius = '{self.border_radius}px';
                                    card.style.overflow = 'hidden';
                                }}
                            }}
                        """)
                        logger.debug(f"已为元素 {selector} 应用 {self.border_radius}px 圆角")
                        return True
                except Exception as e:
                    logger.debug(f"尝试为 {selector} 应用圆角失败: {e}")
                    continue

            logger.warning("未找到任何可用的卡片元素应用圆角")
            return False

        except Exception as e:
            logger.warning(f"应用圆角效果失败：{e}")
            return False
