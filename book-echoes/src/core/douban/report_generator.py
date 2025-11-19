#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Report generator for the Douban rating pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

import pandas as pd

from src.core.douban.analytics import ThemeRatingAnalyzer
from src.core.douban.progress_manager import ProgressManager
from src.utils.logger import get_logger


logger = get_logger(__name__)


@dataclass
class ReportMetrics:
    """Container for aggregated report data."""

    total_rows: int
    status_counts: Dict[str, int]
    completed_count: int
    success_count: int
    no_data_count: int
    pending_count: int
    success_rate: float
    missing_rating_count: int
    rating_available_count: int
    candidate_count: int
    api_pending_count: int
    link_ready_count: int
    link_pending_count: int
    db_done_count: int
    rating_stats: Dict[str, Any]
    rating_buckets: Dict[str, int]
    resolved_columns: Dict[str, Optional[str]] = field(default_factory=dict)
    status_display: Dict[str, str] = field(default_factory=dict)


class DoubanReportGenerator:
    """Generate text report for the Douban module."""

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        """
        Initialize generator.

        Args:
            output_dir: Optional output directory, defaults to runtime/outputs.
        """
        self.output_dir = Path(output_dir) if output_dir else Path("runtime/outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._theme_buckets = ThemeRatingAnalyzer.BUCKETS

    def generate_report(
        self,
        df: pd.DataFrame,
        status_column: str,
        field_mapping: Dict[str, str],
        final_excel_path: str,
        categories: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Build and write the report file.

        Raises:
            ValueError: if required columns are missing.
        """
        if status_column not in df.columns:
            raise ValueError("数据中缺少处理状态列，无法生成报告")

        metrics = self._collect_metrics(df, status_column, field_mapping)
        report_lines = self._build_report_lines(
            metrics=metrics,
            categories=categories,
            df=df,
            field_mapping=field_mapping,
            final_excel_path=final_excel_path,
        )

        excel_path = Path(final_excel_path)
        report_name = f"{excel_path.stem}_分析报告_{datetime.now():%Y%m%d_%H%M%S}.txt"
        report_file = excel_path.parent / report_name
        report_file.write_text("\n".join(report_lines), encoding="utf-8")
        logger.info("豆瓣任务分析报告已生成: %s", report_file)
        return report_file

    def _collect_metrics(
        self, df: pd.DataFrame, status_column: str, field_mapping: Dict[str, str]
    ) -> ReportMetrics:
        """Collect and compute metrics used in the final report."""
        total_rows = len(df)
        status_series = df[status_column].fillna("")
        status_counts = status_series.value_counts(dropna=False).to_dict()
        done_statuses = {
            ProgressManager.STATUS_DOUBAN_DONE,
            getattr(ProgressManager, "STATUS_DONE", ProgressManager.STATUS_DOUBAN_DONE),
        }

        rating_col = self._resolve_column_name(
            df, field_mapping, ("rating", "douban_rating", "评分", "豆瓣评分")
        )
        if rating_col:
            rating_series = pd.to_numeric(df[rating_col], errors="coerce")
        else:
            rating_series = pd.Series([float("nan")] * len(df), index=df.index, dtype=float)
        status_done_mask = status_series.isin(done_statuses)
        success_mask = status_done_mask & rating_series.notna()
        success_count = int(success_mask.sum())
        completed_count = int(status_done_mask.sum())

        title_col = self._resolve_column_name(
            df, field_mapping, ("title", "book_title", "题名", "书名")
        )
        if title_col:
            title_series = df[title_col].fillna("")
        else:
            title_series = pd.Series([""] * len(df), index=df.index, dtype=str)
        no_data_mask = title_series.astype(str).str.contains("豆瓣无数据", na=False)
        no_data_count = int(no_data_mask.sum())

        failure_mask = status_done_mask & rating_series.isna() & (~no_data_mask)
        pending_count = int((~status_done_mask).sum())
        success_rate = (success_count / total_rows) if total_rows else 0.0

        rating_stats = self._build_rating_stats(rating_series)
        rating_buckets = self._build_rating_distribution(rating_series)

        barcode_col = self._resolve_column_name(
            df, field_mapping, ("barcode", "书目条码", "条码")
        )
        candidate_col = self._resolve_candidate_column(df)
        candidate_count = 0
        if candidate_col:
            candidate_count = int(df[candidate_col].fillna("").astype(str).str.strip().astype(bool).sum())

        api_pending_count = int(
            status_series.str.fullmatch(str(ProgressManager.STATUS_API_PENDING)).sum()
        )
        link_ready_count = int(
            status_series.str.fullmatch(str(ProgressManager.STATUS_LINK_READY)).sum()
        )
        link_pending_count = int(
            status_series.str.fullmatch(str(ProgressManager.STATUS_LINK_PENDING)).sum()
        )
        db_done_count = int(
            status_series.str.fullmatch(str(ProgressManager.STATUS_DB_DONE)).sum()
        )

        return ReportMetrics(
            total_rows=total_rows,
            status_counts=status_counts,
            completed_count=completed_count,
            success_count=success_count,
            no_data_count=no_data_count,
            pending_count=pending_count,
            success_rate=success_rate,
            missing_rating_count=int(failure_mask.sum()),
            rating_available_count=int(rating_series.notna().sum()),
            candidate_count=candidate_count,
            api_pending_count=api_pending_count,
            link_ready_count=link_ready_count,
            link_pending_count=link_pending_count,
            db_done_count=db_done_count,
            rating_stats=rating_stats,
            rating_buckets=rating_buckets,
            resolved_columns={
                "rating": rating_col,
                "title": title_col,
                "barcode": barcode_col,
                "candidate": candidate_col,
            },
            status_display=self._build_status_display(),
        )

    def _build_report_lines(
        self,
        metrics: ReportMetrics,
        categories: Optional[Dict[str, Any]],
        df: pd.DataFrame,
        field_mapping: Dict[str, str],
        final_excel_path: str,
    ) -> list[str]:
        """Assemble the text report."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "=" * 70,
            "书海回响 · 模块3 豆瓣任务分析报告",
            "=" * 70,
            f"生成时间: {timestamp}",
            f"结果文件: {final_excel_path}",
            "",
            "【处理概览】",
            f"输入总行数: {metrics.total_rows}",
            f"已完成: {metrics.completed_count}",
            f"待处理: {metrics.pending_count}",
            f"已获取评分: {metrics.success_count}",
            f"缺失评分(已完成): {metrics.missing_rating_count}",
            f"豆瓣无数据标记: {metrics.no_data_count}",
            f"评分填充率(全部行): {metrics.success_rate:.2%}",
        ]
        if metrics.candidate_count:
            lines.append(f"动态筛选候选数: {metrics.candidate_count}")

        lines.append("")
        lines.append("【阶段进度】")
        ordered_statuses = [
            ProgressManager.STATUS_DB_DONE,
            ProgressManager.STATUS_LINK_PENDING,
            ProgressManager.STATUS_LINK_READY,
            ProgressManager.STATUS_API_PENDING,
            ProgressManager.STATUS_DONE,
            ProgressManager.STATUS_DOUBAN_DONE,
            ProgressManager.STATUS_PENDING,
        ]
        printed_keys = set()
        for key in ordered_statuses:
            if key not in metrics.status_counts:
                continue
            printed_keys.add(key)
            label = metrics.status_display.get(key, key or "空状态")
            lines.append(f"  - {label}: {metrics.status_counts.get(key, 0)}")
        for status, count in metrics.status_counts.items():
            if status in printed_keys:
                continue
            label = metrics.status_display.get(status, status or "空状态")
            lines.append(f"  - {label}: {count}")

        lines.extend(
            [
                "",
                "【评分统计】",
                f"有效评分数量: {metrics.rating_stats['count']}",
                f"平均分: {metrics.rating_stats['mean']}",
                f"中位数: {metrics.rating_stats['median']}",
                f"标准差: {metrics.rating_stats['std']}",
                f"最低分: {metrics.rating_stats['min']}",
                f"最高分: {metrics.rating_stats['max']}",
                "",
                "评分分布（按主题分段定义）:",
            ]
        )
        for bucket, count in metrics.rating_buckets.items():
            lines.append(f"  - {bucket}: {count}")

        if categories:
            lines.append("")
            lines.append("【数据库写入分类】")
            for name, rows in categories.items():
                lines.append(f"  - {name}: {len(rows or [])}")

        lines.extend(
            [
                "",
                "【数据质量提醒】",
                f"评分缺失但已完成: {metrics.missing_rating_count}",
                f"待补API状态数: {metrics.api_pending_count}",
                f"标记为候选的记录: {metrics.candidate_count}",
                f"待补链接状态数: {metrics.link_pending_count}",
                f"已获取链接状态数: {metrics.link_ready_count}",
                "说明:",
                "  - 评分缺失但已完成: 状态为已完成但评分为空（排除“无数据”标记）的记录数。",
                "  - 待补API状态数: 状态列值为“待补API”的记录数。",
                "  - 标记为候选的记录: 在候选标记列中标记为True或非空的记录数。",
                "  - 待补链接状态数: 状态列值为“待补链接”的记录数。",
                "  - 已获取链接状态数: 状态列值为“链接已获取”的记录数。",
            ]
        )

        # 在主要区块追加固定说明
        lines.insert(lines.index("【处理概览】") + 1,
                     "说明: 本区块统计任务总体进度，数据来源自状态列与评分列。")
        lines.insert(lines.index("【阶段进度】") + 1,
                     "说明: 按预定义顺序逐个列出状态列中的值及对应行数。")
        lines.insert(lines.index("【评分统计】") + 1,
                     "说明: 对评分列进行基础统计与主题分段分布分析。")
        if categories:
            lines.insert(lines.index("【数据库写入分类】") + 1,
                         "说明: 按调用方提供的分组结果统计各分类行数。")

        return lines

    def _build_rating_stats(self, rating_series: pd.Series) -> Dict[str, Any]:
        """Create a dict with rating statistics."""
        stats = {
            "count": 0,
            "mean": "N/A",
            "median": "N/A",
            "std": "N/A",
            "min": "N/A",
            "max": "N/A",
        }
        if rating_series.empty:
            return stats
        valid = rating_series.dropna()
        if valid.empty:
            return stats
        stats.update(
            {
                "count": int(valid.count()),
                "mean": f"{valid.mean():.2f}",
                "median": f"{valid.median():.2f}",
                "std": f"{valid.std():.2f}" if valid.count() > 1 else "0.00",
                "min": f"{valid.min():.1f}",
                "max": f"{valid.max():.1f}",
            }
        )
        return stats

    def _build_rating_distribution(self, rating_series: pd.Series) -> Dict[str, int]:
        """Build rating distribution using ThemeRatingAnalyzer buckets."""
        buckets: Dict[str, int] = {bucket.description: 0 for bucket in self._theme_buckets}
        if rating_series.empty or rating_series.dropna().empty:
            return buckets
        valid = rating_series.dropna()
        for bucket in self._theme_buckets:
            mask = self._build_bucket_mask(valid, bucket)
            buckets[bucket.description] = int(mask.sum())
        return buckets

    def _build_bucket_mask(self, ratings: pd.Series, bucket) -> pd.Series:
        """Generate boolean mask for a bucket definition."""
        mask = pd.Series(True, index=ratings.index)
        if bucket.lower is not None:
            if bucket.include_lower:
                mask &= ratings >= bucket.lower
            else:
                mask &= ratings > bucket.lower
        if bucket.upper is not None:
            if bucket.include_upper:
                mask &= ratings <= bucket.upper
            else:
                mask &= ratings < bucket.upper
        return mask

    def _resolve_column_name(
        self,
        df: pd.DataFrame,
        field_mapping: Dict[str, str],
        candidates: Sequence[str],
    ) -> Optional[str]:
        """Resolve logical column names to actual DataFrame columns."""
        for key in candidates:
            if not key:
                continue
            mapped = field_mapping.get(key)
            if mapped and mapped in df.columns:
                return mapped
            if key in df.columns:
                return key
        return None

    def _resolve_candidate_column(self, df: pd.DataFrame) -> Optional[str]:
        """Locate candidate flag column if it exists."""
        candidates = [
            "候选状态",
            "候选标记",
            "候选",
            "candidate",
            "is_candidate",
        ]
        for name in candidates:
            if name in df.columns:
                return name
        return None

    def _build_status_display(self) -> Dict[str, str]:
        """Readable labels for status values."""
        return {
            ProgressManager.STATUS_PENDING: "待处理",
            ProgressManager.STATUS_DB_DONE: "数据库已写回",
            ProgressManager.STATUS_LINK_PENDING: "待补链接",
            ProgressManager.STATUS_LINK_READY: "链接已获取",
            ProgressManager.STATUS_API_PENDING: "待补API",
            ProgressManager.STATUS_DONE: "完成",
            ProgressManager.STATUS_DOUBAN_DONE: "豆瓣完成",
        }