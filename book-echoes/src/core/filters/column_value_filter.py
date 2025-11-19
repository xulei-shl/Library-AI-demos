"""
列值筛选器 - 规则C：Excel列值筛选
"""

import pandas as pd
import re
from typing import Dict, Any, Tuple
from .base_filter import BaseFilter
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ColumnValueFilter(BaseFilter):
    """列值筛选器"""
    
    def apply(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """应用列值筛选"""
        result_data = data.copy()
        valid_columns = self._validate_columns(data)
        
        if not valid_columns:
            return result_data, {
                'status': 'skipped',
                'reason': f'目标列 {self.target_columns} 不存在'
            }
        
        target_column = valid_columns[0]
        filter_type = self.config.get('filter_type', 'regex')
        action = self.config.get('action', 'exclude')
        
        # 应用筛选
        if filter_type == 'regex':
            pattern = self.config.get('pattern', '')
            excluded_mask = self._regex_filter(result_data[target_column], pattern, action)
        elif filter_type == 'exclude_contains':
            exclude_patterns = self.config.get('exclude_patterns', [])
            excluded_mask = self._exclude_contains_filter(result_data[target_column], exclude_patterns, action)
        else:
            logger.warning(f"不支持的筛选类型: {filter_type}")
            return result_data, {
                'status': 'skipped',
                'reason': f'不支持的筛选类型: {filter_type}'
            }
        
        excluded_count = excluded_mask.sum()
        result_data = result_data[~excluded_mask]
        
        logger.info(f"规则C - 列值筛选 [{target_column}]: 排除 {excluded_count} 条记录")
        
        return result_data, {
            'description': self.description,
            'target_column': target_column,
            'filter_type': filter_type,
            'action': action,
            'excluded_count': excluded_count,
            'excluded_ratio': excluded_count / len(data) if len(data) > 0 else 0
        }
    
    def _regex_filter(self, text_series: pd.Series, pattern: str, action: str) -> pd.Series:
        """正则表达式筛选"""
        if not pattern:
            return pd.Series(False, index=text_series.index)
        
        try:
            if action == 'keep_only':
                # 只保留匹配模式的记录
                return ~text_series.astype(str).str.match(pattern, na=False)
            else:  # exclude
                # 排除匹配模式的记录
                return text_series.astype(str).str.match(pattern, na=False)
        except Exception as e:
            logger.warning(f"正则表达式筛选失败: {e}")
            return pd.Series(False, index=text_series.index)
    
    def _exclude_contains_filter(self, text_series: pd.Series, exclude_patterns: list, action: str) -> pd.Series:
        """排除包含指定关键词的筛选"""
        if not exclude_patterns:
            return pd.Series(False, index=text_series.index)
        
        excluded_mask = pd.Series(False, index=text_series.index)
        
        for pattern in exclude_patterns:
            excluded_mask |= text_series.astype(str).str.contains(pattern, na=False, case=False)
        
        return excluded_mask