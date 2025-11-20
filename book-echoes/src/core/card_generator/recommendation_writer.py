#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
推荐结果数据库写入器

负责将筛选通过的评选数据写入recommendation_results表
"""

import pandas as pd
import sqlite3
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class RecommendationResultsWriter:
    """推荐结果数据库写入器"""

    def __init__(self, config: Dict, db_path: str = "runtime/database/books_history.db"):
        """
        初始化写入器

        Args:
            config: 完整配置
            db_path: 数据库文件路径
        """
        self.config = config
        self.db_path = db_path
        self.conn = None

        # 获取字段映射
        self.fields_mapping = self.config.get('fields_mapping', {})
        self.excel_to_db = self.fields_mapping.get('excel_to_database', {})
        self.recommendation_mapping = self.excel_to_db.get('recommendation_results', {})

        # 获取统计配置(用于evaluation_batch)
        self.statistics_config = self.config.get('statistics', {})

        if not self.recommendation_mapping:
            raise ValueError("未找到recommendation_results表的字段映射配置")

    def _ensure_db_directory(self):
        """确保数据库目录存在"""
        db_dir = Path(self.db_path).parent
        if not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"创建数据库目录: {db_dir}")

    def connect(self):
        """连接数据库"""
        try:
            self._ensure_db_directory()
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            logger.debug(f"连接数据库成功: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"连接数据库失败: {e}")
            return False

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.debug("数据库连接已关闭")

    def _convert_value(self, value, target_field: str):
        """
        转换数据类型

        Args:
            value: 原始值
            target_field: 目标字段名

        Returns:
            转换后的值
        """
        if value is None or value == '' or pd.isna(value):
            return None

        try:
            # 处理浮点类型字段(分数)
            if target_field in ['preliminary_score', 'final_score']:
                if isinstance(value, (int, float)):
                    return float(value)
                return float(str(value).strip())

            # 处理文本类型字段
            else:
                value_str = str(value).strip()
                return value_str if value_str else None

        except (ValueError, TypeError):
            logger.debug(f"转换值失败: {value} -> {target_field}, 使用原值")
            return value

    def _get_evaluation_batch(self) -> str:
        """
        获取评选批次标识

        Returns:
            str: 评选批次(如"2025-09")
        """
        target_month = self.statistics_config.get('target_month', '')
        if target_month:
            return target_month
        else:
            # 如果没有配置,使用当前年月
            return datetime.now().strftime('%Y-%m')

    def write_recommendation_results(self, df: pd.DataFrame) -> int:
        """
        将筛选通过的评选数据写入recommendation_results表

        Args:
            df: 筛选后的DataFrame(只包含初评结果为"通过"的记录)

        Returns:
            int: 成功写入的记录数
        """
        if not self.connect():
            logger.error("无法连接数据库,写入失败")
            return 0

        try:
            # 开始事务
            self.conn.execute("BEGIN TRANSACTION")

            # 获取评选批次
            evaluation_batch = self._get_evaluation_batch()
            logger.info(f"评选批次: {evaluation_batch}")

            success_count = 0
            error_count = 0

            # 遍历DataFrame,准备数据
            for index, row in df.iterrows():
                try:
                    # 检查初评结果是否为"通过"
                    preliminary_result_col = None
                    for excel_col, db_field in self.recommendation_mapping.items():
                        if db_field == 'preliminary_result':
                            preliminary_result_col = excel_col
                            break

                    if not preliminary_result_col or preliminary_result_col not in row:
                        logger.warning(f"行 {index}: 未找到初评结果列,跳过")
                        error_count += 1
                        continue

                    preliminary_result = str(row[preliminary_result_col]).strip()
                    if preliminary_result != "通过":
                        logger.debug(f"行 {index}: 初评结果不是'通过'({preliminary_result}),跳过")
                        continue

                    # 准备数据
                    record_data = self._prepare_record_data(row, evaluation_batch)
                    if not record_data:
                        logger.warning(f"行 {index}: 数据准备失败,跳过")
                        error_count += 1
                        continue

                    # 写入数据库
                    if self._insert_or_update_record(record_data):
                        success_count += 1
                    else:
                        error_count += 1

                except Exception as e:
                    logger.error(f"处理行 {index} 时发生错误: {e}")
                    error_count += 1
                    continue

            # 提交事务
            self.conn.commit()
            logger.info(f"推荐结果写入完成: 成功 {success_count} 条, 失败 {error_count} 条")

            return success_count

        except Exception as e:
            logger.error(f"写入推荐结果失败: {e}", exc_info=True)
            if self.conn:
                self.conn.rollback()
            return 0

        finally:
            self.close()

    def _prepare_record_data(self, row: pd.Series, evaluation_batch: str) -> Optional[Dict]:
        """
        准备单条记录数据

        Args:
            row: Excel行数据
            evaluation_batch: 评选批次

        Returns:
            Optional[Dict]: 记录数据字典,失败返回None
        """
        try:
            record_data = {}

            # 遍历字段映射,提取数据
            for excel_col, db_field in self.recommendation_mapping.items():
                if excel_col in row:
                    value = row[excel_col]
                    # 转换数据类型
                    converted_value = self._convert_value(value, db_field)
                    if converted_value is not None:
                        record_data[db_field] = converted_value

            # 检查必填字段barcode
            if 'barcode' not in record_data or not record_data['barcode']:
                logger.warning("缺少书目条码,无法写入")
                return None

            # 添加评选批次
            record_data['evaluation_batch'] = evaluation_batch

            # 添加元数据
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            record_data['created_at'] = current_time
            record_data['updated_at'] = current_time

            return record_data

        except Exception as e:
            logger.error(f"准备记录数据失败: {e}")
            return None

    def _insert_or_update_record(self, record_data: Dict) -> bool:
        """
        插入或更新记录(使用UPSERT)

        Args:
            record_data: 记录数据

        Returns:
            bool: 是否成功
        """
        try:
            barcode = record_data['barcode']
            evaluation_batch = record_data['evaluation_batch']

            # 构建UPSERT语句
            # 使用barcode和evaluation_batch作为唯一键
            columns = list(record_data.keys())
            placeholders = ','.join(['?' for _ in columns])
            column_names = ','.join(columns)

            # 构建UPDATE子句(排除barcode和evaluation_batch)
            update_clauses = []
            for col in columns:
                if col not in ['barcode', 'evaluation_batch']:
                    update_clauses.append(f"{col} = excluded.{col}")

            sql = f"""
                INSERT INTO recommendation_results ({column_names})
                VALUES ({placeholders})
                ON CONFLICT(barcode, evaluation_batch) DO UPDATE SET
                    {', '.join(update_clauses)}
            """

            self.conn.execute(sql, list(record_data.values()))
            logger.debug(f"记录写入成功: barcode={barcode}, batch={evaluation_batch}")
            return True

        except Exception as e:
            logger.error(f"插入/更新记录失败: {e}")
            return False

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
