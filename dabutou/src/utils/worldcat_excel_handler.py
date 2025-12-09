"""
WorldCat专用Excel处理模块
处理WorldCat爬取结果的Excel读写，避免与CiNii结果冲突
"""
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging
from datetime import datetime

from src.scrapers.worldcat_scraper import WorldCatResult


class WorldCatExcelHandler:
    """WorldCat专用Excel处理器"""

    def __init__(self, original_excel_path: str, output_suffix: str = "_worldcat_results"):
        """
        初始化Excel处理器
        Args:
            original_excel_path: 原始Excel文件路径
            output_suffix: 输出文件后缀
        """
        self.original_path = Path(original_excel_path)
        self.output_suffix = output_suffix
        self.logger = logging.getLogger(self.__class__.__name__)

        # 生成输出文件路径
        self.output_path = self._generate_output_path()

        # 读取原始Excel数据
        self.original_data = self._read_original_data()

    def _generate_output_path(self) -> Path:
        """生成输出文件路径"""
        base_name = self.original_path.stem
        extension = self.original_path.suffix

        # 添加时间戳和后缀
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"{base_name}{self.output_suffix}_{timestamp}{extension}"

        return self.original_path.parent / output_name

    def _read_original_data(self) -> Optional[pd.DataFrame]:
        """读取原始Excel数据"""
        try:
            if self.original_path.exists():
                df = pd.read_excel(self.original_path, engine='openpyxl')
                self.logger.info(f"成功读取原始Excel文件: {self.original_path}, 行数: {len(df)}")
                return df
            else:
                self.logger.warning(f"原始Excel文件不存在: {self.original_path}")
                return None
        except Exception as e:
            self.logger.error(f"读取原始Excel文件失败: {str(e)}")
            return None

    def create_results_dataframe(self, results: List[WorldCatResult],
                               isbn_col: str = 'ISBN',
                               title_col: str = '题名') -> pd.DataFrame:
        """
        创建结果DataFrame
        Args:
            results: WorldCat爬取结果列表
            isbn_col: ISBN列名
            title_col: 题名列名
        Returns:
            结果DataFrame
        """
        # 准备结果数据
        result_data = []

        for result in results:
            # 为每个图书馆创建一行数据
            if result.libraries:
                for library in result.libraries:
                    result_data.append({
                        '检索词': result.search_term,
                        '海外图书馆': library,
                        '检索成功': result.success,
                        '图书馆数量': result.libraries_count,
                        '错误信息': result.error_message if not result.success else '',
                        '检索时间': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
            else:
                # 即使没有找到图书馆也要记录
                result_data.append({
                    '检索词': result.search_term,
                    '海外图书馆': '',
                    '检索成功': result.success,
                    '图书馆数量': 0,
                    '错误信息': result.error_message if not result.success else '未找到海外图书馆',
                    '检索时间': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

        return pd.DataFrame(result_data)

    def create_summary_dataframe(self, results: List[WorldCatResult]) -> pd.DataFrame:
        """
        创建汇总统计DataFrame
        Args:
            results: WorldCat爬取结果列表
        Returns:
            汇总统计DataFrame
        """
        summary_data = []

        total_searches = len(results)
        successful_searches = sum(1 for r in results if r.success)
        total_libraries = sum(r.libraries_count for r in results)

        # 总体统计
        summary_data.append({
            '统计项': '总搜索词数',
            '数量': total_searches,
            '说明': '所有搜索的词总数'
        })

        summary_data.append({
            '统计项': '成功搜索数',
            '数量': successful_searches,
            '说明': '找到至少一个海外图书馆的搜索词数'
        })

        summary_data.append({
            '统计项': '成功率',
            '数量': f"{successful_searches/total_searches*100:.1f}%" if total_searches > 0 else "0%",
            '说明': '成功搜索的百分比'
        })

        summary_data.append({
            '统计项': '总图书馆数',
            '数量': total_libraries,
            '说明': '所有海外图书馆总数（去重后）'
        })

        # 按搜索词统计
        summary_data.append({
            '统计项': '平均每个搜索词的图书馆数',
            '数量': f"{total_libraries/total_searches:.1f}" if total_searches > 0 else "0",
            '说明': '每个成功搜索词平均找到的图书馆数'
        })

        return pd.DataFrame(summary_data)

    def save_results(self, results: List[WorldCatResult],
                    isbn_col: str = 'ISBN',
                    title_col: str = '题名',
                    include_original_data: bool = True) -> str:
        """
        保存结果到Excel文件
        Args:
            results: WorldCat爬取结果列表
            isbn_col: ISBN列名
            title_col: 题名列名
            include_original_data: 是否包含原始数据
        Returns:
            输出文件路径
        """
        try:
            with pd.ExcelWriter(self.output_path, engine='openpyxl') as writer:
                # 如果需要包含原始数据且原始数据存在
                if include_original_data and self.original_data is not None:
                    # 写入原始数据
                    self.original_data.to_excel(
                        writer,
                        sheet_name='原始数据',
                        index=False
                    )
                    self.logger.info(f"已写入原始数据到工作表: 原始数据")

                # 写入WorldCat结果
                results_df = self.create_results_dataframe(results, isbn_col, title_col)
                results_df.to_excel(
                    writer,
                    sheet_name='WorldCat结果',
                    index=False
                )
                self.logger.info(f"已写入WorldCat结果到工作表: WorldCat结果, 行数: {len(results_df)}")

                # 写入汇总统计
                summary_df = self.create_summary_dataframe(results)
                summary_df.to_excel(
                    writer,
                    sheet_name='统计汇总',
                    index=False
                )
                self.logger.info(f"已写入统计汇总到工作表: 统计汇总")

            self.logger.info(f"WorldCat结果已保存到: {self.output_path}")
            return str(self.output_path)

        except Exception as e:
            self.logger.error(f"保存WorldCat结果失败: {str(e)}")
            raise

    def update_original_excel_with_row_results(self, row_results: List[Dict[str, Any]],
                                             worldcat_col_prefix: str = 'WorldCat海外图书馆') -> str:
        """
        在原始Excel文件中添加WorldCat结果列（基于行处理结果）
        每个海外图书馆占据单独的列（横向排列）
        Args:
            row_results: 行处理结果列表，每个结果包含row_index和libraries等信息
            worldcat_col_prefix: WorldCat结果列名前缀
        Returns:
            新文件路径
        """
        try:
            if self.original_data is None:
                raise ValueError("原始Excel数据不存在，无法更新")

            # 创建原始数据的副本
            updated_data = self.original_data.copy()

            # 首先找到最大的海外图书馆数量，用于确定列数
            max_libraries = max((len(result.get('libraries', [])) for result in row_results), default=0)

            # 为每个图书馆创建一列
            if max_libraries > 0:
                for i in range(1, max_libraries + 1):
                    col_name = f"{worldcat_col_prefix}{i}"
                    updated_data[col_name] = ""

                # 创建行索引到结果的映射
                row_result_map = {}
                for result in row_results:
                    row_index = result.get('row_index')
                    if row_index is not None:
                        row_result_map[row_index] = result

                # 更新每一行的WorldCat结果
                for index in updated_data.index:
                    if index in row_result_map:
                        result = row_result_map[index]
                        libraries = result.get('libraries', [])
                        if libraries:
                            # 每个图书馆占据一列
                            for i, library in enumerate(libraries):
                                if i < max_libraries:  # 确保不超过最大列数
                                    col_name = f"{worldcat_col_prefix}{i + 1}"
                                    updated_data.at[index, col_name] = library
                        else:
                            # 如果没有图书馆，第一列标记为"未找到海外图书馆"
                            col_name = f"{worldcat_col_prefix}1"
                            updated_data.at[index, col_name] = "未找到海外图书馆"
                    else:
                        # 如果没有搜索结果，第一列标记为"未搜索"
                        col_name = f"{worldcat_col_prefix}1"
                        updated_data.at[index, col_name] = "未搜索"
            else:
                # 如果没有任何图书馆，只创建一个统计列
                col_name = f"{worldcat_col_prefix}"
                updated_data[col_name] = "未找到海外图书馆"

            # 生成新的文件名
            updated_output_path = self.original_path.parent / f"{self.original_path.stem}_with_worldcat_results{self.original_path.suffix}"

            # 保存更新后的文件
            updated_data.to_excel(updated_output_path, index=False, engine='openpyxl')

            self.logger.info(f"已更新原始Excel文件并保存到: {updated_output_path}")
            self.logger.info(f"Excel格式 - 总列数: {len(updated_data.columns)}, WorldCat列数: {max_libraries if max_libraries > 0 else 1}")
            return str(updated_output_path)

        except Exception as e:
            self.logger.error(f"更新原始Excel文件失败: {str(e)}")
            raise

    def get_excel_data_iterator(self, isbn_col: str = 'ISBN',
                               title_col: str = '题名',
                               sheet_name: str = 0):
        """
        获取Excel数据的迭代器
        Args:
            isbn_col: ISBN列名
            title_col: 题名列名
            sheet_name: 工作表名称或索引
        Yields:
            (row_index, row_data) 元组
        """
        try:
            if self.original_data is None:
                self.logger.warning("原始Excel数据不存在")
                return

            for index, row in self.original_data.iterrows():
                yield index, row

        except Exception as e:
            self.logger.error(f"读取Excel数据失败: {str(e)}")