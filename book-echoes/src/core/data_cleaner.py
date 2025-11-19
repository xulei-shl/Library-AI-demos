"""
统一数据清洗器

整合原有的通用数据清洗器和借阅数据专用清洗器，
通过配置参数支持不同类型的数据清洗需求。
"""

import pandas as pd
import re
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataCleanerConfig:
    """数据清洗配置类"""
    
    def __init__(self, 
                 data_type: str = "general",
                 filter_chinese_books: bool = False,
                 remove_invalid_records: bool = False,
                 required_columns: List[str] = None):
        """
        初始化清洗配置
        
        Args:
            data_type: 数据类型 ("monthly_return", "borrowing", "general")
            filter_chinese_books: 是否筛选中文图书
            remove_invalid_records: 是否移除无效记录
            required_columns: 必需的列名列表
        """
        self.data_type = data_type
        self.filter_chinese_books = filter_chinese_books
        self.remove_invalid_records = remove_invalid_records
        self.required_columns = required_columns or []
        
        # 根据数据类型设置默认配置
        if data_type == "monthly_return":
            self.filter_chinese_books = True
        elif data_type == "borrowing":
            self.remove_invalid_records = True
            self.required_columns = ['清理后索书号', '提交时间']


class UnifiedDataCleaner:
    """统一数据清洗器类"""
    
    def __init__(self, config: DataCleanerConfig = None):
        """
        初始化统一数据清洗器
        
        Args:
            config: 数据清洗配置，如果为None则使用默认配置
        """
        self.config = config or DataCleanerConfig()
        self.chinese_book_prefix = "中文图书"
    
    def clean_call_number(self, call_number: str) -> str:
        """
        标准化索书号
        
        处理规则：
        1. 去除末尾的#和*及后面的数字，如 #10*2, #8 等
        2. 如果有两个以上/，保留到第二个/为止
        
        Args:
            call_number: 原始索书号
            
        Returns:
            str: 清理后的索书号
        """
        if not call_number or pd.isna(call_number):
            return ""
        
        # 转换为字符串并去除前后空格
        cleaned = str(call_number).strip()
        
        # 去除末尾的#和*及后面的数字
        # 匹配 #数字 或 *数字 或 #数字*数字 等模式
        cleaned = re.sub(r'[#*]\d+(?:[*]\d+)?$', '', cleaned)
        
        # 如果有两个以上/，保留到第二个/为止
        parts = cleaned.split('/')
        if len(parts) > 2:
            cleaned = '/'.join(parts[:2])
        
        # 再次去除可能产生的尾随空格和特殊字符
        cleaned = re.sub(r'[#*]\s*$', '', cleaned)
        
        return cleaned.strip()
    
    def filter_chinese_books(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        筛选中文图书
        
        只保留"类型/册数"列中以"中文图书"开头的行数据
        
        Args:
            data: 原始数据
            
        Returns:
            DataFrame: 筛选后的中文图书数据
        """
        if '类型/册数' not in data.columns:
            logger.warning("数据中不存在'类型/册数'列，跳过中文图书筛选")
            return data
        
        # 筛选中文图书
        chinese_mask = data['类型/册数'].str.startswith(self.chinese_book_prefix, na=False)
        filtered_data = data[chinese_mask].copy()
        
        logger.info(f"中文图书筛选结果: {len(filtered_data)}/{len(data)} 条记录保留")
        
        # 记录筛选统计
        if len(data) > 0:
            retention_rate = len(filtered_data) / len(data) * 100
            logger.info(f"中文图书保留率: {retention_rate:.2f}%")
        
        return filtered_data
    
    def remove_invalid_records(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        移除无效记录
        
        Args:
            data: 原始数据
            
        Returns:
            DataFrame: 过滤后的数据
        """
        if not self.config.required_columns:
            logger.warning("未指定必需列，跳过无效记录移除")
            return data
        
        initial_count = len(data)
        valid_mask = pd.Series(True, index=data.index)
        
        # 检查每个必需列
        for col in self.config.required_columns:
            if col in data.columns:
                if col == '清理后索书号':
                    # 索书号不能为空
                    valid_mask &= (data[col] != "") & (data[col].notna())
                elif col == '提交时间':
                    # 时间不能为空
                    valid_mask &= data[col].notna()
                else:
                    # 其他列不能为空
                    valid_mask &= data[col].notna()
        
        filtered_data = data[valid_mask].copy()
        removed_count = initial_count - len(filtered_data)
        
        if removed_count > 0:
            logger.info(f"移除无效记录: {removed_count} 条记录被移除")
        
        return filtered_data
    
    def standardize_datetime(self, data: pd.DataFrame, datetime_column: str = '提交时间') -> pd.DataFrame:
        """
        标准化时间格式
        
        Args:
            data: 数据框
            datetime_column: 时间列名
            
        Returns:
            DataFrame: 标准化后的数据
        """
        if datetime_column not in data.columns:
            logger.warning(f"数据中不存在'{datetime_column}'列，跳过时间标准化")
            return data
        
        data = data.copy()
        
        try:
            # 尝试解析时间
            data[datetime_column] = pd.to_datetime(data[datetime_column])
            logger.info(f"时间列'{datetime_column}'标准化成功")
            
        except Exception as e:
            logger.warning(f"时间列'{datetime_column}'标准化失败: {str(e)}")
        
        return data
    
    def add_cleaned_call_number(self, data: pd.DataFrame, 
                              original_column: str = '索书号',
                              cleaned_column: str = '清理后索书号') -> pd.DataFrame:
        """
        添加清理后的索书号列
        
        Args:
            data: 原始数据
            original_column: 原始索书号列名
            cleaned_column: 清理后索书号列名
            
        Returns:
            DataFrame: 包含清理后索书号的数据
        """
        if original_column not in data.columns:
            logger.error(f"数据中不存在'{original_column}'列，跳过索书号清理")
            return data
        
        data = data.copy()
        
        # 应用索书号清理
        data[cleaned_column] = data[original_column].apply(self.clean_call_number)
        
        # 统计清理效果
        if len(data) > 0:
            original_unique = data[original_column].nunique()
            cleaned_unique = data[cleaned_column].nunique()
            
            logger.info(f"索书号清理效果:")
            logger.info(f"  原始唯一索书号: {original_unique}")
            logger.info(f"  清理后唯一索书号: {cleaned_unique}")
            logger.info(f"  合并效果: {original_unique - cleaned_unique} 个索书号被合并")
        
        return data
    
    def get_cleaning_statistics(self, original_data: pd.DataFrame, 
                               cleaned_data: pd.DataFrame) -> Dict[str, Any]:
        """
        获取清洗统计信息
        
        Args:
            original_data: 原始数据
            cleaned_data: 清洗后数据
            
        Returns:
            Dict: 统计信息
        """
        stats = {
            "原始数据量": len(original_data),
            "清洗后数据量": len(cleaned_data),
            "数据保留率(%)": round(len(cleaned_data) / len(original_data) * 100, 2) if len(original_data) > 0 else 0,
            "数据损失量": len(original_data) - len(cleaned_data)
        }
        
        # 索书号统计
        if '索书号' in original_data.columns and '索书号' in cleaned_data.columns:
            original_call_nums = original_data['索书号'].nunique()
            cleaned_call_nums = cleaned_data['索书号'].nunique()
            
            stats.update({
                "原始唯一索书号": original_call_nums,
                "清洗后唯一索书号": cleaned_call_nums,
                "索书号合并数量": original_call_nums - cleaned_call_nums
            })
        
        # 类型分布统计
        if '类型/册数' in original_data.columns:
            original_type_dist = original_data['类型/册数'].value_counts()
            cleaned_type_dist = cleaned_data['类型/册数'].value_counts() if len(cleaned_data) > 0 else pd.Series()
            
            stats.update({
                "原始数据类型分布": original_type_dist.head(5).to_dict(),
                "清洗后主要类型": cleaned_type_dist.head(3).to_dict() if len(cleaned_data) > 0 else {}
            })
        
        # 时间分布统计
        if '提交时间' in original_data.columns and '提交时间' in cleaned_data.columns:
            original_valid_times = original_data['提交时间'].notna().sum()
            cleaned_valid_times = cleaned_data['提交时间'].notna().sum()
            
            stats.update({
                "原始有效时间记录": original_valid_times,
                "清洗后有效时间记录": cleaned_valid_times,
                "时间数据保留率(%)": round(cleaned_valid_times / original_valid_times * 100, 2) if original_valid_times > 0 else 0
            })
        
        return stats
    
    def clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        完整的数据清洗流程
        
        Args:
            data: 原始数据
            
        Returns:
            DataFrame: 清洗后的数据
        """
        logger.info(f"开始{self.config.data_type}数据清洗流程")
        
        # 记录原始数据信息
        original_stats = {
            "原始数据量": len(data),
            "原始列数": len(data.columns),
            "原始列名": list(data.columns)
        }
        logger.info(f"原始{self.config.data_type}数据信息: {original_stats}")
        
        data = data.copy()
        
        # 步骤1: 筛选中文图书（如果配置启用）
        if self.config.filter_chinese_books:
            data = self.filter_chinese_books(data)
        
        # 步骤2: 标准化时间格式
        data = self.standardize_datetime(data)
        
        # 步骤3: 添加清理后的索书号
        data = self.add_cleaned_call_number(data)
        
        # 步骤4: 移除无效记录（如果配置启用）
        if self.config.remove_invalid_records:
            data = self.remove_invalid_records(data)
        
        logger.info(f"{self.config.data_type}数据清洗流程完成")
        
        return data


# 便捷函数
def clean_monthly_return_data(data: pd.DataFrame) -> pd.DataFrame:
    """
    便捷函数：清洗月归还数据
    
    Args:
        data: 原始月归还数据
        
    Returns:
        DataFrame: 清洗后的数据
    """
    config = DataCleanerConfig(data_type="monthly_return")
    cleaner = UnifiedDataCleaner(config)
    return cleaner.clean_data(data)


def clean_borrowing_data(data: pd.DataFrame) -> pd.DataFrame:
    """
    便捷函数：清洗借阅数据
    
    Args:
        data: 原始借阅数据
        
    Returns:
        DataFrame: 清洗后的数据
    """
    config = DataCleanerConfig(data_type="borrowing")
    cleaner = UnifiedDataCleaner(config)
    return cleaner.clean_data(data)


def create_custom_cleaner(data_type: str = "general",
                         filter_chinese_books: bool = False,
                         remove_invalid_records: bool = False,
                         required_columns: List[str] = None) -> UnifiedDataCleaner:
    """
    创建自定义清洗器的便捷函数
    
    Args:
        data_type: 数据类型标识
        filter_chinese_books: 是否筛选中文图书
        remove_invalid_records: 是否移除无效记录
        required_columns: 必需列名列表
        
    Returns:
        UnifiedDataCleaner: 配置好的清洗器实例
    """
    config = DataCleanerConfig(
        data_type=data_type,
        filter_chinese_books=filter_chinese_books,
        remove_invalid_records=remove_invalid_records,
        required_columns=required_columns
    )
    return UnifiedDataCleaner(config)


if __name__ == "__main__":
    # 测试统一数据清洗器
    from src.core.data_loader import load_monthly_return_data, load_recent_three_months_borrowing_data
    
    try:
        print("=== 测试月归还数据清洗 ===")
        # 加载原始月归还数据
        print("正在加载月归还数据...")
        monthly_data = load_monthly_return_data()
        
        # 清洗数据
        print("\n正在清洗月归还数据...")
        cleaned_monthly = clean_monthly_return_data(monthly_data)
        
        print(f"\n月归还数据清洗完成:")
        print(f"原始数据: {len(monthly_data)} 行")
        print(f"清洗后数据: {len(cleaned_monthly)} 行")
        
        print("\n=== 测试借阅数据清洗 ===")
        # 加载原始借阅数据
        print("正在加载借阅数据...")
        borrowing_data = load_recent_three_months_borrowing_data()
        
        # 清洗数据
        print("\n正在清洗借阅数据...")
        cleaned_borrowing = clean_borrowing_data(borrowing_data)
        
        print(f"\n借阅数据清洗完成:")
        print(f"原始数据: {len(borrowing_data)} 行")
        print(f"清洗后数据: {len(cleaned_borrowing)} 行")
        
        # 测试自定义清洗器
        print("\n=== 测试自定义清洗器 ===")
        custom_cleaner = create_custom_cleaner(
            data_type="custom_test",
            filter_chinese_books=True,
            remove_invalid_records=True,
            required_columns=['清理后索书号', '提交时间']
        )
        
        if len(monthly_data) > 0:
            custom_cleaned = custom_cleaner.clean_data(monthly_data)
            print(f"自定义清洗结果: {len(custom_cleaned)} 行")
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")