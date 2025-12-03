#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ISBN API 调用步骤.

负责批量调用豆瓣 ISBN API 获取图书信息。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

import pandas as pd

from src.utils.logger import get_logger
from src.utils.config_manager import get_config_manager
from src.core.douban.api.isbn_client import IsbnApiClient, IsbnApiConfig
from src.core.douban.api.subject_mapper import map_subject_payload

from .constants import ProcessStatus

if TYPE_CHECKING:
    from src.core.douban.progress_manager import ProgressManager

logger = get_logger(__name__)


class ApiCaller:
    """ISBN API 调用器.

    负责批量调用豆瓣 ISBN API 获取图书信息。
    """

    # 需要调用 API 的分类
    NEED_API_CATEGORIES: Set[str] = {"new", "existing_stale", "existing_valid_incomplete"}

    def __init__(
        self,
        max_concurrent: int = 2,
        qps: float = 0.5,
        timeout: float = 15.0,
        random_delay_min: float = 1.5,
        random_delay_max: float = 3.5,
        batch_cooldown_interval: int = 20,
        batch_cooldown_min: float = 30.0,
        batch_cooldown_max: float = 60.0,
        retry_max_times: int = 3,
        retry_backoff: Optional[List[float]] = None,
        save_interval: int = 15,
    ):
        """初始化 API 调用器.

        Args:
            max_concurrent: 最大并发数
            qps: 每秒请求数
            timeout: 请求超时时间
            random_delay_min: 随机延迟最小值
            random_delay_max: 随机延迟最大值
            batch_cooldown_interval: 批次冷却间隔
            batch_cooldown_min: 批次冷却最小时间
            batch_cooldown_max: 批次冷却最大时间
            retry_max_times: 最大重试次数
            retry_backoff: 重试退避时间列表
            save_interval: 保存间隔
        """
        self.max_concurrent = max_concurrent
        self.qps = qps
        self.timeout = timeout
        self.random_delay_min = random_delay_min
        self.random_delay_max = random_delay_max
        self.batch_cooldown_interval = batch_cooldown_interval
        self.batch_cooldown_min = batch_cooldown_min
        self.batch_cooldown_max = batch_cooldown_max
        self.retry_max_times = retry_max_times
        self.retry_backoff = retry_backoff or [2, 5, 10]
        self.save_interval = save_interval
        self._config_manager = get_config_manager()

    async def call_api(
        self,
        df: pd.DataFrame,
        progress: "ProgressManager",
        field_mapping: Dict[str, str],
        row_category_map: Optional[Dict[int, str]] = None,
    ) -> Dict[str, int]:
        """调用 ISBN API.

        处理以下三类数据：
        - new: 新记录，需要调用API获取
        - existing_stale: 过期记录，需要调用API刷新
        - existing_valid_incomplete: 不完整记录，需要调用API补充

        Args:
            df: 数据框
            progress: 进度管理器
            field_mapping: 字段映射
            row_category_map: 行分类映射

        Returns:
            统计信息 {"success": int, "failed": int, "skipped": int}
        """
        stats = {"success": 0, "failed": 0, "skipped": 0}

        # 确定需要处理的行
        to_process = self._find_rows_to_process(df, row_category_map)

        if not to_process:
            logger.info("没有需要处理的记录")
            return stats

        total = len(to_process)
        logger.info(f"需要调用 ISBN API: {total} 条记录")

        # 构建 API 配置
        api_config = self._build_api_config()

        async with IsbnApiClient(config=api_config) as client:
            for current, (idx, isbn) in enumerate(to_process, 1):
                success = await self._process_single_isbn(
                    client=client,
                    df=df,
                    idx=idx,
                    isbn=isbn,
                    field_mapping=field_mapping,
                    current=current,
                    total=total,
                    progress=progress,
                )

                if success:
                    stats["success"] += 1
                else:
                    stats["failed"] += 1

                # 定期保存进度
                if current % self.save_interval == 0:
                    progress.save_partial(df, force=True, reason=f"progress_{current}")

        # 最终保存
        progress.save_partial(df, force=True, reason="api_complete")

        return stats

    def _find_rows_to_process(
        self,
        df: pd.DataFrame,
        row_category_map: Optional[Dict[int, str]],
    ) -> List[Tuple[int, str]]:
        """查找需要处理的行.

        Returns:
            列表 [(index, normalized_isbn), ...]
        """
        to_process: List[Tuple[int, str]] = []
        row_category_map = row_category_map or {}

        for idx in df.index:
            status = df.at[idx, "处理状态"]

            # 跳过所有终态状态:
            # - DONE: 已完成
            # - FROM_DB: 从数据库获取的完整记录
            # - NOT_FOUND: API 调用失败,已经尝试过
            # - INVALID_ISBN: ISBN 格式无效,无法调用 API
            # - NO_ISBN: ISBN 为空且无法补充,无法调用 API
            skip_statuses = {
                ProcessStatus.DONE,
                ProcessStatus.FROM_DB,
                ProcessStatus.NOT_FOUND,
                ProcessStatus.INVALID_ISBN,
                ProcessStatus.NO_ISBN,
            }
            if status in skip_statuses:
                continue

            # 检查是否在需要处理的分类中
            row_category = row_category_map.get(idx)
            if row_category and row_category not in self.NEED_API_CATEGORIES:
                continue

            normalized_isbn = df.at[idx, "_normalized_isbn"]
            if not normalized_isbn:
                continue

            to_process.append((idx, normalized_isbn))

        return to_process

    def _build_api_config(self) -> IsbnApiConfig:
        """构建 API 配置."""
        api_config = IsbnApiConfig(
            max_concurrent=self.max_concurrent,
            qps=self.qps,
            timeout=self.timeout,
            random_delay_min=self.random_delay_min,
            random_delay_max=self.random_delay_max,
            batch_cooldown_interval=self.batch_cooldown_interval,
            batch_cooldown_min=self.batch_cooldown_min,
            batch_cooldown_max=self.batch_cooldown_max,
            retry_max_times=self.retry_max_times,
            retry_backoff=self.retry_backoff,
        )

        # 从配置加载额外设置
        douban_config = self._config_manager.get_douban_config()
        isbn_api_config = douban_config.get("isbn_api", {})
        if isbn_api_config:
            if "base_url" in isbn_api_config:
                api_config.base_url = isbn_api_config["base_url"]

            random_delay = isbn_api_config.get("random_delay", {})
            if random_delay.get("enabled", True):
                api_config.random_delay_enabled = True
                api_config.random_delay_min = random_delay.get("min", 1.5)
                api_config.random_delay_max = random_delay.get("max", 3.5)

            batch_cooldown = isbn_api_config.get("batch_cooldown", {})
            if batch_cooldown.get("enabled", True):
                api_config.batch_cooldown_enabled = True
                api_config.batch_cooldown_interval = batch_cooldown.get("interval", 20)
                api_config.batch_cooldown_min = batch_cooldown.get("min", 30)
                api_config.batch_cooldown_max = batch_cooldown.get("max", 60)

        return api_config

    async def _process_single_isbn(
        self,
        client: IsbnApiClient,
        df: pd.DataFrame,
        idx: int,
        isbn: str,
        field_mapping: Dict[str, str],
        current: int,
        total: int,
        progress: "ProgressManager",
    ) -> bool:
        """处理单个 ISBN.

        Returns:
            是否成功
        """
        try:
            payload = await client.fetch_by_isbn(isbn)

            if payload:
                # 映射数据
                mapped = map_subject_payload(payload)

                # 写入 DataFrame
                for logical_key, column_name in field_mapping.items():
                    if logical_key in mapped and column_name in df.columns:
                        try:
                            df[column_name] = df[column_name].astype("object")
                        except Exception:
                            pass
                        df.at[idx, column_name] = mapped[logical_key]

                # 特殊处理：从 payload 获取豆瓣链接
                url_col = field_mapping.get("url", "豆瓣链接")
                if url_col in df.columns:
                    if "url" in payload:
                        df.at[idx, url_col] = payload["url"]
                    elif "share_url" in payload:
                        df.at[idx, url_col] = payload["share_url"]

                df.at[idx, "处理状态"] = ProcessStatus.DONE
                progress.append_source(df, idx, "api")
                logger.info(f"[{current}/{total}] ISBN {isbn} 获取成功")
                return True
            else:
                df.at[idx, "处理状态"] = ProcessStatus.NOT_FOUND
                logger.warning(f"[{current}/{total}] ISBN {isbn} 未找到")
                return False

        except Exception as e:
            df.at[idx, "处理状态"] = ProcessStatus.NOT_FOUND
            logger.error(f"[{current}/{total}] ISBN {isbn} 获取失败: {e}")
            return False
