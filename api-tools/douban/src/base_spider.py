"""
基础浏览器管理模块
负责启动、关闭浏览器，以及随机延迟等基础功能
"""

import time
import random
import logging
from typing import Optional
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BaseSpider:
    """基础爬虫类，负责浏览器管理和基础功能"""
    
    def __init__(self, headless: bool = False):
        """
        初始化基础爬虫
        
        Args:
            headless: 是否使用无头模式
        """
        self.base_url = "https://book.douban.com"
        self.search_url = "https://search.douban.com/book/subject_search"
        self.playwright = None
        self.browser = None
        self.page = None
        self.headless = headless
        
        # 随机延迟配置（根据页面类型优化）
        self.min_delay = 1  # 搜索页面最小延迟
        self.max_delay = 3  # 搜索页面最大延迟
        self.detail_min_delay = 3  # 详情页面最小延迟
        self.detail_max_delay = 6  # 详情页面最大延迟
        
        # User-Agent池
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
    def start_driver(self):
        """启动浏览器"""
        try:
            self.playwright = sync_playwright().start()
            # 启动浏览器
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--window-size=1920,1080',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection',
                    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ]
            )
            # 创建页面
            self.page = self.browser.new_page()
            
            # 添加初始化脚本伪装浏览器指纹
            self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en'],
                });
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({
                        query: () => Promise.resolve({ state: 'granted' })
                    }),
                });
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 8,
                });
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 8,
                });
                Object.defineProperty(screen, 'width', {
                    get: () => 1920,
                });
                Object.defineProperty(screen, 'height', {
                    get: () => 1080,
                });
            """)
            
            # 设置更真实的请求头
            self.page.set_extra_http_headers({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"'
            })
            # 设置超时
            self.page.set_default_timeout(30000)  # 30秒超时
            
            logger.info("浏览器启动成功")
        except Exception as e:
            logger.error(f"启动浏览器失败: {e}")
            logger.error("请确保：")
            logger.error("1. 已安装requirements.txt中的依赖包")
            logger.error("2. 已安装playwright浏览器驱动（运行：playwright install）")
            logger.error("3. 网络连接正常")
            raise
    
    def close_driver(self):
        """关闭浏览器"""
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            logger.info("浏览器已关闭")
        except Exception as e:
            logger.error(f"关闭浏览器时发生错误: {e}")
    
    def _random_delay(self, page_type: str = "search"):
        """
        根据页面类型进行随机延迟
        
        Args:
            page_type: 页面类型 ('search', 'detail', 'normal')
        """
        if page_type == "detail":
            delay = random.uniform(self.detail_min_delay, self.detail_max_delay)
        else:
            delay = random.uniform(self.min_delay, self.max_delay)
        
        logger.info(f"等待 {delay:.1f} 秒...")
        time.sleep(delay)
    
    def get_page(self):
        """获取页面对象"""
        return self.page
    
    def is_browser_started(self):
        """检查浏览器是否已启动"""
        return self.page is not None