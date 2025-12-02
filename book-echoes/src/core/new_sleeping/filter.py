"""
零借阅筛选器

负责筛选出在指定时间段内零借阅的新书。
"""

import pandas as pd
from typing import Tuple, Dict, Any
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ZeroBorrowingFilter:
    """零借阅筛选器类"""
    
    def __init__(self):
        """初始化零借阅筛选器"""
        self.barcode_column = '书目条码'
    
    def filter_zero_borrowing_books(
        self, 
        new_books_df: pd.DataFrame, 
        borrowing_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """
        筛选零借阅图书
        
        逻辑：筛选出在新书数据中存在，但在借阅数据中不存在的图书
        匹配字段：书目条码
        
        Args:
            new_books_df: 新书验收数据
            borrowing_df: 借阅数据（近四月）
            
        Returns:
            Tuple[pd.DataFrame, pd.DataFrame, Dict]: 
                (零借阅图书, 有借阅图书, 统计信息)
        """
        logger.info("开始零借阅筛选")
        
        # 验证必需列
        if self.barcode_column not in new_books_df.columns:
            raise ValueError(f"新书数据缺少必需列: {self.barcode_column}")
        
        if self.barcode_column not in borrowing_df.columns:
            raise ValueError(f"借阅数据缺少必需列: {self.barcode_column}")
        
        # 记录原始数据量
        original_count = len(new_books_df)
        logger.info(f"新书数据量: {original_count}")
        logger.info(f"借阅数据量: {len(borrowing_df)}")
        
        # 统一条码类型，防止数字/字符串混用导致匹配异常
        normalized_new_barcodes = self._normalize_barcode_series(new_books_df[self.barcode_column])
        normalized_borrow_barcodes = self._normalize_barcode_series(borrowing_df[self.barcode_column])
        
        # 获取借阅数据中的书目条码集合
        borrowed_barcodes = set(normalized_borrow_barcodes.dropna().tolist())
        logger.info(f"借阅数据中唯一书目条码数量: {len(borrowed_barcodes)}")
        
        # 筛选零借阅图书：在新书中但不在借阅数据中
        zero_borrowing_mask = ~normalized_new_barcodes.isin(borrowed_barcodes)
        
        # 同时排除书目条码为空的记录
        valid_barcode_mask = normalized_new_barcodes.notna()
        zero_borrowing_mask = zero_borrowing_mask & valid_barcode_mask
        
        zero_borrowing_books = new_books_df[zero_borrowing_mask].copy()
        borrowed_books = new_books_df[~zero_borrowing_mask & valid_barcode_mask].copy()
        
        # 统计信息
        zero_count = len(zero_borrowing_books)
        borrowed_count = len(borrowed_books)
        invalid_barcode_count = (~valid_barcode_mask).sum()
        
        stats = {
            '原始新书数量': original_count,
            '零借阅图书数量': zero_count,
            '有借阅图书数量': borrowed_count,
            '无效条码数量': invalid_barcode_count,
            '零借阅比例': f"{zero_count / original_count * 100:.2f}%" if original_count > 0 else "0%"
        }
        
        logger.info(f"零借阅筛选完成:")
        logger.info(f"  原始新书数量: {original_count}")
        logger.info(f"  零借阅图书数量: {zero_count}")
        logger.info(f"  有借阅图书数量: {borrowed_count}")
        logger.info(f"  无效条码数量: {invalid_barcode_count}")
        logger.info(f"  零借阅比例: {stats['零借阅比例']}")
        
        return zero_borrowing_books, borrowed_books, stats
    
    def _normalize_barcode_series(self, barcode_series: pd.Series) -> pd.Series:
        """
        标准化书目条码列
        
        Args:
            barcode_series: 含有书目条码的数据列
            
        Returns:
            pd.Series: 去除空白并统一为字符串类型的条码列
        """
        normalized = barcode_series.astype('string')
        normalized = normalized.str.strip()
        normalized = normalized.replace(
            {
                'nan': pd.NA,
                'NaN': pd.NA,
                'None': pd.NA,
                'NaT': pd.NA,
                '': pd.NA
            }
        )
        return normalized
    
    def get_statistics(self, zero_borrowing_df: pd.DataFrame) -> Dict[str, Any]:
        """
        获取零借阅图书的统计信息
        
        Args:
            zero_borrowing_df: 零借阅图书数据
            
        Returns:
            Dict: 统计信息
        """
        stats = {
            '总数量': len(zero_borrowing_df),
            '列数': len(zero_borrowing_df.columns),
            '列名': list(zero_borrowing_df.columns)
        }
        
        # 如果有索书号列，添加分类统计
        if '索书号' in zero_borrowing_df.columns:
            # 提取分类号（索书号的第一个字母）
            zero_borrowing_df_copy = zero_borrowing_df.copy()
            zero_borrowing_df_copy['分类号'] = zero_borrowing_df_copy['索书号'].astype(str).str[0]
            category_counts = zero_borrowing_df_copy['分类号'].value_counts()
            stats['分类统计'] = category_counts.to_dict()
        
        # 如果有题名列，统计题名信息
        if '题名' in zero_borrowing_df.columns:
            null_title_count = zero_borrowing_df['题名'].isnull().sum()
            stats['空题名数量'] = null_title_count
        
        # 如果有ISBN列，统计ISBN信息
        if 'isbn' in zero_borrowing_df.columns:
            null_isbn_count = zero_borrowing_df['isbn'].isnull().sum()
            stats['空ISBN数量'] = null_isbn_count
        
        return stats
