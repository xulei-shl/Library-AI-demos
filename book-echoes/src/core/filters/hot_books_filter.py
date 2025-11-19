"""
热门图书筛选器 - 规则A：排除顶流热门（前15%借阅次数最高的图书）
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from .base_filter import BaseFilter
from src.utils.logger import get_logger

logger = get_logger(__name__)


class HotBooksFilter(BaseFilter):
    """热门图书筛选器 - 排除顶流热门"""
    
    def apply(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """应用热门图书筛选规则"""
        result_data = data.copy()
        valid_columns = self._validate_columns(data)
        
        if not valid_columns:
            return result_data, {
                'status': 'skipped',
                'reason': f'目标列 {self.target_columns} 不存在'
            }
        
        target_column = valid_columns[0]
        
        # 动态计算阈值
        threshold = self._calculate_dynamic_threshold(result_data[target_column])
        
        # 应用筛选：排除借阅次数大于等于阈值的记录
        excluded_mask = result_data[target_column] >= threshold
        
        excluded_count = excluded_mask.sum()
        result_data = result_data[~excluded_mask]
        
        logger.info(f"规则A - 热门图书筛选: 排除 {excluded_count} 条记录 (阈值: {threshold}次)")
        
        return result_data, {
            'description': self.description,
            'target_column': target_column,
            'threshold': threshold,
            'threshold_method': 'percentile',
            'excluded_count': excluded_count,
            'excluded_ratio': excluded_count / len(data) if len(data) > 0 else 0,
            'excluded_books': excluded_count,
            'unique_call_numbers_excluded': len(result_data) if excluded_count > 0 else 0
        }
    
    def _calculate_dynamic_threshold(self, borrowing_counts: pd.Series) -> int:
        """动态计算借阅次数阈值"""
        # 获取非零借阅次数
        non_zero_data = borrowing_counts[borrowing_counts > 0]
        
        if len(non_zero_data) == 0:
            fallback_count = self.config['methods']['percentile']['fallback_count']
            logger.warning("没有非零借阅数据，使用后备阈值")
            return fallback_count
        
        # 检查分位数方法是否启用
        if self.config['methods']['percentile']['enabled']:
            percentile = self.config['methods']['percentile']['threshold_percentile']
            threshold = np.percentile(non_zero_data, 100 - percentile)
            
            # 如果分位数结果过小，使用75%分位数
            if threshold < 5:
                threshold = np.percentile(non_zero_data, 75)
                logger.info(f"使用75%分位数作为阈值: {threshold}")
            
            return int(threshold)
        
        # 检查绝对次数方法是否启用
        elif self.config['methods']['absolute_count']['enabled']:
            threshold = self.config['methods']['absolute_count']['threshold_borrowing_count']
            return threshold
        
        # 默认使用分位数方法
        else:
            threshold = np.percentile(non_zero_data, 85)  # 默认排除前15%
            return int(threshold)