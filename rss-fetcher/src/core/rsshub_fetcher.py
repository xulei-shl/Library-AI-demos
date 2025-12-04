"""RSSHub 协议处理器

实现对 rsshub:// 协议的支持，将自定义协议转换为标准 HTTP URL 并获取 RSS 内容。
"""

import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote_plus, urljoin

from src.core.rss_fetcher import RSSFetcher
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RSSHubFetcher:
    """RSSHub 协议处理器，支持 rsshub:// 协议的 RSS 源获取"""
    
    # 多个 RSSHub 实例，支持备用机制
    RSSHUB_INSTANCES = [
        "https://rsshub.app",      # 官方实例
        "https://rsshub.smzdm.com", # 什么值得买镜像
        "https://rsshub.t1qx.com",  # 备用镜像1
        "https://rsshub.iowen.cn",  # 备用镜像2
    ]
    
    def __init__(self, user_agent: Optional[str] = None):
        """初始化 RSSHub fetcher
        
        Args:
            user_agent: 可选的用户代理字符串
        """
        self.user_agent = user_agent
        self.fallback_fetcher = RSSFetcher(user_agent)
    
    def is_rsshub_url(self, url: str) -> bool:
        """检查 URL 是否是 rsshub:// 协议
        
        Args:
            url: 要检查的 URL
            
        Returns:
            bool: 是否是 rsshub:// 协议
        """
        return url.startswith("rsshub://")
    
    def parse_rsshub_url(self, url: str) -> Dict[str, str]:
        """解析 rsshub:// 协议的 URL
        
        Args:
            url: rsshub:// 协议的 URL，如 rsshub://thepaper/list/25483
            
        Returns:
            dict: 解析结果，包含路由路径等信息
        """
        if not self.is_rsshub_url(url):
            raise ValueError(f"不是有效的 rsshub:// 协议 URL: {url}")
        
        # 移除协议前缀
        path_part = url[9:]  # len("rsshub://") = 9
        
        # 解析路由路径
        parts = path_part.split('/')
        if len(parts) < 2:
            raise ValueError(f"rsshub:// URL 格式不正确: {url}")
        
        service_name = parts[0]
        route_path = '/'.join(parts[1:])
        
        return {
            "service": service_name,
            "route": route_path,
            "full_path": path_part
        }
    
    def convert_to_http_url(self, rsshub_url: str, instance: Optional[str] = None) -> str:
        """将 rsshub:// URL 转换为实际的 HTTP URL
        
        Args:
            rsshub_url: rsshub:// 协议的 URL
            instance: RSSHub 实例地址，如果为 None 则使用第一个实例
            
        Returns:
            str: 转换后的 HTTP URL
        """
        parsed = self.parse_rsshub_url(rsshub_url)
        instance_url = instance or self.RSSHUB_INSTANCES[0]
        
        # 构建 HTTP URL
        # 确保实例 URL 以 / 结尾，然后添加路径
        if not instance_url.endswith('/'):
            instance_url += '/'
        
        http_url = urljoin(instance_url, parsed['full_path'])
        
        logger.debug(f"转换 rsshub:// URL: {rsshub_url} -> {http_url}")
        return http_url
    
    def fetch_rsshub_feed(
        self,
        rsshub_url: str,
        feed_config: Optional[Dict] = None,
        hours_lookback: int = 24,
        start_time: Optional = None,
        end_time: Optional = None,
    ) -> Optional[Dict]:
        """获取 RSSHub 订阅源的内容
        
        Args:
            rsshub_url: rsshub:// 协议的 URL
            feed_config: RSS 源配置（可选）
            hours_lookback: 回溯时间（小时）
            start_time: 可选起始时间
            end_time: 可选结束时间
            
        Returns:
            dict 或 None: 获取的文章列表或 None（如果失败）
        """
        if not self.is_rsshub_url(rsshub_url):
            logger.error(f"URL 不是有效的 rsshub:// 协议: {rsshub_url}")
            return None
        
        try:
            parsed = self.parse_rsshub_url(rsshub_url)
            logger.info(f"开始获取 RSSHub 订阅源: {parsed['service']}/{parsed['route']}")
        except Exception as e:
            logger.error(f"解析 rsshub:// URL 失败: {e}")
            return None
        
        # 准备 RSS 源配置
        name = feed_config.get("name", f"RSSHub-{parsed['service']}") if feed_config else f"RSSHub-{parsed['service']}"
        
        # 构建 URL 列表：主 RSSHub 实例 + 备用实例
        urls_to_try = []
        for instance in self.RSSHUB_INSTANCES:
            http_url = self.convert_to_http_url(rsshub_url, instance)
            urls_to_try.append({
                "name": f"{name} ({instance.replace('https://', '').replace('http://', '')})",
                "url": http_url,
                "backup_urls": []  # 在这里清空，因为我们已经准备了多个实例
            })
        
        # 使用现有的 RSS fetcher
        articles = self.fallback_fetcher.fetch_recent_articles(
            feeds=urls_to_try,
            hours_lookback=hours_lookback,
            start_time=start_time,
            end_time=end_time
        )
        
        if articles:
            logger.info(f"成功获取 {len(articles)} 篇来自 {rsshub_url} 的文章")
        else:
            logger.warning(f"未获取到来自 {rsshub_url} 的文章")
        
        return {
            "source": name,
            "original_url": rsshub_url,
            "articles": articles
        }
    
    def test_rsshub_url(self, rsshub_url: str, test_instance: Optional[str] = None) -> Tuple[bool, str, str]:
        """测试 rsshub:// URL 的可用性
        
        Args:
            rsshub_url: 要测试的 rsshub:// URL
            test_instance: 要测试的 RSSHub 实例（可选）
            
        Returns:
            Tuple[bool, str, str]: (是否成功, 状态信息, 实际使用的 URL)
        """
        if not self.is_rsshub_url(rsshub_url):
            return False, "不是有效的 rsshub:// 协议 URL", ""
        
        try:
            parsed = self.parse_rsshub_url(rsshub_url)
            test_url = self.convert_to_http_url(rsshub_url, test_instance)
            
            logger.info(f"测试 RSSHub URL: {rsshub_url}")
            logger.info(f"目标服务: {parsed['service']}")
            logger.info(f"路由路径: {parsed['route']}")
            logger.info(f"HTTP URL: {test_url}")
            
            # 简单测试：尝试获取一下看看是否可用
            import requests
            response = requests.get(test_url, timeout=10)
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                if 'xml' in content_type.lower() or 'rss' in content_type.lower():
                    return True, "RSS 源可用且返回 XML 内容", test_url
                else:
                    return False, f"返回的不是 RSS 内容 (Content-Type: {content_type})", test_url
            else:
                return False, f"HTTP 错误: {response.status_code}", test_url
                
        except Exception as e:
            error_msg = f"测试失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, ""
    
    def get_supported_services(self) -> List[str]:
        """获取支持的 RSSHub 服务列表（常见的）
        
        Returns:
            List[str]: 支持的服务列表
        """
        return [
            "thepaper",        # 澎湃新闻
            "weibo",          # 微博
            "zhihu",          # 知乎
            "bilibili",       # B站
            "juejin",         # 掘金
            "csdn",           # CSDN
            "jianshu",        # 简书
            "toutiao",        # 今日头条
            "tencent",        # 腾讯新闻
            "sina",           # 新浪
            "netease",        # 网易
            "sohu",           # 搜狐
            "iqiyi",          # 爱奇艺
            "youku",          # 优酷
            "youtube",        # YouTube
            "github",         # GitHub
            "gitlab",         # GitLab
            "stackoverflow",  # Stack Overflow
            "reddit",         # Reddit
            "medium",         # Medium
            "devto",          # DEV Community
            # 可以继续添加更多...
        ]