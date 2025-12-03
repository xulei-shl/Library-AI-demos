#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ISBN 预处理步骤.

负责 ISBN 预处理和 ISBN 补充检索。
"""

from __future__ import annotations

import asyncio
from dataclasses import replace as dataclass_replace
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import pandas as pd

from src.utils.logger import get_logger
from src.core.douban.api.isbn_client import normalize_isbn

from .constants import ProcessStatus

if TYPE_CHECKING:
    from src.core.douban.progress_manager import ProgressManager

logger = get_logger(__name__)


class IsbnPreprocessor:
    """ISBN 预处理器.

    负责：
    1. ISBN 格式标准化（去除分隔符、校验格式）
    2. ISBN 补充检索（通过 FOLIO 获取缺失的 ISBN）
    """

    def __init__(self, isbn_column: str = "ISBN", barcode_column: str = "书目条码"):
        """初始化预处理器.

        Args:
            isbn_column: ISBN 列名
            barcode_column: 条码列名
        """
        self.isbn_column = isbn_column
        self.barcode_column = barcode_column

    def preprocess(self, df: pd.DataFrame) -> Dict[str, int]:
        """预处理 ISBN 列.

        去除分隔符，校验格式，标记无效 ISBN。

        Args:
            df: 数据框

        Returns:
            统计信息 {"valid": int, "invalid": int}
        """
        valid_count = 0
        invalid_count = 0

        # 添加标准化 ISBN 列
        df["_normalized_isbn"] = ""

        for idx in df.index:
            raw_isbn = df.at[idx, self.isbn_column] if self.isbn_column in df.columns else ""
            normalized = normalize_isbn(raw_isbn)

            if normalized:
                df.at[idx, "_normalized_isbn"] = normalized
                valid_count += 1
            else:
                df.at[idx, "_normalized_isbn"] = ""
                if pd.notna(raw_isbn) and str(raw_isbn).strip():
                    # 有值但格式无效
                    if df.at[idx, "处理状态"] == ProcessStatus.PENDING:
                        df.at[idx, "处理状态"] = ProcessStatus.INVALID_ISBN
                    invalid_count += 1
                else:
                    # ISBN 为空,检查是否有条码
                    barcode = str(
                        df.at[idx, self.barcode_column] if self.barcode_column in df.columns else ""
                    ).strip()
                    # 如果没有条码,则无法通过 FOLIO 补充,直接标记为 NO_ISBN
                    if (not barcode or barcode.lower() == "nan") and df.at[idx, "处理状态"] == ProcessStatus.PENDING:
                        df.at[idx, "处理状态"] = ProcessStatus.NO_ISBN

        return {"valid": valid_count, "invalid": invalid_count}

    def supplement_isbn(
        self,
        df: pd.DataFrame,
        progress: "ProgressManager",
        douban_config: Dict,
        min_threshold: int = 5,
        enable_supplement: bool = True,
    ) -> Dict[str, int]:
        """ISBN 补充检索.

        对 ISBN 为空且状态为"待处理"的记录进行 FOLIO ISBN 补充检索。

        Args:
            df: 数据框
            progress: 进度管理器
            douban_config: 豆瓣配置
            min_threshold: 最小阈值，只有当需要补充的记录数>=此值时才启动FOLIO处理器
            enable_supplement: 是否启用补充功能

        Returns:
            统计信息 {"total": int, "success": int, "failed": int, "skipped": int}
        """
        if not enable_supplement:
            logger.info("[ISBN补充] 已禁用，跳过")
            return {"total": 0, "success": 0, "failed": 0, "skipped": 0}

        # 检查配置是否启用 ISBN 补充
        resolver_conf = (douban_config.get("isbn_resolver") if douban_config else {}) or {}
        if not resolver_conf.get("enabled", True):
            logger.info("[ISBN补充] 配置禁止了FOLIO ISBN检索，跳过补充阶段")
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "skipped": 0,
                "disabled": True,
            }

        logger.info("=" * 80)
        logger.info("[ISBN补充] 开始检查需要补充ISBN的记录")
        logger.info("=" * 80)

        # 筛选需要补充 ISBN 的行
        indices_to_process = self._find_indices_to_supplement(df)

        if not indices_to_process:
            logger.info("[ISBN补充] 无需补充ISBN的记录")
            return {"total": 0, "success": 0, "failed": 0, "skipped": 0}

        logger.info(f"[ISBN补充] 发现 {len(indices_to_process)} 条记录需要补充ISBN")

        # 检查是否达到最小阈值
        if len(indices_to_process) < min_threshold:
            logger.info(
                f"[ISBN补充] 需要补充的记录数({len(indices_to_process)}) "
                f"< 最小阈值({min_threshold}),跳过FOLIO检索"
            )
            return {
                "total": len(indices_to_process),
                "success": 0,
                "failed": 0,
                "skipped": len(indices_to_process),
            }

        # 调用 FOLIO ISBN 处理器
        return self._call_folio_processor(
            df=df,
            indices_to_process=indices_to_process,
            progress=progress,
            douban_config=douban_config,
        )

    def _find_indices_to_supplement(self, df: pd.DataFrame) -> List[int]:
        """查找需要补充 ISBN 的行索引."""
        indices_to_process = []
        for index in df.index:
            # 检查 ISBN 是否为空
            isbn_value = str(
                df.at[index, self.isbn_column] if self.isbn_column in df.columns else ""
            ).strip()
            if isbn_value and isbn_value.lower() not in ["nan", "", "获取失败"]:
                continue

            # 检查状态是否为"待处理"
            status = df.at[index, "处理状态"]
            if status != ProcessStatus.PENDING:
                continue

            # 检查是否有条码
            barcode = str(
                df.at[index, self.barcode_column] if self.barcode_column in df.columns else ""
            ).strip()
            if not barcode or barcode.lower() == "nan":
                continue

            indices_to_process.append(index)

        return indices_to_process

    def _call_folio_processor(
        self,
        df: pd.DataFrame,
        indices_to_process: List[int],
        progress: "ProgressManager",
        douban_config: Dict,
    ) -> Dict[str, int]:
        """调用 FOLIO ISBN 处理器."""
        try:
            from src.core.douban.folio_isbn_async_processor import ISBNAsyncProcessor

            # 获取配置
            isbn_config = douban_config.get("isbn_processor", {}) or {}
            processing_config = self._resolve_processing_config(isbn_config)

            # 创建处理器
            processor = ISBNAsyncProcessor(
                processing_config=processing_config,
                enable_database=False,  # 补充阶段不使用数据库
            )

            # 获取 partial 文件路径
            partial_path = str(progress.partial_path)

            logger.info(f"[ISBN补充] 开始调用FOLIO处理器,处理 {len(indices_to_process)} 条记录")

            # 异步调用处理器
            _, stats = asyncio.run(
                processor.process_excel_file(
                    excel_file_path=partial_path,
                    barcode_column=self.barcode_column,
                    output_column=self.isbn_column,
                    retry_failed=True,
                    target_indices=indices_to_process,
                )
            )

            logger.info("[ISBN补充] FOLIO处理完成,开始更新状态")

            # 重新加载 DataFrame（因为处理器会修改 Excel 文件）
            df_updated = pd.read_excel(partial_path)

            # 更新状态
            success_count = 0
            failed_count = 0

            for index in indices_to_process:
                isbn_value = str(
                    df_updated.at[index, self.isbn_column]
                    if self.isbn_column in df_updated.columns
                    else ""
                ).strip()

                if isbn_value and isbn_value not in ["", "nan", "获取失败"]:
                    # 成功获取ISBN，同步数据到 df
                    for col in df.columns:
                        if col in df_updated.columns:
                            df.at[index, col] = df_updated.at[index, col]
                    success_count += 1
                    logger.debug(f"[ISBN补充] 行{index+1}: 成功获取ISBN={isbn_value}")
                else:
                    # 仍然失败,标记为无ISBN
                    if df.at[index, "处理状态"] == ProcessStatus.PENDING:
                        df.at[index, "处理状态"] = ProcessStatus.NO_ISBN
                    failed_count += 1
                    logger.debug(f"[ISBN补充] 行{index+1}: 未能获取ISBN,已标记为无ISBN")

            # 保存更新后的状态
            progress.save_partial(df, force=True, reason="isbn_supplement")

            logger.info("=" * 80)
            logger.info("[ISBN补充] 处理完成:")
            logger.info(f"  总记录数: {len(indices_to_process)}")
            logger.info(f"  成功获取: {success_count}")
            logger.info(f"  仍然失败: {failed_count}")
            logger.info("=" * 80)

            return {
                "total": len(indices_to_process),
                "success": success_count,
                "failed": failed_count,
                "skipped": 0,
            }

        except Exception as e:
            logger.error(f"[ISBN补充] 处理失败: {e}", exc_info=True)
            return {
                "total": len(indices_to_process),
                "success": 0,
                "failed": len(indices_to_process),
                "skipped": 0,
            }

    def _resolve_processing_config(self, isbn_config: Dict[str, Any]):
        """根据配置字典构建 ProcessingConfig."""
        from src.core.douban.isbn_processor_config import (
            get_config,
            load_config_from_yaml,
        )

        raw_config = isbn_config or {}
        config = load_config_from_yaml(raw_config) or get_config("balanced")
        override_fields = (
            "max_concurrent",
            "batch_size",
            "min_delay",
            "max_delay",
            "retry_times",
            "timeout",
            "browser_startup_timeout",
            "page_navigation_timeout",
        )
        overrides: Dict[str, Any] = {}
        for field_name in override_fields:
            if field_name in raw_config and raw_config[field_name] is not None:
                overrides[field_name] = raw_config[field_name]
        if overrides:
            config = dataclass_replace(config, **overrides)
        return config
