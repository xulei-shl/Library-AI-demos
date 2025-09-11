"""
日志工具模块
提供统一的日志记录功能
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config.settings import LOG_FOLDER, LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT


class Logger:
    """统一日志管理器"""
    
    _instance: Optional['Logger'] = None
    _logger: Optional[logging.Logger] = None
    
    def __new__(cls) -> 'Logger':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._logger is None:
            self._setup_logger()
    
    def _setup_logger(self) -> None:
        """设置日志配置"""
        # 创建日志目录
        log_dir = Path(LOG_FOLDER)
        log_dir.mkdir(exist_ok=True)
        
        # 创建日志文件名（按日期）
        today = datetime.now().strftime('%Y%m%d')
        log_file = log_dir / f'excel_merge_{today}.log'
        
        # 配置日志器
        self._logger = logging.getLogger('ExcelMerge')
        self._logger.setLevel(getattr(logging, LOG_LEVEL.upper()))
        
        # 避免重复添加处理器
        if not self._logger.handlers:
            # 文件处理器
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            
            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # 设置格式
            formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # 添加处理器
            self._logger.addHandler(file_handler)
            self._logger.addHandler(console_handler)
    
    def info(self, message: str) -> None:
        """记录信息日志"""
        self._logger.info(message)
    
    def warning(self, message: str) -> None:
        """记录警告日志"""
        self._logger.warning(message)
    
    def error(self, message: str) -> None:
        """记录错误日志"""
        self._logger.error(message)
    
    def debug(self, message: str) -> None:
        """记录调试日志"""
        self._logger.debug(message)
    
    def exception(self, message: str) -> None:
        """记录异常日志（包含堆栈信息）"""
        self._logger.exception(message)


# 全局日志实例
logger = Logger()