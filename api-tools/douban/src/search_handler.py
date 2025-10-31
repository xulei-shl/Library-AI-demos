"""
搜索功能模块（优化版）
负责根据ISBN搜索图书并获取详情页链接
优化：避免重复登录，保持浏览器会话
"""

import logging
import time
from bs4 import BeautifulSoup
import re
from typing import Optional
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)


class SearchHandler:
    """搜索处理类（优化版）"""
    
    def __init__(self, page, delay_func, login_handler):
        """
        初始化搜索处理器
        
        Args:
            page: Playwright页面对象
            delay_func: 延迟函数
            login_handler: 登录处理器
        """
        self.page = page
        self._delay_func = delay_func
        self.login_handler = login_handler
        self.search_url = "https://search.douban.com/book/subject_search"
        
        # 添加登录状态管理
        self.login_completed = False  # 标记是否已完成登录
        self.login_attempted = False  # 标记是否已尝试过登录
        
    def search_by_isbn(self, isbn: str) -> Optional[str]:
        """
        通过ISBN搜索图书并获取详情页链接（优化版：避免重复登录）
        
        Args:
            isbn: ISBN号码
            
        Returns:
            图书详情页链接，如果未找到则返回None
        """
        try:
            logger.info(f"开始搜索ISBN: {isbn}")
            logger.info(f"当前登录状态: login_attempted={self.login_attempted}, login_completed={self.login_completed}")
            
            # 确保浏览器已启动
            if not self.page:
                raise Exception("浏览器未启动")
            
            # 如果登录已完成，直接开始搜索
            if self.login_completed:
                logger.info("登录已完成，直接开始搜索...")
                # 尝试直接URL搜索（更可靠）
                result = self._search_by_direct_url(isbn)
                if result:
                    return result
            
            # 访问豆瓣图书首页
            logger.info("访问豆瓣图书首页")
            self.page.goto("https://book.douban.com", wait_until="networkidle", timeout=30000)
            self._delay_func()
            
            # 优化登录检查：只有在未尝试过登录的情况下才检查
            # 如果已经尝试过登录，则假设浏览器处于已处理状态
            if not self.login_attempted:
                logger.info("首次检查登录状态...")
                if self.login_handler.check_login_page(page_type="normal"):
                    logger.warning("检测到需要登录或访问异常")
                    # 如果检测到需要登录，则尝试处理登录
                    if not self.login_completed:
                        logger.info("处理登录情况...")
                        result = self._handle_login_situation_optimized(isbn)
                        if result is not None:
                            return result
            else:
                logger.info("已跳过登录检查（登录状态已处理或跳过）")
            
            # 执行正常搜索流程
            logger.info("执行正常搜索流程")
            return self._perform_search(isbn)
                
        except PlaywrightTimeoutError:
            logger.error("搜索超时，请检查网络连接")
            return None
        except Exception as e:
            logger.error(f"搜索ISBN时发生错误: {e}")
            return None
    
    def _handle_login_situation_optimized(self, isbn: str) -> Optional[str]:
        """处理登录情况的多层级解决方案（优化版：设置登录状态）"""
        logger.info("开始处理登录情况...")
        
        # 方案1: 尝试自动登录
        if not self.login_handler.headless:  # 只有非无头模式才能自动登录
            logger.info("尝试自动登录...")
            if self.login_handler.auto_login():
                logger.info("自动登录成功，尝试重新搜索")
                self.login_completed = True
                self.login_attempted = True
                logger.info("登录后开始重新搜索...")
                return self._search_after_login(isbn)
            else:
                logger.warning("自动登录失败，尝试手动登录...")
        else:
            logger.info("当前为无头模式，跳过自动登录，直接手动登录...")
        
        # 方案2: 等待用户手动登录
        if self.login_handler.wait_for_manual_login():
            logger.info("用户完成手动登录，尝试重新搜索")
            self.login_completed = True
            self.login_attempted = True
            logger.info("登录后开始重新搜索...")
            return self._search_after_login(isbn)
        
        # 方案3: 尝试直接通过URL搜索，并标记已尝试登录
        logger.info("登录失败或跳过，尝试通过直接URL搜索")
        self.login_attempted = True
        return self._search_by_direct_url(isbn)
    
    def _search_after_login(self, isbn: str) -> Optional[str]:
        """登录后重新搜索（改进版）"""
        try:
            logger.info("重新开始搜索...")
            
            # 方法1: 直接通过搜索URL搜索（更可靠）
            logger.info("尝试直接通过搜索URL搜索...")
            direct_result = self._search_by_direct_url(isbn)
            if direct_result:
                return direct_result
            
            # 方法2: 如果直接搜索失败，尝试重新访问首页
            logger.info("直接搜索失败，尝试重新访问豆瓣首页...")
            try:
                # 获取当前页面状态，避免重复访问
                current_url = self.page.url
                logger.info(f"当前页面URL: {current_url}")
                
                # 如果当前页面已经是豆瓣相关页面，尝试刷新
                if "douban.com" in current_url:
                    logger.info("刷新当前页面...")
                    self.page.reload(wait_until="networkidle", timeout=20000)
                else:
                    # 否则访问豆瓣图书首页
                    logger.info("访问豆瓣图书首页...")
                    self.page.goto("https://book.douban.com", wait_until="networkidle", timeout=20000)
                
                self._delay_func()
                
                # 检查页面是否正常
                if self.login_handler.check_login_page(page_type="normal"):
                    logger.warning("登录后页面仍然异常")
                    return None
                
                # 执行搜索
                return self._perform_search(isbn)
                
            except Exception as home_error:
                logger.warning(f"重新访问首页失败: {home_error}")
                logger.info("尝试最后一次直接搜索...")
                return self._search_by_direct_url(isbn)
            
        except Exception as e:
            logger.error(f"登录后搜索失败: {e}")
            return None
    
    def _perform_search(self, isbn: str) -> Optional[str]:
        """执行搜索操作"""
        try:
            # 等待搜索框加载
            search_input = self.page.wait_for_selector("#inp-query", timeout=10000)
            search_input.fill(isbn)
            
            # 点击搜索按钮
            submit_button = self.page.wait_for_selector("input[type='submit'][value='搜索']", timeout=10000)
            submit_button.click()
            
            # 等待搜索结果
            self.page.wait_until("networkidle", timeout=30000)
            self._delay_func(page_type="search")
            
            # 提取搜索结果
            html = self.page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # 检查搜索结果
            if '没有找到' in html or 'not found' in html.lower():
                logger.warning(f"搜索结果为空")
                return None
            
            # 查找图书链接
            book_link = self._extract_book_link_from_search(soup, isbn)
            if book_link:
                logger.info(f"找到图书链接: {book_link}")
                return book_link
            else:
                logger.warning(f"未找到ISBN {isbn} 对应的图书")
                return None
                
        except Exception as e:
            logger.error(f"搜索操作失败: {e}")
            return None
    
    def _search_by_direct_url(self, isbn: str) -> Optional[str]:
        """通过直接URL搜索（改进版）"""
        try:
            # 构造直接搜索URL
            search_url = f"https://search.douban.com/book/subject_search?search_text={isbn}&cat=1001"
            logger.info(f"尝试直接访问搜索URL: {search_url}")
            
            # 访问搜索URL，使用更宽松的超时设置
            self.page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
            self._delay_func(page_type="search")
            
            # 检查是否需要登录（降低严格程度）
            if self.login_handler.check_login_page(page_type="search"):
                logger.warning("直接URL访问检测到登录要求")
                # 等待一下再试一次
                time.sleep(3)
                self.page.reload(wait_until="domcontentloaded", timeout=15000)
                self._delay_func(page_type="search")
                
                # 再次检查
                if self.login_handler.check_login_page(page_type="search"):
                    logger.warning("直接URL访问仍需要登录")
                    return None
            
            # 等待搜索结果加载 - 修复选择器
            try:
                # 根据实际HTML结构，等待对应的容器出现
                # 优先等待 detail 容器出现
                self.page.wait_for_selector(".detail", timeout=8000)
                logger.info("搜索结果页面加载完成（找到 detail 容器）")
            except:
                try:
                    # 备选方案：等待 title-text 链接出现
                    self.page.wait_for_selector(".title-text", timeout=5000)
                    logger.info("搜索结果页面加载完成（找到 title-text 链接）")
                except:
                    logger.warning("未找到搜索结果容器，检查页面内容...")
                    # 检查页面内容
                    html = self.page.content()
                    if '没有找到' in html or 'not found' in html.lower():
                        logger.warning("搜索结果为空")
                        return None
                    # 检查是否有实际的搜索结果
                    elif 'href=' in html and 'subject' in html:
                        logger.info("页面包含搜索结果，可能需要稍后提取")
                    else:
                        logger.warning("页面内容异常，无法确定搜索结果状态")
                        return None
            
            # 提取结果
            html = self.page.content()
            soup = BeautifulSoup(html, 'html.parser')
            book_link = self._extract_book_link_from_search(soup, isbn)
            
            if book_link:
                logger.info(f"直接URL搜索成功: {book_link}")
                return book_link
            else:
                logger.warning("直接URL搜索未找到结果")
                # 尝试检查页面状态
                current_url = self.page.url
                if "search" not in current_url:
                    logger.warning(f"页面URL异常，可能被重定向: {current_url}")
                return None
            
        except Exception as e:
            logger.error(f"直接URL搜索失败: {e}")
            return None
    
    def _extract_book_link_from_search(self, soup: BeautifulSoup, isbn: str) -> Optional[str]:
        """
        从搜索结果页面提取图书链接
        
        Args:
            soup: BeautifulSoup对象
            isbn: 搜索的ISBN
            
        Returns:
            图书详情页链接
        """
        try:
            # 根据您提供的HTML结构，优先查找 class='detail' 的div
            detail_divs = soup.find_all('div', class_='detail')
            
            for detail in detail_divs:
                # 在 detail div 中查找 class='title-text' 的链接
                title_link = detail.find('a', class_='title-text')
                if title_link and title_link.get('href'):
                    link = title_link.get('href')
                    # 检查是否包含subject（完整的URL或相对路径）
                    if 'subject' in link:
                        # 确保链接是完整的URL
                        if link.startswith('https://'):
                            logger.info(f"找到完整的图书链接: {link}")
                            return link
                        elif link.startswith('/'):
                            # 相对路径，转换为完整URL
                            full_link = 'https://book.douban.com' + link
                            logger.info(f"找到相对路径图书链接: {full_link}")
                            return full_link
                        else:
                            # 如果是其他格式，构建完整URL
                            if link.startswith('subject/'):
                                full_link = 'https://book.douban.com/' + link
                                logger.info(f"构建完整图书链接: {full_link}")
                                return full_link
            
            # 如果没有找到detail结构，尝试其他方式：查找所有包含subject的链接
            all_links = soup.find_all('a', href=True)
            for link_elem in all_links:
                href = link_elem.get('href')
                if href and 'subject' in href:
                    # 确保链接是完整的URL
                    if href.startswith('https://'):
                        logger.info(f"通过备选方式找到图书链接: {href}")
                        return href
                    elif href.startswith('/'):
                        full_link = 'https://book.douban.com' + href
                        logger.info(f"通过备选方式找到相对链接，转换为: {full_link}")
                        return full_link
            
            # 最后尝试通过正则表达式匹配subject URL模式
            subject_links = soup.find_all('a', href=re.compile(r'.*subject.*\d+.*'))
            if subject_links:
                for link_elem in subject_links:
                    href = link_elem.get('href')
                    if href:
                        if href.startswith('https://'):
                            logger.info(f"通过正则表达式找到完整链接: {href}")
                            return href
                        elif href.startswith('/'):
                            full_link = 'https://book.douban.com' + href
                            logger.info(f"通过正则表达式找到相对链接，转换为: {full_link}")
                            return full_link
            
            logger.warning("未找到符合条件的图书链接")
            return None
            
        except Exception as e:
            logger.error(f"提取图书链接时发生错误: {e}")
            return None