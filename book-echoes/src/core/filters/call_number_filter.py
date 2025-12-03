"""
索书号和CLC号筛选器 - 规则B：基于模式配置的保留/排除策略

支持的指令优先级（从高到低）：
1. DROP! / EXCLUDE! - 高优先级排除（不受 KEEP 保护）
2. KEEP / INCLUDE / ALLOW - 保留规则
3. DROP / EXCLUDE / DENY - 普通排除（受 KEEP 保护）
"""

import pandas as pd
from typing import Dict, Any, Tuple, List
from .base_filter import BaseFilter
from src.utils.rule_file_parser import RuleFileParser, CallNumberRules
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CallNumberFilter(BaseFilter):
    """索书号和CLC号筛选器"""

    def apply(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """应用索书号和CLC号筛选"""
        result_data = data.copy()
        valid_columns = self._validate_columns(data)

        if not valid_columns:
            return result_data, {
                'status': 'skipped',
                'reason': f'目标列 {self.target_columns} 不存在'
            }

        # 使用统一解析器加载规则
        rules = RuleFileParser.load_call_number_rules(self.config['file'])

        if not rules.has_rules:
            return result_data, {
                'status': 'skipped',
                'reason': '没有加载到任何筛选模式'
            }

        match_type = self.config['match_type']

        # 构建各类掩码
        high_priority_mask = self._build_mask(
            result_data, valid_columns, rules.high_priority_exclude, match_type
        )
        include_mask = self._build_mask(
            result_data, valid_columns, rules.include, match_type
        )
        exclude_mask = self._build_mask(
            result_data, valid_columns, rules.exclude, match_type
        )

        # 组合逻辑：
        # - 高优先级排除：直接排除（不受 KEEP 保护）
        # - 普通排除：仅当未命中保留规则时才排除
        to_exclude_mask = high_priority_mask | ((~include_mask) & exclude_mask)
        excluded_count = to_exclude_mask.sum()
        result_data = result_data[~to_exclude_mask]

        logger.info(
            "规则B - 索书号/CLC号筛选: 排除 %s 条记录 (%s)",
            excluded_count,
            rules.get_summary(),
        )

        return result_data, {
            'status': 'completed',
            'description': self.description,
            'target_columns': valid_columns,
            'match_type': match_type,
            'high_priority_exclude_count': len(rules.high_priority_exclude),
            'include_patterns_count': len(rules.include),
            'exclude_patterns_count': len(rules.exclude),
            'excluded_count': excluded_count,
            'excluded_ratio': excluded_count / len(data) if len(data) > 0 else 0,
            'include_patterns_preview': rules.include[:10],
            'exclude_patterns_preview': rules.exclude[:10],
        }

    def _build_mask(
        self,
        dataframe: pd.DataFrame,
        columns: List[str],
        patterns: List[str],
        match_type: str,
    ) -> pd.Series:
        """对给定列和模式构建布尔掩码"""
        if not patterns:
            return pd.Series(False, index=dataframe.index)

        mask = pd.Series(False, index=dataframe.index)
        for column in columns:
            series = dataframe[column].fillna('').astype(str)
            for pattern in patterns:
                mask |= self._match_pattern(series, pattern, match_type)
        return mask
