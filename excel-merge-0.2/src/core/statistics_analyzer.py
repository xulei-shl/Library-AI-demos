"""
统计分析核心模块
负责数据筛选、聚合和统计报表生成
"""
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
import re

from ..utils.logger import logger
from ..utils.excel_utils import ExcelUtils
from ..config.settings import (
    TARGET_FILE_PATH, EXCEL_SHEET_NAME, STATISTICS_CONFIG
)


class StatisticsAnalyzer:
    """统计分析器"""
    
    def __init__(self):
        self.config = STATISTICS_CONFIG
        self.target_file_path = Path(TARGET_FILE_PATH)
        self.output_file_path = Path(self.config['output_file_path'])
        logger.debug("StatisticsAnalyzer: 初始化统计分析器")
    
    def run_analysis(self) -> bool:
        """
        执行完整的统计分析流程
        
        Returns:
            是否执行成功
        """
        try:
            logger.info("=" * 60)
            logger.info("开始执行统计分析")
            logger.info("=" * 60)
            
            # 1. 检查配置
            if not self.config['enabled']:
                logger.info("统计分析功能已禁用")
                return True
            
            # 2. 读取目标文件数据
            df = self._read_target_data()
            if df is None or df.empty:
                logger.error("无法读取目标文件数据或数据为空")
                return False
            
            # 3. 筛选上月数据
            filtered_df = self._filter_by_previous_month(df)
            if filtered_df is None or filtered_df.empty:
                logger.warning("筛选后无数据，可能目标文件中没有上月的业务数据")
                return True
            
            # 4. 按馆藏编号聚合
            aggregated_df = self._aggregate_by_group(filtered_df)
            if aggregated_df is None or aggregated_df.empty:
                logger.error("数据聚合失败")
                return False
            
            # 5. 导出到统计文件
            success = self._export_to_statistics_file(aggregated_df)
            if success:
                logger.info("统计分析完成")
                logger.info(f"处理了 {len(filtered_df)} 条原始数据")
                logger.info(f"生成了 {len(aggregated_df)} 条聚合结果")
                logger.info(f"结果已保存到: {self.output_file_path}")
            else:
                logger.error("统计结果导出失败")
            
            logger.info("=" * 60)
            return success
            
        except Exception as e:
            logger.exception(f"统计分析执行失败: {str(e)}")
            return False
    
    def _read_target_data(self) -> Optional[pd.DataFrame]:
        """
        读取目标文件数据
        
        Returns:
            目标文件的DataFrame或None
        """
        try:
            logger.info(f"读取目标文件: {self.target_file_path}")
            
            if not self.target_file_path.exists():
                logger.error(f"目标文件不存在: {self.target_file_path}")
                return None
            
            df = ExcelUtils.read_excel_file(
                self.target_file_path, 
                sheet_name=EXCEL_SHEET_NAME,
                filename=self.target_file_path.name
            )
            
            if df is not None:
                logger.info(f"成功读取目标文件，数据行数: {len(df)}")
            
            return df
            
        except Exception as e:
            logger.exception(f"读取目标文件失败: {str(e)}")
            return None
    
    def _filter_by_previous_month(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        筛选上个月的业务数据
        
        Args:
            df: 原始数据DataFrame
            
        Returns:
            筛选后的DataFrame或None
        """
        try:
            # 使用回退机制查找业务时间列（优先列名，兜底字母索引）
            business_time_col = ExcelUtils.find_column_by_name_or_letter(
                df, 
                self.config['business_time_column'],
                self.config.get('business_time_column_letter')
            )
            
            if not business_time_col:
                logger.error(f"未找到业务时间列: {self.config['business_time_column']}")
                return None
            
            # 计算上个月的时间标识
            prev_month_text = self._get_previous_month_text()
            logger.info(f"筛选业务时间为: {prev_month_text}")
            
            # 筛选数据
            filtered_df = df[df[business_time_col] == prev_month_text].copy()
            
            logger.info(f"筛选结果: {len(filtered_df)} 条数据匹配上月时间")
            
            return filtered_df
            
        except Exception as e:
            logger.exception(f"按时间筛选数据失败: {str(e)}")
            return None
    
    def _get_previous_month_text(self) -> str:
        """
        获取上个月的文本表示（YYYY年M月格式）
        
        Returns:
            上个月的文本表示
        """
        try:
            now = datetime.now()
            
            # 计算上个月，处理跨年情况
            if now.month == 1:
                # 如果是1月，上个月是去年12月
                prev_month = 12
                prev_year = now.year - 1
            else:
                # 其他月份，直接减1
                prev_month = now.month - 1
                prev_year = now.year
            
            # 格式化为 "YYYY年M月" 文本格式
            prev_month_text = f"{prev_year}年{prev_month}月"
            
            logger.debug(f"计算得到上月时间: {prev_month_text}")
            return prev_month_text
            
        except Exception as e:
            logger.exception(f"计算上月时间失败: {str(e)}")
            # 返回默认值
            return "2025年8月"
    
    def _aggregate_by_group(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        按馆藏编号分组聚合数据
        
        Args:
            df: 筛选后的数据DataFrame
            
        Returns:
            聚合后的DataFrame或None
        """
        try:
            # 使用回退机制查找分组列（优先列名，兜底字母索引）
            group_col = ExcelUtils.find_column_by_name_or_letter(
                df,
                self.config['group_by_column'],
                self.config.get('group_by_column_letter')
            )
            
            # 直接使用字母索引查找目标列（不使用列名）
            target_col = None
            if self.config.get('target_column_letter'):
                # 直接通过字母索引查找列
                column_index = ExcelUtils._letter_to_index(self.config['target_column_letter'])
                if 0 <= column_index < len(df.columns):
                    target_col = df.columns[column_index]
                    logger.info(f"使用字母索引 '{self.config['target_column_letter']}' (索引{column_index}) 找到列: {target_col}")
                else:
                    logger.error(f"字母列号 '{self.config['target_column_letter']}' 对应的索引 {column_index} 超出范围（共 {len(df.columns)} 列）")
            
            # 检查必要的列是否存在
            if not group_col:
                logger.error(f"未找到分组列: {self.config['group_by_column']}")
                return None
            
            if not target_col:
                logger.error(f"未找到目标聚合列: {self.config['target_column']}")
                return None
            
            logger.info(f"按 '{group_col}' 分组，对 '{target_col}' 求和")
            
            # 清理数据：移除空值和非数值数据
            df_clean = df.dropna(subset=[group_col, target_col]).copy()
            
            # 确保目标列为数值类型
            df_clean[target_col] = pd.to_numeric(df_clean[target_col], errors='coerce')
            df_clean = df_clean.dropna(subset=[target_col])
            
            if df_clean.empty:
                logger.warning("清理后无有效数据可聚合")
                return None
            
            # 按分组列聚合
            aggregated = df_clean.groupby(group_col)[target_col].sum().reset_index()
            
            # 重命名列以便输出（使用配置中的标准列名）
            standard_target_col = self.config['target_column']
            aggregated.columns = [group_col, f'{standard_target_col}_sum']
            
            logger.info(f"聚合完成，生成 {len(aggregated)} 个分组结果")
            logger.debug(f"聚合结果预览:\n{aggregated.head()}")
            
            return aggregated
            
        except Exception as e:
            logger.exception(f"数据聚合失败: {str(e)}")
            return None
    
    def _export_to_statistics_file(self, aggregated_df: pd.DataFrame) -> bool:
        """
        导出聚合结果到统计文件
        
        Args:
            aggregated_df: 聚合后的数据
            
        Returns:
            是否导出成功
        """
        try:
            logger.info(f"开始导出统计结果到: {self.output_file_path}")
            
            # 准备输出数据
            output_data = self._prepare_output_data(aggregated_df)
            if output_data is None:
                return False
            
            # 确保输出目录存在
            self.output_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 检查目标文件是否存在
            if not self.output_file_path.exists():
                logger.info("目标统计文件不存在，将创建新文件")
                success = self._create_statistics_file(output_data)
            else:
                logger.info("目标统计文件已存在，将追加数据")
                success = self._append_to_statistics_file(output_data)
            
            return success
            
        except Exception as e:
            logger.exception(f"导出统计结果失败: {str(e)}")
            return False
    
    def _prepare_output_data(self, aggregated_df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        准备输出数据格式
        
        Args:
            aggregated_df: 聚合数据
            
        Returns:
            格式化后的输出数据
        """
        try:
            group_col = self.config['group_by_column']
            target_col = f"{self.config['target_column']}_sum"
            
            # 创建输出DataFrame
            output_df = pd.DataFrame()
            
            # A列：馆藏编号
            output_df['馆藏编号'] = aggregated_df[group_col]
            
            # B列：数量求和
            output_df['数量'] = aggregated_df[target_col]
            
            # C列：时间标识（YYYYMM格式）
            prev_month_code = self._get_previous_month_code()
            output_df['时间'] = prev_month_code
            
            logger.debug(f"输出数据格式化完成，共 {len(output_df)} 行")
            return output_df
            
        except Exception as e:
            logger.exception(f"准备输出数据失败: {str(e)}")
            return None
    
    def _get_previous_month_code(self) -> str:
        """
        获取上个月的代码格式（YYYYMM）
        
        Returns:
            上个月的代码（如202508）
        """
        try:
            now = datetime.now()
            
            # 计算上个月
            if now.month == 1:
                prev_month = 12
                prev_year = now.year - 1
            else:
                prev_month = now.month - 1
                prev_year = now.year
            
            # 格式化为 YYYYMM
            prev_month_code = f"{prev_year}{prev_month:02d}"
            
            logger.debug(f"上月代码: {prev_month_code}")
            return prev_month_code
            
        except Exception as e:
            logger.exception(f"生成上月代码失败: {str(e)}")
            return "202508"  # 默认值
    
    def _create_statistics_file(self, output_data: pd.DataFrame) -> bool:
        """
        创建新的统计文件
        
        Args:
            output_data: 输出数据
            
        Returns:
            是否创建成功
        """
        try:
            logger.info("创建新的统计文件")
            
            success = ExcelUtils.write_excel_file(
                output_data,
                self.output_file_path,
                self.config['output_sheet_name']
            )
            
            if success:
                logger.info(f"统计文件创建成功: {self.output_file_path}")
            
            return success
            
        except Exception as e:
            logger.exception(f"创建统计文件失败: {str(e)}")
            return False
    
    def _append_to_statistics_file(self, output_data: pd.DataFrame) -> bool:
        """
        追加数据到现有统计文件
        
        Args:
            output_data: 输出数据
            
        Returns:
            是否追加成功
        """
        try:
            logger.info("追加数据到现有统计文件")
            
            success = ExcelUtils.append_to_excel_file(
                output_data,
                self.output_file_path,
                self.config['output_sheet_name']
            )
            
            if success:
                logger.info(f"数据追加成功，新增 {len(output_data)} 行")
            
            return success
            
        except Exception as e:
            logger.exception(f"追加数据到统计文件失败: {str(e)}")
            return False