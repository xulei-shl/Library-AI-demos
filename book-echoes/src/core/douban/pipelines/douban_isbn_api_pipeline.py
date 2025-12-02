#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""豆瓣 ISBN API 流水线.

通过 ISBN 直接调用豆瓣 API 获取图书信息的完整流水线，
包含 ISBN 预处理、API 调用、评分过滤和结果输出。
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

from src.utils.config_manager import get_config_manager
from src.utils.logger import get_logger
from src.utils.time_utils import get_timestamp

from src.core.douban.api.isbn_client import IsbnApiClient, IsbnApiConfig, normalize_isbn
from src.core.douban.api.subject_mapper import map_subject_payload
from src.core.douban.progress_manager import ProgressManager
from src.core.douban.database.database_manager import DatabaseManager
from src.core.douban.analytics.dynamic_threshold_filter import DynamicThresholdFilter

logger = get_logger(__name__)

__all__ = ["DoubanIsbnApiPipeline", "DoubanIsbnApiPipelineOptions"]


@dataclass
class DoubanIsbnApiPipelineOptions:
    """ISBN API 流水线配置."""
    excel_file: str
    barcode_column: str = "书目条码"
    isbn_column: str = "ISBN"
    # 反爬配置
    max_concurrent: int = 2
    qps: float = 0.5
    timeout: float = 15.0
    random_delay_min: float = 1.5
    random_delay_max: float = 3.5
    batch_cooldown_interval: int = 20
    batch_cooldown_min: float = 30.0
    batch_cooldown_max: float = 60.0
    # 重试配置
    retry_max_times: int = 3
    retry_backoff: List[float] = field(default_factory=lambda: [2, 5, 10])
    # 数据库配置
    disable_database: bool = False
    force_update: bool = False
    db_path: Optional[str] = None
    # 保存配置
    save_interval: int = 15
    # 报告配置
    generate_report: bool = True
    # 评分过滤配置
    enable_rating_filter: bool = True
    candidate_column: str = "候选状态"  # 与原流程保持一致，确保衔接模块4
    # ISBN 补充配置
    enable_isbn_supplement: bool = True
    isbn_supplement_min_threshold: int = 5  # 最小阈值，只有当需要补充的记录数>=此值时才启动FOLIO处理器


class DoubanIsbnApiPipeline:
    """豆瓣 ISBN API 流水线.

    流程步骤：
    1. 数据加载：读取 Excel，获取 ISBN 列
    2. ISBN 预处理：去除分隔符，校验格式，过滤无效 ISBN
    3. 数据库查重（可选）：检查是否已有数据
    4. ISBN API 调用：批量异步请求，带反爬策略
    5. 数据映射：复用 subject_mapper
    6. 实时写入 Excel
    7. 评分过滤（可选）：复用 DynamicThresholdFilter
    8. 结果输出：生成最终 Excel 和报告
    """

    STATUS_PENDING = "待处理"
    STATUS_DONE = "完成"
    STATUS_NOT_FOUND = "未找到"
    STATUS_INVALID_ISBN = "ISBN无效"
    STATUS_FROM_DB = "数据库已有"

    def __init__(self):
        self._config_manager = get_config_manager()

    def run(self, options: DoubanIsbnApiPipelineOptions) -> Tuple[str, Dict[str, Any]]:
        """执行流水线.

        Args:
            options: 流水线配置

        Returns:
            (output_file_path, stats_dict)
        """
        logger.info("=" * 60)
        logger.info("豆瓣 ISBN API 流水线启动")
        logger.info("=" * 60)

        # 加载配置
        full_config = self._config_manager.get_config()
        douban_config = self._config_manager.get_douban_config()
        field_mapping = full_config.get("fields_mapping", {}).get("douban", {})

        # 1. 数据加载
        logger.info("步骤 1: 加载数据")
        progress = ProgressManager(
            excel_file=options.excel_file,
            status_column="处理状态",
            save_interval=options.save_interval,
        )
        df = progress.load_dataframe()
        total_records = len(df)
        logger.info(f"加载数据完成，共 {total_records} 条记录")

        # 确保必要的列存在
        self._ensure_columns(df, field_mapping, options.candidate_column)

        # 2. ISBN 预处理
        logger.info("步骤 2: ISBN 预处理")
        isbn_stats = self._preprocess_isbn(df, options.isbn_column)
        logger.info(
            f"ISBN 预处理完成：有效 {isbn_stats['valid']} 条，"
            f"无效 {isbn_stats['invalid']} 条"
        )

        # 3. ISBN 补充（可选）
        # 优先从配置文件读取，其次使用 options 中的值
        isbn_api_config = douban_config.get("isbn_api", {})
        isbn_supplement_config = isbn_api_config.get("isbn_supplement", {})
        enable_isbn_supplement = isbn_supplement_config.get("enabled", options.enable_isbn_supplement)
        isbn_supplement_min_threshold = isbn_supplement_config.get("min_threshold", options.isbn_supplement_min_threshold)

        isbn_supplement_stats = {}
        if enable_isbn_supplement:
            logger.info("步骤 3: ISBN 补充检索")
            isbn_supplement_stats = self._supplement_isbn(
                df=df,
                options=options,
                progress=progress,
                douban_config=douban_config,
                min_threshold_override=isbn_supplement_min_threshold,
            )
            if isbn_supplement_stats.get("success", 0) > 0:
                # 重新进行 ISBN 预处理，因为可能有新的 ISBN 被补充
                logger.info("重新进行 ISBN 预处理...")
                isbn_stats = self._preprocess_isbn(df, options.isbn_column)
                logger.info(
                    f"ISBN 重新预处理完成：有效 {isbn_stats['valid']} 条，"
                    f"无效 {isbn_stats['invalid']} 条"
                )
        else:
            logger.info("步骤 3: 跳过 ISBN 补充（已禁用）")

        # 4. 数据库查重（可选）
        db_manager = None
        categories = None
        if not options.disable_database:
            logger.info("步骤 4: 数据库查重")
            db_manager, categories = self._database_check(
                df=df,
                options=options,
                douban_config=douban_config,
                field_mapping=field_mapping,
            )
            if categories:
                logger.info(
                    f"数据库查重完成：已有数据 {len(categories.get('existing_valid', []))} 条，"
                    f"需要获取 {len(categories.get('new', []))} 条"
                )
        else:
            logger.info("步骤 4: 跳过数据库查重（已禁用）")

        # 5. ISBN API 调用
        logger.info("步骤 5: 调用 ISBN API")
        api_stats = asyncio.run(
            self._call_isbn_api(
                df=df,
                options=options,
                progress=progress,
                field_mapping=field_mapping,
                categories=categories,
            )
        )
        logger.info(
            f"ISBN API 调用完成：成功 {api_stats['success']} 条，"
            f"失败 {api_stats['failed']} 条，"
            f"跳过 {api_stats['skipped']} 条"
        )

        # 6. 评分过滤（可选）
        filter_stats = {}
        if options.enable_rating_filter:
            logger.info("步骤 6: 评分过滤")
            filter_stats = self._apply_rating_filter(
                df=df,
                field_mapping=field_mapping,
                candidate_column=options.candidate_column,
            )
            logger.info(f"评分过滤完成：候选图书 {filter_stats.get('candidate_count', 0)} 本")
        else:
            logger.info("步骤 6: 跳过评分过滤（已禁用）")

        # 7. 数据库写入（如果启用）
        if db_manager and not options.disable_database:
            logger.info("步骤 7: 写入数据库")
            self._write_to_database(
                df=df,
                db_manager=db_manager,
                options=options,
                field_mapping=field_mapping,
            )

        # 8. 输出结果
        logger.info("步骤 8: 输出结果")
        output_file = self._finalize_output(
            df=df,
            progress=progress,
            options=options,
        )

        # 9. 生成报告（可选）
        report_file = None
        if options.generate_report:
            logger.info("步骤 9: 生成报告")
            report_file = self._generate_report(
                df=df,
                output_file=output_file,
                total_records=total_records,
                isbn_stats=isbn_stats,
                isbn_supplement_stats=isbn_supplement_stats,
                api_stats=api_stats,
                filter_stats=filter_stats,
            )

        # 关闭数据库连接
        if db_manager:
            db_manager.close()

        # 汇总统计
        stats = {
            "total_records": total_records,
            "valid_isbn_count": isbn_stats["valid"],
            "invalid_isbn_count": isbn_stats["invalid"],
            "isbn_supplement_total": isbn_supplement_stats.get("total", 0),
            "isbn_supplement_success": isbn_supplement_stats.get("success", 0),
            "isbn_supplement_failed": isbn_supplement_stats.get("failed", 0),
            "api_success_count": api_stats["success"],
            "api_failed_count": api_stats["failed"],
            "api_skipped_count": api_stats["skipped"],
            "candidate_count": filter_stats.get("candidate_count", 0),
            "output_file": output_file,
            "report_file": report_file,
        }

        logger.info("=" * 60)
        logger.info("豆瓣 ISBN API 流水线完成")
        logger.info(f"输出文件: {output_file}")
        if report_file:
            logger.info(f"报告文件: {report_file}")
        logger.info("=" * 60)

        return output_file, stats

    def _ensure_columns(
        self,
        df: pd.DataFrame,
        field_mapping: Dict[str, str],
        candidate_column: str,
    ) -> None:
        """确保必要的列存在."""
        for logical_key, column_name in field_mapping.items():
            if column_name not in df.columns:
                df[column_name] = ""

        # 确保处理状态列存在
        if "处理状态" not in df.columns:
            df["处理状态"] = self.STATUS_PENDING

        # 确保候选状态列存在（与原流程保持一致）
        if candidate_column and candidate_column not in df.columns:
            df[candidate_column] = ""

    def _preprocess_isbn(
        self,
        df: pd.DataFrame,
        isbn_column: str,
    ) -> Dict[str, int]:
        """预处理 ISBN 列.

        去除分隔符，校验格式，标记无效 ISBN。

        Returns:
            统计信息 {"valid": int, "invalid": int}
        """
        valid_count = 0
        invalid_count = 0

        # 添加标准化 ISBN 列
        df["_normalized_isbn"] = ""

        for idx in df.index:
            raw_isbn = df.at[idx, isbn_column] if isbn_column in df.columns else ""
            normalized = normalize_isbn(raw_isbn)

            if normalized:
                df.at[idx, "_normalized_isbn"] = normalized
                valid_count += 1
            else:
                df.at[idx, "_normalized_isbn"] = ""
                if pd.notna(raw_isbn) and str(raw_isbn).strip():
                    # 有值但格式无效
                    if df.at[idx, "处理状态"] == self.STATUS_PENDING:
                        df.at[idx, "处理状态"] = self.STATUS_INVALID_ISBN
                    invalid_count += 1

        return {"valid": valid_count, "invalid": invalid_count}

    def _supplement_isbn(
        self,
        df: pd.DataFrame,
        options: DoubanIsbnApiPipelineOptions,
        progress: ProgressManager,
        douban_config: Dict,
        min_threshold_override: Optional[int] = None,
    ) -> Dict[str, int]:
        """ISBN 补充检索.

        对 ISBN 为空且状态为"待处理"的记录进行 FOLIO ISBN 补充检索。

        Args:
            df: 数据框
            options: 流水线配置
            progress: 进度管理器
            douban_config: 豆瓣配置
            min_threshold_override: 覆盖最小阈值（从配置文件读取时使用）

        Returns:
            统计信息 {"total": int, "success": int, "failed": int, "skipped": int}
        """
        # 检查配置是否启用 ISBN 补充
        resolver_conf = (douban_config.get('isbn_resolver') if douban_config else {}) or {}
        if not resolver_conf.get('enabled', True):
            logger.info("[ISBN补充] 配置禁止了FOLIO ISBN检索，跳过补充阶段")
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "skipped": 0,
                "disabled": True,
            }

        isbn_column = options.isbn_column
        barcode_column = options.barcode_column
        # 优先使用覆盖值，其次使用 options 中的值
        min_threshold = min_threshold_override if min_threshold_override is not None else options.isbn_supplement_min_threshold

        logger.info("=" * 80)
        logger.info("[ISBN补充] 开始检查需要补充ISBN的记录")
        logger.info("=" * 80)

        # 筛选需要补充 ISBN 的行: ISBN为空 且 状态为"待处理"
        indices_to_process = []
        for index in df.index:
            # 检查 ISBN 是否为空
            isbn_value = str(df.at[index, isbn_column] if isbn_column in df.columns else "").strip()
            if isbn_value and isbn_value.lower() not in ["nan", "", "获取失败"]:
                continue

            # 检查状态是否为"待处理"
            status = df.at[index, "处理状态"]
            if status != self.STATUS_PENDING:
                continue

            # 检查是否有条码
            barcode = str(df.at[index, barcode_column] if barcode_column in df.columns else "").strip()
            if not barcode or barcode.lower() == "nan":
                continue

            indices_to_process.append(index)

        if not indices_to_process:
            logger.info("[ISBN补充] 无需补充ISBN的记录")
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "skipped": 0
            }

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
                "skipped": len(indices_to_process)
            }

        # 调用 FOLIO ISBN 处理器
        try:
            from src.core.douban.folio_isbn_async_processor import ISBNAsyncProcessor
            from src.core.douban.isbn_processor_config import (
                ProcessingConfig,
                get_config,
                load_config_from_yaml,
            )
            from dataclasses import replace as dataclass_replace

            # 获取配置
            isbn_config = douban_config.get('isbn_processor', {}) or {}
            processing_config = self._resolve_processing_config(isbn_config)

            # 创建处理器
            processor = ISBNAsyncProcessor(
                processing_config=processing_config,
                enable_database=False  # 补充阶段不使用数据库
            )

            # 获取 partial 文件路径
            partial_path = str(progress.partial_path)

            logger.info(f"[ISBN补充] 开始调用FOLIO处理器,处理 {len(indices_to_process)} 条记录")

            # 异步调用处理器
            _, stats = asyncio.run(processor.process_excel_file(
                excel_file_path=partial_path,
                barcode_column=barcode_column,
                output_column=isbn_column,
                retry_failed=True,
                target_indices=indices_to_process
            ))

            logger.info("[ISBN补充] FOLIO处理完成,开始更新状态")

            # 重新加载 DataFrame（因为处理器会修改 Excel 文件）
            df_updated = pd.read_excel(partial_path)

            # 更新状态
            success_count = 0
            failed_count = 0

            for index in indices_to_process:
                isbn_value = str(df_updated.at[index, isbn_column] if isbn_column in df_updated.columns else "").strip()

                if isbn_value and isbn_value not in ["", "nan", "获取失败"]:
                    # 成功获取ISBN，同步数据到 df
                    for col in df.columns:
                        if col in df_updated.columns:
                            df.at[index, col] = df_updated.at[index, col]
                    success_count += 1
                    logger.debug(f"[ISBN补充] 行{index+1}: 成功获取ISBN={isbn_value}")
                else:
                    # 仍然失败
                    failed_count += 1
                    logger.debug(f"[ISBN补充] 行{index+1}: 未能获取ISBN")

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
                "skipped": 0
            }

        except Exception as e:
            logger.error(f"[ISBN补充] 处理失败: {e}", exc_info=True)
            return {
                "total": len(indices_to_process),
                "success": 0,
                "failed": len(indices_to_process),
                "skipped": 0
            }

    def _resolve_processing_config(self, isbn_config: Dict[str, Any]):
        """根据配置字典构建 ProcessingConfig，优先复用全局配置策略."""
        from src.core.douban.isbn_processor_config import (
            ProcessingConfig,
            get_config,
            load_config_from_yaml,
        )
        from dataclasses import replace as dataclass_replace

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

    def _database_check(
        self,
        df: pd.DataFrame,
        options: DoubanIsbnApiPipelineOptions,
        douban_config: Dict,
        field_mapping: Dict[str, str],
    ) -> Tuple[Optional[DatabaseManager], Optional[Dict]]:
        """数据库查重.

        使用 DataChecker 进行数据分类：
        - existing_valid: 数据库有完整数据且未过期 → 跳过API
        - existing_valid_incomplete: 数据库有数据但不完整 → 需要调用API补充
        - existing_stale: 数据库有数据但已过期 → 需要调用API刷新
        - new: 数据库无记录 → 需要调用API获取

        Returns:
            (db_manager, categories)
        """
        from src.core.douban.database.data_checker import DataChecker

        db_config = douban_config.get("database", {})
        db_path = options.db_path or db_config.get("db_path", "runtime/database/books_history.db")

        try:
            db_manager = DatabaseManager(db_path)
            db_manager.init_database()

            # 构建 refresh_config，合并配置文件和命令行参数
            refresh_config = db_config.get("refresh_strategy", {}).copy()
            if options.force_update:
                refresh_config["force_update"] = True

            # 使用 DataChecker 进行分类
            data_checker = DataChecker(db_manager, refresh_config)

            # 构建 excel_data 列表供 DataChecker 使用
            excel_data: List[Dict] = []
            for idx, row in df.iterrows():
                data = row.to_dict()
                data["_index"] = idx
                data["barcode"] = str(row.get(options.barcode_column, "")).strip()
                excel_data.append(data)

            # 调用 DataChecker 进行分类
            categories = data_checker.check_and_categorize_books(excel_data)

            # 构建索引到分类的映射，用于后续判断
            self._row_category_map: Dict[int, str] = {}

            # 处理 existing_valid: 从数据库填充数据，标记为完成
            for item in categories.get("existing_valid", []):
                idx = item.get("_index")
                if idx is None:
                    continue
                barcode = str(item.get("barcode", "")).strip()
                df.at[idx, "处理状态"] = self.STATUS_FROM_DB
                self._row_category_map[idx] = "existing_valid"
                # 从数据库填充数据
                self._fill_from_database(
                    df=df,
                    idx=idx,
                    barcode=barcode,
                    db_manager=db_manager,
                    field_mapping=field_mapping,
                )

            # 处理 existing_valid_incomplete: 从数据库填充数据，但需要调用API补充
            for item in categories.get("existing_valid_incomplete", []):
                idx = item.get("_index")
                if idx is None:
                    continue
                barcode = str(item.get("barcode", "")).strip()
                df.at[idx, "处理状态"] = self.STATUS_PENDING  # 需要API补充
                self._row_category_map[idx] = "existing_valid_incomplete"
                # 先从数据库填充已有数据
                self._fill_from_database(
                    df=df,
                    idx=idx,
                    barcode=barcode,
                    db_manager=db_manager,
                    field_mapping=field_mapping,
                )

            # 处理 existing_stale: 从数据库填充基础数据，需要调用API刷新
            for item in categories.get("existing_stale", []):
                idx = item.get("_index")
                if idx is None:
                    continue
                barcode = str(item.get("barcode", "")).strip()
                df.at[idx, "处理状态"] = self.STATUS_PENDING  # 需要API刷新
                self._row_category_map[idx] = "existing_stale"
                # 先从数据库填充基础数据（ISBN等）
                self._fill_from_database(
                    df=df,
                    idx=idx,
                    barcode=barcode,
                    db_manager=db_manager,
                    field_mapping=field_mapping,
                )

            # 处理 new: 标记为待处理
            for item in categories.get("new", []):
                idx = item.get("_index")
                if idx is None:
                    continue
                df.at[idx, "处理状态"] = self.STATUS_PENDING
                self._row_category_map[idx] = "new"

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

    async def _call_isbn_api(
        self,
        df: pd.DataFrame,
        options: DoubanIsbnApiPipelineOptions,
        progress: ProgressManager,
        field_mapping: Dict[str, str],
        categories: Optional[Dict],
    ) -> Dict[str, int]:
        """调用 ISBN API.

        处理以下三类数据：
        - new: 新记录，需要调用API获取
        - existing_stale: 过期记录，需要调用API刷新
        - existing_valid_incomplete: 不完整记录，需要调用API补充

        Returns:
            统计信息 {"success": int, "failed": int, "skipped": int}
        """
        stats = {"success": 0, "failed": 0, "skipped": 0}

        # 确定需要处理的行
        to_process: List[Tuple[int, str]] = []  # (index, normalized_isbn)

        # 使用 _row_category_map 来判断哪些行需要处理
        # 需要处理的分类: new, existing_stale, existing_valid_incomplete
        need_api_categories = {"new", "existing_stale", "existing_valid_incomplete"}

        for idx in df.index:
            status = df.at[idx, "处理状态"]

            # 跳过已完成或已从数据库获取的完整记录
            if status in {self.STATUS_DONE, self.STATUS_FROM_DB, self.STATUS_NOT_FOUND, self.STATUS_INVALID_ISBN}:
                stats["skipped"] += 1
                continue

            # 检查是否在需要处理的分类中
            row_category = getattr(self, "_row_category_map", {}).get(idx)
            if row_category and row_category not in need_api_categories:
                stats["skipped"] += 1
                continue

            normalized_isbn = df.at[idx, "_normalized_isbn"]
            if not normalized_isbn:
                stats["skipped"] += 1
                continue

            to_process.append((idx, normalized_isbn))

        if not to_process:
            logger.info("没有需要处理的记录")
            return stats

        total = len(to_process)
        logger.info(f"需要调用 ISBN API: {total} 条记录")

        # 构建 API 配置
        api_config = IsbnApiConfig(
            max_concurrent=options.max_concurrent,
            qps=options.qps,
            timeout=options.timeout,
            random_delay_min=options.random_delay_min,
            random_delay_max=options.random_delay_max,
            batch_cooldown_interval=options.batch_cooldown_interval,
            batch_cooldown_min=options.batch_cooldown_min,
            batch_cooldown_max=options.batch_cooldown_max,
            retry_max_times=options.retry_max_times,
            retry_backoff=options.retry_backoff,
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

        async with IsbnApiClient(config=api_config) as client:
            for current, (idx, isbn) in enumerate(to_process, 1):
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
                        if "url" in payload:
                            url_col = field_mapping.get("url", "豆瓣链接")
                            if url_col in df.columns:
                                df.at[idx, url_col] = payload["url"]
                        elif "share_url" in payload:
                            url_col = field_mapping.get("url", "豆瓣链接")
                            if url_col in df.columns:
                                df.at[idx, url_col] = payload["share_url"]

                        df.at[idx, "处理状态"] = self.STATUS_DONE
                        stats["success"] += 1
                        logger.info(f"[{current}/{total}] ISBN {isbn} 获取成功")
                    else:
                        df.at[idx, "处理状态"] = self.STATUS_NOT_FOUND
                        stats["failed"] += 1
                        logger.warning(f"[{current}/{total}] ISBN {isbn} 未找到")

                except Exception as e:
                    df.at[idx, "处理状态"] = self.STATUS_NOT_FOUND
                    stats["failed"] += 1
                    logger.error(f"[{current}/{total}] ISBN {isbn} 获取失败: {e}")

                # 定期保存进度
                if current % options.save_interval == 0:
                    progress.save_partial(df, force=True, reason=f"progress_{current}")

        # 最终保存
        progress.save_partial(df, force=True, reason="api_complete")

        return stats

    def _apply_rating_filter(
        self,
        df: pd.DataFrame,
        field_mapping: Dict[str, str],
        candidate_column: str,
    ) -> Dict[str, Any]:
        """应用评分过滤.

        Args:
            df: 数据框
            field_mapping: 字段映射
            candidate_column: 候选状态列名（与原流程保持一致）

        Returns:
            统计信息
        """
        rating_col = field_mapping.get("rating", "豆瓣评分")
        rating_count_col = field_mapping.get("rating_count", "豆瓣评价人数")

        # 尝试识别索书号列
        call_number_col = None
        for col_name in ["索书号", "清理后索书号", "CLC号"]:
            if col_name in df.columns:
                call_number_col = col_name
                break

        try:
            filter_engine = DynamicThresholdFilter(source_df=df)
            dataset = filter_engine.prepare_dataset(
                df=df,
                rating_column=rating_col,
                call_number_column=call_number_col,
                rating_count_column=rating_count_col,
            )
            result = filter_engine.analyze(dataset)

            # 标记候选图书（使用配置的列名，与原流程保持一致）
            for idx in result.candidate_indexes:
                if idx in df.index:
                    df.at[idx, candidate_column] = "候选"

            return {
                "candidate_count": len(result.candidate_indexes),
                "total_samples": result.total_samples,
                "stats": result.stats,
            }

        except Exception as e:
            logger.error(f"评分过滤失败: {e}")
            return {"candidate_count": 0, "error": str(e)}

    def _write_to_database(
        self,
        df: pd.DataFrame,
        db_manager: DatabaseManager,
        options: DoubanIsbnApiPipelineOptions,
        field_mapping: Dict[str, str],
    ) -> None:
        """写入数据库.

        只写入以下分类的记录（排除 existing_valid，因为那些数据来自DB无需写回）：
        - new: API成功获取的新记录
        - existing_stale: API成功刷新的过期记录
        - existing_valid_incomplete: API成功补充的不完整记录
        """
        try:
            from .database.excel_to_database_writer import ExcelToDatabaseWriter

            full_config = self._config_manager.get_config()
            writer = ExcelToDatabaseWriter(full_config, update_mode="merge")

            # 需要写入数据库的分类
            write_to_db_categories = {"new", "existing_stale", "existing_valid_incomplete"}

            # 只写入成功获取数据且属于需要写入分类的记录
            books_data = []
            for idx in df.index:
                status = df.at[idx, "处理状态"]

                # 只处理状态为"完成"的记录
                if status != self.STATUS_DONE:
                    continue

                # 检查是否属于需要写入数据库的分类
                row_category = getattr(self, "_row_category_map", {}).get(idx)
                if row_category and row_category not in write_to_db_categories:
                    logger.debug(f"跳过写入DB - idx={idx}, category={row_category}")
                    continue

                row = df.loc[idx]
                payload = writer.build_single_payload(
                    row=row,
                    barcode_column=options.barcode_column,
                    isbn_column=options.isbn_column,
                    douban_fields_mapping=field_mapping,
                )
                if payload and payload[0]:
                    books_data.append(payload[0])

            if not books_data:
                logger.info("没有需要写入数据库的记录")
                return

            db_manager.batch_save_data(
                books_data=books_data,
                borrow_records_list=[],
                statistics_list=[],
                batch_size=100,
                update_mode="merge",
            )
            logger.info(f"成功写入数据库: {len(books_data)} 条记录")

        except Exception as e:
            logger.error(f"写入数据库失败: {e}")

    def _finalize_output(
        self,
        df: pd.DataFrame,
        progress: ProgressManager,
        options: DoubanIsbnApiPipelineOptions,
    ) -> str:
        """输出最终结果.

        Returns:
            输出文件路径
        """
        # 删除临时列
        if "_normalized_isbn" in df.columns:
            df.drop(columns=["_normalized_isbn"], inplace=True)

        # 生成输出文件名
        timestamp = get_timestamp()
        input_stem = Path(options.excel_file).stem

        # 如果输入文件名包含 _partial，去掉这个后缀
        if input_stem.endswith("_partial"):
            input_stem = input_stem[:-8]

        output_dir = Path("runtime/outputs")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"{input_stem}_ISBN_API结果_{timestamp}.xlsx"

        # 保存最终文件
        progress.finalize_output(output_file, df)

        return str(output_file)

    def _generate_report(
        self,
        df: pd.DataFrame,
        output_file: str,
        total_records: int,
        isbn_stats: Dict[str, int],
        isbn_supplement_stats: Dict[str, int],
        api_stats: Dict[str, int],
        filter_stats: Dict[str, Any],
    ) -> str:
        """生成处理报告.

        Returns:
            报告文件路径
        """
        timestamp = get_timestamp()
        output_dir = Path("runtime/outputs")
        report_file = output_dir / f"ISBN_API_处理报告_{timestamp}.txt"

        lines = [
            "=" * 60,
            "豆瓣 ISBN API 处理报告",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            "",
            "【数据概览】",
            f"  总记录数: {total_records}",
            f"  有效 ISBN: {isbn_stats['valid']}",
            f"  无效 ISBN: {isbn_stats['invalid']}",
            "",
        ]

        # 添加 ISBN 补充统计
        if isbn_supplement_stats.get("total", 0) > 0 or isbn_supplement_stats.get("disabled"):
            lines.extend([
                "【ISBN 补充统计】",
            ])
            if isbn_supplement_stats.get("disabled"):
                lines.append("  状态: 已禁用（配置关闭）")
            else:
                lines.extend([
                    f"  需补充记录: {isbn_supplement_stats.get('total', 0)}",
                    f"  成功补充: {isbn_supplement_stats.get('success', 0)}",
                    f"  补充失败: {isbn_supplement_stats.get('failed', 0)}",
                    f"  跳过: {isbn_supplement_stats.get('skipped', 0)}",
                ])
            lines.append("")

        lines.extend([
            "【API 调用统计】",
            f"  成功获取: {api_stats['success']}",
            f"  未找到: {api_stats['failed']}",
            f"  跳过: {api_stats['skipped']}",
            f"  成功率: {api_stats['success'] / max(1, api_stats['success'] + api_stats['failed']) * 100:.1f}%",
            "",
            "【评分过滤统计】",
            f"  候选图书数: {filter_stats.get('candidate_count', 0)}",
            f"  总样本数: {filter_stats.get('total_samples', 0)}",
            "",
            "【输出文件】",
            f"  Excel: {output_file}",
            "",
        ])

        # 添加分类统计
        if filter_stats.get("stats"):
            lines.append("【分类详情】")
            for stat in filter_stats["stats"]:
                lines.append(
                    f"  {stat['letter']}: "
                    f"总数={stat['total']}, "
                    f"候选={stat.get('candidate_count', 0)}, "
                    f"阈值={stat.get('score_threshold', 'N/A')}"
                )
            lines.append("")

        lines.append("=" * 60)

        with open(report_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"报告已生成: {report_file}")
        return str(report_file)
