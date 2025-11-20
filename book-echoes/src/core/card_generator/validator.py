"""
数据验证器模块
负责验证Excel数据的完整性和有效性
"""

import os
from typing import Dict, List, Tuple
import pandas as pd
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataValidator:
    """数据验证器类"""

    def __init__(self, config: Dict):
        """
        初始化验证器

        Args:
            config: 配置字典
        """
        self.config = config
        self.required_fields = config.get('fields', {}).get('required', [])
        self.filter_config = config.get('fields', {}).get('filter', {})
        self.filter_source = "未执行"

    def validate_excel_file(self, excel_path: str) -> bool:
        """
        验证Excel文件是否存在且可读

        Args:
            excel_path: Excel文件路径

        Returns:
            bool: 文件存在且可读返回True，否则返回False
        """
        if not os.path.exists(excel_path):
            logger.critical(f"错误：Excel文件不存在：{excel_path}")
            return False

        if not os.path.isfile(excel_path):
            logger.critical(f"错误：路径不是文件：{excel_path}")
            return False

        try:
            # 尝试读取文件（只读第一行验证）
            pd.read_excel(excel_path, nrows=1)
            return True
        except Exception as e:
            logger.critical(f"错误：无法读取Excel文件：{excel_path}，错误：{e}")
            return False

    def validate_required_columns(
        self, df: pd.DataFrame, required_columns: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        验证必填列是否存在

        Args:
            df: DataFrame对象
            required_columns: 必填列列表

        Returns:
            Tuple[bool, List[str]]: (验证是否通过, 缺失的列列表)
        """
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            logger.critical(f"错误：Excel缺少必填列：{missing_columns}")
            return False, missing_columns

        return True, []

    def validate_row_data(
        self, row: pd.Series, required_fields: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        验证单行数据的必填字段

        Args:
            row: DataFrame行数据
            required_fields: 必填字段列表

        Returns:
            Tuple[bool, List[str]]: (验证是否通过, 缺失的字段列表)
        """
        missing_fields = []

        for field in required_fields:
            if field not in row.index:
                missing_fields.append(field)
                continue

            value = row[field]
            # 检查是否为空值
            if pd.isna(value) or str(value).strip() == "":
                missing_fields.append(field)

        if missing_fields:
            barcode = row.get('书目条码', 'Unknown')
            logger.warning(
                f"警告：书目条码 {barcode} 缺少必填字段：{missing_fields}，跳过处理"
            )
            return False, missing_fields

        return True, []

    def filter_passed_books(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        强制使用"人工评选"列筛选通过的图书
        
        逻辑：
        1. 强制检查"人工评选"列是否存在
        2. 如果列不存在，记录错误日志并返回空DataFrame
        3. 如果列存在，筛选值为"通过"的记录
        4. 如果筛选结果为空，记录警告日志并返回空DataFrame
        """
        # 强制使用"人工评选"列
        mandatory_column = "人工评选"
        mandatory_value = "通过"
        
        # 检查列是否存在
        if mandatory_column not in df.columns:
            logger.critical(f"错误：Excel文件缺少必需的列 '{mandatory_column}'，无法继续处理")
            logger.critical(f"请确保Excel文件包含 '{mandatory_column}' 列")
            self.filter_source = f"失败（缺少 '{mandatory_column}' 列）"
            return pd.DataFrame()  # 返回空DataFrame
        
        # 筛选"人工评选"为"通过"的记录
        logger.info(f"使用强制筛选列 '{mandatory_column}'，筛选值为 '{mandatory_value}'")
        filtered_df = df[df[mandatory_column].astype(str).str.strip() == mandatory_value].copy()
        
        # 检查筛选结果
        if filtered_df.empty:
            logger.warning(f"警告：'{mandatory_column}' 列中没有发现 '{mandatory_value}' 的记录")
            logger.warning(f"数据总数：{len(df)}，筛选后数量：0")
            logger.warning("程序将正常结束，无需生成卡片")
            self.filter_source = f"'{mandatory_column}' 列（无匹配记录）"
            return pd.DataFrame()  # 返回空DataFrame
        
        logger.info(
            f"筛选 '{mandatory_column}' 为 '{mandatory_value}' 的图书：{len(filtered_df)} / {len(df)}"
        )
        self.filter_source = f"强制规则列 '{mandatory_column}'"
        return filtered_df
    
    # =========================================================================
    # 以下为原智能筛选逻辑，已注释保留，如需恢复可取消注释
    # =========================================================================
    # def filter_passed_books(self, df: pd.DataFrame) -> pd.DataFrame:
    #     """
    #     筛选终评结果为"通过"的图书（智能筛选版本）
    #     
    #     逻辑：
    #     1. 检查配置中是否定义了 priority_rule
    #     2. 如果定义且列存在，尝试筛选 priority_rule 指定的值
    #     3. 如果优先筛选结果不为空，则使用该结果
    #     4. 否则，按照原逻辑筛选（通常是 '终评结果' == '通过'）
    #     """
    #     # 优先检查配置中的优先规则
    #     priority_rule = self.filter_config.get('priority_rule')
    #     if priority_rule:
    #         priority_col = priority_rule.get('column')
    #         priority_val = priority_rule.get('value')
    #         
    #         if priority_col and priority_col in df.columns:
    #             logger.info(f"发现优先筛选列 '{priority_col}'，尝试使用该列进行筛选")
    #             # 确保列值为字符串并去除空格
    #             priority_filtered_df = df[df[priority_col].astype(str).str.strip() == priority_val].copy()
    #             
    #             if not priority_filtered_df.empty:
    #                 logger.info(
    #                     f"筛选 '{priority_col}' 为'{priority_val}'的图书：{len(priority_filtered_df)} / {len(df)}"
    #                 )
    #                 self.filter_source = f"优先规则列 '{priority_col}'"
    #                 return priority_filtered_df
    #             else:
    #                 logger.info(f"'{priority_col}' 列中没有发现'{priority_val}'的记录，将执行原有逻辑作为兜底")
    #
    #     # 原有逻辑
    #     filter_column = self.filter_config.get('column', '终评结果')
    #     filter_value = self.filter_config.get('value', '通过')
    #
    #     if filter_column not in df.columns:
    #         logger.warning(f"警告：过滤列 {filter_column} 不存在，返回所有数据")
    #         self.filter_source = "无过滤（列不存在）"
    #         return df
    #
    #     # 筛选数据
    #     filtered_df = df[df[filter_column] == filter_value].copy()
    #
    #     logger.info(
    #         f"筛选 {filter_column} 为'{filter_value}'的图书：{len(filtered_df)} / {len(df)}"
    #     )
    #     
    #     self.filter_source = f"默认规则列 '{filter_column}'"
    #     return filtered_df

    def generate_validation_report(self, results: Dict) -> str:
        """
        生成验证报告

        Args:
            results: 验证结果字典

        Returns:
            str: 验证报告文本
        """
        report_lines = [
            "=" * 60,
            "数据验证报告",
            "=" * 60,
            "",
            f"Excel文件: {results.get('excel_path', 'N/A')}",
            f"总记录数: {results.get('total_count', 0)}",
            f"通过筛选: {results.get('filtered_count', 0)}",
            "",
        ]

        # 验证结果
        if results.get('success', False):
            report_lines.append("验证状态: ✓ 通过")
        else:
            report_lines.append("验证状态: ✗ 失败")

        # 缺失列信息
        if results.get('missing_columns'):
            report_lines.append("")
            report_lines.append("缺失的必填列:")
            for col in results.get('missing_columns', []):
                report_lines.append(f"  - {col}")

        # 警告信息
        if results.get('warnings'):
            report_lines.append("")
            report_lines.append(f"警告信息 ({len(results.get('warnings', []))}):")
            for warning in results.get('warnings', [])[:10]:  # 只显示前10条
                report_lines.append(f"  - {warning}")
            if len(results.get('warnings', [])) > 10:
                report_lines.append(f"  ... 还有 {len(results.get('warnings', [])) - 10} 条警告")

        report_lines.append("")
        report_lines.append("=" * 60)

        return "\n".join(report_lines)
