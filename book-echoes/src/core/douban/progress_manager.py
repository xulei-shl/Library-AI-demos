#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Excel / 数据库 进度管理器."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, Set

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ProgressManager:
    """统一管理 Excel 持久化、状态列与数据库刷写."""

    STATUS_PENDING = "待处理"
    STATUS_DB_DONE = "已写库"
    STATUS_LINK_PENDING = "待补链接"
    STATUS_LINK_READY = "链接已获取"
    STATUS_API_PENDING = "待补API"
    STATUS_DONE = "完成"

    # 兼容旧状态
    STATUS_ISBN_DONE = "ISBN完成"
    STATUS_DOUBAN_DONE = "豆瓣完成"
    TERMINAL_STATUSES = {STATUS_DONE, STATUS_DOUBAN_DONE}

    def __init__(
        self,
        excel_file: str,
        status_column: str = "处理状态",
        save_interval: int = 15,
        source_column: str = "豆瓣数据来源",
    ) -> None:
        self.original_path = Path(excel_file)
        self.status_column = status_column
        self.source_column = source_column
        self.partial_path = self._resolve_partial_path()
        self._db_meta_path = self._resolve_db_meta_path()
        self.save_interval = max(save_interval, 5)
        self._last_save_at = 0.0
        self._db_manager = None
        self._db_writer = None
        self._db_update_mode = "merge"
        self._db_flushed_indexes: Set[int] = set()
        self._row_category_map: Dict[int, str] = {}
        self._categories: Optional[Dict] = None
        self._full_config: Optional[Dict] = None
        self._db_config: Dict = {}

    def _resolve_partial_path(self) -> Path:
        output_dir = Path("runtime/outputs")
        output_dir.mkdir(parents=True, exist_ok=True)
        suffix = self.original_path.suffix or ".xlsx"
        stem = self.original_path.stem

        # 如果输入文件本身就是 partial 文件，则直接使用它作为 partial 路径
        # 避免生成 _partial_partial.xlsx
        if stem.endswith("_partial"):
            return output_dir / f"{stem}{suffix}"

        return output_dir / f"{stem}_partial{suffix}"

    def _resolve_db_meta_path(self) -> Path:
        return self._resolve_partial_path().with_suffix(".dbmeta.json")

    def load_dataframe(self) -> pd.DataFrame:
        source_path = self.partial_path if self.partial_path.exists() else self.original_path
        logger.info("加载数据源: %s", source_path)
        df = pd.read_excel(source_path)
        if self.status_column not in df.columns:
            df[self.status_column] = self.STATUS_PENDING
        else:
            df[self.status_column] = df[self.status_column].fillna(self.STATUS_PENDING)
        if self.source_column not in df.columns:
            df[self.source_column] = ""
        return df

    def row_status(self, df: pd.DataFrame, index: int) -> str:
        value = df.at[index, self.status_column]
        return str(value or "").strip()

    # -------- 状态写入 --------
    def mark_status(self, df: pd.DataFrame, index: int, status: str) -> None:
        df.at[index, self.status_column] = status

    def mark_db_written(self, df: pd.DataFrame, index: int) -> None:
        if self.row_status(df, index) in self.TERMINAL_STATUSES:
            return
        self.mark_status(df, index, self.STATUS_DB_DONE)

    def mark_link_pending(self, df: pd.DataFrame, index: int) -> None:
        if self.row_status(df, index) in self.TERMINAL_STATUSES:
            return
        self.mark_status(df, index, self.STATUS_LINK_PENDING)

    def mark_link_ready(self, df: pd.DataFrame, index: int) -> None:
        if self.row_status(df, index) in self.TERMINAL_STATUSES:
            return
        self.mark_status(df, index, self.STATUS_LINK_READY)

    def mark_api_pending(self, df: pd.DataFrame, index: int) -> None:
        if self.row_status(df, index) in self.TERMINAL_STATUSES:
            return
        self.mark_status(df, index, self.STATUS_API_PENDING)

    def mark_done(self, df: pd.DataFrame, index: int) -> None:
        self.mark_status(df, index, self.STATUS_DONE)

    # 兼容旧接口
    def mark_isbn_done(self, df: pd.DataFrame, index: int) -> None:
        self.mark_db_written(df, index)

    def mark_douban_done(self, df: pd.DataFrame, index: int) -> None:
        self.mark_done(df, index)

    # -------- 状态判断 --------
    def should_skip_barcode(self, df: pd.DataFrame, index: int) -> bool:
        return self.row_status(df, index) in self.TERMINAL_STATUSES

    def needs_link(self, df: pd.DataFrame, index: int) -> bool:
        status = self.row_status(df, index)
        return status in {
            self.STATUS_PENDING,
            self.STATUS_DB_DONE,
            self.STATUS_LINK_PENDING,
            self.STATUS_ISBN_DONE,
        }

    def needs_api(self, df: pd.DataFrame, index: int) -> bool:
        status = self.row_status(df, index)
        return status in {self.STATUS_API_PENDING}

    def needs_douban(self, df: pd.DataFrame, index: int) -> bool:
        return self.needs_api(df, index)

    def needs_isbn(self, df: pd.DataFrame, index: int) -> bool:
        return not self.should_skip_barcode(df, index)

    def append_source(self, df: pd.DataFrame, index: int, source: str) -> None:
        if not source:
            return
        current_value = df.at[index, self.source_column]
        current = "" if pd.isna(current_value) else str(current_value or "")
        parts = {item.strip() for item in current.split(",") if item.strip()}
        parts.add(source)
        df.at[index, self.source_column] = ",".join(sorted(parts))

    # -------- 文件/数据库操作 --------
    def save_partial(self, df: pd.DataFrame, force: bool = False, reason: str = "") -> None:
        now = time.time()
        if not force and (now - self._last_save_at) < self.save_interval:
            return
        df.to_excel(self.partial_path, index=False)
        self._last_save_at = now
        logger.info("[进度持久化] 已写入 %s (%s)", self.partial_path, reason)

    def configure_database(
        self,
        db_manager,
        full_config: Dict,
        db_config: Dict,
        categories: Optional[Dict],
    ) -> None:
        if not db_manager or not categories:
            return
        from .database.excel_to_database_writer import ExcelToDatabaseWriter

        refresh_config = (db_config or {}).get("refresh_strategy", {}) if db_config else {}
        self._db_update_mode = refresh_config.get("update_mode", "merge")
        self._db_manager = db_manager
        self._full_config = full_config
        self._db_config = db_config or {}
        self._categories = categories
        self._db_writer = ExcelToDatabaseWriter(full_config, update_mode=self._db_update_mode)
        self._row_category_map = self._build_row_category_map(categories)
        logger.info("ProgressManager 已启用数据库刷写功能")

    def _build_row_category_map(self, categories: Dict) -> Dict[int, str]:
        mapping: Dict[int, str] = {}
        for category_name, items in categories.items():
            if not isinstance(items, list):
                continue
            for item in items:
                index = item.get("_index")
                if index is not None:
                    mapping[index] = category_name
        return mapping

    def flush_row_to_database(
        self,
        df: pd.DataFrame,
        index: int,
        barcode_column: str,
        isbn_column: str,
        douban_fields_mapping: Dict[str, str],
    ) -> None:
        if (
            not self._db_manager
            or not self._db_writer
            or index in self._db_flushed_indexes
        ):
            return

        category = self._row_category_map.get(index)
        if category not in ("existing_stale", "new", "existing_valid_incomplete"):
            return

        row = df.iloc[index]
        payload = self._db_writer.build_single_payload(
            row=row,
            barcode_column=barcode_column,
            isbn_column=isbn_column,
            douban_fields_mapping=douban_fields_mapping,
        )
        if not payload:
            return
        book_data, borrow_record, stat_record = payload
        books_data = [book_data] if book_data else []
        borrow_records = [borrow_record] if borrow_record else []
        stats = [stat_record] if stat_record else []

        if not any((books_data, borrow_records, stats)):
            return

        self._db_manager.batch_save_data(
            books_data=books_data,
            borrow_records_list=borrow_records,
            statistics_list=stats,
            batch_size=1,
            update_mode=self._db_update_mode,
        )
        self._db_flushed_indexes.add(index)
        logger.info("数据库增量刷写完成 - index=%s category=%s", index, category)

    def cleanup_partial_if_exists(self) -> None:
        if self.partial_path.exists():
            self.partial_path.unlink()
            logger.info("Deleted partial file: %s", self.partial_path)
        if self._db_meta_path.exists():
            self._db_meta_path.unlink()
            logger.info("Deleted partial meta file: %s", self._db_meta_path)

    def partial_exists(self) -> bool:
        return self.partial_path.exists()

    def persist_db_meta(
        self,
        categories: Optional[Dict[str, Any]],
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not categories:
            return
        payload = {
            "version": 1,
            "generated_at": time.time(),
            "excel_file": str(self.original_path),
            "partial_path": str(self.partial_path),
            "categories": categories,
            "extra": extra or {},
        }
        try:
            with self._db_meta_path.open("w", encoding="utf-8", newline="") as fp:
                json.dump(payload, fp, ensure_ascii=False, indent=2)
            logger.info("Persisted DB classification metadata: %s", self._db_meta_path)
        except Exception as exc:
            logger.warning("Failed to persist DB metadata: %s", exc)

    def load_db_meta(self) -> Optional[Dict[str, Any]]:
        if not self._db_meta_path.exists():
            return None
        try:
            with self._db_meta_path.open("r", encoding="utf-8") as fp:
                return json.load(fp)
        except Exception as exc:
            logger.warning("Failed to read DB metadata: %s", exc)
            return None

    def finalize_output(self, final_path: Path, df: pd.DataFrame) -> None:
        df.to_excel(final_path, index=False)
        logger.info("主输出: %s", final_path)
        self.cleanup_partial_if_exists()
