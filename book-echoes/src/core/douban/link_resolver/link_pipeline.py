#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ISBN -> 豆瓣链接解析流水线."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd

from src.utils.logger import get_logger
from .exceptions import LinkResolveError
from .isbn_searcher import DoubanIsbnSearcher, LinkSearchResult
from .login_session import DoubanLoginSession

logger = get_logger(__name__)


@dataclass
class LinkResolveTask:
    index: int
    isbn: str
    barcode: str = ""
    existing_url: str = ""


class DoubanLinkResolver:
    def __init__(
        self,
        crawler_config: Dict,
        progress_manager,
        url_column: str,
        rating_column: Optional[str] = None,
        rating_count_column: Optional[str] = None,
    ) -> None:
        self._session = DoubanLoginSession(crawler_config)
        retry_times = crawler_config.get("retry_times", 3)
        search_delay = crawler_config.get("search_delay", 1.2)
        self._searcher = DoubanIsbnSearcher(
            session=self._session,
            retry_times=retry_times,
            search_delay=search_delay,
        )
        self._progress = progress_manager
        self._url_column = url_column
        self._rating_column = rating_column
        self._rating_count_column = rating_count_column

    async def resolve(self, df: pd.DataFrame, tasks: List[LinkResolveTask]) -> Dict[str, int]:
        stats = {"total": len(tasks), "success": 0, "no_data": 0, "failed": 0}
        for idx, task in enumerate(tasks, 1):
            if not task.isbn:
                logger.debug("跳过空 ISBN - row=%s", task.index)
                continue
            try:
                result = await self._searcher.search(task.isbn)
            except LinkResolveError as exc:
                stats["failed"] += 1
                logger.error("链接解析失败 - row=%s isbn=%s err=%s", task.index, task.isbn, exc)
                continue

            self._apply_result(df, task, result)
            if result.status == "SUCCESS":
                stats["success"] += 1
            elif result.status == "NO_DATA":
                stats["no_data"] += 1
            else:
                stats["failed"] += 1

            if idx % 5 == 0:
                self._progress.save_partial(df, reason="link_stage")

        await self._session.close()
        return stats

    def _apply_result(self, df: pd.DataFrame, task: LinkResolveTask, result: LinkSearchResult) -> None:
        if result.status == "SUCCESS" and result.douban_url:
            df.at[task.index, self._url_column] = result.douban_url
            if self._rating_column and self._rating_column in df.columns and result.rating:
                df.at[task.index, self._rating_column] = result.rating
            if self._rating_count_column and self._rating_count_column in df.columns and (result.rating_count is not None):
                df.at[task.index, self._rating_count_column] = result.rating_count
            self._progress.mark_link_ready(df, task.index)
            self._progress.append_source(df, task.index, "LINK")
        elif result.status == "NO_DATA":
            self._progress.mark_done(df, task.index)
        else:
            self._progress.mark_link_pending(df, task.index)
