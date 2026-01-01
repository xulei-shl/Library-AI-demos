"""
时间处理工具

提供时间解析、格式化、筛选等功能，支持近三个月数据筛选
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple, List, Dict, Any, Optional
import calendar
import logging

from src.utils.logger import get_logger
from src.utils.config_manager import get_statistics_config

logger = get_logger(__name__)


class TimeUtils:
    """时间工具类"""
    
    @staticmethod
    def parse_datetime(datetime_str: str) -> Optional[datetime]:
        """
        解析时间字符串
        
        支持多种时间格式，如：2025-09-30 16:30:56
        
        Args:
            datetime_str: 时间字符串
            
        Returns:
            datetime: 解析后的时间对象，解析失败返回None
        """
        if not datetime_str or pd.isna(datetime_str):
            return None
        
        # 支持的日期时间格式
        datetime_formats = [
            '%Y-%m-%d %H:%M:%S',  # 2025-09-30 16:30:56
            '%Y-%m-%d %H:%M',     # 2025-09-30 16:30
            '%Y-%m-%d',           # 2025-09-30
            '%Y/%m/%d %H:%M:%S',  # 2025/09/30 16:30:56
            '%Y/%m/%d %H:%M',     # 2025/09/30 16:30
            '%Y/%m/%d',           # 2025/09/30
        ]
        
        for fmt in datetime_formats:
            try:
                return datetime.strptime(str(datetime_str).strip(), fmt)
            except (ValueError, TypeError):
                continue
        
        # 如果所有格式都失败，尝试pandas的通用解析
        try:
            return pd.to_datetime(datetime_str)
        except (ValueError, TypeError):
            logger.warning(f"无法解析时间字符串: {datetime_str}")
            return None
    
    @staticmethod
    def get_recent_three_months(target_date: datetime = None) -> Tuple[datetime, datetime, List[datetime]]:
        """
        获取近三个月的时间范围
        
        Args:
            target_date: 目标日期，默认为当前时间
            
        Returns:
            Tuple[datetime, datetime, List[datetime]]: 
                (三个月开始时间, 三个月结束时间, 三个月列表)
        """
        if target_date is None:
            target_date = datetime.now()
        
        # 计算三个月前的时间
        three_months_ago = target_date.replace(day=1)  # 设为当月1号
        for _ in range(3):
            # 获取上个月的最后一天
            if three_months_ago.month == 1:
                prev_month = three_months_ago.replace(year=three_months_ago.year - 1, month=12)
            else:
                prev_month = three_months_ago.replace(month=three_months_ago.month - 1)
            three_months_ago = prev_month.replace(day=calendar.monthrange(prev_month.year, prev_month.month)[1])
        
        # 获取三个月列表
        months_list = []
        current_month = target_date.replace(day=1)
        
        for i in range(3):
            if current_month.month - i <= 0:
                month_year = current_month.year - 1
                month_month = 12 + (current_month.month - i)
            else:
                month_year = current_month.year
                month_month = current_month.month - i
            
            month_date = datetime(month_year, month_month, 1)
            months_list.append(month_date)
        
        months_list.reverse()  # 早到晚排序
        
        # 确定三个月范围的开始和结束
        start_date = months_list[0]  # 最早月份的第一天
        end_date = months_list[-1]   # 最新月份的最后一天
        end_date = end_date.replace(
            day=calendar.monthrange(end_date.year, end_date.month)[1],
            hour=23, minute=59, second=59
        )
        
        logger.info(f"近三个月时间范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
        logger.info(f"月份列表: {[month.strftime('%Y-%m') for month in months_list]}")
        
        return start_date, end_date, months_list
    
    @staticmethod
    def get_recent_three_months_from_config() -> Tuple[datetime, datetime, List[datetime]]:
        """
        基于配置文件中的月份设置获取近三个月的时间范围

        Returns:
            Tuple[datetime, datetime, List[datetime]]:
                (三个月开始时间, 三个月结束时间, 三个月列表)
        """
        return TimeUtils.get_recent_four_months_from_config(months_count=3)

    @staticmethod
    def get_recent_four_months_from_config(months_count: int = 4) -> Tuple[datetime, datetime, List[datetime]]:
        """
        基于配置文件中的月份设置获取近N个月的时间范围

        Args:
            months_count: 月份数量，默认4个月

        Returns:
            Tuple[datetime, datetime, List[datetime]]:
                (N个月开始时间, N个月结束时间, N个月列表)
        """
        config = get_statistics_config()
        target_month_str = config.get('target_month', '2025-09')
        use_target_month_previous = config.get('use_target_month_previous', True)

        try:
            # 解析目标月份
            target_month = datetime.strptime(target_month_str, '%Y-%m')
        except ValueError:
            logger.warning(f"无法解析配置的目标月份 '{target_month_str}', 使用默认的2025-09")
            target_month = datetime(2025, 9, 1)

        # 如果配置为基于上个月，则目标月份实际上是配置月份的下个月
        if use_target_month_previous:
            # 目标月份表示"借阅统计数据基于X月份"，那么实际计算应该是X+1月份的数据
            if target_month.month == 12:
                reference_month = target_month.replace(year=target_month.year + 1, month=1)
            else:
                reference_month = target_month.replace(month=target_month.month + 1)
        else:
            reference_month = target_month

        logger.info(f"基于配置计算{months_count}个月范围: 目标月份={target_month_str}, 参考月份={reference_month.strftime('%Y-%m')}")

        # 基于参考月份计算近N个月
        months_list = []

        # 计算参考月份向前推N个月的月份列表
        for i in range(months_count):
            if reference_month.month - i <= 0:
                month_year = reference_month.year - 1
                month_month = 12 + (reference_month.month - i)
            else:
                month_year = reference_month.year
                month_month = reference_month.month - i

            month_date = datetime(month_year, month_month, 1)
            months_list.append(month_date)

        months_list.reverse()  # 早到晚排序

        # 确定N个月范围的开始和结束
        start_date = months_list[0]  # 最早月份的第一天
        end_date = months_list[-1]   # 最新月份的最后一天
        end_date = end_date.replace(
            day=calendar.monthrange(end_date.year, end_date.month)[1],
            hour=23, minute=59, second=59
        )

        logger.info(f"基于配置的近{months_count}个月时间范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
        logger.info(f"月份列表: {[month.strftime('%Y-%m') for month in months_list]}")

        return start_date, end_date, months_list
    
    @staticmethod
    def filter_data_by_time_range(data: pd.DataFrame, 
                                 start_date: datetime, 
                                 end_date: datetime,
                                 datetime_column: str = '提交时间') -> pd.DataFrame:
        """
        按时间范围筛选数据
        
        Args:
            data: 数据框
            start_date: 开始时间
            end_date: 结束时间
            datetime_column: 时间列名
            
        Returns:
            DataFrame: 筛选后的数据
        """
        if datetime_column not in data.columns:
            logger.warning(f"数据中不存在'{datetime_column}'列")
            return data
        
        # 确保时间列是datetime类型
        data[datetime_column] = pd.to_datetime(data[datetime_column], errors='coerce')
        
        # 筛选时间范围内的数据
        mask = (data[datetime_column] >= start_date) & (data[datetime_column] <= end_date)
        filtered_data = data[mask].copy()
        
        logger.info(f"时间范围筛选结果: {len(filtered_data)}/{len(data)} 条记录在指定时间范围内")
        
        return filtered_data
    
    @staticmethod
    def get_monthly_data_split(data: pd.DataFrame,
                              months_list: List[datetime],
                              datetime_column: str = '提交时间') -> Dict[str, pd.DataFrame]:
        """
        按月分割数据
        
        Args:
            data: 数据框
            months_list: 月份列表
            datetime_column: 时间列名
            
        Returns:
            Dict[str, DataFrame]: 每月的数据字典，键为'YYYY-MM'格式
        """
        if datetime_column not in data.columns:
            logger.warning(f"数据中不存在'{datetime_column}'列")
            return {}
        
        monthly_data = {}
        
        # 确保时间列是datetime类型
        data[datetime_column] = pd.to_datetime(data[datetime_column], errors='coerce')
        
        for month_date in months_list:
            month_key = month_date.strftime('%Y-%m')
            month_start = month_date
            month_end = month_date.replace(
                day=calendar.monthrange(month_date.year, month_date.month)[1],
                hour=23, minute=59, second=59
            )
            
            # 筛选当月数据
            mask = (data[datetime_column] >= month_start) & (data[datetime_column] <= month_end)
            monthly_data[month_key] = data[mask].copy()
            
            logger.info(f"{month_key} 数据量: {len(monthly_data[month_key])} 条")
        
        return monthly_data
    
    @staticmethod
    def calculate_time_statistics(data: pd.DataFrame, 
                                 datetime_column: str = '提交时间') -> Dict[str, Any]:
        """
        计算时间相关统计信息
        
        Args:
            data: 数据框
            datetime_column: 时间列名
            
        Returns:
            Dict: 时间统计信息
        """
        if datetime_column not in data.columns:
            return {}
        
        # 确保时间列是datetime类型
        data[datetime_column] = pd.to_datetime(data[datetime_column], errors='coerce')
        
        # 去除无效时间
        valid_times = data[datetime_column].dropna()
        
        if len(valid_times) == 0:
            return {"错误": "没有有效的时间数据"}
        
        stats = {
            "数据时间范围": {
                "最早时间": valid_times.min().strftime('%Y-%m-%d %H:%M:%S'),
                "最晚时间": valid_times.max().strftime('%Y-%m-%d %H:%M:%S'),
                "时间跨度(天)": (valid_times.max() - valid_times.min()).days
            },
            "数据分布": {
                "总记录数": len(data),
                "有效时间记录数": len(valid_times),
                "无效时间记录数": len(data) - len(valid_times),
                "有效率(%)": round(len(valid_times) / len(data) * 100, 2)
            }
        }
        
        # 按月统计
        if len(valid_times) > 0:
            monthly_counts = valid_times.dt.to_period('M').value_counts().sort_index()
            stats["月度分布"] = {
                month.strftime('%Y-%m'): count 
                for month, count in monthly_counts.items()
            }
        
        return stats
    
    @staticmethod
    def filter_recent_three_months_data(data: pd.DataFrame,
                                       target_date: datetime = None,
                                       datetime_column: str = '提交时间') -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        筛选近三个月的数据
        
        Args:
            data: 数据框
            target_date: 目标日期，默认为当前时间
            datetime_column: 时间列名
            
        Returns:
            Tuple[DataFrame, Dict]: (筛选后的数据, 时间统计信息)
        """
        # 获取三个月时间范围
        start_date, end_date, months_list = TimeUtils.get_recent_three_months(target_date)
        
        # 按时间范围筛选数据
        filtered_data = TimeUtils.filter_data_by_time_range(data, start_date, end_date, datetime_column)
        
        # 按月分割数据
        monthly_data = TimeUtils.get_monthly_data_split(filtered_data, months_list, datetime_column)
        
        # 计算统计信息
        time_stats = TimeUtils.calculate_time_statistics(filtered_data, datetime_column)
        time_stats["三个月时间范围"] = {
            "开始时间": start_date.strftime('%Y-%m-%d %H:%M:%S'),
            "结束时间": end_date.strftime('%Y-%m-%d %H:%M:%S'),
            "月份列表": [month.strftime('%Y-%m') for month in months_list]
        }
        time_stats["月度数据量"] = {month: len(data) for month, data in monthly_data.items()}
        
        logger.info(f"近三个月数据筛选完成，共{len(filtered_data)}条记录")
        
        return filtered_data, time_stats


def parse_submission_time(time_str: str) -> Optional[datetime]:
    """
    便捷函数：解析提交时间
    
    Args:
        time_str: 提交时间字符串
        
    Returns:
        datetime: 解析后的时间对象
    """
    return TimeUtils.parse_datetime(time_str)


def filter_recent_three_months_borrowing_data(data: pd.DataFrame,
                                            target_date: datetime = None,
                                            datetime_column: str = '提交时间') -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    便捷函数：筛选近三个月的借阅数据
    
    Args:
        data: 借阅数据
        target_date: 目标日期
        datetime_column: 时间列名
        
    Returns:
        Tuple[DataFrame, Dict]: (筛选后的数据, 统计信息)
    """
    return TimeUtils.filter_recent_three_months_data(data, target_date, datetime_column)
def get_timestamp():
    """获取时间戳，用于文件名生成
    
    Returns:
        str: 时间戳字符串，格式为 YYYYMMDD_HHMMSS
    """
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def filter_recent_three_months_borrowing_data(data: pd.DataFrame,
                                            target_date: datetime = None,
                                            datetime_column: str = '提交时间') -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    便捷函数：筛选近三个月的借阅数据
    
    Args:
        data: 借阅数据
        target_date: 目标日期
        datetime_column: 时间列名
        
    Returns:
        Tuple[DataFrame, Dict]: (筛选后的数据, 统计信息)
    """
    return TimeUtils.filter_recent_three_months_data(data, target_date, datetime_column)


if __name__ == "__main__":
    # 测试时间工具
    from src.core.data_loader import load_monthly_return_data
    from src.core.data_cleaner import clean_monthly_return_data
    
    try:
        # 加载并清洗数据
        original_data = load_monthly_return_data()
        cleaned_data = clean_monthly_return_data(original_data)
        
        # 测试时间处理
        print("测试时间统计:")
        time_stats = TimeUtils.calculate_time_statistics(cleaned_data)
        for key, value in time_stats.items():
            print(f"  {key}: {value}")
        
        # 测试近三个月筛选
        print("\n测试近三个月数据筛选:")
        recent_data, recent_stats = filter_recent_three_months_borrowing_data(cleaned_data)
        print(f"近三个月数据量: {len(recent_data)} 条")
        print(f"时间统计: {recent_stats}")
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")