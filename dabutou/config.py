"""
配置文件
"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent

# 默认配置
DEFAULT_CONFIG = {
    # 日志配置
    'log_dir': BASE_DIR / 'logs',
    'log_level': 'INFO',

    # Excel配置
    'excel': {
        'isbn_col': 'ISBN',
        'title_col': '题名',
        'sheet_name': 0,
        'real_time_save': True,
        'backup_enabled': True,
        'library_columns_prefix': '图书馆_'
    },

    # CiNii爬虫配置
    'cinii': {
        'base_url': 'https://ci.nii.ac.jp',
        'timeout': 30,
        'delay': 2,  # 请求间隔（秒）
        'max_retries': 3,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    },

    # 其他网站爬虫配置（预留）
    'other_sites': {
        # 可以在这里添加其他网站的配置
    }
}

# 环境变量配置
def get_config_from_env():
    """从环境变量获取配置"""
    config = {}

    # 日志配置
    if os.getenv('LOG_DIR'):
        config['log_dir'] = Path(os.getenv('LOG_DIR'))
    if os.getenv('LOG_LEVEL'):
        config['log_level'] = os.getenv('LOG_LEVEL')

    return config

# 合并配置
def get_config():
    """获取最终配置"""
    config = DEFAULT_CONFIG.copy()
    config.update(get_config_from_env())
    return config