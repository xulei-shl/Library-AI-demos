#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理器

负责管理应用配置，支持：
1. YAML主配置文件读取
2. 环境变量支持
3. .env文件支持
4. 敏感信息的安全管理
5. 统计模块配置
6. 路径配置

"""

import os
import sys
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv(path: str):
        return False
import logging

# 添加项目路径
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, 
                 config_file: str = "config/setting.yaml",
                 env_file: str = "config/.env"):
        """
        初始化配置管理器
        
        Args:
            config_file: YAML配置文件路径
            env_file: .env文件路径
        """
        self.config_file = config_file
        self.env_file = env_file
        self.config = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        # 1. 加载.env文件
        if os.path.exists(self.env_file):
            load_dotenv(self.env_file)
            logger.info(f"已加载环境变量文件: {self.env_file}")
        else:
            logger.info(f"环境变量文件不存在: {self.env_file}")
        
        # 2. 加载YAML配置文件
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f) or {}
                logger.info(f"已加载主配置文件: {self.config_file}")
            except Exception as e:
                logger.error(f"加载配置文件失败: {str(e)}")
                self.config = self._get_default_config()
        else:
            logger.warning(f"主配置文件不存在: {self.config_file}")
            self.config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "paths": {
                "outputs_dir": "runtime/outputs",
                "logs_dir": "runtime/logs",
                "excel_files": {
                    "monthly_return_file": "data/月归还.xlsx",
                    "recent_three_months_borrowing_file": "data/近三月借阅.xlsx"
                }
            },
            "statistics": {
                "target_month": "2025-09",
                "month_calculation": {
                    "use_target_month_previous": True
                }
            },
            "douban": {
                "isbn_resolver": {
                    "enabled": True,
                    "base_url": "https://circ-folio.library.sh.cn/shlcirculation-query/literatureHistory",
                    "timeout": 30,
                    "delay": 2.0,
                    "username_env_var": "FOLIO_USERNAME",
                    "password_env_var": "FOLIO_PASSWORD"
                },
                "general": {
                    "max_retry": 3,
                    "log_level": "INFO",
                    "backup_enabled": True,
                    "backup_interval": 24
                }
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点号分隔的层级，如 'douban.isbn_resolver.timeout'
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            
            # 如果是字符串，检查是否需要从环境变量读取
            if isinstance(value, str) and value.endswith('_env_var'):
                env_var = value
                env_value = os.getenv(env_var)
                if env_value:
                    logger.debug(f"从环境变量获取配置 {env_var}: {'*' * len(env_value)}")
                    return env_value
                else:
                    logger.warning(f"环境变量 {env_var} 未设置，使用默认值")
                    return default
            
            return value
            
        except (KeyError, TypeError):
            return default
    
    def get_secure(self, key: str, env_var: str, default: str = None) -> str:
        """
        安全获取敏感配置（从环境变量读取）
        
        Args:
            key: 配置键
            env_var: 环境变量名
            default: 默认值
            
        Returns:
            敏感配置值
        """
        value = os.getenv(env_var)
        if value:
            logger.debug(f"安全读取配置 {key}: {'*' * len(value)}")
            return value
        else:
            logger.warning(f"环境变量 {env_var} 未设置")
            return default
    
    def get_douban_config(self) -> Dict[str, Any]:
        """获取豆瓣模块配置"""
        douban_config = self.get('douban', {})
        
        # 安全获取敏感配置
        username = self.get_secure(
            'douban.username', 
            douban_config.get('isbn_resolver', {}).get('username_env_var', 'FOLIO_USERNAME'),
            'sl_dczx01'  # 向后兼容的默认值
        )
        
        password = self.get_secure(
            'douban.password',
            douban_config.get('isbn_resolver', {}).get('password_env_var', 'FOLIO_PASSWORD'),
            'LTcx@01'  # 向后兼容的默认值
        )
        
        # 返回完整的配置
        config = douban_config.copy()
        if 'isbn_resolver' not in config:
            config['isbn_resolver'] = {}
        if 'general' not in config:
            config['general'] = {}
        
        # 设置敏感值
        config['isbn_resolver']['username'] = username
        config['isbn_resolver']['password'] = password
        
        return config
    
    def get_douban_crawler_config(self) -> Dict[str, Any]:
        """获取豆瓣爬虫配置（豆瓣评分处理器专用）

        Returns:
            豆瓣爬虫配置字典
        """
        config = self.get('douban', {})

        # 确保包含豆瓣爬虫配置
        crawler_config = config.get('douban_crawler', {
            'enabled': True,
            'base_url': 'https://book.douban.com',
            'headless': False,
            'delay': 1.0,
            'login': {
                'auto_login': False,
                'timeout': 30
            },
            'crawl': {
                'retry_times': 3,
                'timeout': 15,
                'enable_stealth': True
            },
            'save_interval': 10
        })

        # 安全获取豆瓣账号密码
        crawler_config.setdefault('login', {})
        crawler_config['login']['username'] = self.get_secure(
            'douban.login.username',
            'DOUBAN_USERNAME',
            ''
        )
        crawler_config['login']['password'] = self.get_secure(
            'douban.login.password',
            'DOUBAN_PASSWORD',
            ''
        )

        # 获取FOLIO系统配置
        isbn_resolver = config.get('isbn_resolver', {})
        crawler_config['isbn_resolver'] = {
            'username': isbn_resolver.get('username'),
            'password': isbn_resolver.get('password'),
            'base_url': isbn_resolver.get('base_url'),
            'timeout': isbn_resolver.get('timeout', 30)
        }

        return crawler_config

    def get_statistics_config(self) -> Dict[str, Any]:
        """获取统计相关配置"""
        return {
            'target_month': self.get('statistics.target_month', '2025-09'),
            'use_target_month_previous': self.get('statistics.month_calculation.use_target_month_previous', True)
        }
    
    def get_config(self) -> Dict[str, Any]:
        """获取完整配置"""
        return self.config.copy()

    def reload_config(self):
        """重新加载配置"""
        self._load_config()
        logger.info("配置已重新加载")
    
    def is_douban_enabled(self) -> bool:
        """检查豆瓣模块是否启用"""
        return self.get('douban.isbn_resolver.enabled', True)
    
    def get_output_dir(self) -> str:
        """获取输出目录"""
        return self.get('paths.outputs_dir', 'runtime/outputs')
    
    def get_logs_dir(self) -> str:
        """获取日志目录"""
        return self.get('paths.logs_dir', 'runtime/logs')


# 全局配置管理器实例
_config_manager = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config(key: str, default: Any = None) -> Any:
    """便捷的全局配置获取函数"""
    return get_config_manager().get(key, default)


def get_douban_config() -> Dict[str, Any]:
    """便捷的豆瓣配置获取函数"""
    return get_config_manager().get_douban_config()


def get_statistics_config() -> Dict[str, Any]:
    """
    便捷函数：获取统计配置
    
    Returns:
        Dict: 统计配置字典
    """
    return get_config_manager().get_statistics_config()

def get_douban_config() -> Dict[str, Any]:
    """便捷的豆瓣配置获取函数"""
    return get_config_manager().get_douban_config()


def get_douban_crawler_config() -> Dict[str, Any]:
    """便捷的豆瓣爬虫配置获取函数"""
    return get_config_manager().get_douban_crawler_config()





def get_paths_config() -> Dict[str, str]:
    """
    便捷函数：获取路径配置
    
    Returns:
        Dict: 路径配置字典
    """
    return get_config_manager().get_paths_config()


def reload_config():
    """便捷的配置重载函数"""
    get_config_manager().reload_config()


# 向后兼容的全局配置实例（为了兼容原有代码）
class _GlobalConfig:
    """全局配置实例 - 用于向后兼容"""
    
    def __init__(self):
        self._config = get_config_manager()
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self._config.get(key, default)
    
    def get_statistics_config(self) -> Dict[str, Any]:
        """获取统计相关配置"""
        return self._config.get_statistics_config()
    
    def get_paths_config(self) -> Dict[str, str]:
        """获取路径相关配置"""
        return self._config.get_paths_config()


# 为了向后兼容，提供全局config实例
config = _GlobalConfig()


if __name__ == "__main__":
    # 测试配置管理器
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 创建配置管理器实例
    config_manager = ConfigManager()
    
    # 测试配置读取
    print("=== 配置管理器测试 ===")
    print(f"输出目录: {config_manager.get('paths.outputs_dir')}")
    print(f"豆瓣模块启用状态: {config_manager.is_douban_enabled()}")
    print(f"ISBN解析器基础URL: {config_manager.get('douban.isbn_resolver.base_url')}")
    
    # 测试豆瓣配置
    douban_config = config_manager.get_douban_config()
    print(f"\n豆瓣配置: {douban_config}")
    
    # 测试统计配置
    stats_config = config_manager.get_statistics_config()
    print(f"\n统计配置: {stats_config}")
    
    # 测试路径配置
    paths_config = config_manager.get_config().get('paths', {})
    print(f"\n路径配置: {paths_config}")
    
    # 测试敏感信息读取
    username = config_manager.get_secure('douban.username', 'FOLIO_USERNAME', 'default_user')
    password = config_manager.get_secure('douban.password', 'FOLIO_PASSWORD', 'default_pass')
    print(f"\n敏感信息测试:")
    print(f"用户名: {username}")
    print(f"密码: {password}")
    