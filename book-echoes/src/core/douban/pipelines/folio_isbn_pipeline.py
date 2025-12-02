#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FOLIO ISBN 流程流水线
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple, Any, Callable
import tempfile

import pandas as pd

from src.utils.config_manager import get_config_manager
from src.utils.logger import get_logger
from src.core.douban.isbn_processor_config import (
    ProcessingConfig,
    get_config,
    get_config_for_data_size,
    load_config_from_yaml,
)
from src.core.douban.folio_isbn_async_processor import process_isbn_async

logger = get_logger(__name__)


@dataclass
class FolioIsbnPipelineOptions:
    """FOLIO ISBN 流程配置"""

    excel_file: str
    barcode_column: str = "书目条码"
    isbn_column: str = "ISBN"
    config_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    disable_database: bool = False
    force_update: bool = False
    db_path: Optional[str] = None
    retry_failed: bool = True
    limit_rows: Optional[int] = None
    save_interval: int = 25


class FolioIsbnPipeline:
    """封装 FOLIO ISBN 流程，提供可回退的同步入口"""

    def __init__(self, config_manager=None):
        self.config_manager = config_manager or get_config_manager()

    def run(self, options: FolioIsbnPipelineOptions) -> Tuple[str, Dict[str, Any]]:
        """执行 FOLIO 流程"""
        excel_path = self._validate_excel(options.excel_file)
        douban_config = self.config_manager.get_douban_config()
        resolver_conf = (douban_config.get("isbn_resolver") or {})

        if not resolver_conf.get("enabled", True):
            logger.info("FOLIO ISBN 功能已在配置中禁用，跳过该阶段，直接返回原Excel: %s", excel_path)
            skipped_stats = {
                "pipeline": "folio_isbn",
                "input_file": str(excel_path),
                "output_file": str(excel_path),
                "skipped": True,
                "reason": "disabled_in_config",
                "total_records": 0,
                "success_count": 0,
                "failed_count": 0,
                "success_rate": 0.0,
            }
            return str(excel_path), skipped_stats

        config = self._resolve_processing_config(options, excel_path)
        db_config = self._build_db_config(options)
        username, password = self._resolve_credentials(options)

        subset_path, cleanup = self._prepare_subset_if_needed(excel_path, options.limit_rows)
        try:
            output_file, stats = process_isbn_async(
                excel_file_path=str(subset_path),
                max_concurrent=config.max_concurrent if config else 2,
                save_interval=options.save_interval,
                barcode_column=options.barcode_column,
                output_column=options.isbn_column,
                username=username,
                password=password,
                retry_failed=options.retry_failed,
                enable_database=not options.disable_database,
                db_config=db_config,
                processing_config=config,
            )
        finally:
            if cleanup:
                cleanup()

        stats = stats or {}
        stats.setdefault("pipeline", "folio_isbn")
        stats.setdefault("processing_config", config.name if config else "default")
        stats.setdefault("input_file", str(excel_path))
        stats.setdefault("output_file", output_file)
        return output_file, stats

    def _validate_excel(self, excel_file: str) -> Path:
        path = Path(excel_file).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"未找到Excel文件: {path}")
        try:
            df = pd.read_excel(path, nrows=1)
            if df.empty:
                raise ValueError("Excel文件为空")
        except Exception as exc:
            raise ValueError(f"无法读取Excel文件: {path}") from exc
        return path

    def _resolve_processing_config(
        self,
        options: FolioIsbnPipelineOptions,
        excel_path: Path,
    ) -> ProcessingConfig:
        douban_config = self.config_manager.get_douban_config()
        isbn_config = douban_config.get("isbn_processor", {})
        config = load_config_from_yaml(isbn_config)

        if options.config_name:
            config = get_config(options.config_name)
        elif isbn_config.get("strategy") == "auto":
            data_size = self._count_rows(excel_path)
            config = get_config_for_data_size(data_size)

        return config or get_config("balanced")

    def _count_rows(self, excel_path: Path) -> int:
        try:
            df = pd.read_excel(excel_path, usecols=[0])
            return len(df)
        except Exception as exc:
            logger.warning(f"无法计算数据量，使用默认配置: {exc}")
            return 0

    def _build_db_config(self, options: FolioIsbnPipelineOptions) -> Dict[str, Any]:
        douban_config = self.config_manager.get_douban_config()
        db_config = (douban_config.get("database") or {}).copy()

        if options.force_update:
            db_config.setdefault("refresh_strategy", {})["force_update"] = True
        if options.db_path:
            db_config["db_path"] = options.db_path

        return db_config

    def _resolve_credentials(
        self,
        options: FolioIsbnPipelineOptions,
    ) -> Tuple[Optional[str], Optional[str]]:
        douban_config = self.config_manager.get_douban_config()
        resolver_conf = douban_config.get("isbn_resolver", {})
        username = options.username or resolver_conf.get("username")
        password = options.password or resolver_conf.get("password")
        return username, password

    def _prepare_subset_if_needed(
        self,
        excel_path: Path,
        limit_rows: Optional[int],
    ) -> Tuple[Path, Optional[Callable[[], None]]]:
        if not limit_rows:
            return excel_path, None

        df = pd.read_excel(excel_path)
        subset = df.head(limit_rows)
        temp_dir = Path(tempfile.mkdtemp(prefix="folio_subset_"))
        temp_path = temp_dir / excel_path.name
        subset.to_excel(temp_path, index=False)

        def _cleanup():
            try:
                for child in temp_dir.iterdir():
                    child.unlink(missing_ok=True)
                temp_dir.rmdir()
            except OSError:
                pass

        logger.info(f"测试模式启用，仅处理前 {len(subset)} 条记录")
        return temp_path, _cleanup
