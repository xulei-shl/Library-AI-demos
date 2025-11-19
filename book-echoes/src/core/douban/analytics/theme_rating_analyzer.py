#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate rating-bucket statistics based on Douban crawl results."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd

from src.utils.logger import get_logger
from .dynamic_threshold_filter import (
    DynamicFilterResult,
    DynamicThresholdFilter,
    UNKNOWN_CALL_VALUE as FILTER_UNKNOWN_CALL_VALUE,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class RatingBucket:
    """Describe a closed or open interval for ratings."""

    label: str
    description: str
    lower: Optional[float] = None
    upper: Optional[float] = None
    include_lower: bool = True
    include_upper: bool = False


class ThemeRatingAnalyzer:
    """Builds rating distribution summaries grouped by call-number themes."""

    UNKNOWN_CALL_VALUE = FILTER_UNKNOWN_CALL_VALUE
    BUCKETS: Sequence[RatingBucket] = (
        RatingBucket(
            label="<7.8",
            description="7.8分（不含7.8）以下",
            lower=None,
            upper=7.8,
            include_lower=False,
            include_upper=False,
        ),
        RatingBucket(
            label="7.8-8.2",
            description="7.8-8.2",
            lower=7.8,
            upper=8.2,
            include_lower=True,
            include_upper=False,
        ),
        RatingBucket(
            label="8.2-8.5",
            description="8.2-8.5",
            lower=8.2,
            upper=8.5,
            include_lower=True,
            include_upper=False,
        ),
        RatingBucket(
            label="8.5-8.8",
            description="8.5-8.8",
            lower=8.5,
            upper=8.8,
            include_lower=True,
            include_upper=False,
        ),
        RatingBucket(
            label="8.8-9.0",
            description="8.8-9.0",
            lower=8.8,
            upper=9.0,
            include_lower=True,
            include_upper=False,
        ),
        RatingBucket(
            label="9.0-9.3",
            description="9.0-9.3",
            lower=9.0,
            upper=9.3,
            include_lower=True,
            include_upper=False,
        ),
        RatingBucket(
            label=">=9.3",
            description="9.3以上",
            lower=9.3,
            upper=None,
            include_lower=True,
            include_upper=True,
        ),
    )

    def __init__(
        self,
        output_dir: Optional[Path | str] = None,
        dynamic_filter: Optional[DynamicThresholdFilter] = None,
    ) -> None:
        self.output_dir = Path(output_dir) if output_dir else Path("runtime/outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.dynamic_filter = dynamic_filter or DynamicThresholdFilter()

    def generate_report(
        self,
        df: pd.DataFrame,
        rating_column: Optional[str],
        call_number_column: Optional[str],
        rating_count_column: Optional[str] = None,
        source_excel: Optional[Path | str] = None,
        prepared_dataset: Optional[pd.DataFrame] = None,
        dynamic_filter_result: Optional[DynamicFilterResult] = None,
    ) -> Optional[Path]:
        """Create a text report that links Douban rating with call-number themes."""
        if not rating_column or rating_column not in df.columns:
            logger.debug("跳过主题评分统计：缺少评分列 %s", rating_column)
            return None
        if not call_number_column or call_number_column not in df.columns:
            logger.debug("跳过主题评分统计：缺少索书号列 %s", call_number_column)
            return None

        working = prepared_dataset
        if working is None:
            working = self.dynamic_filter.prepare_dataset(
                df=df,
                rating_column=rating_column,
                call_number_column=call_number_column,
                rating_count_column=rating_count_column,
            )
        if working.empty:
            return self._write_empty_report(source_excel)

        bucket_stats = self._build_bucket_statistics(working)
        call_letter_stats = self._build_call_letter_statistics(working)
        filter_result = dynamic_filter_result
        if filter_result is None and self.dynamic_filter:
            filter_result = self.dynamic_filter.analyze(working)
        dynamic_threshold_stats = filter_result.stats if filter_result else []
        filter_config = (
            filter_result.config if filter_result else self.dynamic_filter.config
        )
        dynamic_total_samples = (
            filter_result.total_samples if filter_result else len(working)
        )
        return self._write_report(
            bucket_stats=bucket_stats,
            call_letter_stats=call_letter_stats,
            dynamic_threshold_stats=dynamic_threshold_stats,
            total_samples=len(working),
            source_excel=source_excel,
            filter_config=filter_config,
            dynamic_total_samples=dynamic_total_samples,
        )

    def _build_bucket_statistics(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        stats: List[Dict[str, Any]] = []
        total = len(df)
        ratings = df["rating"]
        for bucket in self.BUCKETS:
            mask = self._build_bucket_mask(ratings, bucket)
            bucket_df = df[mask]
            stats.append(self._summarize_bucket(bucket, bucket_df, total))
        return stats

    def _build_call_letter_statistics(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        if df.empty:
            return []
        group_stats: List[Dict[str, Any]] = []
        total_samples = len(df)
        grouped = df.groupby("call_letter", sort=True)
        for letter, group in grouped:
            sample_count = int(len(group))
            letter_label = letter or self.UNKNOWN_CALL_VALUE
            bucket_entries: List[Dict[str, Any]] = []
            ratings = group["rating"]
            for bucket in self.BUCKETS:
                mask = self._build_bucket_mask(ratings, bucket)
                bucket_df = group[mask]
                bucket_entries.append(
                    {
                        "label": bucket.label,
                        "description": bucket.description,
                        "count": int(len(bucket_df)),
                        "ratio": (len(bucket_df) / sample_count)
                        if sample_count
                        else math.nan,
                        "comment_stats": self._summarize_comment_counts(bucket_df),
                    }
                )
            group_stats.append(
                {
                    "letter": letter_label,
                    "total": sample_count,
                    "ratio": (sample_count / total_samples)
                    if total_samples
                    else math.nan,
                    "buckets": bucket_entries,
                    "overall_comment_stats": self._summarize_comment_counts(group),
                }
            )

        group_stats.sort(
            key=lambda item: (
                item["letter"] == self.UNKNOWN_CALL_VALUE,
                item["letter"],
            )
        )
        return group_stats

    def _build_bucket_mask(
        self,
        ratings: pd.Series,
        bucket: RatingBucket,
    ) -> pd.Series:
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

    def _summarize_bucket(
        self,
        bucket: RatingBucket,
        bucket_df: pd.DataFrame,
        total_samples: int,
    ) -> Dict[str, Any]:
        sample_count = int(len(bucket_df))
        ratio = (sample_count / total_samples) if total_samples else math.nan
        call_letters = self._summarize_call_letters(bucket_df, sample_count)
        comment_stats = self._summarize_comment_counts(bucket_df)
        return {
            "label": bucket.label,
            "description": bucket.description,
            "count": sample_count,
            "ratio": ratio,
            "call_letters": call_letters,
            "comment_stats": comment_stats,
        }

    def _summarize_call_letters(
        self,
        bucket_df: pd.DataFrame,
        bucket_size: int,
    ) -> List[Dict[str, Any]]:
        if bucket_size == 0 or bucket_df.empty:
            return []
        distributions = bucket_df["call_letter"].value_counts(dropna=False)
        stats: List[Dict[str, Any]] = []
        for letter, count in distributions.items():
            stats.append(
                {
                    "letter": letter,
                    "count": int(count),
                    "ratio": (count / bucket_size) if bucket_size else math.nan,
                }
            )
        return stats

    def _summarize_comment_counts(self, bucket_df: pd.DataFrame) -> Dict[str, Any]:
        if bucket_df.empty or "rating_count" not in bucket_df.columns:
            return {"avg": None, "median": None, "min": None, "max": None}
        counts = bucket_df["rating_count"].dropna()
        if counts.empty:
            return {"avg": None, "median": None, "min": None, "max": None}
        return {
            "avg": float(counts.mean()),
            "median": float(counts.median()),
            "min": float(counts.min()),
            "max": float(counts.max()),
        }

    def _write_report(
        self,
        bucket_stats: Sequence[Dict[str, Any]],
        call_letter_stats: Sequence[Dict[str, Any]],
        dynamic_threshold_stats: Sequence[Dict[str, Any]],
        total_samples: int,
        source_excel: Optional[Path | str],
        filter_config: Optional[Dict[str, Any]] = None,
        dynamic_total_samples: Optional[int] = None,
    ) -> Path:
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        base_name = Path(source_excel).stem if source_excel else "link_stage"
        report_name = (
            f"{base_name}_评分分段统计_{timestamp}.md"
        )
        report_path = self.output_dir / report_name

        lines: List[str] = [
            "# 豆瓣评分分段统计",
            f"- 数据来源: {Path(source_excel).name if source_excel else 'N/A'}",
            f"- 统计时间: {now:%Y-%m-%d %H:%M:%S}",
            f"- 总样本: {total_samples}",
            "",
            "## 分段详情",
            "",
            "| 序号 | 分段 | 数量 | 占比 | 评论人数（均/中位/最低/最高） | 索书号首字母 |",
            "| --- | --- | --- | --- | --- | --- |",
        ]

        for idx, item in enumerate(bucket_stats):
            comment_stats = item["comment_stats"]
            comment_cell = self._format_comment_summary(comment_stats)
            lines.append(
                "| {index} | {label} | {count} | {ratio} | {comments} | {calls} |".format(
                    index=idx + 1,
                    label=item["description"],
                    count=item["count"],
                    ratio=self._format_ratio(item["ratio"]),
                    comments=comment_cell,
                    calls=self._format_call_distribution(item["call_letters"]),
                )
            )

        if dynamic_threshold_stats:
            candidate_entries = [
                entry
                for entry in dynamic_threshold_stats
                if entry.get("candidate_count") is not None
            ]
            candidate_total = (
                sum(entry["candidate_count"] for entry in candidate_entries)
                if candidate_entries
                else 0
            )
            effective_dynamic_total = (
                dynamic_total_samples if dynamic_total_samples is not None else total_samples
            )
            candidate_ratio_total = (
                candidate_total / effective_dynamic_total
                if effective_dynamic_total
                else math.nan
            )
            cfg = filter_config or {}
            lower_pct_label = int(cfg.get("review_lower_percentile", 40) or 0)
            upper_pct_label = int(cfg.get("review_upper_percentile", 80) or 0)
            rating_pct_label = int(cfg.get("rating_percentile_large", 75) or 0)
            min_sample_size = int(cfg.get("min_sample_size", 30) or 0)
            raw_top_n = cfg.get("top_n_per_category")
            top_n_value: Optional[int] = None
            if raw_top_n is not None:
                try:
                    top_n_value = int(raw_top_n)
                except (TypeError, ValueError):
                    top_n_value = None
            lines.extend(
                [
                    "",
                    "## 动态过滤阈值参考",
                    "",
                    "> 规则：按索书号首字母划分类别，在评论人数 P{low} 至 P{high} 的黄金区间内，样本数 < {min_sample} 使用类别最低分，小样本之外使用 max(P{rating_pct}，类别最低分) 作为评分门槛。".format(
                        low=lower_pct_label,
                        high=upper_pct_label,
                        min_sample=min_sample_size,
                        rating_pct=rating_pct_label,
                    ),
                    f"- 候选池规模：{self._format_int(candidate_total)}（占总体 {self._format_ratio(candidate_ratio_total)}）",
                ]
            )
            if top_n_value:
                lines.append(
                    f"- 建议每个类别按评分降序保留前 {top_n_value} 本（config/setting.yaml 可调）"
                )
            lines.extend(
                [
                    "",
                    "| 索书号首字母 | 样本数 | 样本类型 | 评论P{low} | 评论P{high} | 评分门槛 | 候选数 | 组内占比 | 全局占比 |".format(
                        low=lower_pct_label,
                        high=upper_pct_label,
                    ),
                    "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
                ]
            )
            for entry in dynamic_threshold_stats:
                lines.append(
                    "| {letter} | {total} | {sample_type} | {p_low} | {p_high} | {score} | {candidate} | {ratio_group} | {ratio_all} |".format(
                        letter=entry["letter"],
                        total=entry["total"],
                        sample_type=entry.get("sample_type", "-"),
                        p_low=self._format_int(entry.get("review_lower_bound")),
                        p_high=self._format_int(entry.get("review_upper_bound")),
                        score=self._format_float(entry.get("score_threshold")),
                        candidate=self._format_int(entry.get("candidate_count")),
                        ratio_group=self._format_ratio(entry.get("candidate_ratio_in_group")),
                        ratio_all=self._format_ratio(entry.get("candidate_ratio_overall")),
                    )
                )

        if call_letter_stats:
            lines.extend(
                [
                    "",
                    "## 索书号首字母分类",
                ]
            )
            for entry in call_letter_stats:
                letter = entry["letter"]
                lines.extend(
                    [
                        "",
                        f"### {letter}",
                        f"- 样本数: {entry['total']}",
                        f"- 总体占比: {self._format_ratio(entry.get('ratio'))}",
                        f"- 评论人数总结: {self._format_comment_summary(entry['overall_comment_stats'])}",
                        "",
                        "| 分段 | 数量 | 占比 | 评论人数（均/中位/最低/最高） |",
                        "| --- | --- | --- | --- |",
                    ]
                )
                for bucket in entry["buckets"]:
                    comment_stats = bucket["comment_stats"]
                    comment_cell = self._format_comment_summary(comment_stats)
                    lines.append(
                        "| {label} | {count} | {ratio} | {comments} |".format(
                            label=bucket["description"],
                            count=bucket["count"],
                            ratio=self._format_ratio(bucket["ratio"]),
                            comments=comment_cell,
                        )
                    )

        report_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("已生成评分分段统计报告：%s", report_path)
        return report_path

    def _format_call_distribution(
        self,
        rows: Sequence[Dict[str, Any]],
    ) -> str:
        if not rows:
            return "暂无数据"
        parts: List[str] = []
        for row in rows:
            label = row.get("letter") or self.UNKNOWN_CALL_VALUE
            if label != self.UNKNOWN_CALL_VALUE:
                label = f"{label}类"
            parts.append(
                f"{label} {row.get('count', 0)} ({self._format_ratio(row.get('ratio'))})"
            )
        return "；".join(parts)

    def _write_empty_report(self, source_excel: Optional[Path | str]) -> Path:
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        base_name = Path(source_excel).stem if source_excel else "link_stage"
        report_name = (
            f"{base_name}_评分分段统计_{timestamp}.md"
        )
        report_path = self.output_dir / report_name
        lines = [
            "# 豆瓣评分分段统计",
            f"- 数据来源: {Path(source_excel).name if source_excel else 'N/A'}",
            f"- 统计时间: {now:%Y-%m-%d %H:%M:%S}",
            "- 总样本: 0",
            "",
            "> 暂无可用作统计的评分数据。",
        ]
        report_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("未找到可用数据，输出空统计报告：%s", report_path)
        return report_path

    def _format_ratio(self, value: Optional[float]) -> str:
        if value is None or math.isnan(value):
            return "-"
        return f"{value * 100:.1f}%"

    def _format_float(self, value: Optional[float]) -> str:
        if value is None or math.isnan(value):
            return "-"
        return f"{value:.2f}"

    def _format_int(self, value: Optional[float]) -> str:
        if value is None:
            return "-"
        if isinstance(value, float) and math.isnan(value):
            return "-"
        return f"{int(round(value))}"

    def _format_comment_summary(self, comment_stats: Dict[str, Any]) -> str:
        return "均 {avg} / 中位 {median} / 最低 {min} / 最高 {max}".format(
            avg=self._format_float(comment_stats.get("avg")),
            median=self._format_int(comment_stats.get("median")),
            min=self._format_int(comment_stats.get("min")),
            max=self._format_int(comment_stats.get("max")),
        )
