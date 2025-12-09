"""
Excel文件写入器
负责将爬取结果写入Excel文件
"""
import pandas as pd
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path
import copy


class ExcelWriter:
    """Excel文件写入器"""

    # 定义列的数据类型映射
    COLUMN_DTYPES = {
        'keyword_type': str,
        'keyword_value': str,
        'success': bool,
        'error_message': str,
        'libraries_count': int,
        'ISBN': str,
        '题名': str
    }

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._backup_file()

    def _backup_file(self):
        """备份原文件"""
        if self.file_path.exists():
            backup_path = self.file_path.with_suffix(
                f'.backup_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}{self.file_path.suffix}'
            )
            try:
                import shutil
                shutil.copy2(self.file_path, backup_path)
                self.logger.info(f"已备份原文件到: {backup_path}")
            except Exception as e:
                self.logger.warning(f"备份文件失败: {str(e)}")

    def _ensure_columns_exist(self, df: pd.DataFrame, columns: List[str]) -> None:
        """
        确保指定的列存在于DataFrame中，如果不存在则创建
        Args:
            df: 目标DataFrame
            columns: 需要确保存在的列名列表
        """
        for col_name in columns:
            if col_name not in df.columns:
                # 根据预定义的数据类型设置默认值
                dtype = self.COLUMN_DTYPES.get(col_name, str)
                if dtype == bool:
                    df[col_name] = False
                elif dtype == int:
                    df[col_name] = 0
                else:
                    df[col_name] = ''

    def _safe_set_value(self, df: pd.DataFrame, row_index: int, column: str, value: Any) -> None:
        """
        安全地设置DataFrame中的值，确保数据类型匹配
        Args:
            df: 目标DataFrame
            row_index: 行索引
            column: 列名
            value: 要设置的值
        """
        try:
            # 确保列存在
            self._ensure_columns_exist(df, [column])

            # 根据预定义的数据类型进行转换
            dtype = self.COLUMN_DTYPES.get(column, str)
            if dtype == bool:
                converted_value = bool(value)
            elif dtype == int:
                converted_value = int(value) if str(value).isdigit() else 0
            else:
                converted_value = str(value)

            # 确保列的数据类型与值兼容，避免FutureWarning
            if dtype == str:
                df[column] = df[column].astype(str)
            elif dtype == int:
                df[column] = df[column].astype(int)
            elif dtype == bool:
                df[column] = df[column].astype(bool)

            # 设置值
            df.loc[row_index, column] = converted_value

        except Exception as e:
            self.logger.warning(f"设置值失败 (行:{row_index}, 列:{column}, 值:{value}): {str(e)}")
            # 回退到字符串类型
            try:
                df[column] = df[column].astype(str)
                df.loc[row_index, column] = str(value)
            except:
                pass

    def read_original_data(self, sheet_name: str = 0) -> pd.DataFrame:
        """
        读取原始数据
        Args:
            sheet_name: 工作表名称或索引
        Returns:
            原始数据的DataFrame
        """
        try:
            return pd.read_excel(self.file_path, sheet_name=sheet_name, engine='openpyxl')
        except FileNotFoundError:
            # 如果文件不存在，返回空的DataFrame
            return pd.DataFrame()

    def write_results(self, results: List[Dict[str, Any]],
                     output_path: Optional[str] = None,
                     sheet_name: str = 0,
                     library_columns_prefix: str = '图书馆_') -> str:
        """
        将爬取结果写入Excel文件
        Args:
            results: 爬取结果列表
            output_path: 输出文件路径，如果为None则使用原文件路径
            sheet_name: 工作表名称或索引
            library_columns_prefix: 图书馆列的前缀
        Returns:
            输出文件的路径
        """
        output_file = output_path or str(self.file_path)

        try:
            # 读取原始数据
            original_df = self.read_original_data(sheet_name)

            if original_df.empty:
                self.logger.warning("原始文件为空，创建新文件")
                # 创建新的DataFrame
                all_rows = []
                for result in results:
                    row_data = {
                        'ISBN': result.get('original_isbn', ''),
                        '题名': result.get('original_title', ''),
                        'keyword_type': result.get('keyword_type', ''),
                        'keyword_value': result.get('keyword_value', ''),
                        'success': result.get('success', False),
                        'error_message': result.get('error_message', ''),
                        'libraries_count': result.get('libraries_count', 0)
                    }

                    # 添加图书馆列
                    libraries = result.get('libraries', [])
                    for i, library in enumerate(libraries, 1):
                        row_data[f'{library_columns_prefix}{i}'] = library

                    all_rows.append(row_data)

                df = pd.DataFrame(all_rows)
            else:
                # 复制原始DataFrame
                df = copy.deepcopy(original_df)

                # 为每行添加结果
                for result in results:
                    row_index = result.get('row_index')
                    if row_index is not None and row_index < len(df):
                        # 使用安全的方法添加基本结果信息
                        self._safe_set_value(df, row_index, 'keyword_type', result.get('keyword_type', ''))
                        self._safe_set_value(df, row_index, 'keyword_value', result.get('keyword_value', ''))
                        self._safe_set_value(df, row_index, 'success', result.get('success', False))
                        self._safe_set_value(df, row_index, 'error_message', result.get('error_message', ''))
                        self._safe_set_value(df, row_index, 'libraries_count', result.get('libraries_count', 0))

                        # 添加图书馆信息
                        libraries = result.get('libraries', [])
                        for i, library in enumerate(libraries, 1):
                            col_name = f'{library_columns_prefix}{i}'
                            if col_name not in df.columns:
                                df[col_name] = ''
                            df.loc[row_index, col_name] = library

            # 写入Excel文件
            df.to_excel(output_file, index=False, engine='openpyxl')
            self.logger.info(f"成功写入结果到: {output_file}")
            return output_file

        except Exception as e:
            self.logger.error(f"写入Excel文件失败: {str(e)}")
            raise

    def write_single_row_result(self, row_index: int, result: Dict[str, Any],
                              sheet_name: str = 0,
                              library_columns_prefix: str = '图书馆_'):
        """
        写入单行结果（实时保存）
        Args:
            row_index: 行索引
            result: 单行结果
            sheet_name: 工作表名称或索引
            library_columns_prefix: 图书馆列的前缀
        """
        try:
            # 读取当前数据
            df = self.read_original_data(sheet_name)

            if row_index >= len(df):
                self.logger.warning(f"行索引 {row_index} 超出范围 (DataFrame 长度: {len(df)})")
                return

            if row_index < 0:
                self.logger.warning(f"行索引 {row_index} 不能为负数")
                return

            # 使用安全的方法更新数据
            self._safe_set_value(df, row_index, 'keyword_type', result.get('keyword_type', ''))
            self._safe_set_value(df, row_index, 'keyword_value', result.get('keyword_value', ''))
            self._safe_set_value(df, row_index, 'success', result.get('success', False))
            self._safe_set_value(df, row_index, 'error_message', result.get('error_message', ''))
            self._safe_set_value(df, row_index, 'libraries_count', result.get('libraries_count', 0))

            # 添加图书馆信息
            libraries = result.get('libraries', [])
            if libraries:
                self.logger.debug(f"为第 {row_index} 行添加 {len(libraries)} 个图书馆信息")

            for i, library in enumerate(libraries, 1):
                col_name = f'{library_columns_prefix}{i}'
                if col_name not in df.columns:
                    df[col_name] = ''
                df.loc[row_index, col_name] = str(library)

            # 立即保存
            df.to_excel(self.file_path, index=False, engine='openpyxl')
            self.logger.debug(f"已更新并保存第 {row_index} 行结果，成功状态: {result.get('success', False)}")

        except FileNotFoundError:
            self.logger.error(f"Excel文件不存在: {self.file_path}")
            raise
        except PermissionError:
            self.logger.error(f"没有权限写入文件: {self.file_path}，请确保文件未被其他程序打开")
            raise
        except Exception as e:
            self.logger.error(f"写入单行结果失败 (行:{row_index}): {str(e)}")
            self.logger.debug(f"结果数据: {result}")
            raise