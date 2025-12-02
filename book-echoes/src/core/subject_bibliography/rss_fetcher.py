"""RSS 抓取模块"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import feedparser
from dateutil import parser as date_parser

from src.utils.logger import get_logger

logger = get_logger(__name__)


class RSSFetcher:
    """负责从 RSS 源抓取并解析文章。"""

    def __init__(self, user_agent: Optional[str] = None):
        self.user_agent = user_agent or "Mozilla/5.0 (compatible; LibraryAI/1.0)"

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

            logger.info(f"正在抓取 RSS: {name} ({url})")
            
            try:
                # feedparser.parse 可以处理 URL
                feed = feedparser.parse(url, agent=self.user_agent)
                
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
                logger.error(f"抓取 RSS {name} 失败: {e}")

        if start_time or end_time:
            logger.info(
                f"共抓取到 {len(articles)} 篇指定时间范围内的文章："
                f"{start_time or '-'} -> {end_time or '-'}。"
            )
        else:
            logger.info(f"共抓取到 {len(articles)} 篇 {hours_lookback} 小时内的文章。")
        return articles

    def _parse_date(self, entry) -> Optional[datetime]:
        """尝试解析发布时间。"""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            return datetime.fromtimestamp(time.mktime(entry.published_parsed))
        
        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            return datetime.fromtimestamp(time.mktime(entry.updated_parsed))
            
        # 尝试解析字符串格式
        date_str = entry.get("published") or entry.get("updated")
        if date_str:
            try:
                return date_parser.parse(date_str, fuzzy=True).replace(tzinfo=None)
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
