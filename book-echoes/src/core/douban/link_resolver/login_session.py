#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""豆瓣登录会话管理."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from src.core.douban.browser_recovery import BrowserRecoveryMixin
from src.core.douban.link_resolver.douban_crawler_adapter import DoubanCrawlerAdapter
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DoubanLoginSession(BrowserRecoveryMixin):
    """薄封装的 Playwright 会话管理，负责启动/关闭浏览器."""

    def __init__(self, crawler_config: Dict[str, Any]):
        super().__init__(max_restarts=crawler_config.get("max_restarts", 3))
        self._crawler = DoubanCrawlerAdapter(crawler_config)
        self._headless = crawler_config.get("headless", False)
        self._ready = False
        self._lock = asyncio.Lock()

    async def ensure_started(self) -> None:
        if self._ready:
            return
        async with self._lock:
            if self._ready:
                return
            await self._crawler.init_browser_with_config(headless=self._headless)
            self._ready = True
            logger.info("豆瓣浏览器会话已启动")

    async def close(self) -> None:
        if not self._ready:
            return
        await self._crawler.close_browser()
        self._ready = False

    async def resolve_link(self, isbn: str) -> Optional[str]:
        await self.ensure_started()
        return await self._crawler.resolve_book_url(isbn)

    @property
    def crawler(self) -> DoubanCrawlerAdapter:
        return self._crawler
