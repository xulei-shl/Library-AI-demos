"""
借阅统计核心算法

使用月归还数据而非近三月借阅数据进行统计的问题。
使用近三月借阅.xlsx数据作为统计基准，计算每个索书号在近三个月内的借阅次数，
然后将这些统计数据映射回月归还数据的每条记录。
"""

import pandas as pd
from typing import Dict, List, Tuple, Any
import logging
from collections import defaultdict
import calendar

from src.utils.logger import get_logger
from src.utils.time_utils import TimeUtils

logger = get_logger(__name__)


class BorrowingStatisticsCorrected:
    """修正版借阅统计器类"""
    
    def __init__(self):
        """初始化统计器"""
        self.new_columns = [
            '近四个月总次数',
            '第一个月借阅次数',
            '第二个月借阅次数',
            '第三个月借阅次数',
            '第四个月借阅次数',
            '借阅人数'
        ]
    
    def calculate_borrowing_statistics_from_borrowing_data(self,
                                                          monthly_return_data: pd.DataFrame,
                                                          borrowing_data: pd.DataFrame,
                                                          monthly_return_call_column: str = '索书号',
                                                          borrowing_call_column: str = '索书号',
                                                          datetime_column: str = '提交时间',
                                                          user_id_column: str = '读者卡号',
                                                          target_date = None) -> pd.DataFrame:
        """
        使用近三月借阅数据计算借阅统计数据，然后映射到月归还数据
        
        Args:
            monthly_return_data: 月归还数据（需要添加统计信息的原始数据）
            borrowing_data: 近三个月借阅数据（用作统计基准）
            monthly_return_call_column: 月归还数据中的索书号列名
            borrowing_call_column: 借阅数据中的索书号列名
            datetime_column: 时间列名
            user_id_column: 用户标识列名（如读者卡号）
            target_date: 目标日期，默认为当前时间
            
        Returns:
            DataFrame: 包含新增统计列的月归还数据
        """
        logger.info("开始使用近三月借阅数据计算借阅统计数据")
        
        if monthly_return_call_column not in monthly_return_data.columns:
            logger.error(f"月归还数据中不存在'{monthly_return_call_column}'列")
            return monthly_return_data
        
        if borrowing_call_column not in borrowing_data.columns:
            logger.error(f"借阅数据中不存在'{borrowing_call_column}'列")
            return monthly_return_data
        
        if datetime_column not in borrowing_data.columns:
            logger.error(f"借阅数据中不存在'{datetime_column}'列")
            return monthly_return_data
        
        # 准备数据副本
        result_data = monthly_return_data.copy()
        
        # 确保借阅数据的时间列是datetime类型
        borrowing_data = borrowing_data.copy()
        borrowing_data[datetime_column] = pd.to_datetime(borrowing_data[datetime_column], errors='coerce')
        
        # 获取四个月时间范围（优先使用基于配置的版本）
        start_date, end_date, months_list = TimeUtils.get_recent_four_months_from_config(months_count=4)
        
        logger.info(f"计算时间范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
        
        # 筛选近三个月内的有效借阅数据
        valid_borrowing_mask = (
            (borrowing_data[datetime_column].notna()) & 
            (borrowing_data[datetime_column] >= start_date) & 
            (borrowing_data[datetime_column] <= end_date) &
            (borrowing_data[borrowing_call_column] != "") &
            (borrowing_data[borrowing_call_column].notna())
        )
        valid_borrowing_data = borrowing_data[valid_borrowing_mask].copy()
        
        logger.info(f"有效借阅统计数据: {len(valid_borrowing_data)} 条记录（原始借阅数据: {len(borrowing_data)} 条）")
        
        # 按索书号分组统计借阅次数和借阅人数
        statistics_dict = self._calculate_borrowing_statistics(valid_borrowing_data, months_list, borrowing_call_column, datetime_column, user_id_column)
        
        # 为月归还数据的每个记录分配统计数据
        result_data = self._assign_statistics_to_monthly_records(result_data, statistics_dict, monthly_return_call_column, borrowing_call_column)
        
        logger.info(f"借阅统计数据计算完成，新增 {len(self.new_columns)} 列统计数据")
        
        return result_data
    
    def _calculate_borrowing_statistics(self,
                                       borrowing_data: pd.DataFrame,
                                       months_list: List,
                                       call_column: str,
                                       datetime_column: str,
                                       user_id_column: str = '读者卡号') -> Dict[str, Dict[str, int]]:
        """
        从借阅数据计算每个索书号的统计数据（包括借阅人数）

        Args:
            borrowing_data: 借阅数据
            months_list: 月份列表
            call_column: 索书号列名
            datetime_column: 时间列名
            user_id_column: 用户标识列名

        Returns:
            Dict: 统计数据字典 {索书号: {total: 总次数, month1: 月1次数, month2: 月2次数, month3: 月3次数, month4: 月4次数, unique_borrowers: 借阅人数}}
        """
        statistics = defaultdict(lambda: {
            'total': 0,
            'month1': 0,
            'month2': 0,
            'month3': 0,
            'month4': 0,
            'unique_borrowers': 0
        })
        
        # 检查借阅数据是否有清理后索书号列
        cleaned_call_column = '清理后索书号'
        if cleaned_call_column not in borrowing_data.columns:
            logger.warning(f"借阅数据中不存在'{cleaned_call_column}'列，将使用原始索书号进行统计")
            cleaned_call_column = call_column
        else:
            logger.info(f"使用清理后的索书号进行统计: {cleaned_call_column}")
        
        # 检查用户标识列是否存在
        if user_id_column not in borrowing_data.columns:
            logger.warning(f"借阅数据中不存在'{user_id_column}'列，将使用默认的'读者卡号'进行统计")
            # 尝试常见的用户标识列名
            possible_user_columns = ['读者卡号', '用户ID', '借阅证号', '读者编号', '用户号']
            for col in possible_user_columns:
                if col in borrowing_data.columns:
                    user_id_column = col
                    logger.info(f"使用'{user_id_column}'列作为用户标识")
                    break
            else:
                # 如果都没有找到，创建一个虚拟的用户标识列（基于索引）
                borrowing_data = borrowing_data.copy()
                borrowing_data['虚拟用户ID'] = borrowing_data.index
                user_id_column = '虚拟用户ID'
                logger.warning("未找到用户标识列，将使用行索引作为虚拟用户ID进行统计")
        
        # 按月统计（优化版 - 减少重复过滤）
        # 预先过滤出非空索书号的记录
        valid_borrowing_data = borrowing_data[borrowing_data[cleaned_call_column].notna() & (borrowing_data[cleaned_call_column] != "")].copy()
        
        for idx, month_date in enumerate(months_list, 1):
            month_key = f'month{idx}'
            month_start = month_date
            # 使用calendar模块获取正确月份的天数
            last_day = calendar.monthrange(month_date.year, month_date.month)[1]
            month_end = month_date.replace(
                day=last_day, hour=23, minute=59, second=59
            )
            
            # 获取当月数据（使用优化的过滤）
            month_mask = (valid_borrowing_data[datetime_column] >= month_start) & (valid_borrowing_data[datetime_column] <= month_end)
            month_data = valid_borrowing_data[month_mask]
            
            # 按清理后的索书号统计当月借阅次数
            if len(month_data) > 0:
                month_counts = month_data[cleaned_call_column].value_counts().to_dict()
                
                # 累加到统计数据中
                for call_number, count in month_counts.items():
                    if call_number:  # 确保索书号不为空
                        statistics[call_number]['total'] += count
                        statistics[call_number][month_key] += count
        
        # 统计累计总次数（如果前面没有计算的话）
        # 补充计算total字段（确保每个索书号都有total统计）
        all_month_counts = valid_borrowing_data[cleaned_call_column].value_counts().to_dict()
        for call_number, total_count in all_month_counts.items():
            if call_number in statistics:
                # 如果之前没有total数据，使用全量数据计算
                if statistics[call_number]['total'] == 0:
                    statistics[call_number]['total'] = total_count
        
        # 计算借阅人数（优化版 - 使用groupby代替逐行搜索）
        logger.info("开始计算借阅人数统计...")
        
        # 预计算所有索书号的借阅人数（使用groupby优化性能）
        try:
            # 使用groupby一次性计算所有索书号的借阅人数
            borrowers_count = borrowing_data.groupby(cleaned_call_column)[user_id_column].nunique().to_dict()
            
            # 将借阅人数分配到统计字典中
            for call_number in statistics.keys():
                statistics[call_number]['unique_borrowers'] = borrowers_count.get(call_number, 0)
            
            logger.info(f"借阅人数计算完成")
            
        except Exception as e:
            logger.warning(f"优化算法失败，回退到原算法: {str(e)}")
            # 回退到原算法（仅在优化失败时使用）
            for call_number in statistics.keys():
                # 获取该索书号的所有借阅记录
                call_borrowings = borrowing_data[borrowing_data[cleaned_call_column] == call_number]
                
                # 统计不同用户数量
                if len(call_borrowings) > 0:
                    unique_users = call_borrowings[user_id_column].nunique()
                    statistics[call_number]['unique_borrowers'] = unique_users
                else:
                    statistics[call_number]['unique_borrowers'] = 0
        
        # 记录统计信息
        logger.info(f"索书号分组统计完成，共 {len(statistics)} 个唯一索书号")
        
        # 输出一些统计摘要
        total_counts = [stats['total'] for stats in statistics.values()]
        if total_counts:
            logger.info(f"借阅次数统计摘要:")
            logger.info(f"  平均借阅次数: {sum(total_counts) / len(total_counts):.2f}")
            logger.info(f"  最高借阅次数: {max(total_counts)}")
            logger.info(f"  最低借阅次数: {min(total_counts)}")
        
        # 借阅人数统计摘要
        unique_borrowers_counts = [stats['unique_borrowers'] for stats in statistics.values()]
        if unique_borrowers_counts:
            logger.info(f"借阅人数统计摘要:")
            logger.info(f"  平均借阅人数: {sum(unique_borrowers_counts) / len(unique_borrowers_counts):.2f}")
            logger.info(f"  最高借阅人数: {max(unique_borrowers_counts)}")
            logger.info(f"  最低借阅人数: {min(unique_borrowers_counts)}")
        
        return dict(statistics)
    
    def _assign_statistics_to_monthly_records(self,
                                             monthly_data: pd.DataFrame,
                                             statistics_dict: Dict[str, Dict[str, int]],
                                             monthly_call_column: str,
                                             borrowing_call_column: str = '索书号') -> pd.DataFrame:
        """
        为月归还数据的每个记录分配对应的统计数据
        
        Args:
            monthly_data: 月归还数据
            statistics_dict: 统计数据字典
            monthly_call_column: 月归还数据中的索书号列名
            borrowing_call_column: 借阅数据中的索书号列名
            
        Returns:
            DataFrame: 包含统计数据的月归还数据
        """
        result_data = monthly_data.copy()
        
        # 检查月归还数据是否有清理后索书号列
        cleaned_call_column = '清理后索书号'
        if cleaned_call_column not in result_data.columns:
            logger.warning(f"月归还数据中不存在'{cleaned_call_column}'列，将使用原始索书号进行匹配")
            cleaned_call_column = monthly_call_column
        
        # 初始化新列为0
        for col in self.new_columns:
            result_data[col] = 0
        
        # 分配统计数据
        assigned_count = 0
        not_matched_count = 0
        
        for idx, row in result_data.iterrows():
            # 使用清理后的索书号进行匹配
            call_number = row[cleaned_call_column] if cleaned_call_column in result_data.columns else row[monthly_call_column]

            if call_number in statistics_dict:
                stats = statistics_dict[call_number]
                result_data.loc[idx, '近四个月总次数'] = stats['total']
                result_data.loc[idx, '第一个月借阅次数'] = stats['month1']
                result_data.loc[idx, '第二个月借阅次数'] = stats['month2']
                result_data.loc[idx, '第三个月借阅次数'] = stats['month3']
                result_data.loc[idx, '第四个月借阅次数'] = stats['month4']
                result_data.loc[idx, '借阅人数'] = stats['unique_borrowers']
                assigned_count += 1
            else:
                not_matched_count += 1
        
        # 统计信息
        logger.info(f"成功分配统计数据的记录: {assigned_count}/{len(result_data)} 条")
        logger.info(f"未匹配到统计数据的记录: {not_matched_count} 条")
        logger.info(f"统计覆盖率: {assigned_count/len(result_data)*100:.2f}%")
        
        return result_data
    
    def get_statistics_summary(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        获取统计数据摘要

        Args:
            data: 包含统计数据的数据框

        Returns:
            Dict: 统计数据摘要
        """
        if '近四个月总次数' not in data.columns:
            return {"错误": "数据中没有统计数据列"}

        summary = {
            "数据总量": len(data),
            "统计数据": {}
        }

        # 统计每个新列的基本信息
        for col in self.new_columns:
            if col in data.columns:
                col_stats = {
                    "总和": int(data[col].sum()),
                    "平均值": round(data[col].mean(), 2),
                    "最大值": int(data[col].max()),
                    "最小值": int(data[col].min()),
                    "非零记录数": (data[col] > 0).sum()
                }
                summary["统计数据"][col] = col_stats

        # 索书号统计
        if '索书号' in data.columns:
            unique_call_numbers = data['索书号'].nunique()
            summary["索书号统计"] = {
                "唯一索书号数量": unique_call_numbers,
                "平均每索书号记录数": round(len(data) / unique_call_numbers, 2)
            }

        # 借阅次数分布
        if '近四个月总次数' in data.columns:
            borrowing_dist = data['近四个月总次数'].value_counts().sort_index()
            summary["借阅次数分布"] = borrowing_dist.head(10).to_dict()

        return summary


def calculate_corrected_borrowing_stats(monthly_return_data: pd.DataFrame,
                                       borrowing_data: pd.DataFrame,
                                       monthly_return_call_column: str = '索书号',
                                       borrowing_call_column: str = '索书号',
                                       datetime_column: str = '提交时间',
                                       user_id_column: str = '读者卡号',
                                       target_date = None) -> pd.DataFrame:
    """
    便捷函数：使用借阅数据计算月归还数据的借阅统计（包括借阅人数）
    
    Args:
        monthly_return_data: 月归还数据
        borrowing_data: 近三个月借阅数据
        monthly_return_call_column: 月归还数据中的索书号列名
        borrowing_call_column: 借阅数据中的索书号列名
        datetime_column: 时间列名
        user_id_column: 用户标识列名（如读者卡号）
        target_date: 目标日期
        
    Returns:
        DataFrame: 包含统计数据（包括借阅人数）的月归还数据
    """
    calculator = BorrowingStatisticsCorrected()
    return calculator.calculate_borrowing_statistics_from_borrowing_data(
        monthly_return_data, borrowing_data,
        monthly_return_call_column, borrowing_call_column,
        datetime_column, user_id_column, target_date
    )


# 向后兼容性别名
BorrowingStatistics = BorrowingStatisticsCorrected

if __name__ == "__main__":
    # 测试修正后的借阅统计
    from src.core.data_loader import load_monthly_return_data, load_recent_three_months_borrowing_data
    from src.core.data_cleaner import clean_monthly_return_data
    
    try:
        print("加载数据...")
        
        # 加载月归还数据
        monthly_return_data = load_monthly_return_data()
        print(f"月归还数据: {len(monthly_return_data)} 条")
        
        # 加载近三月借阅数据
        borrowing_data = load_recent_three_months_borrowing_data()
        print(f"近三月借阅数据: {len(borrowing_data)} 条")
        
        # 清洗月归还数据
        print("清洗月归还数据...")
        cleaned_monthly_data = clean_monthly_return_data(monthly_return_data)
        
        # 计算修正后的借阅统计
        print("计算修正后的借阅统计...")
        corrected_stats_data = calculate_corrected_borrowing_stats(
            cleaned_monthly_data, borrowing_data
        )
        
        print(f"修正后统计完成，结果数据量: {len(corrected_stats_data)} 条")
        
        # 显示统计摘要
        calculator = BorrowingStatisticsCorrected()
        summary = calculator.get_statistics_summary(corrected_stats_data)
        print("修正后统计摘要:")
        for key, value in summary.items():
            print(f"  {key}: {value}")
        
        # 特别显示有统计数据的索书号
        has_stats = corrected_stats_data[corrected_stats_data['近四个月总次数'] > 0]
        if len(has_stats) > 0:
            print(f"\n有统计数据的索书号示例 (前5个):")
            sample_cols = ['索书号', '清理后索书号'] + calculator.new_columns
            available_cols = [col for col in sample_cols if col in has_stats.columns]
            print(has_stats[available_cols].head().to_string(index=False))
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
