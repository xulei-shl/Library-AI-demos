#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dynamic threshold filtering for Douban link candidates."""

from __future__ import annotations

import math
import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence, Set

import pandas as pd

from src.utils.config_manager import get_config_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)

CALL_LETTER_PATTERN = re.compile(r"[A-Za-z]")
UNKNOWN_CALL_VALUE = "未知"


@dataclass(frozen=True)
class DynamicFilterResult:
    stats: Sequence[Dict[str, Any]]
    candidate_indexes: Set[int]
    total_samples: int
    config: Dict[str, Any]


class DynamicThresholdFilter:
    DEFAULT_FILTERING_CONFIG: Dict[str, Any] = {
        "min_sample_size": 30,
        "review_lower_percentile": 40,
        "review_upper_percentile": 80,
        "rating_percentile_large": 75,
        "top_n_per_category": 20,
        "category_min_scores": {
            "I": 8.0,
            "K": 7.8,
            "T": 7.5,
            "E": 7.4,
            "B": 8.2,
            "default": 7.5,
        },
        "column_filters": {
            "enabled": False,
            "rules": [],
        },
    }

    def __init__(self, config_manager=None, source_df: Optional[pd.DataFrame] = None) -> None:
        self._config_manager = config_manager
        self._source_df = source_df  # 保存原始DataFrame引用,用于列值验证
        self.config = self._load_filtering_config()

    def prepare_dataset(
        self,
        df: pd.DataFrame,
        rating_column: Optional[str],
        call_number_column: Optional[str],
        rating_count_column: Optional[str],
    ) -> pd.DataFrame:
        if not rating_column or rating_column not in df.columns:
            return pd.DataFrame(columns=["rating", "call_letter", "rating_count"])

        working = pd.DataFrame(index=df.index)
        working["rating"] = pd.to_numeric(df[rating_column], errors="coerce")

        if call_number_column and call_number_column in df.columns:
            call_source = (
                df[call_number_column]
                .astype(str)
                .str.strip()
                .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
                .fillna("")
            )
        else:
            call_source = pd.Series("", index=df.index, dtype="string")

        working["call_letter"] = (
            call_source.map(self._extract_call_letter).fillna(UNKNOWN_CALL_VALUE)
        )

        if rating_count_column and rating_count_column in df.columns:
            working["rating_count"] = pd.to_numeric(
                df[rating_count_column], errors="coerce"
            )
        else:
            working["rating_count"] = pd.Series(
                data=pd.NA, index=df.index, dtype="Float64"
            )

        working = working.dropna(subset=["rating"]).copy()
        return working

    def analyze(self, dataset: pd.DataFrame) -> DynamicFilterResult:
        if dataset is None or dataset.empty:
            return DynamicFilterResult(
                stats=[],
                candidate_indexes=set(),
                total_samples=0,
                config=self.config,
            )

        config = self.config
        min_sample_size = int(config.get("min_sample_size", 30) or 0)
        review_lower_pct = float(config.get("review_lower_percentile", 40) or 0) / 100.0
        review_upper_pct = float(config.get("review_upper_percentile", 80) or 0) / 100.0
        rating_pct_large = float(config.get("rating_percentile_large", 75) or 0) / 100.0
        total_samples = len(dataset)
        threshold_stats: list[Dict[str, Any]] = []
        candidate_indexes: Set[int] = set()
        grouped = dataset.groupby("call_letter", sort=True)

        for letter, group in grouped:
            sample_count = int(len(group))
            letter_label = letter or UNKNOWN_CALL_VALUE
            review_lower_bound = self._safe_quantile(
                group["rating_count"], review_lower_pct
            )
            review_upper_bound = self._safe_quantile(
                group["rating_count"], review_upper_pct
            )
            score_floor = self._get_category_floor(letter)
            is_small_sample = sample_count < min_sample_size
            relative_threshold = (
                None
                if is_small_sample
                else self._safe_quantile(group["rating"], rating_pct_large)
            )
            score_threshold = score_floor
            if not is_small_sample and relative_threshold is not None:
                score_threshold = max(score_floor, relative_threshold)
            score_threshold = float(score_threshold) if score_threshold is not None else None

            candidate_count: Optional[int] = None
            ratio_in_group = math.nan
            ratio_overall = math.nan
            if (
                review_lower_bound is not None
                and review_upper_bound is not None
                and score_threshold is not None
            ):
                candidate_mask = pd.Series(True, index=group.index)
                candidate_mask &= group["rating_count"].ge(review_lower_bound).fillna(False)
                candidate_mask &= group["rating_count"].le(review_upper_bound).fillna(False)
                candidate_mask &= group["rating"].ge(score_threshold).fillna(False)
                
                # 应用列值验证过滤
                for idx in group.index:
                    if candidate_mask.at[idx] and not self._apply_column_filters(idx):
                        candidate_mask.at[idx] = False
                
                matched_indexes = candidate_mask[candidate_mask].index.tolist()
                candidate_indexes.update(matched_indexes)
                candidate_count = int(candidate_mask.sum())
                if sample_count:
                    ratio_in_group = candidate_count / sample_count
                if total_samples:
                    ratio_overall = candidate_count / total_samples

            threshold_stats.append(
                {
                    "letter": letter_label,
                    "total": sample_count,
                    "sample_type": "小样本" if is_small_sample else "大样本",
                    "review_lower_bound": review_lower_bound,
                    "review_upper_bound": review_upper_bound,
                    "score_threshold": score_threshold,
                    "candidate_count": candidate_count,
                    "candidate_ratio_in_group": ratio_in_group,
                    "candidate_ratio_overall": ratio_overall,
                }
            )

        threshold_stats.sort(
            key=lambda item: (
                item["letter"] == UNKNOWN_CALL_VALUE,
                item["letter"],
            )
        )
        return DynamicFilterResult(
            stats=threshold_stats,
            candidate_indexes=candidate_indexes,
            total_samples=total_samples,
            config=config,
        )

    def _load_filtering_config(self) -> Dict[str, Any]:
        config = deepcopy(self.DEFAULT_FILTERING_CONFIG)
        try:
            config_manager = self._config_manager or get_config_manager()
            douban_config = config_manager.get_douban_config() or {}
            analytics_config = (
                (douban_config.get("analytics") or {}).get("theme_rating") or {}
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("加载主题评分过滤配置失败，使用默认值：%s", exc)
            analytics_config = {}

        if isinstance(analytics_config, dict):
            for key, value in analytics_config.items():
                if key == "category_min_scores" and isinstance(value, dict):
                    config["category_min_scores"].update(value)
                else:
                    config[key] = value
        return config

    def _get_category_floor(self, letter: Optional[str]) -> float:
        score_map = self.config.get("category_min_scores") or {}
        default_floor = score_map.get("default", 0.0)
        if letter and letter in score_map:
            return float(score_map[letter])
        return float(default_floor)

    def _safe_quantile(self, series: pd.Series, quantile: float) -> Optional[float]:
        if series is None:
            return None
        clean = series.dropna()
        if clean.empty:
            return None
        try:
            return float(clean.quantile(quantile))
        except (ValueError, TypeError):
            return None

    def _extract_call_letter(self, call_no: Optional[str]) -> Optional[str]:
        if call_no is None or pd.isna(call_no):
            return None
        normalized = str(call_no).strip().upper()
        if not normalized:
            return None
        match = CALL_LETTER_PATTERN.search(normalized)
        return match.group(0) if match else None

    def _apply_column_filters(self, index: int) -> bool:
        """应用列值验证规则,返回True表示通过验证,False表示应被过滤."""
        if self._source_df is None:
            return True
        
        column_filters_config = self.config.get("column_filters", {})
        if not column_filters_config.get("enabled", False):
            return True
        
        rules = column_filters_config.get("rules", [])
        if not rules:
            return True
        
        for rule in rules:
            if not rule.get("enabled", False):
                continue
            
            column = rule.get("column")
            if not column or column not in self._source_df.columns:
                continue
            
            filter_type = rule.get("filter_type", "not_empty")
            value = self._source_df.at[index, column]
            
            if filter_type == "not_empty":
                if not self._check_not_empty(value):
                    return False
            elif filter_type == "regex":
                pattern = rule.get("pattern")
                if pattern and not self._check_regex(value, pattern):
                    return False
        
        return True

    def _check_not_empty(self, value: Any) -> bool:
        """检查值是否非空."""
        if value is None or pd.isna(value):
            return False
        str_value = str(value).strip()
        return bool(str_value)

    def _check_regex(self, value: Any, pattern: str) -> bool:
        """检查值是否匹配正则表达式."""
        if value is None or pd.isna(value):
            return False
        try:
            str_value = str(value)
            return bool(re.match(pattern, str_value))
        except re.error:
            logger.warning("无效的正则表达式: %s", pattern)
            return False
