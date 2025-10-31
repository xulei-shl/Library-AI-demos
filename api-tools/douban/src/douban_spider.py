"""
豆瓣图书信息爬取脚本（重构版）
功能：1. 通过ISBN搜索获取图书链接
      2. 从图书详情页提取详细信息
      3. 保存到Excel文件

重构说明：
- 将原有的大文件分解为多个模块
- 保持爬取逻辑完全不变
- 提高代码可维护性和可读性

依赖：
- playwright
- beautifulsoup4
- openpyxl
- pandas

模块说明：
- base_spider: 基础浏览器管理
- login_handler: 登录处理
- search_handler: 搜索功能
- detail_extractor: 详情页提取
- data_manager: 数据管理
"""

import logging
from typing import List
from base_spider import BaseSpider
from login_handler import LoginHandler
from search_handler import SearchHandler
from detail_extractor import DetailExtractor
from data_manager import DataManager

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DoubanBookSpider:
    """豆瓣图书爬虫（重构版）"""
    
    def __init__(self, headless: bool = False):
        """
        初始化豆瓣图书爬虫
        
        Args:
            headless: 是否使用无头模式
        """
        # 初始化各个模块
        self.base_spider = BaseSpider(headless)
        self.data_manager = DataManager()
        
        # 这些模块需要等浏览器启动后才能初始化
        self.login_handler = None
        self.search_handler = None
        self.detail_extractor = None
        
        # 添加登录状态管理
        self.login_completed = False  # 标记是否已完成登录
        self.login_attempted = False  # 标记是否已尝试过登录
        
    def start_driver(self):
        """启动浏览器和初始化模块"""
        try:
            # 启动基础浏览器
            self.base_spider.start_driver()
            
            # 获取页面对象
            page = self.base_spider.get_page()
            
            # 初始化其他处理器（需要页面对象）
            self.login_handler = LoginHandler(page, self.base_spider.headless)
            self.search_handler = SearchHandler(page, self.base_spider._random_delay, self.login_handler)
            self.detail_extractor = DetailExtractor(page, self.base_spider._random_delay, self.login_handler)
            
            logger.info("所有模块初始化完成")
            
        except Exception as e:
            logger.error(f"启动失败: {e}")
            raise
    
    def close_driver(self):
        """关闭浏览器"""
        self.base_spider.close_driver()
        logger.info("浏览器已关闭")
    
    def search_by_isbn(self, isbn: str) -> str:
        """
        通过ISBN搜索图书并获取详情页链接
        
        Args:
            isbn: ISBN号码
            
        Returns:
            图书详情页链接，如果未找到则返回None
        """
        if not self.search_handler:
            raise Exception("搜索引擎未初始化，请先调用start_driver()")
        
        return self.search_handler.search_by_isbn(isbn)
    
    def extract_book_details(self, book_url: str) -> dict:
        """
        从图书详情页提取详细信息
        
        Args:
            book_url: 图书详情页URL
            
        Returns:
            包含图书信息的字典
        """
        if not self.detail_extractor:
            raise Exception("详情提取器未初始化，请先调用start_driver()")
        
        return self.detail_extractor.extract_book_details(book_url)
    
    def save_to_excel(self, filename: str = "豆瓣图书信息.xlsx"):
        """
        保存图书信息到Excel文件
        
        Args:
            filename: Excel文件名
        """
        self.data_manager.save_to_excel(filename)
    
    def crawl_books(self, isbns: List[str], output_file: str = "豆瓣图书信息.xlsx"):
        """
        爬取多个ISBN对应的图书信息（改进版：只在第一次处理时登录）
        
        Args:
            isbns: ISBN列表
            output_file: 输出文件名
        """
        try:
            # 启动浏览器和初始化模块
            self.start_driver()
            # 清空之前的数据
            self.data_manager.clear_data()
            
            # 重置登录状态
            self.login_completed = False
            self.login_attempted = False
            
            for i, isbn in enumerate(isbns):
                logger.info(f"开始处理第 {i+1}/{len(isbns)} 个ISBN: {isbn}")
                
                try:
                    # 第一次处理ISBN时，执行登录逻辑
                    if i == 0:
                        logger.info("第一个ISBN，访问首页并处理登录逻辑...")
                        # 访问首页来触发登录检查和可能的登录流程
                        self._handle_initial_login()
                    
                    # 第一步：搜索ISBN获取链接
                    book_url = self.search_by_isbn(isbn)
                    
                    if book_url:
                        # 第二步：提取图书详情
                        book_info = self.extract_book_details(book_url)
                        if book_info:
                            self.data_manager.add_book_info(book_info)
                            logger.info(f"成功获取 {isbn} 的图书信息")
                        else:
                            logger.warning(f"无法获取 {isbn} 的图书详情")
                    else:
                        logger.warning(f"无法找到 {isbn} 对应的图书链接")
                
                except Exception as e:
                    logger.error(f"处理ISBN {isbn} 时发生错误: {e}")
                    continue
                
                # 添加延迟，避免被反爬虫机制检测
                if i < len(isbns) - 1:  # 最后一次不需要延迟
                    self.base_spider._random_delay()
            
            # 保存到Excel
            self.save_to_excel(output_file)
            
        finally:
            # 确保浏览器被关闭
            self.close_driver()
    
    def _handle_initial_login(self):
        """
        处理初始登录逻辑，只在第一个ISBN时执行
        """
        try:
            # 访问豆瓣图书首页来触发登录检查
            page = self.base_spider.get_page()
            page.goto("https://book.douban.com", wait_until="networkidle", timeout=30000)
            
            # 检查是否需要登录
            if self.login_handler.check_login_page(page_type="normal"):
                logger.warning("检测到需要登录，开始登录流程...")
                self._perform_login()
            else:
                logger.info("无需登录，继续正常流程")
                self.login_completed = True
            
            # 同步登录状态到 search_handler
            if self.search_handler:
                self.search_handler.login_attempted = self.login_attempted
                if self.login_completed:
                    self.search_handler.login_completed = True
                logger.info(f"登录状态已同步到 search_handler: login_attempted={self.login_attempted}, login_completed={self.login_completed}")
            
        except Exception as e:
            logger.error(f"处理初始登录时发生错误: {e}")
            # 即使登录处理失败，也不影响后续的正常搜索流程
    
    def _perform_login(self):
        """
        执行登录流程
        """
        try:
            if not self.login_handler.headless:
                # 尝试自动登录
                if self.login_handler.auto_login():
                    logger.info("自动登录成功")
                    self.login_completed = True
                    self.login_attempted = True
                    # 立即同步状态到 search_handler
                    self._sync_login_state()
                    return
                else:
                    logger.warning("自动登录失败，等待手动登录...")
            
            # 等待手动登录
            if self.login_handler.wait_for_manual_login():
                logger.info("用户手动登录成功")
                self.login_completed = True
                self.login_attempted = True
                # 立即同步状态到 search_handler
                self._sync_login_state()
            else:
                logger.warning("登录被跳过或失败")
                self.login_attempted = True
                # 即使登录失败，也要继续执行搜索流程，可能豆瓣不强制登录
                # 同步状态
                self._sync_login_state()
                
        except Exception as e:
            logger.error(f"登录过程中发生错误: {e}")
            self.login_attempted = True
            # 同步状态
            self._sync_login_state()
    
    def _sync_login_state(self):
        """同步登录状态到所有相关模块"""
        if self.search_handler:
            self.search_handler.login_attempted = self.login_attempted
            if self.login_completed:
                self.search_handler.login_completed = True
            logger.info(f"登录状态已同步到 search_handler: login_attempted={self.login_attempted}, login_completed={self.login_completed}")
            
        if self.detail_extractor:
            self.detail_extractor.login_attempted = self.login_attempted
            if self.login_completed:
                self.detail_extractor.login_completed = True
            logger.info(f"登录状态已同步到 detail_extractor: login_attempted={self.login_attempted}, login_completed={self.login_completed}")


# 示例使用函数
def main():
    """主函数 - 示例用法"""
    
    # 要搜索的ISBN列表
    isbns = [
        "9787567577466",
        # "9787305280818",
        # "9787522802435",
        # "9787100217811",
        # 添加更多ISBN...
    ]
    
    # 创建爬虫实例
    spider = DoubanBookSpider(headless=False)  # 设置为False可以看到浏览器操作过程
    
    # 开始爬取
    spider.crawl_books(isbns, "豆瓣图书信息.xlsx")
    
    print("爬取完成！")


if __name__ == "__main__":
    main()