#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Excel更新器

将查询结果更新到Excel文件：
1. 读取Excel文件
2. 根据查重结果更新豆瓣字段
3. 写入Excel文件
4. 使用统一字段映射配置

作者：豆瓣评分模块开发组
版本：2.0
创建时间：2025-11-05
"""

import os
import logging
import pandas as pd
import yaml
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def load_field_mapping(config_path: str = "config/setting.yaml") -> Dict[str, Dict]:
    """从统一字段映射配置加载字段映射"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        fields_mapping = config.get('fields_mapping', {})

        # 豆瓣字段映射 - 从统一配置获取
        douban_fields = fields_mapping.get('douban', {})
        if not douban_fields:
            raise ValueError("未找到统一字段映射配置 (fields_mapping.douban)")

        # 数据库到Excel映射 - 获取books表映射
        db_to_excel = fields_mapping.get('database_to_excel', {}).get('books', {})
        if not db_to_excel:
            raise ValueError("未找到数据库到Excel字段映射配置 (fields_mapping.database_to_excel.books)")

        # 反向映射（数据库字段到Excel列名）
        excel_columns_mapping = db_to_excel

        # 豆瓣字段映射（内部字段名到Excel列名）
        douban_to_excel = {}
        for internal_field, excel_col in douban_fields.items():
            douban_to_excel[f"douban_{internal_field}"] = excel_col

        return {
            'douban_to_excel': douban_to_excel,
            'excel_columns_mapping': excel_columns_mapping
        }

    except Exception as e:
        logger.error(f"加载字段映射配置失败: {e}")
        raise


class ExcelUpdater:
    """Excel更新器"""

    def __init__(self, excel_path: str, config_path: str = "config/setting.yaml"):
        """
        初始化Excel更新器

        Args:
            excel_path: Excel文件路径
            config_path: 配置文件路径
        """
        self.excel_path = excel_path
        self.df = None
        self.backup_path = None

        # 加载字段映射配置
        mappings = load_field_mapping(config_path)
        self.douban_fields_mapping = mappings['douban_to_excel']
        self.excel_columns_mapping = mappings['excel_columns_mapping']

        logger.info(f"Excel更新器初始化: {excel_path}")

    def load(self):
        """加载Excel文件"""
        try:
            if not os.path.exists(self.excel_path):
                raise FileNotFoundError(f"Excel文件不存在: {self.excel_path}")

            self.df = pd.read_excel(self.excel_path)
            logger.info(f"成功加载Excel文件: {len(self.df)} 行数据")
            return True

        except Exception as e:
            logger.error(f"加载Excel文件失败: {e}")
            raise

    def update_from_database(self, books_data: List[Dict]):
        """
        从数据库更新数据到Excel (优化版)

        Args:
            books_data: 从数据库获取的书籍数据列表
        """
        if self.df is None or len(self.df) == 0:
            logger.warning("Excel数据为空，跳过更新")
            return

        if not books_data:
            logger.info("没有数据库数据需要更新")
            return

        logger.info(f"开始从数据库更新 {len(books_data)} 条记录到Excel")

        try:
            # 优化: 一次性构建barcode索引 O(n)
            barcode_to_idx = self._build_barcode_index()

            updated_count = 0
            not_found_count = 0

            # 优化: 直接查找更新 O(m)
            for book_data in books_data:
                barcode = book_data.get('barcode') or book_data.get('书目条码')
                if not barcode:
                    logger.warning("跳过没有barcode的记录")
                    continue

                barcode = str(barcode).strip()

                # O(1)查找
                if barcode in barcode_to_idx:
                    excel_index = barcode_to_idx[barcode]
                    fields_updated = self._update_douban_fields(
                        self.df, excel_index, book_data
                    )

                    if fields_updated > 0:
                        updated_count += 1
                else:
                    not_found_count += 1
                    logger.debug(f"在Excel中未找到条码 {barcode}")

            logger.info(
                f"从数据库更新完成: {updated_count} 条成功, "
                f"{not_found_count} 条未找到"
            )

        except Exception as e:
            logger.error(f"从数据库更新Excel失败: {e}")
            raise

    def update_from_crawler(self, books_data: List[Dict]):
        """
        从爬虫更新数据到Excel (优化版)

        Args:
            books_data: 爬虫获取的书籍数据列表
        """
        if self.df is None or len(self.df) == 0:
            logger.warning("Excel数据为空，跳过更新")
            return

        if not books_data:
            logger.info("没有爬虫数据需要更新")
            return

        logger.info(f"开始从爬虫更新 {len(books_data)} 条记录到Excel")

        try:
            # 优化: 一次性构建barcode索引
            barcode_to_idx = self._build_barcode_index()

            updated_count = 0
            not_found_count = 0

            for book_data in books_data:
                barcode = book_data.get('barcode') or book_data.get('书目条码')
                if not barcode:
                    logger.warning("跳过没有barcode的记录")
                    continue

                barcode = str(barcode).strip()

                # O(1)查找
                if barcode in barcode_to_idx:
                    excel_index = barcode_to_idx[barcode]
                    fields_updated = self._update_douban_fields(
                        self.df, excel_index, book_data
                    )

                    if fields_updated > 0:
                        updated_count += 1
                else:
                    not_found_count += 1
                    logger.debug(f"在Excel中未找到条码 {barcode}")

            logger.info(
                f"从爬虫更新完成: {updated_count} 条成功, "
                f"{not_found_count} 条未找到"
            )

        except Exception as e:
            logger.error(f"从爬虫更新Excel失败: {e}")
            raise

    def _build_barcode_index(self) -> Dict[str, int]:
        """
        构建barcode到行索引的映射

        Returns:
            Dict[str, int]: barcode → DataFrame行索引的映射
        """
        barcode_column = None
        if 'barcode' in self.df.columns:
            barcode_column = 'barcode'
        elif '书目条码' in self.df.columns:
            barcode_column = '书目条码'
        else:
            raise ValueError("Excel中未找到barcode列")

        # 构建映射: O(n)复杂度,但只执行一次
        barcode_to_idx = {}
        for idx, row in self.df.iterrows():
            barcode = str(row[barcode_column]).strip()
            if barcode:
                barcode_to_idx[barcode] = idx

        logger.debug(f"构建barcode索引完成: {len(barcode_to_idx)} 条记录")
        return barcode_to_idx

    def _find_row_index(self, barcode: str) -> int:
        """
        根据barcode查找Excel行索引 (已废弃,保留用于向后兼容)

        Args:
            barcode: 条码

        Returns:
            int: 行索引，如果未找到返回-1

        Note:
            此方法已废弃,建议使用_build_barcode_index()构建索引后直接查找
        """
        # 检查barcode列
        barcode_column = None
        if 'barcode' in self.df.columns:
            barcode_column = 'barcode'
        elif '书目条码' in self.df.columns:
            barcode_column = '书目条码'
        else:
            logger.error("Excel中未找到barcode列")
            return -1

        # 查找匹配的行
        for idx, row in self.df.iterrows():
            row_barcode = str(row[barcode_column]).strip()
            if row_barcode == str(barcode).strip():
                return idx

        return -1

    def _update_douban_fields(self, df: pd.DataFrame, row_index: int, book_data: Dict) -> int:
        """
        更新指定行的豆瓣字段

        Args:
            df: DataFrame对象
            row_index: 行索引
            book_data: 书籍数据

        Returns:
            int: 更新的字段数量
        """
        updated_count = 0

        for db_field, excel_column in self.douban_fields_mapping.items():
            if excel_column not in df.columns:
                # 如果Excel列不存在，跳过
                continue

            if db_field in book_data and book_data[db_field] is not None:
                value = book_data[db_field]

                # 转换类型（如果是数值类型）
                if isinstance(value, (int, float)) and not pd.isna(value):
                    df.at[row_index, excel_column] = value
                    updated_count += 1
                elif isinstance(value, str) and value.strip():
                    df.at[row_index, excel_column] = value.strip()
                    updated_count += 1

        return updated_count

    def update_single_row(self, row_index: int, book_data: Dict):
        """
        更新单行数据

        Args:
            row_index: 行索引
            book_data: 书籍数据
        """
        if self.df is None:
            raise ValueError("请先加载Excel文件")

        updated_count = self._update_douban_fields(self.df, row_index, book_data)

        logger.debug(f"更新第 {row_index + 1} 行，{updated_count} 个字段")

    def save(self, output_path: str = None):
        """
        保存Excel文件

        Args:
            output_path: 输出文件路径（可选，默认覆盖原文件）

        Returns:
            str: 保存的文件路径
        """
        if self.df is None:
            raise ValueError("没有可保存的数据")

        # 确定输出路径
        if not output_path:
            output_path = self.excel_path
        else:
            # 如果指定了新的输出路径，使用新路径
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

        try:
            # 原子性保存：先写临时文件，再重命名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_file = output_path.replace('.xlsx', f'_tmp_{timestamp}.xlsx')

            self.df.to_excel(temp_file, index=False, engine='openpyxl')

            # 删除旧文件（如果存在）
            if os.path.exists(output_path):
                os.remove(output_path)

            # 重命名临时文件
            os.rename(temp_file, output_path)

            logger.info(f"Excel文件保存成功: {output_path}")

            return output_path

        except Exception as e:
            logger.error(f"保存Excel文件失败: {e}")
            raise

    def save_backup(self):
        """
        创建Excel文件备份

        Returns:
            str: 备份文件路径
        """
        if self.df is None:
            raise ValueError("没有可备份的数据")

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.excel_path.replace('.xlsx', f'_backup_{timestamp}.xlsx')

            self.df.to_excel(backup_path, index=False, engine='openpyxl')

            self.backup_path = backup_path
            logger.info(f"创建Excel备份成功: {backup_path}")

            return backup_path

        except Exception as e:
            logger.error(f"创建Excel备份失败: {e}")
            raise

    def get_column_mapping(self) -> Dict:
        """
        获取字段映射信息

        Returns:
            Dict: 字段映射字典
        """
        return DOUBAN_FIELDS_MAPPING

    def check_columns_exist(self) -> Dict:
        """
        检查Excel中是否包含所需的豆瓣字段列

        Returns:
            Dict: 列存在情况
        """
        if self.df is None:
            raise ValueError("请先加载Excel文件")

        existing_columns = {}
        for db_field, excel_column in DOUBAN_FIELDS_MAPPING.items():
            existing_columns[db_field] = excel_column in self.df.columns

        return existing_columns

    def create_missing_columns(self):
        """创建缺失的豆瓣字段列"""
        if self.df is None:
            raise ValueError("请先加载Excel文件")

        created_count = 0
        for db_field, excel_column in DOUBAN_FIELDS_MAPPING.items():
            if excel_column not in self.df.columns:
                self.df[excel_column] = ""
                created_count += 1
                logger.debug(f"创建新列: {excel_column}")

        if created_count > 0:
            logger.info(f"创建了 {created_count} 个缺失的列")

    def get_stats(self) -> Dict:
        """
        获取Excel统计信息

        Returns:
            Dict: 统计信息
        """
        if self.df is None:
            return {}

        stats = {
            'total_rows': len(self.df),
            'total_columns': len(self.df.columns),
            'columns': list(self.df.columns),
            'douban_columns_count': sum(1 for col in self.df.columns if col in DOUBAN_FIELDS_MAPPING.values()),
            'douban_columns': [col for col in self.df.columns if col in DOUBAN_FIELDS_MAPPING.values()]
        }

        # 检查豆瓣字段的填充情况
        filled_douban = 0
        for excel_column in DOUBAN_FIELDS_MAPPING.values():
            if excel_column in self.df.columns:
                non_empty = self.df[excel_column].notna() & (self.df[excel_column] != "")
                filled_douban += non_empty.sum()

        stats['douban_fields_filled'] = filled_douban

        return stats

    def close(self):
        """清理资源"""
        self.df = None
        logger.debug("Excel更新器资源已清理")
