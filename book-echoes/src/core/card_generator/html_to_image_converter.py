"""
HTML转图片转换器模块
负责将HTML卡片转换为PNG图片
"""

import os
import time
import threading
from typing import Dict, Tuple, Optional
from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class HTMLToImageConverter:
    """HTML转图片转换器类"""

    def __init__(self, config: Dict, thread_safe: bool = False):
        """
        初始化转换器

        Args:
            config: 配置字典
            thread_safe: 是否启用线程安全模式（为每个线程创建独立的浏览器实例）
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
        
        # 线程安全模式
        self.thread_safe = thread_safe
        
        if thread_safe:
            # 线程安全模式：使用线程本地存储，每个线程有独立的浏览器实例
            self._thread_local = threading.local()
        else:
            # 传统模式：共享浏览器实例
            self.playwright = None
            self.browser = None
            # 线程锁，用于同步多线程访问browser.new_page()
            self._page_creation_lock = threading.Lock()

    def start_browser(self) -> bool:
        """
        启动浏览器实例
        
        Returns:
            bool: 启动成功返回True,否则返回False
        """
        if self.thread_safe:
            # 线程安全模式：为当前线程创建独立的浏览器实例
            if hasattr(self._thread_local, 'browser') and self._thread_local.browser is not None:
                logger.debug(f"线程 {threading.current_thread().name} 的浏览器实例已存在")
                return True
            
            try:
                self._thread_local.playwright = sync_playwright().start()
                self._thread_local.browser = self._thread_local.playwright.chromium.launch(headless=self.headless)
                logger.info(f"线程 {threading.current_thread().name} 的浏览器实例已启动")
                return True
            except Exception as e:
                logger.error(f"线程 {threading.current_thread().name} 启动浏览器失败：{e}")
                return False
        else:
            # 传统模式：共享浏览器实例
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
        if self.thread_safe:
            # 线程安全模式：关闭当前线程的浏览器实例
            if hasattr(self._thread_local, 'browser') and self._thread_local.browser:
                try:
                    self._thread_local.browser.close()
                    self._thread_local.browser = None
                    logger.info(f"线程 {threading.current_thread().name} 的浏览器实例已关闭")
                except Exception as e:
                    logger.warning(f"关闭线程 {threading.current_thread().name} 的浏览器时发生错误：{e}")
            
            if hasattr(self._thread_local, 'playwright') and self._thread_local.playwright:
                try:
                    self._thread_local.playwright.stop()
                    self._thread_local.playwright = None
                except Exception as e:
                    logger.warning(f"关闭线程 {threading.current_thread().name} 的Playwright时发生错误：{e}")
        else:
            # 传统模式：关闭共享浏览器实例
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
            if self.thread_safe:
                # 线程安全模式：使用当前线程的浏览器实例
                if not hasattr(self._thread_local, 'browser') or self._thread_local.browser is None:
                    if not self.start_browser():
                        return False, ""
                
                page = self._thread_local.browser.new_page(
                    viewport={
                        'width': self.viewport_width,
                        'height': self.viewport_height
                    },
                    device_scale_factor=self.device_scale_factor
                )
            else:
                # 传统模式：使用共享浏览器实例
                if self.browser is None:
                    if not self.start_browser():
                        return False, ""
                
                # 使用线程锁保护页面创建，防止多线程并发调用导致协议错误
                with self._page_creation_lock:
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
        等待页面渲染完成，包括所有图片加载

        Args:
            page: Playwright页面对象
        """
        try:
            # 先等待网络空闲(本地HTML文件通常很快)
            page.wait_for_load_state('networkidle', timeout=self.timeout)

            # 等待所有图片加载完成（包括img标签和CSS背景图）
            try:
                result = page.evaluate("""
                    async () => {
                        console.log('开始图片加载检查...');

                        // 1. 等待所有 <img> 标签加载完成
                        const imgElements = Array.from(document.querySelectorAll('img'));
                        console.log(`找到 ${imgElements.length} 个img标签`);

                        const imgPromises = imgElements.map((img, index) => {
                            console.log(`图片 ${index + 1}: ${img.src}`);

                            if (img.complete) {
                                console.log(`图片 ${index + 1} 已加载完成`);
                                return Promise.resolve();
                            }

                            return new Promise((resolve) => {
                                const originalSrc = img.src;

                                img.onload = () => {
                                    console.log(`图片 ${index + 1} 加载成功: ${originalSrc}`);
                                    resolve();
                                };

                                img.onerror = (e) => {
                                    console.warn(`图片 ${index + 1} 加载失败: ${originalSrc}`, e);
                                    resolve();  // 即使加载失败也继续
                                };

                                // 设置更长的超时时间，特别是针对本地图片
                                setTimeout(() => {
                                    console.log(`图片 ${index + 1} 加载超时: ${originalSrc}`);
                                    resolve();
                                }, 10000);
                            });
                        });

                        // 2. 等待所有CSS背景图加载完成
                        const allElements = Array.from(document.querySelectorAll('*'));
                        console.log(`检查 ${allElements.length} 个元素的背景图...`);

                        const bgPromises = allElements.map((el, index) => {
                            const style = window.getComputedStyle(el);
                            const bgImage = style.backgroundImage;

                            if (bgImage && bgImage !== 'none' && bgImage.startsWith('url(')) {
                                // 提取URL
                                const urlMatch = bgImage.match(/url\\(['"]?([^'"\\)]+)['"]?\\)/);
                                if (urlMatch && urlMatch[1]) {
                                    const url = urlMatch[1];
                                    // 跳过data: URL
                                    if (!url.startsWith('data:')) {
                                        console.log(`背景图 ${index + 1}: ${url}`);

                                        return new Promise((resolve) => {
                                            const img = new Image();
                                            img.onload = () => {
                                                console.log(`背景图 ${index + 1} 加载成功: ${url}`);
                                                resolve();
                                            };
                                            img.onerror = (e) => {
                                                console.warn(`背景图 ${index + 1} 加载失败: ${url}`, e);
                                                resolve();
                                            };
                                            img.src = url;
                                            setTimeout(() => {
                                                console.log(`背景图 ${index + 1} 加载超时: ${url}`);
                                                resolve();
                                            }, 10000);
                                        });
                                    }
                                }
                            }
                            return Promise.resolve();
                        });

                        await Promise.all([...imgPromises, ...bgPromises]);
                        console.log('所有图片和背景图加载检查完成');

                        // 3. 额外等待几帧，确保渲染完成
                        await new Promise(resolve => requestAnimationFrame(resolve));
                        await new Promise(resolve => requestAnimationFrame(resolve));
                        await new Promise(resolve => setTimeout(resolve, 500));

                        return {
                            imgCount: imgElements.length,
                            bgCount: bgPromises.length,
                            allLoaded: true
                        };
                    }
                """)

                if result:
                    logger.info(f"图片加载检查完成: {result.get('imgCount', 0)}个img标签, {result.get('bgCount', 0)}个背景图")

            except Exception as e:
                logger.warning(f"等待图片加载时发生警告: {e}")

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
                    '.poster',            # 点阵模板使用的类名
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
                                # 根据不同模板调整截图边界
                                if selector == '.poster':
                                    # poster模板：需要增加底部padding防止截断
                                    adjusted_box = {
                                        'x': box['x'],
                                        'y': box['y'],
                                        'width': box['width'],
                                        'height': box['height'] + 50
                                    }
                                    logger.debug(f"poster模板：原始高度: {box['height']}, 调整后: {adjusted_box['height']}")
                                else:
                                    # 其他模板（library-card等）：使用原始边界
                                    adjusted_box = box
                                    logger.debug(f"{selector}模板：使用原始边界，高度: {box['height']}")

                                screenshot_options['clip'] = adjusted_box
                                screenshot_options['full_page'] = False
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
                '.poster',            # 点阵模板使用的类名
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

    def get_content_bounds(self, page: Page) -> Optional[Dict]:
        """
        智能检测页面实际内容边界，不依赖特定CSS类名

        Args:
            page: Playwright页面对象

        Returns:
            Dict: 边界信息 {x, y, width, height}，如果检测失败返回None
        """
        try:
            return page.evaluate("""
                () => {
                    console.log('开始智能内容边界检测...');

                    // 1. 优先查找主要的卡片/海报容器
                    const mainSelectors = [
                        '.poster',
                        '.library-card',
                        '.card',
                        '[class*="card"]',
                        '[class*="poster"]',
                        'body > div:first-child',
                        'main'
                    ];

                    let mainElement = null;

                    for (const selector of mainSelectors) {
                        const elements = document.querySelectorAll(selector);
                        for (const el of elements) {
                            const rect = el.getBoundingClientRect();
                            // 寻找合适的尺寸：宽度在300-1000px之间，高度在200-2000px之间
                            if (rect.width >= 300 && rect.width <= 1000 &&
                                rect.height >= 200 && rect.height <= 2000) {
                                // 排除太小的元素
                                if (rect.width > 100 && rect.height > 100) {
                                    mainElement = el;
                                    console.log(`找到主要元素: ${selector}, 尺寸: ${rect.width}x${rect.height}`);
                                    break;
                                }
                            }
                        }
                        if (mainElement) break;
                    }

                    if (mainElement) {
                        // 如果找到了主要元素，使用它的边界
                        const rect = mainElement.getBoundingClientRect();
                        const style = window.getComputedStyle(mainElement);

                        // 考虑元素的margin、border和box-shadow
                        const marginTop = parseFloat(style.marginTop) || 0;
                        const marginBottom = parseFloat(style.marginBottom) || 0;
                        const marginLeft = parseFloat(style.marginLeft) || 0;
                        const marginRight = parseFloat(style.marginRight) || 0;
                        const boxShadow = style.boxShadow;

                        // 如果有box-shadow，添加额外空间
                        let shadowAdjustment = 0;
                        if (boxShadow && boxShadow !== 'none') {
                            shadowAdjustment = 20; // 给shadow足够的空间
                        }

                        const bounds = {
                            x: Math.max(0, Math.round(rect.left - marginLeft - shadowAdjustment)),
                            y: Math.max(0, Math.round(rect.top - marginTop - shadowAdjustment)),
                            width: Math.round(rect.width + marginLeft + marginRight + shadowAdjustment * 2),
                            height: Math.round(rect.height + marginTop + marginBottom + shadowAdjustment * 2)
                        };

                        console.log('主要元素边界检测结果:', bounds);
                        return bounds;
                    }

                    // 2. 回退方案：如果没有找到明确的主体元素，使用更智能的内容检测
                    console.log('未找到明确的主体元素，使用内容检测算法...');

                    const allElements = Array.from(document.querySelectorAll('*'));

                    // 筛选出有实际内容的元素（改进的筛选逻辑）
                    const contentElements = allElements.filter(el => {
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);

                        // 排除不可见元素
                        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
                            return false;
                        }

                        // 排除body和html
                        if (el.tagName === 'BODY' || el.tagName === 'HTML') {
                            return false;
                        }

                        // 排除太小的装饰性元素
                        if (rect.width < 20 || rect.height < 10) {
                            return false;
                        }

                        // 检查是否包含实际内容（文本、图片、或明显的背景）
                        const text = el.textContent && el.textContent.trim();
                        const hasImages = el.querySelectorAll('img').length > 0;
                        const hasBg = style.backgroundImage && style.backgroundImage !== 'none';

                        // 如果有文本内容、图片或背景图，且尺寸合理
                        if ((text && text.length > 5) || hasImages || hasBg) {
                            // 排除纯装饰性的小元素
                            if (rect.width < 100 && rect.height < 100 && !text) {
                                return false;
                            }
                            return true;
                        }

                        return false;
                    });

                    if (contentElements.length === 0) {
                        console.log('未找到任何内容元素');
                        return null;
                    }

                    // 计算包含所有内容元素的最小边界
                    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;

                    contentElements.forEach(el => {
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);

                        // 考虑元素的完整视觉效果
                        const marginTop = parseFloat(style.marginTop) || 0;
                        const marginBottom = parseFloat(style.marginBottom) || 0;
                        const marginLeft = parseFloat(style.marginLeft) || 0;
                        const marginRight = parseFloat(style.marginRight) || 0;

                        minX = Math.min(minX, rect.left - marginLeft);
                        minY = Math.min(minY, rect.top - marginTop);
                        maxX = Math.max(maxX, rect.right + marginRight);
                        maxY = Math.max(maxY, rect.bottom + marginBottom);
                    });

                    // 添加适度的边距
                    const margin = 20;
                    minX = Math.max(0, minX - margin);
                    minY = Math.max(0, minY - margin);
                    maxX = Math.min(window.innerWidth, maxX + margin);
                    maxY = Math.min(window.innerHeight, maxY + margin);

                    // 限制最大尺寸，避免异常情况
                    const maxWidth = Math.min(1200, maxX - minX);
                    const maxHeight = Math.min(3000, maxY - minY);

                    const bounds = {
                        x: Math.round(minX),
                        y: Math.round(minY),
                        width: Math.round(maxWidth),
                        height: Math.round(maxHeight)
                    };

                    console.log('回退内容检测结果:', bounds);
                    return bounds;
                }
            """)
        except Exception as e:
            logger.debug(f"智能内容边界检测失败: {e}")
            return None

    def find_main_element(self, page: Page) -> Optional:
        """
        回退方案：查找页面主要元素

        Args:
            page: Playwright页面对象

        Returns:
            主要元素对象，如果找不到返回None
        """
        try:
            # 按优先级尝试多个选择器
            selectors_to_try = [
                'body > div:first-child',        # 第一个div
                '[class*="card"]',              # 包含card的类
                '[class*="library"]',           # 包含library的类
                'main',                         # main标签
                '[role="main"]',                # main角色
                '.container',                   # container类
                '[class*="wrapper"]',           # wrapper类
                'div[style*="background"]',     # 有背景样式的div
            ]

            for selector in selectors_to_try:
                try:
                    element = page.query_selector(selector)
                    if element:
                        # 检查元素是否足够大
                        box = element.bounding_box()
                        if box and box.width > 100 and box.height > 100:
                            logger.debug(f"找到主要元素: {selector}, 大小: {box.width}x{box.height}")
                            return element
                except Exception as e:
                    logger.debug(f"尝试选择器 {selector} 失败: {e}")
                    continue

            return None
        except Exception as e:
            logger.debug(f"查找主要元素失败: {e}")
            return None
