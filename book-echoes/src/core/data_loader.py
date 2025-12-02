"""
数据加载器

负责安全、高效地加载Excel数据文件，支持多格式Excel文件读取，
数据验证和完整性检查，编码处理和异常捕获。
"""

import pandas as pd
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import logging
from src.utils.logger import get_logger
from src.utils.config_manager import config

logger = get_logger(__name__)


class DataLoader:
    """数据加载器类"""
    
    def __init__(self):
        """初始化数据加载器"""
        self.supported_formats = ['.xlsx', '.xls']
        self.required_columns = {
            '月归还.xlsx': ['索书号', '类型/册数', '提交时间'],
            '近三月借阅.xlsx': ['索书号', '提交时间']  # 近三月借阅数据的基本列
        }
    
    def load_excel_file(self, file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
        """
        加载Excel文件
        
        Args:
            file_path: Excel文件路径
            sheet_name: 工作表名称，None表示第一个工作表
            
        Returns:
            DataFrame: 加载的数据
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式不支持或数据质量问题
        """
        file_path = Path(file_path)
        
        # 检查文件是否存在
        if not file_path.exists():
            error_msg = f"数据文件不存在: {file_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        # 检查文件格式
        if file_path.suffix not in self.supported_formats:
            error_msg = f"不支持的文件格式: {file_path.suffix}, 支持格式: {self.supported_formats}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            logger.info(f"开始加载Excel文件: {file_path}")
            
            # 读取Excel文件
            if sheet_name:
                data = pd.read_excel(file_path, sheet_name=sheet_name)
            else:
                data = pd.read_excel(file_path)
            
            # 记录数据基本信息
            logger.info(f"数据加载成功")
            logger.info(f"数据形状: {data.shape[0]}行 x {data.shape[1]}列")
            logger.info(f"列名: {list(data.columns)}")
            
            return data
            
        except Exception as e:
            error_msg = f"读取Excel文件失败: {str(e)}"
            logger.error(error_msg, extra={"file_path": str(file_path)})
            raise ValueError(error_msg) from e
    
    def validate_data(self, data: pd.DataFrame, file_type: str) -> Tuple[bool, list]:
        """
        验证数据质量
        
        Args:
            data: 要验证的数据
            file_type: 文件类型，用于确定必需的列
            
        Returns:
            Tuple[bool, list]: (验证是否通过, 错误信息列表)
        """
        errors = []
        
        # 检查数据是否为空
        if data.empty:
            errors.append("数据文件为空")
            return False, errors
        
        # 检查必需列
        if file_type in self.required_columns:
            required_cols = self.required_columns[file_type]
            missing_cols = [col for col in required_cols if col not in data.columns]
            
            if missing_cols:
                errors.append(f"缺少必需的列: {missing_cols}")
                logger.warning(f"数据验证失败 - 缺少列: {missing_cols}")
        
        # 检查数据类型
        if '索书号' in data.columns:
            null_call_numbers = data['索书号'].isnull().sum()
            if null_call_numbers > 0:
                errors.append(f"索书号列有{null_call_numbers}个空值")
                logger.warning(f"索书号列有{null_call_numbers}个空值")
        
        if '提交时间' in data.columns:
            null_times = data['提交时间'].isnull().sum()
            if null_times > 0:
                errors.append(f"提交时间列有{null_times}个空值")
                logger.warning(f"提交时间列有{null_times}个空值")
        
        is_valid = len(errors) == 0
        if is_valid:
            logger.info("数据验证通过")
        else:
            logger.warning(f"数据验证失败，共发现{len(errors)}个问题")
        
        return is_valid, errors
    
    def get_data_info(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        获取数据详细信息
        
        Args:
            data: 数据框
            
        Returns:
            Dict: 数据信息字典
        """
        info = {
            "总行数": len(data),
            "总列数": len(data.columns),
            "列名": list(data.columns),
            "内存使用(MB)": round(data.memory_usage(deep=True).sum() / 1024 / 1024, 2),
            "缺失值统计": data.isnull().sum().to_dict(),
            "数据类型": data.dtypes.to_dict()
        }
        
        # 如果有索书号列，添加索书号统计
        if '索书号' in data.columns:
            unique_call_numbers = data['索书号'].nunique()
            info["索书号统计"] = {
                "唯一索书号数量": unique_call_numbers,
                "重复率": round((len(data) - unique_call_numbers) / len(data) * 100, 2)
            }
        
        # 如果有类型/册数列，添加类型统计
        if '类型/册数' in data.columns:
            type_counts = data['类型/册数'].value_counts()
            info["类型/册数统计"] = type_counts.head(10).to_dict()
        
        return info


def load_monthly_return_data(file_path: Optional[str] = None) -> pd.DataFrame:
    """
    便捷函数：加载月归还数据
    
    Args:
        file_path: 月归还文件路径，如果为None则从配置文件读取
        
    Returns:
        DataFrame: 月归还数据
    """
    if file_path is None:
        file_path = config.get('paths.excel_files.monthly_return_file', 'data/月归还.xlsx')
        logger.info(f"从配置文件读取月归还数据路径: {file_path}")
    
    loader = DataLoader()
    data = loader.load_excel_file(file_path)
    
    # 验证数据
    is_valid, errors = loader.validate_data(data, '月归还.xlsx')
    if not is_valid:
        logger.warning(f"月归还数据验证未完全通过: {errors}")
    
    return data


def load_recent_three_months_borrowing_data(file_path: Optional[str] = None) -> pd.DataFrame:
    """
    便捷函数：加载近三月借阅数据
    
    Args:
        file_path: 近三月借阅文件路径，如果为None则从配置文件读取
        
    Returns:
        DataFrame: 近三月借阅数据
    """
    if file_path is None:
        file_path = config.get('paths.excel_files.recent_three_months_borrowing_file', 'data/近三月借阅.xlsx')
        logger.info(f"从配置文件读取近三月借阅数据路径: {file_path}")
    
    loader = DataLoader()
    data = loader.load_excel_file(file_path)
    
    # 验证数据
    is_valid, errors = loader.validate_data(data, '近三月借阅.xlsx')
    if not is_valid:
        logger.warning(f"近三月借阅数据验证未完全通过: {errors}")
    
    return data


def load_new_books_data(file_path: Optional[str] = None) -> pd.DataFrame:
    """
    便捷函数：加载新书验收数据（模块6）
    
    Args:
        file_path: 新书验收文件路径，如果为None则从配置文件读取
        
    Returns:
        DataFrame: 新书验收数据
    """
    if file_path is None:
        file_path = config.get('paths.excel_files.new_books_file', 'data/new/验收.xlsx')
        logger.info(f"从配置文件读取新书验收数据路径: {file_path}")
    
    loader = DataLoader()
    data = loader.load_excel_file(file_path)
    
    logger.info(f"新书验收数据加载完成: {len(data)} 条记录")
    return data


def load_borrowing_data_4months(file_path: Optional[str] = None) -> pd.DataFrame:
    """
    便捷函数：加载近四月借阅数据（模块6）
    
    Args:
        file_path: 近四月借阅文件路径，如果为None则从配置文件读取
        
    Returns:
        DataFrame: 近四月借阅数据
    """
    if file_path is None:
        file_path = config.get('paths.excel_files.borrowing_4months_file', 'data/new/近四月借阅.xlsx')
        logger.info(f"从配置文件读取近四月借阅数据路径: {file_path}")
    
    loader = DataLoader()
    data = loader.load_excel_file(file_path)
    
    logger.info(f"近四月借阅数据加载完成: {len(data)} 条记录")
    return data


if __name__ == "__main__":
    # 测试数据加载器
    try:
        # 加载月归还数据
        monthly_data = load_monthly_return_data()
        print("月归还数据信息:")
        loader = DataLoader()
        info = loader.get_data_info(monthly_data)
        for key, value in info.items():
            print(f"  {key}: {value}")
        
        print("\n" + "="*50)
        
        # 加载近三月借阅数据
        recent_data = load_recent_three_months_borrowing_data()
        print("近三月借阅数据信息:")
        info = loader.get_data_info(recent_data)
        for key, value in info.items():
            print(f"  {key}: {value}")
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")