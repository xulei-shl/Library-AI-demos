"""
配置管理模块
定义系统的所有配置参数
"""
import os
from pathlib import Path

# 基础路径配置
BASE_DIR = Path(__file__).parent.parent.parent

# 目标文件路径配置（绝对路径或相对于BASE_DIR的路径）
# 在实际部署时，请根据需要修改此路径。
TARGET_FILE_PATH = BASE_DIR / "2025年度业务统计表.xlsx" 

# 源Excel文件路径配置（绝对路径或相对于BASE_DIR的路径）
# 建议将所有待处理的源文件放入此目录。
SOURCE_EXCEL_PATH = BASE_DIR / "1"

# 已处理文件夹配置（绝对路径或相对于BASE_DIR的路径）
# 处理后的文件将移动到此目录。
PROCESSED_FOLDER = BASE_DIR / "已处理"

# 日志文件夹配置（相对路径）
LOG_FOLDER = "logs"

# 文件识别模式
FILE_PATTERNS = {
    'yibu': '馆藏业务统计表',
    'erbu': '二部',
    'sanbu': '三部'
}

# ============================================================================== 
# 全局列映射配置 (Global Column Mapping Configuration)
# ============================================================================== 
COLUMN_MAPPINGS = {
    # 默认映射规则，适用于所有文件
    # 注意：只配置需要转换的列名（别名）和特殊映射，标准列名会通过默认直通逻辑自动处理
    "*": {  
        # --- 别名 -> 标准列名 ---
        "统计员": "统计人",
        "统计": "统计人",
        "统计人员": "统计人",
        "计量单位": "单位",
        "单位名称": "单位",
        "度量单位": "单位",
        "移库来源": "上游来源",
        "移库去向": "下游去向",
    },
    
    # 针对 "一部" 的特殊规则 (字母列，源表 I 列 -> 目标 I  列)
    'yibu': {
        "I": "I"
    },
    
    # 针对 "二部" 的特殊规则 (源表 H 列 -> 目标 I  列)
    'erbu': {
        "H": "I"
    },

    # 针对 "三部" 的特殊规则 (源表 K 列 -> 目标 I 列)
    'sanbu': {
        "K": "I"
    }
}

# ============================================================================== 
# 动态列映射配置 (用于通过正则表达式匹配列名)
# ============================================================================== 
DYNAMIC_COLUMN_PATTERNS = {
    # 全局动态模式，适用于所有文件类型
    "*": {
        # # 示例：匹配带数字的列名
        # r'[\]d+[]$': 'I',  # 匹配 [19484], [168690] 等
        # r'^=SUBTOTAL.*': 'I',  # 匹配 SUBTOTAL 公式
        # r'^\d+$': 'I',  # 匹配纯数字列名（如168690等动态计算的数字）
        # r'^=SUM.*': 'I',  # 匹配sum公式
    },
    
    # 各文件类型特定的动态模式
    'yibu': {
        # 一部特定的动态模式
    },
    
    'erbu': {
        # 二部特定的动态模式  
    },
    
    'sanbu': {
        # 三部特定的动态模式
    }
}

# ============================================================================== 
# 缺失列默认值配置 (Default Values for Missing Columns)
# ============================================================================== 
DEFAULT_VALUES = {
    # 全局默认值, 当任何源文件缺失目标列时使用
    "*": {
        # "目标列名": "默认值"
        # 例如: "单位": "册"
    },
    
    # 针对 "一部" 的特殊规则
    'yibu': {
        # 一部文件的默认值
    },
    
    # 针对 "二部" 的特殊规则
    'erbu': {
        # 二部文件的默认值
    },

    # 针对 "三部" 的特殊规则
    'sanbu': {
        "统计人": "XL",
        "单位": "册件"
    }
}

# ============================================================================== 
# 数据处理配置 (Data Processing Configuration)
# ============================================================================== 
DATA_PROCESSING_CONFIG = {
    # 全局数据处理配置
    "*": {
        "enable_default_cleaning": True,  # 是否启用默认数据清洗
        "remove_empty_rows": True,        # 是否移除空行
        "remove_whitespace_rows": True,   # 是否移除空白字符行
    },
    
    # 各文件类型特定的处理配置
    'yibu': {
        "enable_default_cleaning": True,
    },
    
    'erbu': {
        "enable_default_cleaning": True,
        "enable_time_filtering": True,    # 是否启用时间筛选
        "filter_target_month": "last",   # 筛选目标月份："last"表示上个月
    },
    
    'sanbu': {
        "enable_default_cleaning": True,
        "apply_default_values": True,     # 是否应用默认值填充
    }
}


# Excel处理配置
EXCEL_SHEET_NAME = '业务表'
SHEET_PRIORITY = ['业务表', 'Sheet1']  # sheet选择优先级
BUSINESS_TIME_COLUMN = '业务时间'
BUSINESS_TIME_FORMAT = '%Y年%-m月'

# 日志配置
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# 性能配置
CHUNK_SIZE = 10000  # 大文件分块处理大小
MAX_RETRY_TIMES = 3  # 最大重试次数
RETRY_DELAY = 1  # 重试延迟秒数

# 统计分析配置
STATISTICS_CONFIG = {
    'enabled': True,
    'target_column': None,  # 不使用列名，直接使用字母索引
    'target_column_letter': 'I',  # 直接使用列索引8对应的字母I
    'group_by_column': '编号',  # 优先使用列名
    'group_by_column_letter': 'A',  # 兜底使用字母索引A（索引0）
    'business_time_column': '业务时间',  # 优先使用列名
    'business_time_column_letter': 'P',  # 兜底使用字母索引P（索引15）
    'output_file_path': BASE_DIR / "统计动态表.xlsx", # 更改为相对路径
    'output_sheet_name': '业务表',
    'output_columns': {
        'group_column': 'A',
        'sum_column': 'B',
        'time_column': 'C'
    }
}


# ============================================================================== 
# 辅助函数 (Helper Functions) 
# ============================================================================== 

def get_target_file_name() -> str:
    """
    从目标文件路径中解析文件名
    
    Returns:
        目标文件名
    """
    return Path(TARGET_FILE_PATH).name


def get_source_excel_path() -> Path:
    """
    获取源Excel文件路径的Path对象
    
    Returns:
        源Excel文件路径的Path对象
    """
    return Path(SOURCE_EXCEL_PATH)


def get_processed_folder_path() -> Path:
    """
    获取已处理文件夹路径的Path对象
    
    Returns:
        已处理文件夹路径的Path对象
    """
    return Path(PROCESSED_FOLDER)
