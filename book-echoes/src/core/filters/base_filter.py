"""
基础筛选器抽象类 - 确保模块化设计
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, List
import pandas as pd
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BaseFilter(ABC):
    """基础筛选器抽象类 - 确保模块化设计"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('enabled', True)
        self.description = config.get('description', '')
        self.target_columns = self._prepare_target_columns(
            config.get('target_columns'),
            config.get('target_column')
        )
        self.target_column = self.target_columns[0] if self.target_columns else None
    
    @abstractmethod
    def apply(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """应用筛选规则
        
        Returns:
            Tuple[pd.DataFrame, Dict]: (筛选后的数据, 统计信息)
        """
        pass
    
    def _validate_columns(self, data: pd.DataFrame) -> List[str]:
        """验证目标列是否存在"""
        available_columns = list(data.columns)
        valid_columns = []
        
        for col in self.target_columns:
            if col in available_columns:
                valid_columns.append(col)
            else:
                # 尝试自动映射列名
                mapped_col = self._auto_map_column(col, available_columns)
                if mapped_col:
                    valid_columns.append(mapped_col)
        
        return valid_columns

    def _prepare_target_columns(self, columns_config, column_config) -> List[str]:
        """
        标准化目标列配置，确保最终使用字符串列表
        
        Args:
            columns_config: target_columns配置项
            column_config: target_column配置项
            
        Returns:
            List[str]: 规范化后的列名列表
        """
        normalized = []
        seen = set()

        def _append_column(value: Any):
            if value is None:
                return
            text = str(value).strip()
            if not text or text in seen:
                return
            seen.add(text)
            normalized.append(text)

        if isinstance(columns_config, (list, tuple, set)):
            for col in columns_config:
                _append_column(col)
        elif columns_config is not None:
            _append_column(columns_config)

        if not normalized:
            if isinstance(column_config, (list, tuple, set)):
                for col in column_config:
                    _append_column(col)
            else:
                _append_column(column_config)

        return normalized
    
    def _auto_map_column(self, target: str, available: List[str]) -> str:
        """自动映射列名"""
        # 常见的列名映射
        mapping = {
            '索书号': ['索书号', '分类号', 'CallNumber', 'CallNo'],
            'CLC号': ['CLC号', '分类号', '分类号码', 'CLC'],
            '题名': ['题名', '书名', '图书名称', 'Title'],
            '附加信息': ['附加信息', 'AdditionalInfo', 'ExtraInfo'],
            '备注': ['备注', 'Remark', 'Notes'],
            '类型/册数': ['类型/册数', '类型', 'Type']
        }
        
        possible_names = mapping.get(target, [target])
        for name in possible_names:
            if name in available:
                return name
        return None
    
    def _load_patterns(self, file_path: str) -> List[str]:
        """加载筛选模式文件"""
        patterns = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        patterns.append(line)
        except Exception as e:
            logger.warning(f"加载筛选模式文件失败 {file_path}: {e}")
        
        return patterns
    
    def _match_pattern(self, text_series: pd.Series, pattern: str, match_type: str) -> pd.Series:
        """统一匹配算法"""
        if match_type == "contains":
            return text_series.str.contains(pattern, na=False, case=False)
        elif match_type == "starts_with":
            return text_series.str.startswith(pattern, na=False)
        elif match_type == "ends_with":
            return text_series.str.endswith(pattern, na=False)
        elif match_type == "regex":
            return text_series.str.match(pattern, na=False)
        else:
            raise ValueError(f"不支持的匹配类型: {match_type}")
