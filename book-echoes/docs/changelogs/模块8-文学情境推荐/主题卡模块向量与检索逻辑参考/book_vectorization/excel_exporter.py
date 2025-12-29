#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Excel导出器，负责从数据库查询书籍信息并导出为Excel

该模块负责根据book_id列表从数据库查询完整的书籍信息，
并将结果导出为Excel文件，提供更丰富的书籍数据。
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from src.core.book_vectorization.database_reader import DatabaseReader
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ExcelExporter:
    """Excel导出器，负责从数据库查询书籍信息并导出为Excel"""
    
    def __init__(self, db_config: Dict, excel_config: Dict):
        """
        初始化Excel导出器
        
        Args:
            db_config: 数据库配置
            excel_config: Excel导出配置
        """
        self.db_reader = DatabaseReader(db_config)
        self.excel_config = excel_config
        
        # 确保输出目录存在
        output_dir = Path(excel_config.get('default_directory', 'runtime/outputs/excel'))
        if excel_config.get('auto_create_directory', True):
            output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_books_to_excel(self, book_ids: List[int], output_path: str) -> str:
        """
        根据book_id列表查询数据库并导出为Excel
        
        Args:
            book_ids: 书籍ID列表
            output_path: 输出Excel文件路径
            
        Returns:
            实际保存的Excel文件路径
            
        Raises:
            DatabaseError: 数据库查询错误
            IOError: 文件写入错误
        """
        if not book_ids:
            logger.warning("书籍ID列表为空，无法导出Excel")
            raise ValueError("书籍ID列表为空")
        
        logger.info(f"开始导出Excel，共{len(book_ids)}本书籍")
        
        try:
            # 查询数据库获取书籍信息
            books_data = self._query_books_from_database(book_ids)
            
            if not books_data:
                logger.warning("未查询到任何书籍数据")
                raise ValueError("未查询到任何书籍数据")
            
            # 转换为DataFrame并导出Excel
            excel_path = self._export_to_excel(books_data, output_path)
            
            logger.info(f"Excel导出完成: {excel_path}")
            return excel_path
            
        except Exception as e:
            logger.error(f"导出Excel时发生错误: {e}")
            raise
    
    def _query_books_from_database(self, book_ids: List[int]) -> List[Dict]:
        """
        从数据库查询书籍信息
        
        Args:
            book_ids: 书籍ID列表
            
        Returns:
            书籍信息列表
        """
        books_data = []
        
        for book_id in book_ids:
            try:
                book_info = self.db_reader.get_book_by_id(book_id)
                if book_info:
                    # 移除不需要导出的字段
                    book_info_filtered = self._filter_book_fields(book_info)
                    books_data.append(book_info_filtered)
                else:
                    logger.warning(f"未找到ID为{book_id}的书籍")
            except Exception as e:
                logger.error(f"查询书籍ID {book_id} 时发生错误: {e}")
                continue
        
        logger.info(f"成功查询到{len(books_data)}本书籍的完整信息")
        return books_data
    
    def _filter_book_fields(self, book_info: Dict) -> Dict:
        """
        过滤书籍字段，只保留需要导出的字段
        
        Args:
            book_info: 原始书籍信息
            
        Returns:
            过滤后的书籍信息
        """
        # 定义需要排除的字段（不导出的字段）
        exclude_fields = [
            'data_version', 'created_at', 'updated_at', 'embedding_id',
            'embedding_status', 'embedding_date', 'embedding_error', 'retry_count'
        ]
        
        filtered_info = {}
        for field, value in book_info.items():
            if field not in exclude_fields:
                filtered_info[field] = value
        
        # # 添加固定字段：候选状态
        # filtered_info['candidate_status'] = '候选'
        
        return filtered_info
    
    def _export_to_excel(self, books_data: List[Dict], output_path: str) -> str:
        """
        将书籍数据导出为Excel文件
        
        Args:
            books_data: 书籍数据列表
            output_path: 输出文件路径
            
        Returns:
            实际保存的文件路径
        """
        # 创建DataFrame
        df = pd.DataFrame(books_data)
        
        # 重命名列，使其更友好
        column_mapping = {
            'id': 'ID',
            'barcode': '书目条码',
            'call_no': '索书号',
            'cleaned_call_no': '清理后索书号',
            'book_title': '书名',
            'additional_info': '附加信息',
            'isbn': 'ISBN',
            'douban_url': '豆瓣链接',
            'douban_rating': '豆瓣评分',
            'douban_title': '豆瓣书名',
            'douban_subtitle': '豆瓣副标题',
            'douban_original_title': '豆瓣原书名',
            'douban_author': '豆瓣作者',
            'douban_translator': '豆瓣译者',
            'douban_publisher': '豆瓣出版社',
            'douban_producer': '豆瓣出品方',
            'douban_series': '豆瓣丛书',
            'douban_series_link': '豆瓣丛书链接',
            'douban_price': '豆瓣定价',
            'douban_isbn': '豆瓣ISBN',
            'douban_pages': '豆瓣页数',
            'douban_binding': '豆瓣装帧',
            'douban_pub_year': '豆瓣出版年份',
            'douban_rating_count': '豆瓣评价人数',
            'douban_summary': '豆瓣内容简介',
            'douban_author_intro': '豆瓣作者简介',
            'douban_catalog': '豆瓣目录',
            'douban_cover_image': '豆瓣封面图片链接',
        #    'candidate_status': '候选状态'
        }
        
        # 重命名存在的列
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        # 处理输出路径
        output_file = Path(output_path)
        if not output_file.suffix:
            # 如果没有扩展名，添加.xlsx
            output_file = output_file.with_suffix('.xlsx')
        
        # 如果是相对路径，则相对于配置的默认目录
        if not output_file.is_absolute():
            default_dir = Path(self.excel_config.get('default_directory', 'runtime/outputs/excel'))
            output_file = default_dir / output_file
        
        # 确保目录存在
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 导出到Excel
        try:
            with pd.ExcelWriter(str(output_file), engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='书籍信息', index=False)
                
                # 获取工作表对象，设置列宽
                worksheet = writer.sheets['书籍信息']
                self._adjust_column_width(worksheet, df)
            
            logger.info(f"Excel文件已保存到: {output_file}")
            return str(output_file)
            
        except Exception as e:
            logger.error(f"保存Excel文件时发生错误: {e}")
            raise IOError(f"保存Excel文件时发生错误: {e}")
    
    def _adjust_column_width(self, worksheet, df):
        """
        调整Excel列宽以适应内容
        
        Args:
            worksheet: Excel工作表对象
            df: DataFrame对象
        """
        from openpyxl.utils import get_column_letter
        
        # 设置最小和最大列宽
        MIN_WIDTH = 10
        MAX_WIDTH = 50
        
        for col_num, column in enumerate(df.columns, 1):
            # 计算列的最大长度
            max_length = max(
                len(str(column)),  # 列名长度
                df[column].astype(str).map(len).max()  # 列中最大值长度
            )
            
            # 限制在最小和最大宽度之间
            adjusted_width = min(max(MIN_WIDTH, max_length), MAX_WIDTH)
            
            # 设置列宽
            column_letter = get_column_letter(col_num)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    def close(self):
        """关闭数据库连接"""
        self.db_reader.close()