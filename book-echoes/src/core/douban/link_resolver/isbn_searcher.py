#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""基于 Playwright 的 ISBN -> 豆瓣链接解析."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from src.utils.logger import get_logger
from .exceptions import LinkResolveError
from .login_session import DoubanLoginSession

logger = get_logger(__name__)


@dataclass
class LinkSearchResult:
    isbn: str
    douban_url: Optional[str]
    status: str
    message: str = ""
    rating: Optional[str] = None
    rating_count: Optional[int] = None


class DoubanIsbnSearcher:
    def __init__(
        self,
        session: DoubanLoginSession,
        retry_times: int = 3,
        search_delay: float = 1.2,
    ) -> None:
        self._session = session
        self.retry_times = max(1, retry_times)
        self.search_delay = max(search_delay, 0.0)

    async def search(self, isbn: str) -> LinkSearchResult:
        if not isbn:
            raise ValueError("ISBN 不能为空")

        for attempt in range(1, self.retry_times + 1):
            try:
                await asyncio.sleep(self.search_delay)
                link = await self._session.resolve_link(isbn)
                if link == "NO_DATA":
                    last_rating, last_count = (None, None)
                    if hasattr(self._session, "crawler"):
                        try:
                            last_rating, last_count = await self._session.crawler.extract_rating_from_current_page()
                        except Exception:
                            last_rating, last_count = (None, None)
                    return LinkSearchResult(
                        isbn=isbn,
                        douban_url=None,
                        status="NO_DATA",
                        rating=last_rating,
                        rating_count=last_count,
                    )
                if link:
                    last_rating, last_count = (None, None)
                    if hasattr(self._session, "crawler"):
                        try:
                            last_rating, last_count = await self._session.crawler.extract_rating_from_current_page()
                        except Exception:
                            last_rating, last_count = (None, None)
                    return LinkSearchResult(
                        isbn=isbn,
                        douban_url=link,
                        status="SUCCESS",
                        rating=last_rating,
                        rating_count=last_count,
                    )
                logger.warning("未解析到豆瓣链接 - isbn=%s attempt=%s", isbn, attempt)
            except Exception as exc:  # noqa: BLE001
                logger.error("ISBN 链接解析失败 - isbn=%s attempt=%s err=%s", isbn, attempt, exc)
                if attempt >= self.retry_times:
                    raise LinkResolveError(f"解析 {isbn} 失败") from exc
                await self._session.close()
                await asyncio.sleep(attempt)

        raise LinkResolveError(f"解析 {isbn} 失败")
