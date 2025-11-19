#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""豆瓣链接阶段流水线."""

from __future__ import annotations

import asyncio
from typing import Dict

from .base import PipelineStep, StageContext
from src.core.douban.link_resolver.link_pipeline import (
    DoubanLinkResolver,
    LinkResolveTask,
)


class DoubanLinkStep(PipelineStep):
    name = "link_resolver"

    def __init__(self, row_filter=None):
        self.row_filter = row_filter

    def run(self, context: StageContext) -> Dict[str, int]:
        df = context.df
        progress = context.progress_manager

        # 如果传入了行过滤器，直接按过滤器选择任务行
        if self.row_filter is not None:
            filtered_indices = [idx for idx in df.index if self.row_filter(df, idx)]
            if not filtered_indices:
                return {"total": 0, "success": 0, "no_data": 0, "failed": 0}
            # 基于过滤行构造 tasks
            tasks = []
            for index in filtered_indices:
                isbn_value = str(df.at[index, context.isbn_column] or "").strip()
                if not isbn_value:
                    continue
                tasks.append(LinkResolveTask(
                    index=index,
                    isbn=isbn_value,
                    barcode=str(df.at[index, context.barcode_column] or ""),
                    existing_url=str(df.at[index, context.link_column] or "").strip(),
                ))
            crawler_conf = (context.douban_config.get("douban_crawler") or {}).copy()
            crawler_conf["headless"] = crawler_conf.get("headless", False)
            crawler_conf["delay"] = crawler_conf.get("delay", 1.0)
            crawler_conf["search_delay"] = 1.2
            crawler_conf["retry_times"] = crawler_conf.get("retry_times", 3)
            crawler_conf["max_restarts"] = crawler_conf.get("max_restarts", 3)
            url_column = context.link_column
            rating_column = context.get_field("rating")
            rating_count_column = context.get_field("rating_count")
            resolver = DoubanLinkResolver(
                crawler_config=crawler_conf,
                progress_manager=progress,
                url_column=url_column,
                rating_column=rating_column,
                rating_count_column=rating_count_column,
            )
            stats = asyncio.run(resolver.resolve(df, tasks))
            progress.save_partial(df, force=True, reason="link_resolver_final")
            return stats

        link_conf = context.douban_config.get("link_resolver", {}) or {}
        crawler_conf = (context.douban_config.get("douban_crawler") or {}).copy()
        crawler_conf["headless"] = link_conf.get("headless", crawler_conf.get("headless", False))
        crawler_conf["delay"] = link_conf.get("delay", crawler_conf.get("delay", 1.0))
        crawler_conf["search_delay"] = link_conf.get("search_delay", 1.2)
        crawler_conf["retry_times"] = link_conf.get("retry_times", 3)
        crawler_conf["max_restarts"] = link_conf.get("max_restarts", 3)
        url_column = context.link_column or context.get_field("url")
        rating_column = context.get_field("rating")
        rating_count_column = context.get_field("rating_count")
        tasks = []
        for index, row in df.iterrows():
            if not progress.needs_link(df, index):
                continue
            existing_url = str(row.get(url_column, "") or "").strip()
            if existing_url:
                progress.mark_link_ready(df, index)
                continue
            isbn_value = str(row.get(context.isbn_column, "") or "").strip()
            if not isbn_value:
                continue
            tasks.append(
                LinkResolveTask(
                    index=index,
                    isbn=isbn_value,
                    barcode=str(row.get(context.barcode_column, "") or ""),
                    existing_url=existing_url,
                )
            )

        if not tasks:
            return {"total": 0, "success": 0, "no_data": 0, "failed": 0}

        resolver = DoubanLinkResolver(
            crawler_config=crawler_conf,
            progress_manager=progress,
            url_column=url_column,
            rating_column=rating_column,
            rating_count_column=rating_count_column,
        )
        stats = asyncio.run(resolver.resolve(df, tasks))
        progress.save_partial(df, force=True, reason="link_resolver_final")
        return stats
