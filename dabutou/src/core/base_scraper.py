"""
爬虫基类
定义所有网站爬虫必须实现的接口
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass


@dataclass
class ScrapingResult:
    """爬取结果数据类"""
    success: bool
    keyword: str
    libraries: List[str]
    error_message: Optional[str] = None
    search_url: Optional[str] = None
    detail_url: Optional[str] = None


class BaseScraper(ABC):
    """爬虫基类"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def build_search_url(self, keyword: str) -> str:
        """
        根据关键词构建搜索URL
        Args:
            keyword: 搜索关键词
        Returns:
            完整的搜索URL
        """
        pass

    @abstractmethod
    def search_books(self, keyword: str) -> Optional[str]:
        """
        搜索图书，获取第一个结果的详情页URL
        Args:
            keyword: 搜索关键词
        Returns:
            详情页URL，如果没有结果返回None
        """
        pass

    @abstractmethod
    def get_libraries(self, detail_url: str) -> List[str]:
        """
        获取馆藏图书馆信息
        Args:
            detail_url: 图书详情页URL
        Returns:
            图书馆名称列表
        """
        pass

    def scrape(self, keyword: str) -> ScrapingResult:
        """
        完整的爬取流程
        Args:
            keyword: 搜索关键词
        Returns:
            ScrapingResult对象
        """
        try:
            self.logger.info(f"开始爬取关键词: {keyword}")

            # 构建搜索URL
            search_url = self.build_search_url(keyword)
            self.logger.debug(f"搜索URL: {search_url}")

            # 搜索图书
            detail_url = self.search_books(keyword)
            if not detail_url:
                self.logger.info(f"未找到关键词 '{keyword}' 对应的图书")
                return ScrapingResult(
                    success=False,
                    keyword=keyword,
                    libraries=[],
                    error_message="未找到相关图书",
                    search_url=search_url
                )

            # 获取图书馆信息
            libraries = self.get_libraries(detail_url)

            self.logger.info(f"成功获取 {len(libraries)} 个图书馆信息")

            return ScrapingResult(
                success=True,
                keyword=keyword,
                libraries=libraries,
                search_url=search_url,
                detail_url=detail_url
            )

        except Exception as e:
            self.logger.error(f"爬取关键词 '{keyword}' 时发生错误: {str(e)}")
            return ScrapingResult(
                success=False,
                keyword=keyword,
                libraries=[],
                error_message=str(e)
            )