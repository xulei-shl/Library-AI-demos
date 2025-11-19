#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""豆瓣 Subject API 阶段."""

from __future__ import annotations

import asyncio
from typing import Dict, List, Tuple

from src.core.douban.api.subject_client import SubjectApiClient
from src.core.douban.api.subject_mapper import extract_subject_id, map_subject_payload
from src.utils.logger import get_logger
from .base import PipelineStep, StageContext

logger = get_logger(__name__)


class DoubanSubjectStep(PipelineStep):
    name = "subject_api"

    def __init__(self, row_filter=None):
        self.row_filter = row_filter

    def run(self, context: StageContext) -> Dict[str, int]:
        df = context.df
        progress = context.progress_manager
        douban_conf = context.douban_config.get("subject_api", {})
        url_column = context.link_column or context.get_field("url")
        # 只处理状态为“待补API”的行；若传入行过滤器则优先使用
        if self.row_filter is not None:
            candidate_indices = [idx for idx in df.index if self.row_filter(df, idx)]
        else:
            candidate_indices = [idx for idx in df.index if progress.needs_api(df, idx)]

        tasks: List[Tuple[int, str]] = []
        for index in candidate_indices:
            link_value = str(df.at[index, url_column] or "").strip()
            subject_id = extract_subject_id(link_value)
            if not subject_id:
                continue
            tasks.append((index, subject_id))

        if not tasks:
            return {"total": 0, "success": 0, "failed": 0}

        stats = {"total": len(tasks), "success": 0, "failed": 0}

        async def _run_async() -> None:
            async with SubjectApiClient(
                base_url=douban_conf.get("base_url", "https://m.douban.com/rexxar/api/v2/subject"),
                timeout=douban_conf.get("timeout", 10),
                max_concurrent=douban_conf.get("max_concurrent", 5),
                qps=douban_conf.get("qps", 2),
                retry=douban_conf.get("retry", {}),
            ) as client:
                await asyncio.gather(*[self._handle_task(client, context, task, stats) for task in tasks])

        asyncio.run(_run_async())
        progress.save_partial(df, force=True, reason="subject_stage_final")
        return stats

    async def _handle_task(
        self,
        client: SubjectApiClient,
        context: StageContext,
        task: Tuple[int, str],
        stats: Dict[str, int],
    ) -> None:
        index, subject_id = task
        df = context.df
        progress = context.progress_manager
        try:
            payload = await client.fetch_subject(subject_id)
        except Exception as exc:  # noqa: BLE001
            stats["failed"] += 1
            logger.error("Subject API 调用失败 - row=%s subject_id=%s err=%s", index, subject_id, exc)
            return

        if not payload:
            stats["failed"] += 1
            logger.warning("Subject API 无数据 - row=%s subject_id=%s", index, subject_id)
            return

        mapped = map_subject_payload(payload)
        for logical_key, column_name in context.field_mapping.items():
            if logical_key == "url":
                continue
            if logical_key not in mapped:
                continue
            try:
                if column_name in df.columns:
                    df[column_name] = df[column_name].astype("object")
            except Exception:
                pass
            df.at[index, column_name] = mapped[logical_key]

        progress.append_source(df, index, "API")
        progress.mark_done(df, index)
        progress.flush_row_to_database(
            df=df,
            index=index,
            barcode_column=context.barcode_column,
            isbn_column=context.isbn_column,
            douban_fields_mapping=context.field_mapping,
        )
        stats["success"] += 1
