"""
Excel文件读取器
负责读取Excel文件并提取数据
"""
import pandas as pd
from typing import Iterator, Dict, Any, List, Tuple
import logging
from pathlib import Path


class ExcelReader:
    """Excel文件读取器"""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.logger = logging.getLogger(self.__class__.__name__)

        if not self.file_path.exists():
            raise FileNotFoundError(f"Excel文件不存在: {file_path}")

        if not self.file_path.suffix.lower() in ['.xlsx', '.xls']:
            raise ValueError(f"不支持的文件格式: {file_path}")

    def read_excel(self, sheet_name: str = 0) -> pd.DataFrame:
        """
        读取Excel文件
        Args:
            sheet_name: 工作表名称或索引，默认为第一个工作表
        Returns:
            DataFrame对象
        """
        try:
            df = pd.read_excel(self.file_path, sheet_name=sheet_name, engine='openpyxl')
            self.logger.info(f"成功读取Excel文件: {self.file_path}, 行数: {len(df)}")
            return df
        except Exception as e:
            self.logger.error(f"读取Excel文件失败: {str(e)}")
            raise

    def get_rows(self, sheet_name: str = 0) -> Iterator[Dict[str, Any]]:
        """
        逐行读取Excel数据
        Args:
            sheet_name: 工作表名称或索引
        Yields:
            每行数据的字典
        """
        df = self.read_excel(sheet_name)

        for index, row in df.iterrows():
            yield row.to_dict()

    def get_rows_with_keywords(self, isbn_col: str = 'ISBN', title_col: str = '题名',
                              sheet_name: str = 0) -> Iterator[Tuple[int, Dict[str, Any]]]:
        """
        获取包含ISBN和题名的行
        Args:
            isbn_col: ISBN列名
            title_col: 题名列名
            sheet_name: 工作表名称或索引
        Yields:
            (行号, 数据字典)
        """
        df = self.read_excel(sheet_name)

        # 检查列是否存在
        missing_cols = []
        if isbn_col not in df.columns:
            missing_cols.append(isbn_col)
        if title_col not in df.columns:
            missing_cols.append(title_col)

        if missing_cols:
            raise ValueError(f"Excel文件中缺少必要的列: {', '.join(missing_cols)}")

        for index, row in df.iterrows():
            row_data = row.to_dict()
            yield index, row_data

    def get_columns(self, sheet_name: str = 0) -> List[str]:
        """
        获取Excel文件的列名
        Args:
            sheet_name: 工作表名称或索引
        Returns:
            列名列表
        """
        df = self.read_excel(sheet_name)
        return df.columns.tolist()

    def get_file_info(self) -> Dict[str, Any]:
        """
        获取文件信息
        Returns:
            文件信息字典
        """
        try:
            df = self.read_excel()
            return {
                'file_path': str(self.file_path),
                'file_size': self.file_path.stat().st_size,
                'row_count': len(df),
                'column_count': len(df.columns),
                'columns': df.columns.tolist()
            }
        except Exception as e:
            self.logger.error(f"获取文件信息失败: {str(e)}")
            return {
                'file_path': str(self.file_path),
                'error': str(e)
            }