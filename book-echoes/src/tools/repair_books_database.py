#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库修复工具

用途:
1. 备份指定 SQLite 数据库
2. 去重 books.barcode, 将多余记录归档到 books_duplicates_archive
3. 清理仍指向旧表(如books_backup)的 idx_books_* 索引
4. 重新运行 DatabaseManager.init_database() 以重建索引

使用:
    python -m src.tools.repair_books_database --db-path runtime/database/books_history.db
"""

import argparse
import logging
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from src.core.douban.database.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="修复books数据库结构并确保唯一约束")
    parser.add_argument(
        "--db-path",
        type=str,
        default="runtime/database/books_history.db",
        help="SQLite数据库路径(默认: runtime/database/books_history.db)"
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="跳过自动备份(默认会在同目录生成时间戳备份)"
    )
    return parser.parse_args()


def ensure_archive_table(conn: sqlite3.Connection) -> List[str]:
    """确保归档表存在,返回books表字段列表"""
    columns_info = conn.execute("PRAGMA table_info(books)").fetchall()
    if not columns_info:
        raise RuntimeError("未找到books表, 请确认数据库路径是否正确")

    column_defs = []
    column_names = []
    for col in columns_info:
        col_type = col["type"] or "TEXT"
        column_defs.append(f'"{col["name"]}" {col_type}')
        column_names.append(col["name"])

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS books_duplicates_archive (
            %s,
            "archived_at" TEXT NOT NULL
        )
        """ % ", ".join(column_defs)
    )
    return column_names


def fetch_duplicates(conn: sqlite3.Connection) -> List[str]:
    rows = conn.execute(
        """
        SELECT barcode
        FROM books
        WHERE barcode IS NOT NULL AND TRIM(barcode) != ''
        GROUP BY barcode
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    return [row["barcode"] for row in rows]


def archive_and_remove_duplicates(conn: sqlite3.Connection, columns: List[str]) -> Tuple[int, int]:
    """归档并删除重复条码,返回(处理条码数, 删除记录数)"""
    duplicates = fetch_duplicates(conn)
    if not duplicates:
        return 0, 0

    columns_sql = ", ".join(f'"{name}"' for name in columns)
    removed_rows = 0

    for barcode in duplicates:
        rows = conn.execute(
            f"""
            SELECT id, COALESCE(updated_at, created_at) AS ts
            FROM books
            WHERE barcode = ?
            ORDER BY ts DESC, id DESC
            """,
            (barcode,)
        ).fetchall()

        if not rows:
            continue

        keep_id = rows[0]["id"]
        redundant_ids = [row["id"] for row in rows[1:]]
        if not redundant_ids:
            continue

        for redundant_id in redundant_ids:
            conn.execute(
                f"""
                INSERT INTO books_duplicates_archive ({columns_sql}, "archived_at")
                SELECT {columns_sql}, ?
                FROM books
                WHERE id = ?
                """,
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), redundant_id)
            )
        conn.execute(
            f"""
            DELETE FROM books
            WHERE id IN ({",".join(["?"] * len(redundant_ids))})
            """,
            redundant_ids
        )

        removed_rows += len(redundant_ids)
        logger.info(f"条码 {barcode} 保留ID={keep_id}, 已归档并移除 {len(redundant_ids)} 条重复记录")

    return len(duplicates), removed_rows


def cleanup_legacy_indexes(conn: sqlite3.Connection) -> int:
    """移除仍绑定到旧表的 idx_books_* 索引"""
    rows = conn.execute(
        """
        SELECT name, tbl_name
        FROM sqlite_master
        WHERE type='index' AND name LIKE 'idx_books%'
        """
    ).fetchall()

    dropped = 0
    for row in rows:
        if row["tbl_name"] != "books":
            conn.execute(f'DROP INDEX IF EXISTS "{row["name"]}"')
            logger.info(f"删除遗留索引 {row['name']} (绑定表: {row['tbl_name']})")
            dropped += 1
    return dropped


def create_backup(db_path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_name(f"{db_path.stem}_backup_{timestamp}{db_path.suffix}")
    shutil.copy2(db_path, backup_path)
    logger.info(f"已创建备份: {backup_path}")
    return backup_path


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    db_path = Path(args.db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"数据库文件 {db_path} 不存在")

    if not args.skip_backup:
        create_backup(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        columns = ensure_archive_table(conn)
        duplicated_barcodes, removed_records = archive_and_remove_duplicates(conn, columns)
        dropped_indexes = cleanup_legacy_indexes(conn)
        conn.commit()

    logger.info(
        f"去重完成: 重复条码 {duplicated_barcodes}, 删除记录 {removed_records}, 移除遗留索引 {dropped_indexes}"
    )

    db_manager = DatabaseManager(str(db_path))
    db_manager.init_database()
    db_manager.close()
    logger.info("数据库结构检查完成，可继续运行流水线")


if __name__ == "__main__":
    main()
