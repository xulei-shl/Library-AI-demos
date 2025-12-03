#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据库查重步骤.

负责数据库查重和从数据库填充已有数据。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import pandas as pd

from src.utils.logger import get_logger
from src.core.douban.database.database_manager import DatabaseManager

from .constants import ProcessStatus

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class DatabaseChecker:
    """数据库查重器.

    负责：
    1. 数据库查重和分类
    2. 从数据库填充已有数据
    """

    def __init__(self, barcode_column: str = "书目条码"):
        """初始化.

        Args:
            barcode_column: 条码列名
        """
        self.barcode_column = barcode_column
        self.row_category_map: Dict[int, str] = {}

    def check_and_categorize(
        self,
        df: pd.DataFrame,
        douban_config: Dict,
        field_mapping: Dict[str, str],
        db_path: Optional[str] = None,
        force_update: bool = False,
    ) -> Tuple[Optional[DatabaseManager], Optional[Dict]]:
        """数据库查重.

        使用 DataChecker 进行数据分类：
        - existing_valid: 数据库有完整数据且未过期 → 跳过API
        - existing_valid_incomplete: 数据库有数据但不完整 → 需要调用API补充
        - existing_stale: 数据库有数据但已过期 → 需要调用API刷新
        - new: 数据库无记录 → 需要调用API获取

        Args:
            df: 数据框
            douban_config: 豆瓣配置
            field_mapping: 字段映射
            db_path: 数据库路径
            force_update: 是否强制更新

        Returns:
            (db_manager, categories)
        """
        from src.core.douban.database.data_checker import DataChecker

        db_config = douban_config.get("database", {})
        actual_db_path = db_path or db_config.get("db_path", "runtime/database/books_history.db")

        try:
            db_manager = DatabaseManager(actual_db_path)
            db_manager.init_database()

            # 构建 refresh_config
            refresh_config = db_config.get("refresh_strategy", {}).copy()
            if force_update:
                refresh_config["force_update"] = True

            # 使用 DataChecker 进行分类
            data_checker = DataChecker(db_manager, refresh_config)

            # 构建 excel_data 列表
            excel_data: List[Dict] = []
            for idx, row in df.iterrows():
                data = row.to_dict()
                data["_index"] = idx
                data["barcode"] = str(row.get(self.barcode_column, "")).strip()
                excel_data.append(data)

            # 调用 DataChecker 进行分类
            categories = data_checker.check_and_categorize_books(excel_data)

            # 处理各分类
            self._process_existing_valid(df, categories, db_manager, field_mapping)
            self._process_existing_incomplete(df, categories, db_manager, field_mapping)
            self._process_existing_stale(df, categories, db_manager, field_mapping)
            self._process_new(df, categories)

            logger.info(
                f"数据库分类完成: "
                f"有效={len(categories.get('existing_valid', []))}, "
                f"待补API={len(categories.get('existing_valid_incomplete', []))}, "
                f"过期={len(categories.get('existing_stale', []))}, "
                f"新增={len(categories.get('new', []))}"
            )

            return db_manager, categories

        except Exception as e:
            logger.error(f"数据库查重失败: {e}")
            return None, None

    def _process_existing_valid(
        self,
        df: pd.DataFrame,
        categories: Dict,
        db_manager: DatabaseManager,
        field_mapping: Dict[str, str],
    ) -> None:
        """处理 existing_valid: 从数据库填充数据，标记为完成."""
        for item in categories.get("existing_valid", []):
            idx = item.get("_index")
            if idx is None:
                continue
            barcode = str(item.get("barcode", "")).strip()
            df.at[idx, "处理状态"] = ProcessStatus.FROM_DB
            self.row_category_map[idx] = "existing_valid"
            self._fill_from_database(df, idx, barcode, db_manager, field_mapping)

    def _process_existing_incomplete(
        self,
        df: pd.DataFrame,
        categories: Dict,
        db_manager: DatabaseManager,
        field_mapping: Dict[str, str],
    ) -> None:
        """处理 existing_valid_incomplete: 从数据库填充数据，但需要调用API补充."""
        for item in categories.get("existing_valid_incomplete", []):
            idx = item.get("_index")
            if idx is None:
                continue
            barcode = str(item.get("barcode", "")).strip()
            df.at[idx, "处理状态"] = ProcessStatus.PENDING
            self.row_category_map[idx] = "existing_valid_incomplete"
            self._fill_from_database(df, idx, barcode, db_manager, field_mapping)

    def _process_existing_stale(
        self,
        df: pd.DataFrame,
        categories: Dict,
        db_manager: DatabaseManager,
        field_mapping: Dict[str, str],
    ) -> None:
        """处理 existing_stale: 从数据库填充基础数据，需要调用API刷新."""
        for item in categories.get("existing_stale", []):
            idx = item.get("_index")
            if idx is None:
                continue
            barcode = str(item.get("barcode", "")).strip()
            df.at[idx, "处理状态"] = ProcessStatus.PENDING
            self.row_category_map[idx] = "existing_stale"
            self._fill_from_database(df, idx, barcode, db_manager, field_mapping)

    def _process_new(self, df: pd.DataFrame, categories: Dict) -> None:
        """处理 new: 标记为待处理."""
        for item in categories.get("new", []):
            idx = item.get("_index")
            if idx is None:
                continue
            df.at[idx, "处理状态"] = ProcessStatus.PENDING
            self.row_category_map[idx] = "new"

    def _fill_from_database(
        self,
        df: pd.DataFrame,
        idx: int,
        barcode: str,
        db_manager: DatabaseManager,
        field_mapping: Dict[str, str],
    ) -> None:
        """从数据库填充已有数据."""
        try:
            book_data = db_manager.get_book_by_barcode(barcode)
            if not book_data:
                return

            # 数据库字段到 Excel 列的映射
            db_to_excel = {
                "douban_url": field_mapping.get("url", "豆瓣链接"),
                "douban_rating": field_mapping.get("rating", "豆瓣评分"),
                "douban_title": field_mapping.get("title", "豆瓣书名"),
                "douban_subtitle": field_mapping.get("subtitle", "豆瓣副标题"),
                "douban_original_title": field_mapping.get("original_title", "豆瓣原作名"),
                "douban_author": field_mapping.get("author", "豆瓣作者"),
                "douban_translator": field_mapping.get("translator", "豆瓣译者"),
                "douban_publisher": field_mapping.get("publisher", "豆瓣出版社"),
                "douban_producer": field_mapping.get("producer", "豆瓣出品方"),
                "douban_series": field_mapping.get("series", "豆瓣丛书"),
                "douban_series_link": field_mapping.get("series_link", "豆瓣丛书链接"),
                "douban_price": field_mapping.get("price", "豆瓣定价"),
                "douban_isbn": field_mapping.get("isbn", "豆瓣ISBN"),
                "douban_pages": field_mapping.get("pages", "豆瓣页数"),
                "douban_binding": field_mapping.get("binding", "豆瓣装帧"),
                "douban_pub_year": field_mapping.get("pub_year", "豆瓣出版年"),
                "douban_rating_count": field_mapping.get("rating_count", "豆瓣评价人数"),
                "douban_summary": field_mapping.get("summary", "豆瓣内容简介"),
                "douban_author_intro": field_mapping.get("author_intro", "豆瓣作者简介"),
                "douban_catalog": field_mapping.get("catalog", "豆瓣目录"),
                "douban_cover_image": field_mapping.get("cover_image", "豆瓣封面图片链接"),
            }

            for db_field, excel_col in db_to_excel.items():
                value = book_data.get(db_field)
                if value is not None and excel_col in df.columns:
                    df.at[idx, excel_col] = value

        except Exception as e:
            logger.warning(f"从数据库填充数据失败 - barcode={barcode}: {e}")
