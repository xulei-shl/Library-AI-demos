"""
详情页提取模块
负责从图书详情页提取详细信息
"""

import logging
import time
import re
from bs4 import BeautifulSoup
from typing import Dict
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)


class DetailExtractor:
    """详情页提取类"""
    
    def __init__(self, page, delay_func, login_handler):
        """
        初始化详情页提取器
        
        Args:
            page: Playwright页面对象
            delay_func: 延迟函数
            login_handler: 登录处理器
        """
        self.page = page
        self._delay_func = delay_func
        self.login_handler = login_handler
        
        # 添加登录状态管理
        self.login_completed = False  # 标记是否已完成登录
        self.login_attempted = False  # 标记是否已尝试过登录
        
        
    def extract_book_details(self, book_url: str) -> Dict:
        """
        从图书详情页提取详细信息（改进版）
        
        Args:
            book_url: 图书详情页URL
            
        Returns:
            包含图书信息的字典
        """
        try:
            logger.info(f"开始提取图书详情: {book_url}")
            
            # 访问图书详情页 - 优化超时策略
            try:
                # 优先使用更宽松的等待条件
                self.page.goto(book_url, wait_until="domcontentloaded", timeout=25000)
            except PlaywrightTimeoutError:
                logger.warning("domcontentloaded 超时，尝试 networkidle0...")
                try:
                    self.page.goto(book_url, wait_until="networkidle0", timeout=20000)
                except PlaywrightTimeoutError:
                    logger.warning("networkidle0 也超时，尝试基本页面加载...")
                    try:
                        self.page.goto(book_url, timeout=15000)
                        # 等待基本DOM加载
                        self.page.wait_for_selector("h1, .subject, #info", timeout=10000)
                    except PlaywrightTimeoutError:
                        logger.error("页面加载完全超时，使用备用策略")
                        return self._extract_with_retry(book_url)
            
            # 检查是否跳转到登录页面
            if self.login_handler.check_login_page(page_type="detail"):
                logger.error("详情页需要登录访问")
                return {}
            
            # 等待页面关键元素加载 - 减少延迟时间
            self._delay_func(page_type="detail")
            
            # 获取页面HTML
            html = self.page.content()
            
            # 检查页面是否真的加载了内容
            if len(html) < 1000:  # 如果页面内容太少，可能加载失败
                logger.warning("页面内容较少，尝试重新加载...")
                self.page.reload(wait_until="domcontentloaded", timeout=15000)
                self._delay_func(page_type="detail")
                html = self.page.content()
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # 验证页面是否包含预期的元素
            if not self._validate_detail_page(soup):
                logger.warning("详情页面验证失败，可能页面结构异常")
                return {}
            
            # 提取各项信息
            book_info = {
                '链接': book_url,
                '评分': self._extract_rating(soup),
                '题名': self._extract_title(soup),
                '作者': self._extract_author(soup),
                '出版社': self._extract_publisher(soup),
                '出品方': self._extract_producer(soup),
                '副标题': self._extract_subtitle(soup),
                '原作名': self._extract_original_title(soup),
                '译者': self._extract_translator(soup),
                '出版年': self._extract_pub_year(soup),
                '页数': self._extract_pages(soup),
                '定价': self._extract_price(soup),
                '装帧': self._extract_binding(soup),
                '丛书': self._extract_series(soup),
                '丛书链接': self._extract_series_link(soup),
                'ISBN': self._extract_isbn(soup),
                '封面图片链接': self._extract_cover_image(soup),
                '内容简介': self._extract_summary(soup),
                '作者简介': self._extract_author_intro(soup),
                '目录': self._extract_catalog(soup)
            }
            
            logger.info("图书信息提取完成")
            return book_info
            
        except Exception as e:
            logger.error(f"提取图书详情时发生错误: {e}")
            return {}
    
    def _validate_detail_page(self, soup: BeautifulSoup) -> bool:
        """
        验证详情页面是否包含预期元素
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            页面是否有效
        """
        try:
            # 检查页面是否包含豆瓣相关元素
            required_elements = [
                '豆瓣', 'douban', '读书', 'book',
                '<div id="info"', '<div id="interest_sectl"'
            ]
            
            html_content = str(soup)
            element_count = sum(1 for element in required_elements if element in html_content)
            
            # 如果页面内容足够大且包含必要的元素
            if len(html_content) > 2000 and element_count >= 2:
                logger.info("详情页面验证通过")
                return True
            elif len(html_content) > 500:
                # 内容稍少但仍可能有效
                logger.info("详情页面内容较少但可能有效，继续处理")
                return True
            else:
                logger.warning(f"详情页面验证失败 - 内容长度: {len(html_content)}, 元素数量: {element_count}")
                return False
                
        except Exception as e:
            logger.debug(f"页面验证出错: {e}")
            return True  # 出错时保守处理
    
    def _extract_with_retry(self, book_url: str) -> Dict:
        """
        备用提取方法，当正常访问失败时使用
        
        Args:
            book_url: 图书详情页URL
            
        Returns:
            包含图书信息的字典
        """
        try:
            logger.info("尝试备用提取方法...")
            
            # 尝试直接获取页面内容，不等待网络空闲
            self.page.goto(book_url, timeout=10000)
            time.sleep(5)  # 固定等待5秒
            
            html = self.page.content()
            if len(html) < 1000:
                logger.error("备用方法也未能获取到有效内容")
                return {}
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # 提取基本信息
            book_info = {
                '链接': book_url,
                '评分': self._extract_rating(soup),
                '题名': self._extract_title(soup),
                '作者': self._extract_author(soup),
                '出版社': self._extract_publisher(soup),
                '出品方': self._extract_producer(soup),
                '副标题': self._extract_subtitle(soup),
                '原作名': self._extract_original_title(soup),
                '译者': self._extract_translator(soup),
                '出版年': self._extract_pub_year(soup),
                '页数': self._extract_pages(soup),
                '定价': self._extract_price(soup),
                '装帧': self._extract_binding(soup),
                '丛书': self._extract_series(soup),
                '丛书链接': self._extract_series_link(soup),
                'ISBN': self._extract_isbn(soup),
                '封面图片链接': self._extract_cover_image(soup),
                '内容简介': self._extract_summary(soup),
                '作者简介': self._extract_author_intro(soup),
                '目录': self._extract_catalog(soup)
            }
            
            logger.info("备用提取方法完成")
            return book_info
            
        except Exception as e:
            logger.error(f"备用提取方法失败: {e}")
            return {}
    
    def _extract_rating(self, soup: BeautifulSoup) -> str:
        """提取评分"""
        try:
            rating_element = soup.find('strong', class_='ll rating_num')
            if rating_element:
                return rating_element.text.strip()
            return ""
        except:
            return ""
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """提取题名"""
        try:
            title_element = soup.find('h1', {'property': 'v:itemreviewed'})
            if title_element:
                return title_element.text.strip()
            
            # 备选方案
            title_link = soup.find('a', class_='nbg')
            if title_link:
                title = title_link.get('title', '')
                if title:
                    return title.strip()
            
            # 另一个备选方案
            info_div = soup.find('div', id='info')
            if info_div:
                first_span = info_div.find('span', class_='pl')
                if first_span:
                    next_span = first_span.find_next_sibling()
                    if next_span and next_span.name == 'span':
                        return next_span.text.strip()
            
            return ""
        except:
            return ""
    
    def _extract_author(self, soup: BeautifulSoup) -> str:
        """提取作者"""
        try:
            info_div = soup.find('div', id='info')
            if info_div:
                author_span = info_div.find('span', string=re.compile(r'作者'))
                if author_span:
                    author_text = author_span.find_next_sibling().text.strip()
                    # 清理多余的换行和空格
                    return re.sub(r'\s+', ' ', author_text)
            return ""
        except:
            return ""
    
    def _extract_publisher(self, soup: BeautifulSoup) -> str:
        """提取出版社"""
        try:
            info_div = soup.find('div', id='info')
            if info_div:
                publisher_span = info_div.find('span', string=re.compile(r'出版社'))
                if publisher_span:
                    publisher_link = publisher_span.find_next_sibling()
                    if publisher_link:
                        return publisher_link.text.strip()
            return ""
        except:
            return ""
    
    def _extract_producer(self, soup: BeautifulSoup) -> str:
        """提取出品方"""
        try:
            info_div = soup.find('div', id='info')
            if info_div:
                producer_span = info_div.find('span', string=re.compile(r'出品方'))
                if producer_span:
                    producer_link = producer_span.find_next_sibling()
                    if producer_link:
                        return producer_link.text.strip()
            return ""
        except:
            return ""
    
    def _extract_subtitle(self, soup: BeautifulSoup) -> str:
        """提取副标题"""
        try:
            info_div = soup.find('div', id='info')
            if info_div:
                # 使用正则表达式在info区域中查找副标题
                info_text = info_div.get_text()
                match = re.search(r'副标题[:：]\s*([^\n\r<]+)', info_text)
                if match:
                    subtitle = match.group(1).strip()
                    logger.debug(f"提取到副标题: {subtitle}")
                    return subtitle
            
            # 备用方法：直接查找包含"副标题"的文本节点
            subtitle_text = soup.find(text=re.compile(r'副标题[:：]'))
            if subtitle_text:
                match = re.search(r'副标题[:：]\s*([^\n\r<]+)', subtitle_text)
                if match:
                    subtitle = match.group(1).strip()
                    logger.debug(f"备用方法提取到副标题: {subtitle}")
                    return subtitle
                    
            logger.debug("未找到副标题信息")
            return ""
        except Exception as e:
            logger.debug(f"提取副标题失败: {e}")
            return ""
    
    def _extract_binding(self, soup: BeautifulSoup) -> str:
        """提取装帧"""
        try:
            info_div = soup.find('div', id='info')
            if info_div:
                # 使用正则表达式在info区域中查找装帧
                info_text = info_div.get_text()
                match = re.search(r'装帧[:：]\s*([^\n\r<]+)', info_text)
                if match:
                    binding = match.group(1).strip()
                    logger.debug(f"提取到装帧: {binding}")
                    return binding
            
            # 备用方法：直接查找包含"装帧"的文本节点
            binding_text = soup.find(text=re.compile(r'装帧[:：]'))
            if binding_text:
                match = re.search(r'装帧[:：]\s*([^\n\r<]+)', binding_text)
                if match:
                    binding = match.group(1).strip()
                    logger.debug(f"备用方法提取到装帧: {binding}")
                    return binding
                    
            logger.debug("未找到装帧信息")
            return ""
        except Exception as e:
            logger.debug(f"提取装帧失败: {e}")
            return ""
    
    def _extract_original_title(self, soup: BeautifulSoup) -> str:
        """提取原作名"""
        try:
            info_div = soup.find('div', id='info')
            if info_div:
                # 使用正则表达式在info区域中查找原作名
                info_text = info_div.get_text()
                match = re.search(r'原作名[:：]\s*([^\n\r<]+)', info_text)
                if match:
                    original_title = match.group(1).strip()
                    logger.debug(f"提取到原作名: {original_title}")
                    return original_title
            
            # 备用方法：直接查找包含"原作名"的文本节点
            original_text = soup.find(text=re.compile(r'原作名[:：]'))
            if original_text:
                match = re.search(r'原作名[:：]\s*([^\n\r<]+)', original_text)
                if match:
                    original_title = match.group(1).strip()
                    logger.debug(f"备用方法提取到原作名: {original_title}")
                    return original_title
                    
            logger.debug("未找到原作名信息")
            return ""
        except Exception as e:
            logger.debug(f"提取原作名失败: {e}")
            return ""
    
    def _extract_series(self, soup: BeautifulSoup) -> str:
        """提取丛书名称"""
        try:
            info_div = soup.find('div', id='info')
            if info_div:
                # 查找丛书字段
                series_span = info_div.find('span', string=re.compile(r'丛书'))
                if series_span:
                    # 查找紧跟的链接
                    series_link = series_span.find_next_sibling('a')
                    if series_link:
                        return series_link.text.strip()
                    
                    # 如果没有直接的链接，尝试查找后续文本
                    parent = series_span.parent
                    if parent:
                        full_text = parent.get_text()
                        # 使用正则表达式提取丛书名
                        match = re.search(r'丛书[:：]\s*([^\n\r<]+)', full_text)
                        if match:
                            return match.group(1).strip()
            return ""
        except:
            return ""
    
    def _extract_series_link(self, soup: BeautifulSoup) -> str:
        """提取丛书链接"""
        try:
            info_div = soup.find('div', id='info')
            if info_div:
                # 查找丛书字段
                series_span = info_div.find('span', string=re.compile(r'丛书'))
                if series_span:
                    # 查找紧跟的链接
                    series_link = series_span.find_next_sibling('a')
                    if series_link:
                        href = series_link.get('href', '')
                        if href:
                            # 确保是完整的URL
                            if href.startswith('https://'):
                                return href
                            elif href.startswith('//'):
                                return 'https:' + href
                            elif href.startswith('/'):
                                return 'https://book.douban.com' + href
                            else:
                                return href
            return ""
        except:
            return ""
    
    def _extract_translator(self, soup: BeautifulSoup) -> str:
        """提取译者"""
        try:
            info_div = soup.find('div', id='info')
            if info_div:
                translator_span = info_div.find('span', string=re.compile(r'译者'))
                if translator_span:
                    # 获取包含所有译者的父span元素
                    parent_span = translator_span.parent
                    if parent_span:
                        # 获取完整的译者文本（包括所有链接和分隔符）
                        translator_text = parent_span.get_text()
                        # 使用正则表达式提取译者部分，支持多行和换行
                        match = re.search(r'译者[:：]\s*(.+?)(?=\s*<|\s*$)', translator_text, re.DOTALL)
                        if match:
                            translator_names = match.group(1).strip()
                            # 清理多余换行和空格，保留作者间的分隔符
                            translator_names = re.sub(r'\s+', ' ', translator_names)
                            return translator_names
                    
                    # 备用方案：尝试获取所有后续兄弟元素
                    all_translators = []
                    current_element = translator_span.find_next_sibling()
                    while current_element:
                        if hasattr(current_element, 'text'):
                            text = current_element.text.strip()
                            if text and text != '/':
                                all_translators.append(text)
                        current_element = current_element.find_next_sibling()
                    
                    if all_translators:
                        return ' / '.join(all_translators)
            
            return ""
        except:
            return ""
    
    def _extract_pub_year(self, soup: BeautifulSoup) -> str:
        """提取出版年"""
        try:
            info_div = soup.find('div', id='info')
            if info_div:
                # 使用正则表达式在info区域中查找出版年
                info_text = info_div.get_text()
                match = re.search(r'出版年[:：]\s*([^\n\r<]+)', info_text)
                if match:
                    pub_year = match.group(1).strip()
                    logger.debug(f"提取到出版年: {pub_year}")
                    return pub_year
            
            # 备用方法：直接查找包含"出版年"的文本节点
            year_text = soup.find(text=re.compile(r'出版年[:：]'))
            if year_text:
                match = re.search(r'出版年[:：]\s*([^\n\r<]+)', year_text)
                if match:
                    pub_year = match.group(1).strip()
                    logger.debug(f"备用方法提取到出版年: {pub_year}")
                    return pub_year
                    
            logger.debug("未找到出版年信息")
            return ""
        except Exception as e:
            logger.debug(f"提取出版年失败: {e}")
            return ""
    
    def _extract_pages(self, soup: BeautifulSoup) -> str:
        """提取页数"""
        try:
            info_div = soup.find('div', id='info')
            if info_div:
                # 使用正则表达式在info区域中查找页数
                info_text = info_div.get_text()
                match = re.search(r'页数[:：]\s*([^\n\r<]+)', info_text)
                if match:
                    pages = match.group(1).strip()
                    logger.debug(f"提取到页数: {pages}")
                    return pages
            
            # 备用方法：直接查找包含"页数"的文本节点
            pages_text = soup.find(text=re.compile(r'页数[:：]'))
            if pages_text:
                match = re.search(r'页数[:：]\s*([^\n\r<]+)', pages_text)
                if match:
                    pages = match.group(1).strip()
                    logger.debug(f"备用方法提取到页数: {pages}")
                    return pages
                    
            logger.debug("未找到页数信息")
            return ""
        except Exception as e:
            logger.debug(f"提取页数失败: {e}")
            return ""
    
    def _extract_price(self, soup: BeautifulSoup) -> str:
        """提取定价"""
        try:
            info_div = soup.find('div', id='info')
            if info_div:
                # 使用正则表达式在info区域中查找定价
                info_text = info_div.get_text()
                match = re.search(r'定价[:：]\s*([^\n\r<]+)', info_text)
                if match:
                    price = match.group(1).strip()
                    logger.debug(f"提取到定价: {price}")
                    return price
            
            # 备用方法：直接查找包含"定价"的文本节点
            price_text = soup.find(text=re.compile(r'定价[:：]'))
            if price_text:
                match = re.search(r'定价[:：]\s*([^\n\r<]+)', price_text)
                if match:
                    price = match.group(1).strip()
                    logger.debug(f"备用方法提取到定价: {price}")
                    return price
                    
            logger.debug("未找到定价信息")
            return ""
        except Exception as e:
            logger.debug(f"提取定价失败: {e}")
            return ""
    
    def _extract_isbn(self, soup: BeautifulSoup) -> str:
        """提取ISBN"""
        try:
            # 方法1: 查找ISBN字段
            info_div = soup.find('div', id='info')
            if info_div:
                isbn_span = info_div.find('span', string=re.compile(r'ISBN'))
                if isbn_span:
                    # 获取下一个非空白兄弟元素
                    next_element = isbn_span.next_sibling
                    while next_element:
                        if hasattr(next_element, 'strip') and next_element.strip():
                            return next_element.strip()
                        elif hasattr(next_element, 'text') and next_element.text.strip():
                            return next_element.text.strip()
                        next_element = next_element.next_sibling
                    
                    # 备用方案：查找整个文本
                    full_text = info_div.get_text()
                    match = re.search(r'ISBN[:：]\s*([0-9\-]+)', full_text)
                    if match:
                        return match.group(1).strip()
            
            # 方法2: 直接在整个页面中查找ISBN格式的文本
            page_text = soup.get_text()
            isbn_matches = re.findall(r'ISBN[:：]?\s*([0-9\-]{10,})', page_text)
            if isbn_matches:
                return isbn_matches[0].strip()
                
            # 方法3: 查找属性中包含ISBN的内容
            isbn_elements = soup.find_all(text=re.compile(r'ISBN[:：]?\s*[0-9\-]{10,}'))
            if isbn_elements:
                for element in isbn_elements:
                    match = re.search(r'ISBN[:：]?\s*([0-9\-]{10,})', element)
                    if match:
                        return match.group(1).strip()
                        
            return ""
        except Exception as e:
            logger.debug(f"提取ISBN失败: {e}")
            return ""
    
    def _extract_summary(self, soup: BeautifulSoup) -> str:
        """提取内容简介"""
        try:
            # 方法1: 查找link-report区域（这是最常见的位置）
            summary_div = soup.find('div', id='link-report')
            if summary_div:
                # 查找展开全部的内容
                all_content = summary_div.find('span', class_='all')
                if all_content:
                    intro_div = all_content.find('div', class_='intro')
                    if intro_div:
                        paragraphs = intro_div.find_all('p')
                        summary_text = ' '.join([p.get_text().strip() for p in paragraphs])
                        if summary_text.strip():
                            logger.debug(f"提取到内容简介（完整版）: {summary_text[:100]}...")
                            return re.sub(r'\s+', ' ', summary_text)
                
                # 如果没有展开内容，尝试获取简短内容
                short_content = summary_div.find('span', class_='short')
                if short_content:
                    intro_div = short_content.find('div', class_='intro')
                    if intro_div:
                        paragraphs = intro_div.find_all('p')
                        summary_text = ' '.join([p.get_text().strip() for p in paragraphs if not p.find('a')])
                        if summary_text.strip():
                            logger.debug(f"提取到内容简介（简短版）: {summary_text[:100]}...")
                            return re.sub(r'\s+', ' ', summary_text)
            
            # 方法2: 查找包含"内容简介"或"内容提要"的部分
            summary_heading = soup.find(['h2', 'span'], string=re.compile(r'内容简介|内容提要'))
            if summary_heading:
                # 找到下一个内容区域
                container = summary_heading.find_parent()
                if container:
                    content_div = container.find_next_sibling()
                    if content_div and content_div.name == 'div':
                        intro_div = content_div.find('div', class_='intro')
                        if intro_div:
                            paragraphs = intro_div.find_all('p')
                            summary_text = ' '.join([p.get_text().strip() for p in paragraphs])
                            if summary_text.strip():
                                logger.debug(f"提取到内容简介（标题定位）: {summary_text[:100]}...")
                                return re.sub(r'\s+', ' ', summary_text)
            
            # 方法3: 直接在整个页面中查找包含内容简介的div
            intro_divs = soup.find_all('div', class_='intro')
            for intro_div in intro_divs:
                # 查找内容比较长的段落（避免标题或短描述）
                paragraphs = intro_div.find_all('p')
                if paragraphs:
                    summary_text = ' '.join([p.get_text().strip() for p in paragraphs])
                    if len(summary_text) > 50:  # 内容简介通常比较长
                        logger.debug(f"提取到内容简介（直接搜索）: {summary_text[:100]}...")
                        return re.sub(r'\s+', ' ', summary_text)
                        
            logger.debug("未找到内容简介信息")
            return ""
        except Exception as e:
            logger.debug(f"提取内容简介失败: {e}")
            return ""
    
    def _extract_author_intro(self, soup: BeautifulSoup) -> str:
        """提取作者简介"""
        try:
            # 添加调试信息
            logger.debug("开始提取作者简介...")
            
            # 方法1: 查找作者简介区域，并优先获取完整版本
            author_intro_heading = soup.find(['h2', 'span'], string=re.compile(r'作者简介'))
            if author_intro_heading:
                logger.debug("找到作者简介标题，开始提取...")
                # 找到下一个内容区域
                container = author_intro_heading.find_parent()
                if container:
                    content_div = container.find_next_sibling()
                    if content_div and content_div.name == 'div':
                        # 首先尝试查找展开全部的内容（完整版）
                        all_content = content_div.find('span', class_='all')
                        if all_content:
                            intro_div = all_content.find('div', class_='intro')
                            if intro_div:
                                paragraphs = intro_div.find_all('p')
                                intro_text = ' '.join([p.get_text().strip() for p in paragraphs])
                                if intro_text.strip():
                                    logger.debug(f"提取到作者简介（完整版）: {intro_text[:100]}...")
                                    return re.sub(r'\s+', ' ', intro_text)
                        
                        # 如果没有展开内容，尝试获取简短内容
                        short_content = content_div.find('span', class_='short')
                        if short_content:
                            intro_div = short_content.find('div', class_='intro')
                            if intro_div:
                                # 排除展开链接
                                paragraphs = intro_div.find_all('p')
                                paragraphs = [p for p in paragraphs if not p.find('a', class_='j a_show_full')]
                                intro_text = ' '.join([p.get_text().strip() for p in paragraphs])
                                if intro_text.strip():
                                    logger.debug(f"提取到作者简介（简短版）: {intro_text[:100]}...")
                                    return re.sub(r'\s+', ' ', intro_text)
                        
                        # 新增：尝试直接查找intro div（第三种结构）
                        intro_div = content_div.find('div', class_='intro')
                        if intro_div:
                            paragraphs = intro_div.find_all('p')
                            intro_text = ' '.join([p.get_text().strip() for p in paragraphs])
                            if intro_text.strip():
                                logger.debug(f"提取到作者简介（直接结构）: {intro_text[:100]}...")
                                return re.sub(r'\s+', ' ', intro_text)
            else:
                logger.debug("未找到作者简介标题，尝试方法2...")
            
            # 方法2: 直接在整个页面中查找作者简介相关的intro区域
            intro_divs = soup.find_all('div', class_='intro')
            logger.debug(f"找到{len(intro_divs)}个intro div")
            
            for intro_div in intro_divs:
                # 查找包含"关于作者"或"作者简介"内容的段落
                paragraphs = intro_div.find_all('p')
                for p in paragraphs:
                    text = p.get_text().strip()
                    if '关于作者' in text or '作者简介' in text:
                        logger.debug(f"找到相关段落: {text}")
                        # 获取当前段落及其后续段落
                        intro_text = text
                        current_p = p.find_next_sibling()
                        while current_p and current_p.name == 'p':
                            current_text = current_p.get_text().strip()
                            if not current_text:  # 跳过空段落
                                current_p = current_p.find_next_sibling()
                                continue
                            intro_text += ' ' + current_text
                            
                            # 如果遇到新的标题段落，停止
                            if any(keyword in current_text for keyword in ['关于译者', '译者简介', '序言', '前言']):
                                break
                            
                            current_p = current_p.find_next_sibling()
                        
                        if len(intro_text) > 50:  # 确保内容足够长
                            logger.debug(f"提取到作者简介（直接搜索）: {intro_text[:100]}...")
                            return intro_text
            
            # 方法3: 查找可能存在的其他结构
            # 直接查找包含"关于作者"的文本节点
            about_author_texts = soup.find_all(text=re.compile(r'关于作者'))
            if about_author_texts:
                logger.debug(f"找到{len(about_author_texts)}个'关于作者'文本")
                for text_node in about_author_texts:
                    parent_p = text_node.parent
                    if parent_p and parent_p.name == 'p':
                        # 从这个段落开始提取内容
                        intro_text = parent_p.get_text().strip()
                        current_p = parent_p.find_next_sibling()
                        while current_p and current_p.name == 'p':
                            current_text = current_p.get_text().strip()
                            if not current_text:
                                current_p = current_p.find_next_sibling()
                                continue
                            intro_text += ' ' + current_text
                            
                            # 如果遇到新的标题段落，停止
                            if any(keyword in current_text for keyword in ['关于译者', '译者简介', '序言', '前言']):
                                break
                            
                            current_p = current_p.find_next_sibling()
                        
                        if len(intro_text) > 50:
                            logger.debug(f"提取到作者简介（文本节点搜索）: {intro_text[:100]}...")
                            return intro_text
            
            # 方法4: 特殊处理第三种结构（直接包裹在noise或indent中）
            # 查找所有的div元素，然后检查其是否包含作者简介内容
            all_divs = soup.find_all('div')
            for div in all_divs:
                # 检查这个div是否直接包含简介内容
                intro_div = div.find('div', class_='intro')
                if intro_div:
                    paragraphs = intro_div.find_all('p')
                    if paragraphs:
                        # 检查第一个段落是否像作者简介
                        first_paragraph = paragraphs[0].get_text().strip()
                        # 如果段落较长且包含可能的姓名标识，可能是作者简介
                        if (len(first_paragraph) > 100 and
                            ('—' in first_paragraph or '年' in first_paragraph or
                             '教授' in first_paragraph or '博士' in first_paragraph)):
                            
                            intro_text = ' '.join([p.get_text().strip() for p in paragraphs])
                            logger.debug(f"提取到作者简介（特殊结构）: {intro_text[:100]}...")
                            return intro_text
            
            logger.debug("未找到作者简介信息")
            return ""
        except Exception as e:
            logger.error(f"提取作者简介失败: {e}")
            return ""
    
    def _extract_catalog(self, soup: BeautifulSoup) -> str:
        """提取目录"""
        try:
            # 查找目录部分，常见的ID模式
            catalog_div = soup.find('div', id=re.compile(r'dir_\d+_full'))
            if catalog_div:
                # 移除HTML标签，只保留文本内容
                catalog_text = catalog_div.get_text()
                # 清理多余的空格和换行
                lines = [line.strip() for line in catalog_text.split('\n') if line.strip()]
                # 移除多余的"· · · · · ·     (收起)"字符
                lines = [line for line in lines if not re.match(r'^·+\s*\(\s*收起\s*\)$', line) and
                         not re.match(r'^·+\s*$', line)]
                return '\n'.join(lines)
            
            # 备选方案：查找包含"目录"的关键字
            catalog_heading = soup.find(['h2', 'span'], string=re.compile(r'目录'))
            if catalog_heading:
                container = catalog_heading.find_parent()
                if container:
                    next_div = container.find_next_sibling()
                    if next_div and next_div.name == 'div':
                        catalog_text = next_div.get_text()
                        lines = [line.strip() for line in catalog_text.split('\n') if line.strip()]
                        # 移除多余的"· · · · · ·     (收起)"字符
                        lines = [line for line in lines if not re.match(r'^·+\s*\(\s*收起\s*\)$', line) and
                                 not re.match(r'^·+\s*$', line)]
                        return '\n'.join(lines)
            
            return ""
        except:
            return ""
    
    def _extract_cover_image(self, soup: BeautifulSoup) -> str:
        """提取封面图片链接"""
        try:
            # 根据HTML结构查找封面图片
            mainpic_div = soup.find('div', id='mainpic')
            if mainpic_div:
                # 查找img标签
                img_tag = mainpic_div.find('img')
                if img_tag:
                    # 获取图片链接
                    image_url = img_tag.get('src', '')
                    if image_url:
                        # 确保是完整的URL
                        if image_url.startswith('https://'):
                            return image_url
                        elif image_url.startswith('//'):
                            return 'https:' + image_url
                        elif image_url.startswith('/'):
                            return 'https://book.douban.com' + image_url
                        else:
                            return image_url
            
            # 备选方案：查找所有img标签中的第一个
            img_tags = soup.find_all('img', alt=True)
            for img in img_tags:
                src = img.get('src', '')
                if src and ('cover' in src.lower() or 'img' in src.lower()):
                    if src.startswith('https://'):
                        return src
                    elif src.startswith('//'):
                        return 'https:' + src
                    elif src.startswith('/'):
                        return 'https://book.douban.com' + src
            
            return ""
        except:
            return ""