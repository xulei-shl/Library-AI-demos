"""
新书数据预处理器

负责对新书验收数据进行预处理，包括列重命名、数据清洗等。
"""

import pandas as pd
from src.utils.logger import get_logger

logger = get_logger(__name__)


def preprocess_new_books_data(new_books_df: pd.DataFrame) -> pd.DataFrame:
    """
    预处理新书验收数据
    
    主要操作：
    1. 列重命名：馆藏条码 -> 书目条码
    2. 列重命名：标识号 -> ISBN
    3. ISBN列清洗
    
    Args:
        new_books_df: 新书验收数据DataFrame
        
    Returns:
        pd.DataFrame: 预处理后的数据
    """
    logger.info("开始预处理新书验收数据")
    
    # 创建副本以避免修改原始数据
    df = new_books_df.copy()
    
    # 记录原始列名
    logger.info(f"原始列名: {list(df.columns)}")
    
    # 列重命名
    rename_map = {}
    
    if '馆藏条码' in df.columns:
        rename_map['馆藏条码'] = '书目条码'
        logger.info("列重命名: 馆藏条码 -> 书目条码")
    
    if '标识号' in df.columns:
        rename_map['标识号'] = 'ISBN'
        logger.info("列重命名: 标识号 -> ISBN")
    
    if rename_map:
        df = df.rename(columns=rename_map)
    
    # ISBN列清洗
    if 'ISBN' in df.columns:
        # 转换为字符串并去除空格
        df['ISBN'] = df['ISBN'].astype(str).str.strip()
        # 将'nan'字符串和空字符串转换为None
        df.loc[df['ISBN'].isin(['nan', '', 'None']), 'ISBN'] = None
        
        null_isbn_count = df['ISBN'].isnull().sum()
        logger.info(f"ISBN列清洗完成，空值数量: {null_isbn_count}/{len(df)}")
    
    # 书目条码列清洗
    if '书目条码' in df.columns:
        # 转换为字符串并去除空格
        df['书目条码'] = df['书目条码'].astype(str).str.strip()
        # 将'nan'字符串和空字符串转换为None
        df.loc[df['书目条码'].isin(['nan', '', 'None']), '书目条码'] = None
        
        null_barcode_count = df['书目条码'].isnull().sum()
        logger.info(f"书目条码列清洗完成，空值数量: {null_barcode_count}/{len(df)}")
        
        if null_barcode_count > 0:
            logger.warning(f"发现{null_barcode_count}条记录的书目条码为空，这些记录将无法进行零借阅筛选")
    
    logger.info(f"预处理后列名: {list(df.columns)}")
    logger.info(f"预处理完成，数据量: {len(df)} 条")
    
    return df


def clean_isbn_column(df: pd.DataFrame, isbn_column: str = 'isbn') -> pd.DataFrame:
    """
    清洗ISBN列
    
    Args:
        df: 数据DataFrame
        isbn_column: ISBN列名
        
    Returns:
        pd.DataFrame: 清洗后的数据
    """
    if isbn_column not in df.columns:
        logger.warning(f"列 '{isbn_column}' 不存在，跳过ISBN清洗")
        return df
    
    df_copy = df.copy()
    
    # 转换为字符串
    df_copy[isbn_column] = df_copy[isbn_column].astype(str)
    
    # 去除空格和特殊字符
    df_copy[isbn_column] = df_copy[isbn_column].str.strip()
    df_copy[isbn_column] = df_copy[isbn_column].str.replace('-', '')
    df_copy[isbn_column] = df_copy[isbn_column].str.replace(' ', '')
    
    # 将无效值转换为None
    df_copy.loc[df_copy[isbn_column].isin(['nan', '', 'None', 'NaN']), isbn_column] = None
    
    logger.info(f"ISBN列清洗完成")
    
    return df_copy
