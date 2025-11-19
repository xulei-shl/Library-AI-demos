"""
索书号和CLC号筛选器 - 规则B：基于模式配置的保留/排除策略
"""

import pandas as pd
from typing import Dict, Any, Tuple, List
from .base_filter import BaseFilter
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
        
        # 加载模式文件
        pattern_groups = self._load_pattern_groups(self.config['file'])
        include_patterns = pattern_groups['include']
        exclude_patterns = pattern_groups['exclude']

        if not include_patterns and not exclude_patterns:
            return result_data, {
                'status': 'skipped',
                'reason': '没有加载到任何筛选模式'
            }
        
        match_type = self.config['match_type']

        include_mask = self._build_mask(result_data, valid_columns, include_patterns, match_type)
        exclude_mask = self._build_mask(result_data, valid_columns, exclude_patterns, match_type)

        # 仅当命中排除且未命中保留时才剔除
        to_exclude_mask = (~include_mask) & exclude_mask
        excluded_count = to_exclude_mask.sum()
        result_data = result_data[~to_exclude_mask]

        logger.info(
            "规则B - 索书号/CLC号筛选: 排除 %s 条记录 (保留模式: %s, 排除模式: %s)",
            excluded_count,
            len(include_patterns),
            len(exclude_patterns),
        )

        return result_data, {
            'status': 'completed',
            'description': self.description,
            'target_columns': valid_columns,
            'match_type': match_type,
            'include_patterns_count': len(include_patterns),
            'exclude_patterns_count': len(exclude_patterns),
            'excluded_count': excluded_count,
            'excluded_ratio': excluded_count / len(data) if len(data) > 0 else 0,
            'include_patterns_preview': include_patterns[:10],
            'exclude_patterns_preview': exclude_patterns[:10],
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

    def _load_pattern_groups(self, file_path: str) -> Dict[str, List[str]]:
        """加载保留/排除模式配置"""
        groups = {'include': [], 'exclude': []}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parsed = self._parse_pattern_line(line.strip())
                    if not parsed:
                        continue
                    group, pattern = parsed
                    groups[group].append(pattern)
        except Exception as exc:
            logger.warning("加载筛选模式文件失败 %s: %s", file_path, exc)
        return groups

    def _parse_pattern_line(self, line: str):
        """解析单行配置，返回 (group, pattern)"""
        if not line or line.startswith('#'):
            return None

        tokens = line.split(maxsplit=1)
        if len(tokens) == 1:
            # 默认按排除规则处理
            return 'exclude', tokens[0]

        directive, pattern = tokens[0].lower(), tokens[1]
        if directive in ('keep', 'include', 'allow'):
            return 'include', pattern
        if directive in ('drop', 'exclude', 'deny'):
            return 'exclude', pattern

        # 未识别指令时按原始整行作为排除模式处理，确保向后兼容
        return 'exclude', line
