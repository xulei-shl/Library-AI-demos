"""
数据库查重过滤器 - 过滤已在评选阶段入选的书目

功能:
1. 连接SQLite数据库
2. 查询recommendation_results表中manual_selection='通过'的记录
3. 过滤掉已入选的书目
4. 返回查重结果和统计信息
"""

import sqlite3
import os
from typing import Dict, Any, Tuple, List, Optional
import pandas as pd
from pathlib import Path
from .base_filter import BaseFilter
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DbDuplicateFilter(BaseFilter):
    """数据库查重过滤器 - 过滤已在评选阶段入选的书目"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.db_table = config.get('db_table', 'recommendation_results')
        self.db_column = config.get('db_column', 'barcode')
        self.filter_condition = config.get('filter_condition', {})
        self.db_path = None
        self.conn = None
        
        # 初始化数据库连接
        self._init_database_connection()
    
    def _init_database_connection(self):
        """初始化数据库连接"""
        try:
            # 从配置文件读取数据库路径
            db_path = self._get_db_path_from_config()
            
            if not db_path or not os.path.exists(db_path):
                logger.warning(f"数据库文件不存在: {db_path}, 数据库查重功能将被跳过")
                self.enabled = False
                return
            
            self.db_path = db_path
            logger.info(f"数据库查重过滤器初始化成功, 数据库路径: {db_path}")
            
        except Exception as e:
            logger.error(f"初始化数据库连接失败: {e}")
            self.enabled = False
    
    def _get_db_path_from_config(self) -> Optional[str]:
        """从配置文件读取数据库路径"""
        try:
            import yaml
            config_path = "config/setting.yaml"
            
            if not os.path.exists(config_path):
                logger.warning(f"配置文件不存在: {config_path}")
                return None
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 读取数据库路径配置
            db_path = config.get('douban', {}).get('database', {}).get('db_path')
            
            if not db_path:
                logger.warning("配置文件中未找到数据库路径配置 (douban.database.db_path)")
                return None
            
            return db_path
            
        except Exception as e:
            logger.error(f"读取数据库路径配置失败: {e}")
            return None
    
    def _connect_database(self) -> bool:
        """建立数据库连接"""
        try:
            if not self.db_path:
                return False
            
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            return True
            
        except Exception as e:
            logger.error(f"连接数据库失败: {e}")
            return False
    
    def _close_database(self):
        """关闭数据库连接"""
        if self.conn:
            try:
                self.conn.close()
                self.conn = None
            except Exception as e:
                logger.error(f"关闭数据库连接失败: {e}")
    
    def _batch_query_duplicates(self, barcodes: List[str]) -> set:
        """批量查询已入选的书目条码
        
        Args:
            barcodes: 条码列表
            
        Returns:
            set: 已入选的条码集合
        """
        if not self.conn:
            return set()
        
        try:
            # 构建查询条件
            condition_column = self.filter_condition.get('column', 'manual_selection')
            condition_value = self.filter_condition.get('value', '通过')
            
            # 批量查询(使用IN子句)
            placeholders = ','.join(['?' for _ in barcodes])
            sql = f"""
                SELECT DISTINCT {self.db_column}
                FROM {self.db_table}
                WHERE {condition_column} = ?
                AND {self.db_column} IN ({placeholders})
            """
            
            params = [condition_value] + barcodes
            cursor = self.conn.execute(sql, params)
            
            # 获取所有匹配的条码
            duplicate_barcodes = set()
            for row in cursor.fetchall():
                barcode = row[self.db_column]
                if barcode:
                    duplicate_barcodes.add(str(barcode).strip())
            
            logger.info(f"数据库查重完成: 查询 {len(barcodes)} 条记录, 发现 {len(duplicate_barcodes)} 条已入选")
            return duplicate_barcodes
            
        except Exception as e:
            logger.error(f"批量查询数据库失败: {e}")
            return set()
    
    def apply(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """应用数据库查重过滤
        
        Args:
            data: 输入数据
            
        Returns:
            Tuple[pd.DataFrame, Dict]: (过滤后的数据, 统计信息)
        """
        if not self.enabled:
            logger.info("数据库查重过滤器未启用,跳过")
            return data, {
                'status': 'skipped',
                'description': self.description,
                'excluded_count': 0,
                'reason': '数据库不存在或连接失败'
            }
        
        original_count = len(data)
        logger.info(f"开始数据库查重过滤, 原始数据: {original_count} 条")
        
        try:
            # 验证目标列是否存在
            valid_columns = self._validate_columns(data)
            if not valid_columns:
                logger.warning(f"未找到目标列 '{self.target_column}', 数据库查重跳过")
                return data, {
                    'status': 'skipped',
                    'description': self.description,
                    'excluded_count': 0,
                    'target_column': self.target_column,
                    'reason': f"未找到目标列 '{self.target_column}'"
                }
            
            target_col = valid_columns[0]
            
            # 建立数据库连接
            if not self._connect_database():
                logger.warning("数据库连接失败, 数据库查重跳过")
                return data, {
                    'status': 'error',
                    'description': self.description,
                    'excluded_count': 0,
                    'reason': '数据库连接失败'
                }
            
            # 提取所有条码
            barcodes = data[target_col].astype(str).str.strip().tolist()
            
            # 批量查询已入选的条码
            duplicate_barcodes = self._batch_query_duplicates(barcodes)
            
            # 过滤数据
            if duplicate_barcodes:
                # 创建过滤掩码
                mask = data[target_col].astype(str).str.strip().isin(duplicate_barcodes)
                filtered_data = data[~mask].copy()
                excluded_count = mask.sum()
            else:
                filtered_data = data.copy()
                excluded_count = 0
            
            # 关闭数据库连接
            self._close_database()
            
            filtered_count = len(filtered_data)
            excluded_ratio = excluded_count / original_count if original_count > 0 else 0
            
            logger.info(f"数据库查重完成: {original_count} -> {filtered_count} 条 (排除 {excluded_count} 条)")
            
            return filtered_data, {
                'status': 'completed',
                'description': self.description,
                'original_count': original_count,
                'filtered_count': filtered_count,
                'excluded_count': excluded_count,
                'excluded_ratio': excluded_ratio,
                'target_column': target_col,
                'db_table': self.db_table,
                'db_column': self.db_column,
                'filter_condition': self.filter_condition,
                'duplicate_count': len(duplicate_barcodes)
            }
            
        except Exception as e:
            logger.error(f"数据库查重过滤失败: {e}")
            self._close_database()
            return data, {
                'status': 'error',
                'description': self.description,
                'excluded_count': 0,
                'error': str(e)
            }
