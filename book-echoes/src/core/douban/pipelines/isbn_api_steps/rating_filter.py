#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""评分过滤步骤.

负责根据豆瓣评分筛选候选图书。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from src.utils.logger import get_logger
from src.core.douban.analytics.dynamic_threshold_filter import DynamicThresholdFilter

logger = get_logger(__name__)


class RatingFilterStep:
    """评分过滤步骤.

    使用动态阈值过滤器根据评分筛选候选图书。
    """

    # 可能的索书号列名
    CALL_NUMBER_COLUMNS = ["索书号", "清理后索书号", "CLC号"]

    def __init__(self, candidate_column: str = "候选状态"):
        """初始化.

        Args:
            candidate_column: 候选状态列名
        """
        self.candidate_column = candidate_column

    def apply_filter(
        self,
        df: pd.DataFrame,
        field_mapping: Dict[str, str],
    ) -> Dict[str, Any]:
        """应用评分过滤.

        Args:
            df: 数据框
            field_mapping: 字段映射

        Returns:
            统计信息
        """
        rating_col = field_mapping.get("rating", "豆瓣评分")
        rating_count_col = field_mapping.get("rating_count", "豆瓣评价人数")

        # 尝试识别索书号列
        call_number_col = self._find_call_number_column(df)

        try:
            filter_engine = DynamicThresholdFilter(source_df=df)
            dataset = filter_engine.prepare_dataset(
                df=df,
                rating_column=rating_col,
                call_number_column=call_number_col,
                rating_count_column=rating_count_col,
            )
            result = filter_engine.analyze(dataset)

            # 标记候选图书
            for idx in result.candidate_indexes:
                if idx in df.index:
                    df.at[idx, self.candidate_column] = "候选"

            return {
                "candidate_count": len(result.candidate_indexes),
                "total_samples": result.total_samples,
                "stats": result.stats,
            }

        except Exception as e:
            logger.error(f"评分过滤失败: {e}")
            return {"candidate_count": 0, "error": str(e)}

    def _find_call_number_column(self, df: pd.DataFrame) -> Optional[str]:
        """查找索书号列."""
        for col_name in self.CALL_NUMBER_COLUMNS:
            if col_name in df.columns:
                return col_name
        return None
