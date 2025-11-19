#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据库查重阶段."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from src.utils.logger import get_logger
from src.core.douban.database.database_manager import DatabaseManager
from src.core.douban.database.data_checker import DataChecker
from .base import PipelineStep, StageContext

logger = get_logger(__name__)


class DoubanDatabaseStage(PipelineStep):
    name = "database_refresh"

    def __init__(self, enabled: bool, db_config: Dict[str, Any]):
        self.enabled = enabled
        self.db_config = db_config or {}
        self.db_manager: Optional[DatabaseManager] = None
        self.data_checker: Optional[DataChecker] = None

    def prepare(self, context: StageContext) -> None:
        if not self.enabled:
            return
        db_path = self.db_config.get("db_path", "runtime/database/books_history.db")
        self.db_manager = DatabaseManager(db_path)
        self.db_manager.init_database(db_path)
        refresh_config = self.db_config.get("refresh_strategy", {})
        self.data_checker = DataChecker(self.db_manager, refresh_config)
        context.extra["db_manager"] = self.db_manager

    def run(self, context: StageContext) -> Dict[str, int | bool]:
        if not self.enabled or not self.data_checker or not self.db_manager:
            return {"enabled": False}

        df = context.df
        barcode_column = context.barcode_column
        isbn_column = context.isbn_column
        resume_light_mode = bool(context.extra.get("db_stage_light_mode"))
        force_db_stage = bool(context.extra.get("force_db_stage"))
        meta_payload: Optional[Dict[str, Any]] = None
        if resume_light_mode and not force_db_stage:
            meta_payload = context.extra.get("db_meta_payload") or None

        excel_data: List[Dict] = []
        for index, row in df.iterrows():
            data = row.to_dict()
            data["_index"] = index
            excel_data.append(data)

        categories: Dict[str, Any] = {}
        reused_meta = False
        if meta_payload:
            categories = meta_payload.get("categories") or {}
            if categories:
                reused_meta = True
                logger.info("Resume mode detected, reusing cached DB categories from metadata")
        if not categories:
            categories = self.data_checker.check_and_categorize_books(excel_data) or {}
        context.extra["db_categories"] = categories
        context.progress_manager.configure_database(
            db_manager=self.db_manager,
            full_config=context.full_config,
            db_config=self.db_config,
            categories=categories,
        )
        context.progress_manager.persist_db_meta(
            categories,
            extra={
                "source": "meta" if reused_meta else "checker",
                "light_mode": resume_light_mode,
            },
        )

        existing_valid = categories.get("existing_valid") or []
        existing_stale = categories.get("existing_stale") or []
        new_books = categories.get("new") or []

        logger.info(
            "数据库分类统计 - 有效:%s 过期:%s 新增:%s",
            len(existing_valid),
            len(existing_stale),
            len(new_books),
        )

        if isbn_column in df.columns and not resume_light_mode:
            try:
                df[isbn_column] = df[isbn_column].astype("object")
            except Exception:
                pass

        db_mapping = (
            context.full_config.get("fields_mapping", {})
            .get("database_to_excel", {})
            .get("books", {})
        )
        if not db_mapping:
            raise ValueError("缺少 fields_mapping.database_to_excel.books 配置")

        filled_from_db = 0
        if not resume_light_mode:
            for book_data in existing_valid:
                index = book_data.get("_index")
                if index is None:
                    continue
                barcode = self._resolve_barcode(book_data, barcode_column)
                if not barcode:
                    continue
                book_info = self.db_manager.get_book_by_barcode(barcode)
                if not book_info:
                    continue
                self._write_back_from_db(
                    df=df,
                    row_index=index,
                    isbn_column=isbn_column,
                    db_data=book_info,
                    db_mapping=db_mapping,
                    field_mapping=context.field_mapping,
                )
                context.progress_manager.append_source(df, index, "DB")
                context.progress_manager.mark_done(df, index)
                filled_from_db += 1

            pending_rows = existing_stale + new_books
            for record in pending_rows:
                idx = record.get("_index")
                if idx is None:
                    continue
                context.progress_manager.mark_link_pending(context.df, idx)
        else:
            logger.info("Resume mode active: skip Excel write-back in DB stage and only restore categories")

        context.progress_manager.save_partial(df, reason="db_stage")

        return {
            "enabled": True,
            "existing_valid": len(existing_valid),
            "existing_stale": len(existing_stale),
            "new": len(new_books),
            "filled_from_db": filled_from_db,
            "resume_light_mode": resume_light_mode,
            "db_meta_reused": reused_meta,
        }

    def finalize(self, context: StageContext) -> None:
        return

    def _resolve_barcode(self, book_data: Dict, barcode_column: str) -> str:
        value = book_data.get(barcode_column) or book_data.get("barcode")
        if not value:
            return ""
        return str(value).strip()

    def _write_back_from_db(
        self,
        df: pd.DataFrame,
        row_index: int,
        isbn_column: str,
        db_data: Dict[str, Any],
        db_mapping: Dict[str, str],
        field_mapping: Dict[str, str],
    ) -> None:
        isbn_value = db_data.get("isbn")
        if isbn_value:
            current = df.at[row_index, isbn_column] if isbn_column in df.columns else None
            if not current or pd.isna(current) or str(current).strip() == "":
                df.at[row_index, isbn_column] = str(isbn_value).strip()

        douban_isbn_col = field_mapping.get("ISBN") or field_mapping.get("isbn")

        for db_field, excel_col in db_mapping.items():
            if not db_field.startswith("douban_"):
                continue
            if db_field == "douban_isbn":
                if not douban_isbn_col or douban_isbn_col not in df.columns:
                    continue
                value = db_data.get(db_field)
                if not value:
                    continue
                current_val = df.at[row_index, douban_isbn_col]
                if not current_val or pd.isna(current_val) or str(current_val).strip() == "":
                    df.at[row_index, douban_isbn_col] = str(value).strip()
                continue

            if excel_col not in df.columns:
                continue
            value = db_data.get(db_field)
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            df.at[row_index, excel_col] = value
