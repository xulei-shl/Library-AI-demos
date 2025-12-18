#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Excel到数据库写入器 - 独立模块

负责将Excel数据转换并写入数据库的三张表：
1. books表 - 书籍基础信息和豆瓣信息
2. borrow_records表 - 借阅记录
3. borrow_statistics表 - 借阅统计

核心功能：
- 支持不同的写入策略（全部写入 vs 仅增量更新）
- 统一字段映射和类型转换
- 数据验证和清洗

作者：图书馆系统开发团队
版本：1.0.0
创建时间：2025-11-05
"""

import pandas as pd
import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar

logger = logging.getLogger(__name__)


class ExcelToDatabaseWriter:
    """Excel到数据库写入器"""

    def __init__(self, config: Dict[str, Any], update_mode: str = "merge"):
        """
        初始化写入器

        Args:
            config: 完整配置（从get_config_manager获取）
            update_mode: 更新模式（merge保留原字段，overwrite完全覆盖）
        """
        self.config = config
        self.update_mode = update_mode

        # 获取字段映射
        self.fields_mapping = self.config.get('fields_mapping', {})
        if not self.fields_mapping:
            raise ValueError("未找到字段映射配置 (fields_mapping)")

        self.excel_to_db = self.fields_mapping.get('excel_to_database', {})
        if not self.excel_to_db:
            raise ValueError("未找到Excel到数据库的字段映射 (fields_mapping.excel_to_database)")

        self.books_mapping = self.excel_to_db.get('books', {})
        self.borrow_records_mapping = self.excel_to_db.get('borrow_records', {})
        self.borrow_statistics_mapping = self.excel_to_db.get('borrow_statistics', {})

        # 获取统计配置
        self.statistics_config = self.config.get('statistics', {})

    def _normalize_barcode(self, value: Any) -> str:
        """标准化条码，避免Excel把长数字解析成浮点后附带.0"""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return ""

        if isinstance(value, (int, float)):
            return f"{int(value)}"

        value_str = str(value).strip()
        if value_str.endswith('.0') and value_str[:-2].isdigit():
            return value_str[:-2]
        return value_str

    def _convert_value(self, value, target_field: str) -> Any:
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
            # 处理整数类型字段
            if target_field in ['douban_pages', 'douban_pub_year', 'douban_rating_count',
                                'borrow_count_3m', 'borrow_count_m1', 'borrow_count_m2', 'borrow_count_m3',
                                'stat_year', 'stat_month']:
                if isinstance(value, (int, float)):
                    return int(value)

                value_str = str(value).strip()

                # 特殊处理豆瓣出版年字段 - 从日期格式中提取年份
                if target_field == 'douban_pub_year':
                    year_match = re.match(r'(\d{4})', value_str)
                    if year_match:
                        return int(year_match.group(1))

                # 特殊处理豆瓣评价人数字段 - 从 "XX人评价" 中提取数字
                if target_field == 'douban_rating_count':
                    count_match = re.search(r'(\d+)', value_str)
                    if count_match:
                        return int(count_match.group(1))

                # 其他整数字段直接转换
                return int(value_str)

            # 处理浮点类型字段
            elif target_field in ['douban_rating']:
                if isinstance(value, (int, float)):
                    return float(value)
                return float(str(value).strip())

            # 处理文本类型字段
            else:
                value_str = str(value).strip()

                # 特殊处理 additional_info 字段 - 去除 [.*] 格式的附件信息
                if target_field == 'additional_info':
                    clean_match = re.match(r'^(\d+)', value_str)
                    if clean_match:
                        return clean_match.group(1)

                # 特殊处理ISBN相关字段 - 去除 .0 后缀
                if target_field in ['isbn', 'douban_isbn']:
                    if value_str.endswith('.0'):
                        value_str = value_str[:-2]
                    return value_str if value_str else None

                return value_str if value_str else None

        except (ValueError, TypeError):
            logger.debug(f"转换值失败: {value} -> {target_field}, 使用原值")
            return value

    def _calculate_stat_period(self) -> Tuple[int, int, str, str, str]:
        """
        计算统计周期信息

        Returns:
            (stat_year, stat_month, period_start, period_end, period_label)
        """
        # 获取目标月份（从配置或使用当前月份）
        target_month = self.statistics_config.get('target_month')

        if target_month:
            try:
                stat_year, stat_month = map(int, target_month.split('-'))
                # 解析目标月份（YYYY-MM格式）
                first_day = datetime.strptime(target_month + '-01', '%Y-%m-%d')
                last_day = calendar.monthrange(stat_year, stat_month)[1]
                period_end = first_day.replace(day=last_day)
            except (ValueError, AttributeError):
                logger.warning(f"target_month格式错误，使用当前日期作为统计周期")
                target_month = None

        if not target_month:
            # 如果配置文件中没有或格式错误，使用当前日期
            current_date = datetime.now()
            stat_year = current_date.year
            stat_month = current_date.month
            last_day = calendar.monthrange(stat_year, stat_month)[1]
            period_end = current_date.replace(day=last_day)

        # 计算周期范围（最近三个月）
        # 修正周期开始日期为目标月份的第一天
        period_start = first_day - relativedelta(months=2)  # 保留三个月范围的开始日期
        period_start = period_start.replace(day=1)
        period_label = f"{stat_year}-{stat_month:02d}"

        return (
            stat_year,
            stat_month,
            period_start.strftime('%Y-%m-%d'),
            period_end.strftime('%Y-%m-%d'),
            period_label
        )

    def write_all_tables(
        self,
        df: pd.DataFrame,
        categories: Optional[Dict] = None,
        write_books: bool = True,
        write_borrow_records: bool = True,
        write_borrow_statistics: bool = True,
        barcode_column: str = "书目条码",
        isbn_column: str = "ISBN号",
        douban_fields_mapping: Optional[Dict] = None
    ) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        将Excel数据写入数据库三表

        Args:
            df: 完整的Excel数据
            categories: 查重分类结果（existing_valid, existing_stale, new）
            write_books: 是否写入books表
            write_borrow_records: 是否写入borrow_records表
            write_borrow_statistics: 是否写入borrow_statistics表
            barcode_column: 条码列名
            isbn_column: ISBN列名
            douban_fields_mapping: 豆瓣字段映射（用于判断豆瓣数据是否有效）

        Returns:
            (books_data, borrow_records_data, borrow_statistics_data)

        Note:
            写入策略：
            - books表：只有当write_books=True时才写入，且基于categories控制写入范围
                     如果categories存在，只写入existing_stale和new（跳过existing_valid）
                     如果categories不存在，写入全部数据
            - borrow_records表：始终写入全部数据（借阅记录独立于豆瓣数据）
            - borrow_statistics表：始终写入全部数据（统计独立于豆瓣数据）
        """
        books_data = []
        borrow_records_data = []
        borrow_statistics_data = []

        # 计算统计周期
        stat_year, stat_month, period_start, period_end, period_label = self._calculate_stat_period()

        # 记录处理过的barcode，避免重复处理
        processed_barcodes = set()

        # 遍历所有Excel行
        for index, row in df.iterrows():
            barcode = self._normalize_barcode(row.get(barcode_column, ''))
            if not barcode or barcode in processed_barcodes:
                continue
            processed_barcodes.add(barcode)

            # ========== 1. 准备books表数据 ==========
            if write_books:
                # 判断是否需要写入books数据
                should_write_books = True
                if categories:
                    # 如果有查重分类，跳过existing_valid（避免重复写入）
                    existing_valid_barcodes = {item['barcode'] for item in categories.get('existing_valid', [])}
                    if barcode in existing_valid_barcodes:
                        should_write_books = False

                if should_write_books:
                    book_info = self._prepare_books_data(
                        row, barcode, isbn_column, douban_fields_mapping
                    )
                    if book_info:
                        books_data.append(book_info)

            # ========== 2. 准备borrow_records表数据 ==========
            if write_borrow_records:
                borrow_record = self._prepare_borrow_records_data(row, barcode)
                if borrow_record:
                    borrow_records_data.append(borrow_record)

            # ========== 3. 准备borrow_statistics表数据 ==========
            if write_borrow_statistics:
                stat_record = self._prepare_borrow_statistics_data(
                    row, barcode, stat_year, stat_month, period_start, period_end, period_label
                )
                if stat_record:
                    borrow_statistics_data.append(stat_record)

        logger.info(
            f"数据准备完成: "
            f"books={len(books_data)}, "
            f"borrow_records={len(borrow_records_data)}, "
            f"borrow_statistics={len(borrow_statistics_data)}"
        )

        return books_data, borrow_records_data, borrow_statistics_data

    def _prepare_books_data(
        self,
        row: pd.Series,
        barcode: str,
        isbn_column: str,
        douban_fields_mapping: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        准备books表数据

        Args:
            row: Excel行数据
            barcode: 条码
            isbn_column: ISBN列名
            douban_fields_mapping: 豆瓣字段映射（用于判断豆瓣数据是否有效）

        Returns:
            books数据字典，如果无效返回None
        """
        book_info = {
            'barcode': barcode,
            'call_no': str(row.get('索书号', '')).strip(),
            'cleaned_call_no': str(row.get('清理后索书号', '')).strip(),
            'book_title': str(row.get('书名', '')).strip(),
        }

        # 处理 additional_info 字段（去除附件信息）
        additional_info_value = row.get('附加信息', '')
        if additional_info_value and not pd.isna(additional_info_value):
            book_info['additional_info'] = self._convert_value(additional_info_value, 'additional_info')

        # 添加ISBN（优先使用豆瓣爬取到的ISBN）
        isbn_val = row.get(isbn_column, '')
        if not isbn_val or pd.isna(isbn_val) or str(isbn_val).strip() == "":
            # 如果Excel中没有ISBN，尝试使用豆瓣字段中的ISBN
            if douban_fields_mapping:
                isbn_col = douban_fields_mapping.get('ISBN', '')
                if isbn_col:
                    isbn_val = row.get(isbn_col, '')

        book_info['isbn'] = str(isbn_val).strip() if isbn_val and not pd.isna(isbn_val) else ""

        # 检查是否有豆瓣数据（仅在需要时）
        has_douban_data = False
        if douban_fields_mapping:
            # 检查豆瓣评分或豆瓣书名是否有有效数据
            rating_col = douban_fields_mapping.get('评分', '')
            title_col = douban_fields_mapping.get('题名', '')

            rating_val = row.get(rating_col, '') if rating_col else ''
            title_val = row.get(title_col, '') if title_col else ''

            # 豆瓣有效数据：不是"豆瓣无数据"或"豆瓣爬取失败"
            if (rating_val and str(rating_val).strip() not in ["", "豆瓣无数据", "豆瓣爬取失败"] or
                title_val and str(title_val).strip() not in ["", "豆瓣无数据", "豆瓣爬取失败"]):
                has_douban_data = True

        # 添加豆瓣信息（仅当有效时）
        if douban_fields_mapping:
            for field, excel_col in douban_fields_mapping.items():
                value = row.get(excel_col, '')
                if value and str(value).strip() not in ["豆瓣无数据", "豆瓣爬取失败", ""]:
                    # 转换为数据库字段名
                    db_field = self.books_mapping.get(excel_col)
                    if db_field:
                        book_info[db_field] = self._convert_value(value, db_field)

        # 只添加有效的books数据（必须有barcode）
        if not book_info.get('barcode'):
            return None

        # 添加元数据字段
        book_info['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        book_info['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        book_info.setdefault('data_version', '1.0')

        return book_info

    def _prepare_borrow_records_data(self, row: pd.Series, barcode: str) -> Optional[Dict]:
        """
        准备borrow_records表数据

        Args:
            row: Excel行数据
            barcode: 条码

        Returns:
            borrow_records数据字典，如果无效返回None
        """
        borrow_record = {
            'barcode': barcode,
        }

        # 根据映射添加借阅记录字段
        for excel_col, db_field in self.borrow_records_mapping.items():
            if db_field == 'barcode':
                continue  # 已处理
            value = row.get(excel_col, '')
            if value is not None and not pd.isna(value):
                borrow_record[db_field] = self._convert_value(value, db_field)

        # 只添加有效的借阅记录（必须有barcode和reader_card_no）
        if not borrow_record.get('barcode'):
            return None

        reader_card = borrow_record.get('reader_card_no', '')
        if not reader_card or str(reader_card).strip() in ["", "nan"]:
            return None  # 没有读者卡号的记录不写入

        # 添加元数据字段
        borrow_record['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        return borrow_record

    def _prepare_borrow_statistics_data(
        self,
        row: pd.Series,
        barcode: str,
        stat_year: int,
        stat_month: int,
        period_start: str,
        period_end: str,
        period_label: str
    ) -> Optional[Dict]:
        """
        准备borrow_statistics表数据

        Args:
            row: Excel行数据
            barcode: 条码
            stat_year: 统计年份
            stat_month: 统计月份
            period_start: 周期开始日期
            period_end: 周期结束日期
            period_label: 周期标签

        Returns:
            borrow_statistics数据字典，如果无效返回None
        """
        stat_record = {
            'barcode': barcode,
            'stat_period': period_label,
            'stat_year': stat_year,
            'stat_month': stat_month,
            'period_start': period_start,
            'period_end': period_end,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

        # 根据映射添加统计数据字段
        for excel_col, db_field in self.borrow_statistics_mapping.items():
            if db_field in ['barcode', 'stat_period', 'stat_year', 'stat_month',
                           'period_start', 'period_end', 'created_at', 'updated_at']:
                continue  # 已处理或不需要
            value = row.get(excel_col, '')
            if value is not None and not pd.isna(value):
                stat_record[db_field] = self._convert_value(value, db_field)

        # 只添加有效的统计数据（必须有barcode）
        if not stat_record.get('barcode'):
            return None

        return stat_record

    def write_incremental_books_only(
        self,
        df: pd.DataFrame,
        categories: Dict,
        barcode_column: str = "书目条码",
        isbn_column: str = "ISBN号",
        douban_fields_mapping: Optional[Dict] = None
    ) -> List[Dict]:
        """
        仅写入需要更新的books数据（existing_stale + new）

        Args:
            df: 完整的Excel数据
            categories: 查重分类结果
            barcode_column: 条码列名
            isbn_column: ISBN列名
            douban_fields_mapping: 豆瓣字段映射

        Returns:
            books数据列表
        """
        books_data = []

        # 获取需要更新的数据（existing_stale + new）
        books_to_update = categories.get('existing_stale', []) + categories.get('new', [])

        for book_data in books_to_update:
            index = book_data.get('_index')
            if index is None:
                continue

            row = df.iloc[index]
            barcode = self._normalize_barcode(row.get(barcode_column, ''))

            book_info = self._prepare_books_data(
                row, barcode, isbn_column, douban_fields_mapping
            )
            if book_info:
                books_data.append(book_info)

        logger.info(f"增量更新books数据: {len(books_data)}条")
        return books_data

    def write_all_borrow_records(
        self,
        df: pd.DataFrame,
        barcode_column: str = "书目条码"
    ) -> List[Dict]:
        """
        写入所有借阅记录（包括existing_valid）

        Args:
            df: 完整的Excel数据
            barcode_column: 条码列名

        Returns:
            borrow_records数据列表
        """
        borrow_records_data = []

        processed_barcodes = set()
        for index, row in df.iterrows():
            barcode = self._normalize_barcode(row.get(barcode_column, ''))
            if not barcode or barcode in processed_barcodes:
                continue
            processed_barcodes.add(barcode)

            borrow_record = self._prepare_borrow_records_data(row, barcode)
            if borrow_record:
                borrow_records_data.append(borrow_record)

        logger.info(f"写入所有borrow_records数据: {len(borrow_records_data)}条")
        return borrow_records_data

    def write_all_borrow_statistics(
        self,
        df: pd.DataFrame,
        barcode_column: str = "书目条码"
    ) -> List[Dict]:
        """
        写入所有借阅统计（包括existing_valid）

        Args:
            df: 完整的Excel数据
            barcode_column: 条码列名

        Returns:
            borrow_statistics数据列表
        """
        borrow_statistics_data = []

        # 计算统计周期
        stat_year, stat_month, period_start, period_end, period_label = self._calculate_stat_period()

        processed_barcodes = set()
        for index, row in df.iterrows():
            barcode = self._normalize_barcode(row.get(barcode_column, ''))
            if not barcode or barcode in processed_barcodes:
                continue
            processed_barcodes.add(barcode)

            stat_record = self._prepare_borrow_statistics_data(
                row, barcode, stat_year, stat_month, period_start, period_end, period_label
            )
            if stat_record:
                borrow_statistics_data.append(stat_record)

        logger.info(f"写入所有borrow_statistics数据: {len(borrow_statistics_data)}条")
        return borrow_statistics_data

    # =====================================================================
    # 增量写入辅助
    # =====================================================================

    def build_single_payload(
        self,
        row: pd.Series,
        barcode_column: str = "书目条码",
        isbn_column: str = "ISBN号",
        douban_fields_mapping: Optional[Dict] = None
    ) -> Optional[Tuple[Optional[Dict], Optional[Dict], Optional[Dict]]]:
        """
        将单条 Excel 记录转换为数据库写入 payload。

        Args:
            row: 当前行
            barcode_column: 条码列名
            isbn_column: ISBN列名
            douban_fields_mapping: 豆瓣字段映射

        Returns:
            (book, borrow_record, borrow_stat)
        """
        barcode = self._normalize_barcode(row.get(barcode_column, ""))
        if not barcode:
            return None

        try:
            book_info = self._prepare_books_data(
                row, barcode, isbn_column, douban_fields_mapping
            )
            borrow_record = self._prepare_borrow_records_data(row, barcode)
            stat_year, stat_month, period_start, period_end, period_label = self._calculate_stat_period()
            borrow_stat = self._prepare_borrow_statistics_data(
                row, barcode, stat_year, stat_month, period_start, period_end, period_label
            )
            return book_info, borrow_record, borrow_stat
        except Exception as exc:
            logger.error(f"构建增量payload失败: {exc}")
            return None
