"""
题名关键词筛选器 - 规则B：题名关键词排除
"""

import pandas as pd
from typing import Dict, Any, Tuple
from .base_filter import BaseFilter
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TitleKeywordsFilter(BaseFilter):
    """题名关键词筛选器"""
    
    def apply(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """应用题名关键词筛选"""
        result_data = data.copy()
        valid_columns = self._validate_columns(data)
        
        if not valid_columns:
            return result_data, {
                'status': 'skipped',
                'reason': f'目标列 {self.target_columns} 不存在'
            }
        
        target_column = valid_columns[0]
        
        # 加载关键词文件
        patterns = self._load_patterns(self.config['file'])
        if not patterns:
            return result_data, {
                'status': 'skipped',
                'reason': '没有加载到任何筛选关键词'
            }
        
        match_type = self.config['match_type']
        
        # 应用筛选
        excluded_mask = pd.Series(False, index=result_data.index)
        
        for pattern in patterns:
            excluded_mask |= self._match_pattern(
                result_data[target_column].astype(str), pattern, match_type
            )
        
        excluded_count = excluded_mask.sum()
        result_data = result_data[~excluded_mask]
        
        logger.info(f"规则B - 题名关键词筛选: 排除 {excluded_count} 条记录 (关键词数: {len(patterns)})")
        
        return result_data, {
            'description': self.description,
            'target_column': target_column,
            'match_type': match_type,
            'patterns_count': len(patterns),
            'excluded_count': excluded_count,
            'excluded_ratio': excluded_count / len(data) if len(data) > 0 else 0,
            'patterns_used': patterns[:10]  # 记录前10个使用的关键词
        }