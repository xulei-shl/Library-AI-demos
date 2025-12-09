"""
示例：其他网站爬虫
展示如何扩展新的网站爬虫
"""
from typing import Optional, List, Dict, Any
from src.core.base_scraper import BaseScraper


class ExampleOtherScraper(BaseScraper):
    """
    示例其他网站爬虫

    这是一个示例，展示如何为新的网站创建爬虫。
    您需要根据目标网站的具体情况实现以下方法。
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        # 设置网站特定的配置
        self.base_url = "https://example-other-site.com"  # 替换为实际网站
        self.search_url_template = "https://example-other-site.com/search?q={}"

    def build_search_url(self, keyword: str) -> str:
        """
        根据关键词构建搜索URL
        Args:
            keyword: 搜索关键词
        Returns:
            完整的搜索URL
        """
        import urllib.parse
        encoded_keyword = urllib.parse.quote(keyword)
        return self.search_url_template.format(encoded_keyword)

    def search_books(self, keyword: str) -> Optional[str]:
        """
        搜索图书，获取第一个结果的详情页URL
        Args:
            keyword: 搜索关键词
        Returns:
            详情页URL，如果没有结果返回None
        """
        import requests
        from bs4 import BeautifulSoup

        search_url = self.build_search_url(keyword)

        try:
            # 发送HTTP请求
            response = requests.get(
                search_url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                timeout=30
            )
            response.raise_for_status()

            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # 检查是否有搜索结果
            # 需要根据目标网站的HTML结构调整选择器
            no_results = soup.find('div', class_='no-results')  # 示例选择器
            if no_results:
                self.logger.info(f"关键词 '{keyword}' 没有搜索结果")
                return None

            # 获取第一个结果的链接
            # 需要根据目标网站的HTML结构调整选择器
            first_result = soup.find('div', class_='search-result')
            if first_result:
                link = first_result.find('a')
                if link:
                    detail_url = link.get('href')
                    if detail_url:
                        # 确保URL是完整的
                        if not detail_url.startswith('http'):
                            detail_url = self.base_url + detail_url
                        return detail_url

        except requests.RequestException as e:
            self.logger.error(f"搜索请求失败: {str(e)}")
        except Exception as e:
            self.logger.error(f"解析搜索结果失败: {str(e)}")

        return None

    def get_libraries(self, detail_url: str) -> List[str]:
        """
        获取馆藏图书馆信息
        Args:
            detail_url: 图书详情页URL
        Returns:
            图书馆名称列表
        """
        import requests
        from bs4 import BeautifulSoup

        try:
            response = requests.get(
                detail_url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                timeout=30
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            libraries = []

            # 查找图书馆信息
            # 需要根据目标网站的HTML结构调整选择器
            library_items = soup.find_all('div', class_='library-item')  # 示例选择器

            for item in library_items:
                # 提取图书馆名称
                library_name = item.get_text().strip()
                if library_name and library_name not in libraries:
                    libraries.append(library_name)

            self.logger.info(f"从详情页获取到 {len(libraries)} 个图书馆信息")
            return libraries

        except requests.RequestException as e:
            self.logger.error(f"获取详情页失败: {str(e)}")
        except Exception as e:
            self.logger.error(f"解析详情页失败: {str(e)}")

        return []


# 使用示例
def create_example_scraper():
    """创建示例爬虫实例"""
    config = {
        'timeout': 30,
        'delay': 2,
        'max_retries': 3
    }
    return ExampleOtherScraper(config)


# 在主程序中如何添加新爬虫的示例
def extend_main_program():
    """
    展示如何在主程序中添加新爬虫
    这是main.py中需要修改的部分示例
    """

    # 1. 导入新爬虫
    # from src.scrapers.example_other_scraper import ExampleOtherScraper

    # 2. 在BookScraperApp类中修改setup_scraper方法
    def setup_scraper_with_multiple_sites(self):
        """设置多个爬虫实例"""
        self.scrapers = {
            'cinii': CiNiiScraper(self.config.get('cinii', {})),
            'other_site': ExampleOtherScraper(self.config.get('other_site', {}))
        }

        # 当前使用的爬虫
        self.current_scraper = self.scrapers['cinii']  # 或 'other_site'

    # 3. 修改处理逻辑，支持多站点爬取
    def process_excel_multiple_sites(self, excel_path, **kwargs):
        """处理Excel文件，支持多站点爬取"""
        # ... 其他代码 ...

        # 对每个站点进行爬取
        all_libraries = []
        for site_name, scraper in self.scrapers.items():
            result = scraper.scrape(keyword_value)
            if result.success:
                # 合并结果，避免重复
                for library in result.libraries:
                    if library not in all_libraries:
                        all_libraries.append(library)

        # ... 处理合并后的结果 ...

    # 4. 添加配置选项
    multi_site_config = {
        'sites': ['cinii', 'other_site'],  # 要使用的站点列表
        'cinii': { ... },  # CiNii配置
        'other_site': { ... }  # 其他站点配置
    }