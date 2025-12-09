"""
日志配置模块
"""
import logging
import os
from datetime import datetime
from pathlib import Path


class LoggerConfig:
    """日志配置类"""

    def __init__(self, log_dir: str = "logs", log_level: str = "INFO"):
        self.log_dir = Path(log_dir)
        self.log_level = getattr(logging, log_level.upper())
        self._setup_log_dir()

    def _setup_log_dir(self):
        """创建日志目录"""
        if not self.log_dir.exists():
            self.log_dir.mkdir(parents=True)

    def setup_logger(self, name: str = __name__) -> logging.Logger:
        """
        设置日志记录器
        Args:
            name: 日志记录器名称
        Returns:
            配置好的日志记录器
        """
        logger = logging.getLogger(name)
        logger.setLevel(self.log_level)

        # 避免重复添加处理器
        if logger.handlers:
            return logger

        # 创建格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 创建文件处理器
        log_file = self.log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        return logger

    @staticmethod
    def setup_root_logger(log_level: str = "INFO"):
        """设置根日志记录器"""
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


# 便捷函数
def get_logger(name: str, log_dir: str = "logs", log_level: str = "INFO") -> logging.Logger:
    """
    获取配置好的日志记录器
    Args:
        name: 日志记录器名称
        log_dir: 日志目录
        log_level: 日志级别
    Returns:
        日志记录器
    """
    config = LoggerConfig(log_dir, log_level)
    return config.setup_logger(name)