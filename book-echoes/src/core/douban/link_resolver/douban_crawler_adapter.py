#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
豆瓣爬虫适配器 - 适配现有项目架构

核心要求：保持 docs/refs/douban-spider/src/ 中的核心逻辑完全不变
仅进行异步化改造和配置适配

作者: 图书馆系统开发团队
版本: 1.0.0
"""

import asyncio
import logging
import re
import time
from typing import Optional, Dict, Any
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

# 添加项目路径
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from src.utils.logger import get_logger

logger = get_logger(__name__)


class DoubanCrawlerAdapter:
    """豆瓣爬虫适配器 - 适配现有项目架构

    核心要求：保持 docs/refs/douban-spider/src/ 中的核心逻辑完全不变
    仅进行异步化改造和配置适配
    """

    def __init__(self, config: Dict[str, Any]):
        """初始化豆瓣爬虫适配器

        Args:
            config: 配置字典
        """
        self.config = config
        self.page: Optional[Page] = None
        self.browser = None
        self.context = None
        self.playwright = None
        self.base_url = config.get('base_url', 'https://book.douban.com')
        self.delay = config.get('delay', 1.0)

        # 登录状态管理（参考 search_handler.py:33-36）
        self.login_completed = False
        self.login_attempted = False

        # 豆瓣账号配置从环境变量读取
        self.douban_username = self._get_douban_credentials()[0]
        self.douban_password = self._get_douban_credentials()[1]

    def _get_douban_credentials(self) -> tuple:
        """获取豆瓣账号密码从环境变量

        Returns:
            (username, password) 或 (None, None)
        """
        import os
        username = os.getenv('DOUBAN_USERNAME')
        password = os.getenv('DOUBAN_PASSWORD')
        return username or '', password or ''

    async def init_browser(self, page: Page):
        """初始化浏览器 - 对应 base_spider 的功能

        Args:
            page: Playwright页面对象
        """
        self.page = page
        logger.info("豆瓣爬虫浏览器已初始化")

    async def init_browser_with_config(self, headless: bool = False):
        """创建独立的浏览器实例，支持配置headless模式

        Args:
            headless: 是否使用无头模式（默认False，显示浏览器窗口用于验证码）
        """
        from playwright.async_api import async_playwright

        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=headless,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()

            logger.info(f"豆瓣爬虫独立浏览器已初始化 - headless={headless}")

            # 新增：初始化后立即打开豆瓣图书首页，便于可视化模式下人工验证码/登录
            try:
                await self.page.goto(
                    self.base_url,
                    wait_until="networkidle",
                    timeout=30000
                )
                logger.info(f"已打开豆瓣图书首页: {self.base_url}")
            except Exception as nav_err:
                logger.warning(f"初始化后打开豆瓣首页失败，将在检索时重试: {nav_err}")

        except Exception as e:
            logger.error(f"创建豆瓣爬虫浏览器失败: {e}")
            await self.close_browser()
            raise

    async def close_browser(self):
        """关闭豆瓣爬虫浏览器"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("豆瓣爬虫浏览器已关闭")
        except Exception as e:
            logger.error(f"关闭豆瓣爬虫浏览器失败: {e}")

    async def resolve_book_url(self, isbn: str) -> Optional[str]:
        """
        仅解析ISBN对应的豆瓣图书链接，用于阶段化流程的链接补录。

        Args:
            isbn: 原始ISBN

        Returns:
            图书详情页链接/“NO_DATA”/None
        """
        formatted = self._format_isbn_for_search(isbn)
        return await self._search_by_isbn(formatted)

    def _format_isbn_for_search(self, isbn: str) -> str:
        """
        格式化ISBN用于豆瓣检索（去掉连字符）

        Args:
            isbn: 原始ISBN字符串

        Returns:
            格式化后的ISBN（仅包含数字和字母）
        """
        if not isbn:
            return ""
        # 移除所有连字符和空格
        formatted = str(isbn).replace('-', '').replace(' ', '').strip()
        logger.debug(f"格式化ISBN: {isbn} -> {formatted}")
        return formatted

    async def _search_by_isbn(self, isbn: str) -> Optional[str]:
        """异步搜索ISBN（参考 search_handler.py 同步实现）

        Args:
            isbn: ISBN号码

        Returns:
            图书详情页链接，特殊值"NO_DATA"表示豆瓣无数据
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.debug(f"搜索ISBN {isbn} - 第 {attempt + 1} 次尝试")

                # 1. 检查当前页面状态 - 优化：只在真正需要时才跳转
                current_url = self.page.url if self.page else ""
                is_search_page = 'search.douban.com/book/subject_search' in current_url
                is_douban_book_page = 'book.douban.com' in current_url

                if is_search_page:
                    logger.info("当前已在搜索页面，直接执行搜索")
                    # 直接在当前页面执行搜索
                    await self._random_delay()
                elif is_douban_book_page:
                    logger.info("当前在豆瓣图书域下，尝试在当前页面搜索")
                    # 在当前页面执行搜索（可以是详情页、首页等）
                    await self._random_delay()
                else:
                    logger.info("访问豆瓣图书首页...")
                    # 访问豆瓣图书首页
                    await self.page.goto(
                        "https://book.douban.com",
                        wait_until="networkidle",
                        timeout=30000
                    )
                    await self._random_delay()

                # 2. 检查登录状态（参考 search_handler.py:69-83）
                if not self.login_attempted:
                    if await self._check_login_page():
                        logger.warning("检测到需要登录")
                        self.login_attempted = True
                        # 处理登录情况
                        result = await self._handle_login_situation(isbn)
                        if result is not None:
                            return result

                # 3. 执行搜索（参考 search_handler.py:_perform_search）
                result = await self._perform_search(isbn)
                if result == "NO_DATA":
                    logger.info(f"豆瓣确认无此ISBN数据: {isbn}")
                    return "NO_DATA"
                return result

            except PlaywrightTimeoutError:
                logger.warning(f"搜索超时 - 第 {attempt + 1} 次尝试")
                relogin_result = await self._relogin_after_anti_bot(isbn)
                if relogin_result:
                    return relogin_result
                if attempt == max_retries - 1:
                    return None
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"搜索出错 - 第 {attempt + 1} 次尝试: {e}")
                recovered = await self._relogin_after_anti_bot(isbn)
                if recovered:
                    return recovered
                if attempt == max_retries - 1:
                    return None
                await asyncio.sleep(2)

        return None

    async def _perform_search(self, isbn: str) -> Optional[str]:
        """执行搜索操作（参考 search_handler.py 内部方法）

        Args:
            isbn: ISBN号码

        Returns:
            图书详情页链接，未找到则返回None
        """
        try:
            # 检查当前是否在搜索结果页面
            current_url = self.page.url
            is_search_page = 'search.douban.com/book/subject_search' in current_url

            if is_search_page:
                logger.info(f"在当前搜索结果页面执行新搜索: {isbn}")
                # 检查页面是否有搜索框（用于执行新搜索）
                has_search_input = await self._check_page_has_search_box()

                if has_search_input:
                    try:
                        search_input = self.page.locator('#inp-query').first
                        if await search_input.is_visible(timeout=3000):
                            await search_input.clear()
                            await search_input.fill(isbn)
                            logger.debug(f"在搜索框输入: {isbn}")
                            search_button = self.page.locator('input[type="submit"][value="搜索"]').first
                            if await search_button.is_visible(timeout=3000):
                                await search_button.click()
                                logger.debug("点击搜索按钮")
                                result_inline = await self._wait_for_search_outcome(timeout_ms=20000)
                                if result_inline == "__ANTI_BOT__":
                                    return await self._relogin_after_anti_bot(isbn)
                                if result_inline == "NO_DATA" or result_inline:
                                    if result_inline == "NO_DATA":
                                        logger.info(f"豆瓣无数据: {isbn}")
                                        return "NO_DATA"
                                    logger.info(f"搜索成功，找到结果: {result_inline}")
                                    return result_inline
                                raise Exception("页内搜索未稳定产生结果")
                            else:
                                raise Exception("搜索按钮不可见")
                        else:
                            raise Exception("搜索框不可见")

                    except Exception as e:
                        logger.warning(f"当前页面搜索失败，回退到URL跳转: {e}")
                        search_url = f"https://search.douban.com/book/subject_search?search_text={isbn}&cat=1001"
                        await self.page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                        await self._random_delay()
                        direct_result = await self._wait_for_search_outcome(timeout_ms=22000)
                        if direct_result == "__ANTI_BOT__":
                            return await self._relogin_after_anti_bot(isbn)
                        if direct_result == "NO_DATA" or direct_result:
                            if direct_result == "NO_DATA":
                                logger.info(f"豆瓣无数据: {isbn}")
                                return "NO_DATA"
                            logger.info(f"搜索成功，找到结果: {direct_result}")
                            return direct_result
                else:
                    search_url = f"https://search.douban.com/book/subject_search?search_text={isbn}&cat=1001"
                    await self.page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                    await self._random_delay()
                    direct_result = await self._wait_for_search_outcome(timeout_ms=22000)
                    if direct_result == "__ANTI_BOT__":
                        return await self._relogin_after_anti_bot(isbn)
                    if direct_result == "NO_DATA" or direct_result:
                        if direct_result == "NO_DATA":
                            logger.info(f"豆瓣无数据: {isbn}")
                            return "NO_DATA"
                        logger.info(f"搜索成功，找到结果: {direct_result}")
                        return direct_result
            else:
                logger.info(f"直接访问搜索页面: {isbn}")
                # 参考 search_handler.py:132，直接使用搜索URL
                # 避免在当前页面操作搜索框，直接跳转搜索页面
                search_url = f"https://search.douban.com/book/subject_search?search_text={isbn}&cat=1001"
                await self.page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                await self._random_delay()
                direct_result = await self._wait_for_search_outcome(timeout_ms=22000)
                if direct_result == "__ANTI_BOT__":
                    return await self._relogin_after_anti_bot(isbn)
                if direct_result == "NO_DATA" or direct_result:
                    if direct_result == "NO_DATA":
                        logger.info(f"豆瓣无数据: {isbn}")
                        return "NO_DATA"
                    logger.info(f"搜索成功，找到结果: {direct_result}")
                    return direct_result

            # 解析搜索结果页面
            html = await self.page.content()
            if self._is_anti_bot_page(html):
                return await self._relogin_after_anti_bot(isbn)
            soup = BeautifulSoup(html, 'html.parser')

            # 提取第一个搜索结果链接（参考搜索结果解析逻辑）
            result = self._parse_search_results(soup)
            if result == "NO_DATA":
                logger.info(f"豆瓣无数据: {isbn}")
                return "NO_DATA"
            elif result:
                logger.info(f"搜索成功，找到结果: {result}")
            else:
                logger.warning(f"搜索未找到结果: {isbn}")
            return result

        except Exception as e:
            logger.error(f"执行搜索失败: {e}")
            return None

    async def _check_page_has_search_box(self) -> bool:
        """检查当前页面是否包含搜索框

        Returns:
            是否包含搜索框
        """
        try:
            # 优先检查豆瓣标准的搜索框选择器
            search_selectors = [
                '#inp-query',
                'input[name="search_text"]',
                'input[placeholder*="书名、作者、ISBN"]',
                '.inp input'
            ]

            for selector in search_selectors:
                try:
                    element = self.page.locator(selector).first
                    if await element.is_visible(timeout=2000):
                        logger.debug(f"页面包含搜索框，选择器: {selector}")
                        return True
                except:
                    continue

            # 备选方案：检查页面HTML内容
            html = await self.page.content()
            if 'name="search_text"' in html and '<form' in html:
                logger.debug("页面HTML包含搜索表单")
                return True

            logger.debug("页面不包含搜索框")
            return False

        except Exception as e:
            logger.error(f"检查页面搜索框时发生错误: {e}")
            return False

    def _parse_search_results(self, soup: BeautifulSoup) -> Optional[str]:
        """解析搜索结果（保持原有逻辑不变）

        Args:
            soup: BeautifulSoup对象

        Returns:
            图书详情页链接，None表示未找到，特殊标识表示豆瓣无数据
        """
        try:
            # 首先检查是否包含"没有找到关于"的文本（豆瓣无数据的情况）
            page_text = soup.get_text()
            if '没有找到关于' in page_text and '的书' in page_text:
                logger.info("检测到豆瓣无数据：搜索结果为空")
                return "NO_DATA"  # 使用特殊标识表示豆瓣无数据

            # 参考 search_handler.py 中的解析逻辑
            # 查找第一个图书详情页链接
            items = soup.select('.subject-item .pic a')
            if items:
                href = items[0].get('href')
                if href:
                    return href

            # 备用解析方法
            items = soup.select('a[href*="/subject/"]')
            for item in items:
                href = item.get('href')
                if href and '/subject/' in href:
                    return href

            return None
        except Exception as e:
            logger.error(f"解析搜索结果失败: {e}")
            return None


    # ========== 以下是保持原有逻辑的辅助方法 ==========
    # 这些方法从参考代码中复制，保持完全不变

    async def _random_delay(self, page_type: str = "search"):
        """随机延迟（参考 base_spider.py 的随机延迟机制）

        Args:
            page_type: 页面类型，影响延迟时间
        """
        import random
        if page_type == "detail":
            # 详情页延迟时间更长
            delay = self.delay + random.uniform(2.0, 4.0)
        else:
            # 搜索页延迟时间较短
            delay = self.delay + random.uniform(2.0, 4.5)
        await asyncio.sleep(delay)

    async def _check_login_page(self) -> bool:
        """检查是否需要登录（参考 login_handler.py）

        Returns:
            是否需要登录
        """
        try:
            content = await self.page.content()
            content_lower = content.lower()

            # 1. 检查是否包含"登录跳转"页面（参考 login_handler.py:73）
            if '<h1>登录跳转</h1>' in content or ('登录跳转' in content and ('有异常请求' in content or '异常请求' in content)):
                logger.info("检测到登录跳转页面，尝试自动点击登录链接")
                # 尝试自动点击登录链接
                if await self._auto_click_login_link():
                    logger.info("成功点击登录链接，等待跳转...")
                    # 等待页面跳转
                    await asyncio.sleep(3)

                    # 检查跳转结果
                    new_url = self.page.url
                    new_content = (await self.page.content()).lower()

                    # 如果跳转到了真正的登录页面
                    if 'accounts.douban.com/passport/login' in new_url:
                        logger.info("成功跳转到登录页面，需要登录")
                        return True
                    elif 'book.douban.com' in new_url and '登录' not in new_content:
                        logger.info("成功跳转回正常页面，无需登录")
                        return False
                    else:
                        logger.info("点击链接后等待跳转...")
                        return False
                else:
                    logger.warning("无法自动点击登录链接，跳过处理")
                    return False

            # 2. 检查URL是否跳转到明确的登录/验证页面
            login_url_patterns = [
                'login', 'captcha', 'unusual', 'sec.douban.com',
                'accounts.google.com', 'verification'
            ]
            current_url = self.page.url.lower()
            if any(pattern in current_url for pattern in login_url_patterns):
                logger.warning("检测到明确的登录/验证页面跳转")
                return True

            # 3. 检查是否在真正的登录页面（而非仅包含登录提示的页面）
            # 豆瓣详情页经常包含"登录后在评价"等提示，但这是正常页面
            # 需要更精确的判断逻辑

            # 3.1 检查URL - 如果是accounts.douban.com的登录页面，直接返回True
            if 'accounts.douban.com' in current_url and 'login' in current_url:
                logger.info("检测到豆瓣登录URL，确认需要登录")
                return True

            # 3.2 检查页面主体内容 - 查找真正的登录表单
            # 登录表单的关键特征：form标签 + 用户名密码输入框
            form_tags = content.lower().count('<form')
            password_inputs = content_lower.count('type="password"')
            username_inputs = content_lower.count('name="username"') + content_lower.count('name="form_email"')

            # 如果页面包含form标签，且同时包含密码和用户名输入框，才是真正的登录页
            if form_tags > 0 and password_inputs > 0 and username_inputs > 0:
                logger.info("检测到登录表单，确认需要登录")
                return True

            # 3.3 特殊页面模式检查 - 登录跳转页面
            if '<h1>登录跳转</h1>' in content or '登录豆瓣' in content_lower:
                # 检查是否是独立的登录页面（包含表单结构）
                if password_inputs > 0 and username_inputs > 0:
                    logger.info("检测到登录跳转页面包含表单，需要登录")
                    return True
                else:
                    logger.info("登录跳转页面不包含表单，可能只是提示信息")
                    return False

            # 3.4 排除常见误判情况 - 详情页的登录提示不是登录页
            # 如果页面包含书籍详情页的特征元素，说明这不是登录页
            book_page_indicators = [
                'property="v:itemreviewed"',  # 书名标题
                '<div id="info"',              # 书籍信息
                'rating_num',                  # 评分
                'subject-item',                # 搜索结果
                '页数', 'ISBN', '作者', '出版社'  # 书籍信息字段
            ]

            if any(indicator in content_lower for indicator in book_page_indicators):
                logger.info("检测到书籍详情页特征，确认无需登录")
                return False

            return False
        except Exception as e:
            logger.error(f"检查登录页面时发生错误: {e}")
            return False

    async def _wait_for_search_outcome(self, timeout_ms: int = 20000) -> Optional[str]:
        try:
            deadline = time.time() + timeout_ms / 1000.0
            while time.time() < deadline:
                html = await self.page.content()
                if self._is_anti_bot_page(html):
                    return "__ANTI_BOT__"
                soup = BeautifulSoup(html, 'html.parser')
                result = self._parse_search_results(soup)
                if result == "NO_DATA" or result:
                    return result
                await asyncio.sleep(0.6)
            return None
        except Exception:
            return None

    async def _auto_click_login_link(self) -> bool:
        """自动点击登录链接跳转到登录页面（参考 login_handler.py:_auto_click_login_link）

        Returns:
            是否成功点击并跳转
        """
        try:
            # 等待页面完全加载
            await asyncio.sleep(1)

            # 定义可能的登录链接选择器
            login_link_selectors = [
                'a.nav-login',
                'a[href*="passport/login?source=book"]',
                'a[href*="accounts.douban.com/passport/login"]',
                'a[href*="login"]',
                'text=登录',
                'a:has-text("登录")'
            ]

            # 尝试不同的选择器来点击登录链接
            for selector in login_link_selectors:
                try:
                    link = self.page.locator(selector).first
                    if await link.is_visible(timeout=3000):
                        logger.info(f"找到登录链接，选择器: {selector}")
                        await link.click()
                        logger.info("成功点击登录链接")

                        # 等待页面跳转到登录页面
                        await asyncio.sleep(3)

                        # 检查是否成功跳转到登录页面
                        current_url = self.page.url
                        if 'accounts.douban.com/passport/login' in current_url:
                            logger.info(f"成功跳转到登录页面: {current_url}")
                            return True
                        else:
                            logger.warning(f"点击链接后未跳转到预期页面: {current_url}")

                except PlaywrightTimeoutError:
                    logger.debug(f"选择器 {selector} 失败: 元素不可见或超时")
                    continue
                except Exception as e:
                    logger.debug(f"选择器 {selector} 失败: {e}")
                    continue

            logger.warning("无法找到或点击登录链接")
            return False

        except Exception as e:
            logger.error(f"自动点击登录链接时发生错误: {e}")
            return False


    async def _relogin_after_anti_bot(self, isbn: str) -> Optional[str]:
        """触发反爬后的重新登录流程。"""
        logger.warning('检测到豆瓣反爬，需要重新登录后再检索')
        crawler_config = self.config if hasattr(self, 'config') else {}
        headless_mode = crawler_config.get('headless', False)

        import random
        wait_seconds_before_close = random.uniform(9 * 60, 14 * 60)
        logger.info(f'等待约 {wait_seconds_before_close / 60:.2f} 分钟后再关闭浏览器以降低访问频率')
        await asyncio.sleep(wait_seconds_before_close)

        try:
            await self.close_browser()
        except Exception as exc:
            logger.debug(f'关闭浏览器时捕获异常: {exc}')

        await asyncio.sleep(random.uniform(3.0, 4.0))
        await self.init_browser_with_config(headless=headless_mode)

        try:
            await self.page.goto(self.base_url, wait_until='networkidle', timeout=30000)
        except Exception as exc:
            logger.warning(f'重新打开豆瓣首页失败: {exc}')

        await self._auto_click_login_link()
        self.login_attempted = False
        self.login_completed = False

        relogin_result = await self._handle_login_situation(isbn)
        if relogin_result:
            return relogin_result
        logger.warning('重新登录后未立即获取到结果，尝试直接搜索')
        return await self._perform_search(isbn)

    @staticmethod
    def _is_anti_bot_page(page_content: Optional[str]) -> bool:
        """根据页面内容判断是否命中反爬提示。"""
        if not page_content:
            return False
        markers = ['搜索访问太频繁', '访问太频繁', '行为存在异常', '请稍候再试']
        lowered = page_content.lower() if isinstance(page_content, str) else ''
        return any(marker in page_content or marker in lowered for marker in markers)

    async def _handle_login_situation(self, isbn: str) -> Optional[str]:
        """处理登录情况（参考 search_handler.py:_handle_login_situation_optimized）

        Args:
            isbn: ISBN号码

        Returns:
            搜索结果链接，失败则返回None
        """
        logger.info("开始处理登录情况...")

        # 获取浏览器配置判断是否为无头模式
        crawler_config = self.config if hasattr(self, 'config') else {}
        is_headless = crawler_config.get('headless', False)

        # 方案1: 尝试自动登录（非无头模式）
        if not is_headless:
            logger.info("尝试自动登录...")
            if await self._auto_login():
                logger.info("自动登录成功，尝试重新搜索")
                self.login_completed = True
                return await self._search_after_login(isbn)
            else:
                logger.warning("自动登录失败，尝试手动登录...")
        else:
            logger.info("当前为无头模式，跳过自动登录，直接手动登录...")

        # 方案2: 等待用户手动登录
        if await self._wait_for_manual_login():
            logger.info("用户完成手动登录，尝试重新搜索")
            self.login_completed = True
            return await self._search_after_login(isbn)

        # 方案3: 尝试直接通过URL搜索，并标记已尝试登录
        logger.info("登录失败或跳过，尝试通过直接URL搜索")
        return await self._search_by_direct_url(isbn)

    async def _search_after_login(self, isbn: str) -> Optional[str]:
        """登录后重新搜索（参考 search_handler.py:_search_after_login）

        Args:
            isbn: ISBN号码

        Returns:
            搜索结果链接，失败则返回None
        """
        try:
            logger.info("重新开始搜索...")
            return await self._perform_search(isbn)
        except Exception as e:
            logger.error(f"登录后搜索失败: {e}")
            return None

    async def _search_by_direct_url(self, isbn: str) -> Optional[str]:
        """直接通过URL搜索（备用方案）

        Args:
            isbn: ISBN号码

        Returns:
            搜索结果链接，失败则返回None
        """
        try:
            logger.info(f"直接URL搜索ISBN: {isbn}")
            # 直接构建搜索URL并跳转
            search_url = f"https://search.douban.com/book/subject_search?search_text={isbn}&cat=1001"
            await self.page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
            await self._random_delay()

            # 解析搜索结果
            html = await self.page.content()
            soup = BeautifulSoup(html, 'html.parser')
            return self._parse_search_results(soup)
        except Exception as e:
            logger.error(f"直接URL搜索失败: {e}")
            return None

    async def _auto_login(self) -> bool:
        """自动登录（简化版，参考 login_handler.py:auto_login）

        Returns:
            是否登录成功
        """
        logger.info("开始自动登录流程...")

        # 检查是否在登录页面
        if 'accounts.douban.com/passport/login' not in self.page.url:
            logger.warning("当前不在登录页面，无法执行自动登录")
            return False

        try:
            # 从配置文件或环境变量获取凭据
            if not self.douban_username or not self.douban_password:
                logger.warning("未配置豆瓣账号密码，无法自动登录")
                return False

            # 1. 点击"密码登录"标签
            if not await self._click_password_login_tab():
                logger.error("无法点击密码登录标签")
                return False

            # 2. 等待密码登录表单加载
            await asyncio.sleep(2)

            # 3. 输入用户名和密码
            if not await self._fill_login_form(self.douban_username, self.douban_password):
                logger.error("无法填写登录表单")
                return False

            # 4. 点击登录按钮
            if not await self._click_login_button():
                logger.error("无法点击登录按钮")
                return False

            # 5. 等待登录结果
            await asyncio.sleep(3)

            # 6. 检查登录是否成功
            return await self._check_login_success()

        except Exception as e:
            logger.error(f"自动登录过程中发生错误: {e}")
            return False

    async def _wait_for_manual_login(self) -> bool:
        """等待用户手动登录

        Returns:
            是否完成登录
        """
        logger.info("=" * 50)
        logger.info("检测到豆瓣要求登录！")
        logger.info("解决方案:")
        logger.info("1. 浏览器窗口已打开")
        logger.info("2. 请手动登录豆瓣账号")
        logger.info("3. 登录完成后在终端输入 'y' 继续")
        logger.info("=" * 50)

        # 检查是否为无头模式
        crawler_config = self.config if hasattr(self, 'config') else {}
        if crawler_config.get('headless', False):
            logger.error("当前为无头模式，无法进行手动登录。请设置为headless=False")
            return False

        try:
            # 保持浏览器窗口打开
            while True:
                try:
                    user_input = input("请确认登录完成后输入 'y' 继续 (或输入 'n' 跳过): ").strip().lower()
                    if user_input == 'y':
                        logger.info("用户确认已完成登录")
                        # 验证是否真的登录成功
                        if await self._check_login_success():
                            return True
                        else:
                            logger.warning("验证登录状态失败，请重试")
                    elif user_input == 'n':
                        return False
                    else:
                        logger.info("请输入 'y' 继续或 'n' 跳过")
                except (EOFError, KeyboardInterrupt):
                    # 处理 EOF 错误或用户中断
                    logger.warning("无法获取用户输入，登录流程被中断")
                    return False

        except Exception as e:
            logger.debug(f"手动登录等待过程中发生错误: {e}")
            return False

    async def _click_password_login_tab(self) -> bool:
        """点击密码登录标签（参考 login_handler.py:_click_password_login_tab）"""
        try:
            # 等待页面加载完成
            await asyncio.sleep(1)

            # 查找密码登录标签 - 使用更精确的选择器
            password_tab_selectors = [
                'li.account-tab-account',
                '.account-tab-account',
                'a:has-text("密码登录")',
                'text=密码登录'
            ]

            for selector in password_tab_selectors:
                try:
                    logger.debug(f"尝试使用选择器找到密码登录标签: {selector}")
                    element = self.page.locator(selector).first

                    # 检查元素是否可见
                    if await element.is_visible(timeout=5000):
                        await element.click()
                        logger.info(f"成功点击密码登录标签，使用选择器: {selector}")
                        # 等待标签切换完成
                        await asyncio.sleep(2)
                        return True
                    else:
                        logger.debug(f"选择器 {selector} 找到但不可见")
                except Exception as e:
                    logger.debug(f"选择器 {selector} 失败: {e}")
                    continue

            logger.warning("未找到密码登录标签")
            return False

        except Exception as e:
            logger.error(f"点击密码登录标签时发生错误: {e}")
            return False

    async def _fill_login_form(self, username: str, password: str) -> bool:
        """填写登录表单（参考 login_handler.py:_fill_login_form）"""
        try:
            # 1. 输入用户名
            username_selectors = [
                '#username[name="username"]',
                'input[name="username"]',
                '#username'
            ]

            username_filled = False
            for selector in username_selectors:
                try:
                    username_field = self.page.locator(selector).first
                    if await username_field.is_visible(timeout=3000):
                        await username_field.fill(username)
                        logger.info(f"成功输入用户名: {username}")
                        username_filled = True
                        break
                except:
                    continue

            if not username_filled:
                logger.error("无法找到用户名输入框")
                return False

            # 2. 输入密码
            password_selectors = [
                '#password[type="password"]',
                'input[name="password"]',
                '#password'
            ]

            password_filled = False
            for selector in password_selectors:
                try:
                    password_field = self.page.locator(selector).first
                    if await password_field.is_visible(timeout=3000):
                        await password_field.fill(password)
                        logger.info("成功输入密码")
                        password_filled = True
                        break
                except:
                    continue

            if not password_filled:
                logger.error("无法找到密码输入框")
                return False

            return True

        except Exception as e:
            logger.error(f"填写登录表单时发生错误: {e}")
            return False

    async def _click_login_button(self) -> bool:
        """点击登录按钮（参考 login_handler.py:_click_login_button）"""
        try:
            login_button_selectors = [
                '.btn.btn-account',
                'a.btn.btn-account',
                '登录豆瓣',
                'button[type="submit"]'
            ]

            for selector in login_button_selectors:
                try:
                    login_button = self.page.locator(selector).first
                    if await login_button.is_visible(timeout=3000):
                        await login_button.click()
                        logger.info("成功点击登录按钮")
                        return True
                except:
                    continue

            logger.warning("未找到登录按钮")
            return False

        except Exception as e:
            logger.error(f"点击登录按钮时发生错误: {e}")
            return False

    async def _check_login_success(self) -> bool:
        """检查登录是否成功（参考 login_handler.py:_check_login_success）"""
        try:
            await asyncio.sleep(2)  # 等待页面响应

            current_url = self.page.url

            # 检查URL是否已跳转离开登录页面
            if 'login' not in current_url.lower() and 'accounts.douban.com' not in current_url:
                logger.info(f"登录成功，已跳转到: {current_url}")
                return True

            # 检查页面内容是否包含登录成功标识
            content = await self.page.content()
            success_indicators = [
                '欢迎', '个人中心', '我的豆瓣', 'logout', '退出',
                'settings', 'profile'
            ]

            for indicator in success_indicators:
                if indicator in content.lower():
                    logger.info(f"检测到登录成功标识: {indicator}")
                    return True

            # 如果还在登录页面，检查是否有错误信息
            error_indicators = [
                '密码错误', '用户名不存在', '验证码错误', '登录失败',
                'error', 'incorrect'
            ]

            for indicator in error_indicators:
                if indicator in content.lower():
                    logger.error(f"检测到登录错误: {indicator}")
                    return False

            logger.warning("无法确定登录状态，可能需要人工确认")
            return False

        except Exception as e:
            logger.error(f"检查登录状态时发生错误: {e}")
            return False

    async def extract_rating_from_current_page(self) -> tuple[Optional[str], Optional[int]]:
        """
        从当前页面提取评分和评价人数（支持搜索结果和详情页）
        """
        try:
            html = await self.page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # 先找搜索结果中的评分块
            rating_block = None
            subject_item = soup.select_one('.subject-item')
            if subject_item:
                rating_block = subject_item.select_one('.rating')

            # 如果搜索结果结构不存在，尝试详情页结构
            if not rating_block:
                rating_block = soup.select_one('.rating')  # 详情页评分区域

            if not rating_block:
                return None, None

            pl_text_el = rating_block.select_one('.pl')
            rating_nums_el = rating_block.select_one('.rating_nums')

            pl_text = (pl_text_el.get_text(strip=True) if pl_text_el else '')

            # 如果仅是评价人数不足或无人评价，仍返回评分（人数为0）
            rating_val = None
            if rating_nums_el:
                rating_val = rating_nums_el.get_text(strip=True)

            count_val = None
            if pl_text:
                m = re.search(r"(\d+)\s*人评价", pl_text)
                if m:
                    try:
                        count_val = int(m.group(1))
                    except Exception:
                        count_val = None
                elif '评价人数不足' in pl_text or '目前无人评价' in pl_text:
                    count_val = 0

            return (rating_val if rating_val else None,
                    count_val if count_val is not None else None)
        except Exception as e:
            logger.error(f"评分解析失败: {e}")
            return None, None

