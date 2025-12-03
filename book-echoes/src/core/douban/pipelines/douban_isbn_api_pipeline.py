#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""豆瓣 ISBN API 流水线.

通过 ISBN 直接调用豆瓣 API 获取图书信息的完整流水线，
包含 ISBN 预处理、API 调用、评分过滤和结果输出。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.utils.config_manager import get_config_manager
from src.utils.logger import get_logger

from src.core.douban.progress_manager import ProgressManager

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
    3. ISBN 补充（可选）：通过 FOLIO 获取缺失的 ISBN
    4. 数据库查重（可选）：检查是否已有数据
    5. ISBN API 调用：批量异步请求，带反爬策略
    6. 评分过滤（可选）：根据评分筛选候选图书
    7. 数据库写入：将所有 API 成功获取的数据写入数据库
    8. 结果输出：生成最终 Excel
    9. 生成报告（可选）：生成处理报告
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

        # 步骤 3: ISBN 补充（可选）
        isbn_supplement_stats = self._run_isbn_supplement(
            df, options, progress, douban_config, preprocessor
        )

        # 步骤 4: 数据库查重（可选）
        db_manager, db_checker = self._run_database_check(
            df, options, douban_config, field_mapping, progress
        )

        # 步骤 5: ISBN API 调用
        logger.info("步骤 5: 调用 ISBN API")
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

        # 步骤 6: 评分过滤（可选）
        filter_stats = self._run_rating_filter(df, options, field_mapping)

        # 步骤 7: 数据库写入
        if db_manager and not options.disable_database:
            logger.info("步骤 7: 写入数据库")
            db_writer = DatabaseWriter(
                barcode_column=options.barcode_column,
                isbn_column=options.isbn_column,
            )
            db_writer.write_to_database(df, db_manager, field_mapping, row_category_map)

        # 步骤 8-9: 输出结果和生成报告
        report_gen = ReportGenerator()
        logger.info("步骤 8: 输出结果")
        output_file = report_gen.finalize_output(df, progress, options.excel_file)

        report_file = None
        if options.generate_report:
            logger.info("步骤 9: 生成报告")
            report_file = report_gen.generate_report(
                df, output_file, total_records, isbn_stats,
                isbn_supplement_stats, api_stats, filter_stats
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
        """运行 ISBN 补充步骤."""
        isbn_api_config = douban_config.get("isbn_api", {})
        isbn_supplement_config = isbn_api_config.get("isbn_supplement", {})
        enable = isbn_supplement_config.get("enabled", options.enable_isbn_supplement)
        min_threshold = isbn_supplement_config.get(
            "min_threshold", options.isbn_supplement_min_threshold
        )

        if not enable:
            logger.info("步骤 3: 跳过 ISBN 补充（已禁用）")
            return {}

        logger.info("步骤 3: ISBN 补充检索")
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
            logger.info("步骤 4: 跳过数据库查重（已禁用）")
            return None, None

        logger.info("步骤 4: 数据库查重")
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
        """运行评分过滤步骤."""
        if not options.enable_rating_filter:
            logger.info("步骤 6: 跳过评分过滤（已禁用）")
            return {}

        logger.info("步骤 6: 评分过滤")
        rating_filter = RatingFilterStep(candidate_column=options.candidate_column)
        filter_stats = rating_filter.apply_filter(df, field_mapping)
        logger.info(f"评分过滤完成：候选图书 {filter_stats.get('candidate_count', 0)} 本")

        return filter_stats
