"""RSS 抓取模块"""

import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import feedparser
from dateutil import parser as date_parser

from src.utils.logger import get_logger

logger = get_logger(__name__)


class RSSFetcher:
    """负责从 RSS 源抓取并解析文章，支持重试和备用URL机制。"""

    def __init__(self, user_agent: Optional[str] = None):
        self.user_agent = user_agent or "Mozilla/5.0 (compatible; LibraryAI/1.0)"
        
    def _get_retry_config(self, feed_conf: Dict) -> Dict:
        """获取重试配置，默认值"""
        default_config = {
            "max_retries": 3,
            "retry_delay": 2,
            "timeout": 30
        }
        
        retry_config = feed_conf.get("retry_config", {})
        default_config.update(retry_config)
        return default_config
    
    def _fetch_with_retry(self, url: str, name: str, retry_config: Dict) -> Tuple[bool, Optional[feedparser.FeedParserDict], str]:
        """
        带重试机制的RSS获取
        
        Returns:
            Tuple[是否成功, feed对象, 错误信息]
        """
        max_retries = retry_config.get("max_retries", 3)
        retry_delay = retry_config.get("retry_delay", 2)
        timeout = retry_config.get("timeout", 30)
        
        last_error = ""
        
        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"尝试获取 RSS {name} (尝试 {attempt + 1}/{max_retries + 1}): {url}")
                
                # 使用 requests 获取内容，手动控制超时
                response = requests.get(
                    url, 
                    headers={"User-Agent": self.user_agent}, 
                    timeout=timeout
                )
                response.raise_for_status()
                
                # 使用 feedparser 解析内容
                feed = feedparser.parse(response.content)
                
                # 检查解析是否成功
                if feed.bozo:
                    # 如果只是格式警告但有entries，可能是可用的
                    if hasattr(feed, 'entries') and len(feed.entries) > 0:
                        logger.warning(f"RSS {name} 解析时有警告但有内容: {feed.bozo_exception}")
                        return True, feed, ""
                    else:
                        last_error = f"解析失败: {feed.bozo_exception}"
                        continue
                
                # 检查是否有内容
                if not hasattr(feed, 'entries') or len(feed.entries) == 0:
                    last_error = "RSS源没有返回任何文章内容"
                    if attempt < max_retries:
                        logger.warning(f"RSS {name} 无内容，准备重试 (等待 {retry_delay}秒)")
                        time.sleep(retry_delay)
                        continue
                    else:
                        return False, None, last_error
                
                logger.info(f"成功获取 RSS {name}: {len(feed.entries)} 篇文章")
                return True, feed, ""
                
            except requests.exceptions.Timeout:
                last_error = f"请求超时 ({timeout}秒)"
                logger.warning(f"RSS {name} 请求超时: {last_error}")
            except requests.exceptions.ConnectionError:
                last_error = "连接错误"
                logger.warning(f"RSS {name} 连接错误: {last_error}")
            except requests.exceptions.HTTPError as e:
                last_error = f"HTTP错误: {e.response.status_code}"
                logger.warning(f"RSS {name} HTTP错误: {last_error}")
            except Exception as e:
                last_error = f"未知错误: {str(e)}"
                logger.warning(f"RSS {name} 发生错误: {last_error}")
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries:
                logger.info(f"RSS {name} 失败，准备重试 (等待 {retry_delay}秒)")
                time.sleep(retry_delay)
        
        return False, None, last_error

    def fetch_recent_articles(
        self,
        feeds: List[Dict[str, str]],
        hours_lookback: int = 24,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        获取指定时间范围内的文章。

        Args:
            feeds: RSS源列表，每个元素包含 'name' 和 'url'。
            hours_lookback: 回溯时间（小时）。
            start_time: 可选起始时间，若提供则优先使用。
            end_time: 可选结束时间，若提供则优先使用。

        Returns:
            文章列表，每篇文章是一个字典。
        """
        articles = []
        cutoff_time = None
        if not start_time and not end_time:
            cutoff_time = datetime.now() - timedelta(hours=hours_lookback)
        # 转换为 UTC 时间戳以便比较 (feedparser 解析的时间通常是 struct_time)
        # 这里简化处理，统一转换为 datetime 对象比较

        for feed_conf in feeds:
            if not feed_conf.get("enabled", True):
                continue

            name = feed_conf.get("name", "Unknown")
            url = feed_conf.get("url")
            
            if not url:
                logger.warning(f"RSS源 {name} 未配置 URL，跳过。")
                continue

            logger.info(f"正在抓取 RSS: {name}")
            
            # 获取重试配置
            retry_config = self._get_retry_config(feed_conf)
            
            # 构建URL列表：主URL + 备用URL
            urls_to_try = [url]
            backup_urls = feed_conf.get("backup_urls", [])
            if backup_urls:
                urls_to_try.extend(backup_urls)
            
            feed = None
            used_url = None
            success = False
            error_messages = []
            
            # 尝试所有URL
            for try_url in urls_to_try:
                logger.info(f"  -> 尝试 URL: {try_url}")
                
                success, parsed_feed, error_msg = self._fetch_with_retry(try_url, name, retry_config)
                
                if success and parsed_feed:
                    feed = parsed_feed
                    used_url = try_url
                    break
                else:
                    error_messages.append(f"{try_url}: {error_msg}")
                    if try_url != urls_to_try[-1]:  # 不是最后一个URL
                        logger.info(f"  -> 尝试下一个备用URL...")
            
            if not success:
                logger.error(f"RSS {name} 所有URL都失败: {'; '.join(error_messages)}")
                continue
            
            # 处理成功获取的feed
            if used_url != url:
                logger.info(f"RSS {name} 使用备用URL成功: {used_url}")
            
            try:
                # 处理解析警告
                if feed.bozo:
                    logger.warning(f"解析 RSS {name} 时遇到潜在问题: {feed.bozo_exception}")

                for entry in feed.entries:
                    published_dt = self._parse_date(entry)

                    if not published_dt:
                        # 如果无法解析时间，默认保留（或者可以选择丢弃）
                        # 这里选择保留，但记录日志
                        logger.debug(f"无法解析文章时间: {entry.get('title', 'No Title')}, 默认保留。")
                        published_dt = datetime.now() # 作为一个 fallback，或者设为 None

                    # 如果时间有效且在范围内
                    if published_dt and self._is_within_range(
                        published_dt, cutoff_time, start_time, end_time
                    ):
                        article = {
                            "source": name,
                            "title": entry.get("title", ""),
                            "link": entry.get("link", ""),
                            "published_date": published_dt.strftime("%Y-%m-%d %H:%M:%S"),
                            "fetch_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "summary": self._clean_summary(entry),
                            "content": self._get_content(entry)
                        }
                        articles.append(article)
                        
            except Exception as e:
                logger.error(f"处理 RSS {name} 数据时失败: {e}")
                continue

        if start_time or end_time:
            logger.info(
                f"共抓取到 {len(articles)} 篇指定时间范围内的文章："
                f"{start_time or '-'} -> {end_time or '-'}。"
            )
        else:
            logger.info(f"共抓取到 {len(articles)} 篇 {hours_lookback} 小时内的文章。")
        return articles

    def _parse_date(self, entry) -> Optional[datetime]:
        """尝试解析发布时间，统一转换为本地时间。"""
        import pytz
        
        # 获取时区信息
        local_tz = pytz.timezone('Asia/Shanghai')  # 本地时区
        
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            # feedparser 解析的 struct_time 可能是本地时间或UTC时间
            dt = datetime.fromtimestamp(time.mktime(entry.published_parsed))
            # 如果没有明确的时区信息，假设是UTC然后转换到本地
            dt_utc = pytz.utc.localize(dt)
            return dt_utc.astimezone(local_tz).replace(tzinfo=None)
        
        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            dt = datetime.fromtimestamp(time.mktime(entry.updated_parsed))
            dt_utc = pytz.utc.localize(dt)
            return dt_utc.astimezone(local_tz).replace(tzinfo=None)
            
        # 尝试解析字符串格式
        date_str = entry.get("published") or entry.get("updated")
        if date_str:
            try:
                parsed_dt = date_parser.parse(date_str, fuzzy=True)
                # 如果解析出的时间有时区信息，转换到本地时间
                if parsed_dt.tzinfo:
                    return parsed_dt.astimezone(local_tz).replace(tzinfo=None)
                else:
                    # 如果没有时区信息，假设是UTC然后转换到本地
                    dt_utc = pytz.utc.localize(parsed_dt)
                    return dt_utc.astimezone(local_tz).replace(tzinfo=None)
            except Exception:
                pass
        
        return None

    def _clean_summary(self, entry) -> str:
        """清理摘要（移除HTML标签等，这里暂时简单返回）。"""
        summary = entry.get("summary", "")
        # TODO: 可以添加 HTML 清理逻辑，如 BeautifulSoup
        return summary

    def _get_content(self, entry) -> str:
        """获取正文内容，优先使用 content，其次使用 summary。"""
        if hasattr(entry, "content"):
            # content 是一个 list
            return "\n".join([c.value for c in entry.content])
        return entry.get("summary", "")

    def _is_within_range(
        self,
        published_dt: datetime,
        cutoff_time: Optional[datetime],
        start_time: Optional[datetime],
        end_time: Optional[datetime],
    ) -> bool:
        """判断文章时间是否落在指定范围内。"""
        if start_time and published_dt < start_time:
            return False
        if end_time and published_dt > end_time:
            return False
        if cutoff_time and published_dt < cutoff_time:
            return False
        return True
