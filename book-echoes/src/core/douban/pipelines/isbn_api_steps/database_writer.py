#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据库写入步骤.

负责将 API 获取的数据写入数据库。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

import pandas as pd

from src.utils.logger import get_logger
from src.utils.config_manager import get_config_manager

from .constants import ProcessStatus

if TYPE_CHECKING:
    from src.core.douban.database.database_manager import DatabaseManager

logger = get_logger(__name__)


class DatabaseWriter:
    """数据库写入器.

    将所有 API 成功获取的数据写入数据库（不受评分过滤影响）。
    """

    # 需要写入数据库的分类
    WRITE_TO_DB_CATEGORIES: Set[str] = {"new", "existing_stale", "existing_valid_incomplete"}

    def __init__(
        self,
        barcode_column: str = "书目条码",
        isbn_column: str = "ISBN",
    ):
        """初始化.

        Args:
            barcode_column: 条码列名
            isbn_column: ISBN 列名
        """
        self.barcode_column = barcode_column
        self.isbn_column = isbn_column
        self._config_manager = get_config_manager()

    def write_to_database(
        self,
        df: pd.DataFrame,
        db_manager: "DatabaseManager",
        field_mapping: Dict[str, str],
        row_category_map: Optional[Dict[int, str]] = None,
    ) -> int:
        """写入数据库.

        只写入以下分类的记录（排除 existing_valid，因为那些数据来自DB无需写回）：
        - new: API成功获取的新记录
        - existing_stale: API成功刷新的过期记录
        - existing_valid_incomplete: API成功补充的不完整记录

        Args:
            df: 数据框
            db_manager: 数据库管理器
            field_mapping: 字段映射
            row_category_map: 行分类映射

        Returns:
            写入的记录数
        """
        try:
            from src.core.douban.pipelines.database.excel_to_database_writer import (
                ExcelToDatabaseWriter,
            )

            full_config = self._config_manager.get_config()
            writer = ExcelToDatabaseWriter(full_config, update_mode="merge")
            row_category_map = row_category_map or {}

            # 收集需要写入的记录
            books_data = []
            for idx in df.index:
                status = df.at[idx, "处理状态"]

                # 只处理状态为"完成"的记录
                if status != ProcessStatus.DONE:
                    continue

                # 检查是否属于需要写入数据库的分类
                row_category = row_category_map.get(idx)
                if row_category and row_category not in self.WRITE_TO_DB_CATEGORIES:
                    logger.debug(f"跳过写入DB - idx={idx}, category={row_category}")
                    continue

                row = df.loc[idx]
                payload = writer.build_single_payload(
                    row=row,
                    barcode_column=self.barcode_column,
                    isbn_column=self.isbn_column,
                    douban_fields_mapping=field_mapping,
                )
                if payload and payload[0]:
                    books_data.append(payload[0])

            if not books_data:
                logger.info("没有需要写入数据库的记录")
                return 0

            db_manager.batch_save_data(
                books_data=books_data,
                borrow_records_list=[],
                statistics_list=[],
                batch_size=100,
                update_mode="merge",
            )
            logger.info(f"成功写入数据库: {len(books_data)} 条记录")
            return len(books_data)

        except Exception as e:
            logger.error(f"写入数据库失败: {e}")
            return 0
