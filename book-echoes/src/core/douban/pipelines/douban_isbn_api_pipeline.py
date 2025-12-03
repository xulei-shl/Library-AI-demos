#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""豆瓣 ISBN API 流水线.

通过 ISBN 直接调用豆瓣 API 获取图书信息的完整流水线，
包含 FOLIO ISBN 爬取、ISBN 预处理、API 调用、评分过滤和结果输出。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.utils.config_manager import get_config_manager
from src.utils.logger import get_logger

from src.core.douban.progress_manager import ProgressManager
from src.core.douban.isbn_processor_config import (
    get_config,
    load_config_from_yaml,
)

from .isbn_api_steps import (
    ProcessStatus,
    IsbnPreprocessor,
    DatabaseChecker,
    ApiCaller,
    RatingFilterStep,
    DatabaseWriter,
    ReportGenerator,
)

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
    candidate_column: str = "候选状态"
    # ISBN 补充配置
    enable_isbn_supplement: bool = True
    isbn_supplement_min_threshold: int = 5


class DoubanIsbnApiPipeline:
    """豆瓣 ISBN API 流水线.

    流程步骤：
    1. 数据加载：读取 Excel，获取 ISBN 列
    2. ISBN 预处理：去除分隔符，校验格式，过滤无效 ISBN
    3. FOLIO ISBN 爬取（主流程）：对缺失 ISBN 的记录批量获取
    4. ISBN 补充（兜底）：对仍缺失 ISBN 的记录进行补充重试
    5. 数据库查重（可选）：检查是否已有数据
    6. ISBN API 调用：批量异步请求，带反爬策略
    7. 评分过滤（可选）：根据评分筛选候选图书
    8. 数据库写入：将所有 API 成功获取的数据写入数据库
    9. 结果输出：生成最终 Excel
    10. 生成报告（可选）：生成处理报告
    """

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

        # 步骤 1: 数据加载
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

        # 步骤 2: ISBN 预处理
        logger.info("步骤 2: ISBN 预处理")
        preprocessor = IsbnPreprocessor(
            isbn_column=options.isbn_column,
            barcode_column=options.barcode_column,
        )
        isbn_stats = preprocessor.preprocess(df)
        logger.info(f"ISBN 预处理完成：有效 {isbn_stats['valid']} 条，无效 {isbn_stats['invalid']} 条")

        # 步骤 3: FOLIO ISBN 主爬取
        folio_stats = self._run_folio_isbn_fetch(
            df, options, progress, douban_config
        )

        # 如果 FOLIO 爬取有成功记录，重新预处理
        if folio_stats.get("success_count", 0) > 0:
            logger.info("FOLIO 爬取完成，重新进行 ISBN 预处理...")
            isbn_stats = preprocessor.preprocess(df)
            logger.info(
                f"ISBN 重新预处理完成：有效 {isbn_stats['valid']} 条，"
                f"无效 {isbn_stats['invalid']} 条"
            )

        # 步骤 4: ISBN 补充（兜底重试）
        isbn_supplement_stats = self._run_isbn_supplement(
            df, options, progress, douban_config, preprocessor
        )

        # 步骤 5: 数据库查重（可选）
        db_manager, db_checker = self._run_database_check(
            df, options, douban_config, field_mapping, progress
        )

        # 步骤 6: ISBN API 调用
        logger.info("步骤 6: 调用 ISBN API")
        api_caller = ApiCaller(
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
            save_interval=options.save_interval,
        )
        row_category_map = db_checker.row_category_map if db_checker else {}
        api_stats = asyncio.run(
            api_caller.call_api(df, progress, field_mapping, row_category_map)
        )
        logger.info(
            f"ISBN API 调用完成：成功 {api_stats['success']} 条，"
            f"失败 {api_stats['failed']} 条，跳过 {api_stats['skipped']} 条"
        )

        # 步骤 7: 评分过滤（可选）
        filter_stats = self._run_rating_filter(df, options, field_mapping)

        # 步骤 8: 数据库写入
        if db_manager and not options.disable_database:
            logger.info("步骤 8: 写入数据库")
            db_writer = DatabaseWriter(
                barcode_column=options.barcode_column,
                isbn_column=options.isbn_column,
            )
            db_writer.write_to_database(df, db_manager, field_mapping, row_category_map)

        # 步骤 9-10: 输出结果和生成报告
        report_gen = ReportGenerator()
        logger.info("步骤 9: 输出结果")
        output_file = report_gen.finalize_output(df, progress, options.excel_file)

        report_file = None
        if options.generate_report:
            logger.info("步骤 10: 生成报告")
            report_file = report_gen.generate_report(
                df, output_file, total_records, isbn_stats,
                isbn_supplement_stats, api_stats, filter_stats, folio_stats
            )

        # 关闭数据库连接
        if db_manager:
            db_manager.close()

        # 汇总统计
        stats = {
            "total_records": total_records,
            "valid_isbn_count": isbn_stats["valid"],
            "invalid_isbn_count": isbn_stats["invalid"],
            "folio_total": folio_stats.get("total_records", 0),
            "folio_success": folio_stats.get("success_count", 0),
            "folio_failed": folio_stats.get("failed_count", 0),
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
        for _, column_name in field_mapping.items():
            if column_name not in df.columns:
                df[column_name] = ""

        if "处理状态" not in df.columns:
            df["处理状态"] = ProcessStatus.PENDING

        if candidate_column and candidate_column not in df.columns:
            df[candidate_column] = ""

    def _run_isbn_supplement(
        self,
        df: pd.DataFrame,
        options: DoubanIsbnApiPipelineOptions,
        progress: ProgressManager,
        douban_config: Dict,
        preprocessor: IsbnPreprocessor,
    ) -> Dict[str, int]:
        """运行 ISBN 补充步骤（兜底重试）."""
        isbn_api_config = douban_config.get("isbn_api", {})
        isbn_supplement_config = isbn_api_config.get("isbn_supplement", {})
        enable = isbn_supplement_config.get("enabled", options.enable_isbn_supplement)
        min_threshold = isbn_supplement_config.get(
            "min_threshold", options.isbn_supplement_min_threshold
        )

        if not enable:
            logger.info("步骤 4: 跳过 ISBN 补充（已禁用）")
            return {}

        logger.info("步骤 4: ISBN 补充检索（兜底重试）")
        isbn_supplement_stats = preprocessor.supplement_isbn(
            df=df,
            progress=progress,
            douban_config=douban_config,
            min_threshold=min_threshold,
            enable_supplement=enable,
        )

        if isbn_supplement_stats.get("success", 0) > 0:
            logger.info("重新进行 ISBN 预处理...")
            isbn_stats = preprocessor.preprocess(df)
            logger.info(
                f"ISBN 重新预处理完成：有效 {isbn_stats['valid']} 条，"
                f"无效 {isbn_stats['invalid']} 条"
            )

        return isbn_supplement_stats

    def _run_folio_isbn_fetch(
        self,
        df: pd.DataFrame,
        options: DoubanIsbnApiPipelineOptions,
        progress: ProgressManager,
        douban_config: Dict,
    ) -> Dict[str, Any]:
        """运行 FOLIO ISBN 主爬取步骤.

        当 isbn_resolver.enabled=true 时，对所有缺失 ISBN 的记录进行批量爬取。
        """
        resolver_conf = douban_config.get("isbn_resolver", {}) or {}

        if not resolver_conf.get("enabled", True):
            logger.info("步骤 3: 跳过 FOLIO ISBN 爬取（配置 isbn_resolver.enabled=false）")
            return {"skipped": True, "reason": "disabled_in_config"}

        # 检查有多少记录需要爬取 ISBN
        missing_isbn_count = self._count_missing_isbn(df, options.isbn_column, options.barcode_column)

        if missing_isbn_count == 0:
            logger.info("步骤 3: 跳过 FOLIO ISBN 爬取（所有记录已有 ISBN）")
            return {"skipped": True, "reason": "all_have_isbn", "total_records": 0}

        logger.info("步骤 3: FOLIO ISBN 主爬取")
        logger.info(f"需要爬取 ISBN 的记录数: {missing_isbn_count} 条")

        try:
            from src.core.douban.folio_isbn_async_processor import process_isbn_async

            # 获取处理配置
            isbn_config = douban_config.get("isbn_processor", {}) or {}
            processing_config = self._resolve_processing_config(isbn_config)

            # 构建数据库配置
            db_config = self._build_db_config(options, douban_config)

            # 保存当前进度到文件，供 FOLIO 处理器使用
            progress.save_partial(df, force=True, reason="before_folio_fetch")
            partial_path = str(progress.partial_path)

            # 调用 FOLIO ISBN 异步处理器
            output_file, stats = process_isbn_async(
                excel_file_path=partial_path,
                max_concurrent=processing_config.max_concurrent if processing_config else 3,
                save_interval=options.save_interval,
                barcode_column=options.barcode_column,
                output_column=options.isbn_column,
                retry_failed=True,
                enable_database=not options.disable_database,
                db_config=db_config,
                processing_config=processing_config,
            )

            # 重新加载 DataFrame（FOLIO 处理器会修改 Excel 文件）
            df_updated = pd.read_excel(output_file)

            # 同步数据到原 df
            for col in df.columns:
                if col in df_updated.columns:
                    df[col] = df_updated[col]

            # 同步新增的列（如 ISBN 列）
            for col in df_updated.columns:
                if col not in df.columns:
                    df[col] = df_updated[col]

            logger.info("=" * 60)
            logger.info("FOLIO ISBN 爬取完成:")
            logger.info(f"  总记录数: {stats.get('total_records', 0)}")
            logger.info(f"  成功获取: {stats.get('success_count', 0)}")
            logger.info(f"  获取失败: {stats.get('failed_count', 0)}")
            logger.info("=" * 60)

            return stats or {}

        except Exception as e:
            logger.error(f"FOLIO ISBN 爬取失败: {e}", exc_info=True)
            return {
                "error": str(e),
                "total_records": missing_isbn_count,
                "success_count": 0,
                "failed_count": missing_isbn_count,
            }

    def _count_missing_isbn(
        self,
        df: pd.DataFrame,
        isbn_column: str,
        barcode_column: str,
    ) -> int:
        """统计缺失 ISBN 的记录数."""
        count = 0
        for idx in df.index:
            # 检查 ISBN 是否为空
            isbn_value = ""
            if isbn_column in df.columns:
                isbn_value = str(df.at[idx, isbn_column]).strip()

            if isbn_value and isbn_value.lower() not in ["nan", "", "获取失败"]:
                continue

            # 检查是否有条码（有条码才能爬取）
            barcode = ""
            if barcode_column in df.columns:
                barcode = str(df.at[idx, barcode_column]).strip()

            if barcode and barcode.lower() != "nan":
                count += 1

        return count

    def _resolve_processing_config(self, isbn_config: Dict[str, Any]):
        """根据配置字典构建 ProcessingConfig."""
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

    def _build_db_config(
        self,
        options: DoubanIsbnApiPipelineOptions,
        douban_config: Dict,
    ) -> Dict[str, Any]:
        """构建数据库配置."""
        db_config = (douban_config.get("database") or {}).copy()

        if options.force_update:
            db_config.setdefault("refresh_strategy", {})["force_update"] = True
        if options.db_path:
            db_config["db_path"] = options.db_path

        return db_config

    def _run_database_check(
        self,
        df: pd.DataFrame,
        options: DoubanIsbnApiPipelineOptions,
        douban_config: Dict,
        field_mapping: Dict[str, str],
        progress: Optional[ProgressManager] = None,
    ) -> Tuple[Any, Optional[DatabaseChecker]]:
        """运行数据库查重步骤."""
        if options.disable_database:
            logger.info("步骤 5: 跳过数据库查重（已禁用）")
            return None, None

        logger.info("步骤 5: 数据库查重")
        db_checker = DatabaseChecker(barcode_column=options.barcode_column)
        db_manager, categories = db_checker.check_and_categorize(
            df=df,
            douban_config=douban_config,
            field_mapping=field_mapping,
            progress=progress,
            db_path=options.db_path,
            force_update=options.force_update,
        )

        if categories:
            logger.info(
                f"数据库查重完成：已有数据 {len(categories.get('existing_valid', []))} 条，"
                f"需要获取 {len(categories.get('new', []))} 条"
            )

        return db_manager, db_checker

    def _run_rating_filter(
        self,
        df: pd.DataFrame,
        options: DoubanIsbnApiPipelineOptions,
        field_mapping: Dict[str, str],
    ) -> Dict[str, Any]:
        """运行评分过滤步骤.

        优先读取配置文件中的 rating_filter.dynamic_filter_enabled 开关，
        如果配置为 false，则跳过动态评分过滤（适用于新书数据，后续使用命令10单独过滤）。
        """
        # 从配置文件读取动态过滤开关
        full_config = self._config_manager.get_config()
        rating_filter_config = full_config.get("rating_filter", {})
        dynamic_filter_enabled = rating_filter_config.get("dynamic_filter_enabled", True)

        # 如果配置禁用动态过滤，则跳过
        if not dynamic_filter_enabled:
            logger.info("步骤 7: 跳过评分过滤（配置 rating_filter.dynamic_filter_enabled=false）")
            return {}

        # 如果选项禁用评分过滤，则跳过
        if not options.enable_rating_filter:
            logger.info("步骤 7: 跳过评分过滤（已禁用）")
            return {}

        logger.info("步骤 7: 评分过滤")
        rating_filter = RatingFilterStep(candidate_column=options.candidate_column)
        filter_stats = rating_filter.apply_filter(df, field_mapping)
        logger.info(f"评分过滤完成：候选图书 {filter_stats.get('candidate_count', 0)} 本")

        return filter_stats
