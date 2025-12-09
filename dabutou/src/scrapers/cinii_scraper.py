"""
CiNii网站爬虫
https://ci.nii.ac.jp/
"""
import requests
from bs4 import BeautifulSoup
from typing import Optional, List, Dict, Any
import re
import time
import urllib.parse
from src.core.base_scraper import BaseScraper, ScrapingResult


class CiNiiScraper(BaseScraper):
    """CiNii网站爬虫"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.base_url = "https://ci.nii.ac.jp"
        self.search_url_template = "https://ci.nii.ac.jp/books/search?advanced=false&count=20&sortorder=3&q={}&type=0&update_keep=true"

        # 设置请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        # 设置请求参数
        self.timeout = self.config.get('timeout', 30)
        self.delay = self.config.get('delay', 2)  # 请求间隔
        self.max_retries = self.config.get('max_retries', 3)

    def build_search_url(self, keyword: str) -> str:
        """
        根据关键词构建搜索URL
        """
        # 对关键词进行URL编码
        encoded_keyword = urllib.parse.quote(keyword)
        return self.search_url_template.format(encoded_keyword)

    def _make_request(self, url: str, retries: int = 0) -> Optional[requests.Response]:
        """
        发送HTTP请求
        """
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            self.logger.warning(f"请求失败 (尝试 {retries + 1}/{self.max_retries}): {str(e)}")

            if retries < self.max_retries - 1:
                time.sleep(self.delay * (retries + 1))  # 递增延迟
                return self._make_request(url, retries + 1)

            return None

    def search_books(self, keyword: str) -> Optional[str]:
        """
        搜索图书，获取第一个结果的详情页URL
        """
        search_url = self.build_search_url(keyword)

        response = self._make_request(search_url)
        if not response:
            return None

        try:
            soup = BeautifulSoup(response.text, 'html.parser')

            # 检查是否有搜索结果
            result_count = self._get_result_count(soup)
            if result_count == 0:
                self.logger.info(f"关键词 '{keyword}' 没有搜索结果")
                return None

            # 获取第一个结果的链接
            first_result = self._get_first_result(soup)
            if first_result:
                detail_path = first_result.get('href')
                if detail_path:
                    full_url = urllib.parse.urljoin(self.base_url, detail_path)
                    self.logger.info(f"找到第一个结果: {full_url}")
                    return full_url

        except Exception as e:
            self.logger.error(f"解析搜索结果页面失败: {str(e)}")

        return None

    def _get_result_count(self, soup: BeautifulSoup) -> int:
        """
        获取搜索结果数量
        """
        try:
            # 查找搜索结果数量
            result_heading = soup.find('h1', class_='heading')
            if result_heading:
                text = result_heading.get_text()
                # 使用正则表达式提取数字
                match = re.search(r'(\d+)件', text)
                if match:
                    return int(match.group(1))
        except Exception as e:
            self.logger.debug(f"获取结果数量失败: {str(e)}")

        return 0

    def _get_first_result(self, soup: BeautifulSoup) -> Optional[any]:
        """
        获取第一个搜索结果
        """
        try:
            # 查找第一个结果项
            first_item = soup.find('div', class_='listitem')
            if first_item:
                # 查找链接
                link = first_item.find('a', class_='taggedlink')
                return link
        except Exception as e:
            self.logger.debug(f"获取第一个结果失败: {str(e)}")

        return None

    def get_libraries(self, detail_url: str) -> List[str]:
        """
        获取馆藏图书馆信息
        """
        response = self._make_request(detail_url)
        if not response:
            return []

        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            libraries = []

            # 查找图书馆列表
            library_items = self._find_library_items(soup)

            for item in library_items:
                library_name = self._extract_library_name(item)
                if library_name and library_name not in libraries:
                    libraries.append(library_name)

            self.logger.info(f"从详情页获取到 {len(libraries)} 个图书馆信息")
            return libraries

        except Exception as e:
            self.logger.error(f"解析详情页失败: {str(e)}")
            return []

    def _find_library_items(self, soup: BeautifulSoup) -> List:
        """
        查找图书馆列表项
        """
        try:
            # 查找图书馆列表容器
            library_list = soup.find('ul', id='library-list')
            if library_list:
                # 查找所有图书馆项 - 使用属性过滤器
                return library_list.find_all('li', attrs={'name': 'library'})
        except Exception as e:
            self.logger.debug(f"查找图书馆项失败: {str(e)}")

        return []

    def _extract_library_name(self, library_item) -> Optional[str]:
        """
        提取图书馆名称
        """
        try:
            # 查找图书馆链接
            library_link = library_item.find('a')
            if library_link:
                library_name = library_link.get_text().strip()
                # 清理图书馆名称，但保留中文字符
                library_name = re.sub(r'\s+', '', library_name)  # 移除所有空白字符
                # 移除额外的标记字符（如果有的话）
                library_name = re.sub(r'図$', '', library_name)  # 移除末尾的"図"字符
                return library_name
        except Exception as e:
            self.logger.debug(f"提取图书馆名称失败: {str(e)}")

        return None

    def scrape(self, keyword: str) -> ScrapingResult:
        """
        重写scrape方法，添加延迟
        """
        # 添加请求延迟
        if hasattr(self, '_last_request_time'):
            elapsed = time.time() - self._last_request_time
            if elapsed < self.delay:
                time.sleep(self.delay - elapsed)

        result = super().scrape(keyword)
        self._last_request_time = time.time()

        return result