"""
增强版中文日志系统

支持中文级别名称、中文格式、按日期轮转和分级存储。
提供函数调用日志装饰器，便于调试和监控。
"""

import logging
import os
import sys
import time
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler
from typing import Optional, Callable, Any
from pathlib import Path


class ChineseFormatter(logging.Formatter):
    """中文日志格式化器

    特性：
    1. 中文级别名称（调试、信息、警告、错误、严重）
    2. 中文格式模板
    3. 消息截断（避免日志过长）
    4. 自定义时间格式
    """

    # 中文级别映射
    LEVEL_MAP = {
        'DEBUG': '调试',
        'INFO': '信息',
        'WARNING': '警告',
        'ERROR': '错误',
        'CRITICAL': '严重',
        'FATAL': '致命',
    }

    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        # 默认格式：时间 | 级别 | 模块 | 行号 | 函数 | 信息
        if fmt is None:
            fmt = (
                "时间=%(asctime)s | "
                "级别=%(levelname)s | "
                "模块=%(name)s | "
                "行号=%(lineno)d | "
                "函数=%(funcName)s | "
                "信息=%(message)s"
            )

        super().__init__(fmt=fmt, datefmt=datefmt or "%Y-%m-%d %H:%M:%S")

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        # 转换级别名称为中文
        record.levelname = self.LEVEL_MAP.get(record.levelname, record.levelname)

        # 截断过长的消息
        if hasattr(record, 'message'):
            record.message = self._truncate_message(record.getMessage())

        return super().format(record)

    def _truncate_message(self, message: str, max_len: int = 2000) -> str:
        """截断日志消息"""
        if not message or len(message) <= max_len:
            return message

        return (
            message[:max_len] +
            f"...(省略{len(message) - max_len}字符)"
        )


class LoggerManager:
    """日志管理器

    负责初始化和配置全局日志系统。
    """

    _initialized = False

    @staticmethod
    def init(
        logs_dir: str = "runtime/logs",
        level: str = "INFO",
        console_level: str = "INFO",
        file_level: str = "DEBUG",
        backup_count: int = 7,
        max_file_size: int = 50 * 1024 * 1024  # 50MB
    ) -> None:
        """初始化日志系统

        Args:
            logs_dir: 日志目录
            level: 全局日志级别
            console_level: 控制台日志级别
            file_level: 文件日志级别
            backup_count: 保留日志文件数量
            max_file_size: 单个日志文件最大大小
        """
        if LoggerManager._initialized:
            return

        # 创建日志目录
        Path(logs_dir).mkdir(parents=True, exist_ok=True)

        # 配置根Logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

        # 清除现有处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, console_level.upper(), logging.INFO))
        console_handler.setFormatter(ChineseFormatter())
        root_logger.addHandler(console_handler)

        # 普通日志文件处理器（按日期轮转）
        normal_log = TimedRotatingFileHandler(
            filename=os.path.join(logs_dir, "llm.log"),
            when="D",
            interval=1,
            backupCount=backup_count,
            encoding="utf-8",
            utc=False,
        )
        normal_log.setLevel(getattr(logging, file_level.upper(), logging.DEBUG))
        normal_log.setFormatter(ChineseFormatter())
        root_logger.addHandler(normal_log)

        # 错误日志文件处理器（按大小轮转）
        error_log = RotatingFileHandler(
            filename=os.path.join(logs_dir, "error.log"),
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding="utf-8",
        )
        error_log.setLevel(logging.ERROR)
        error_log.setFormatter(ChineseFormatter())
        root_logger.addHandler(error_log)

        # 调试日志文件处理器（仅调试级别）
        debug_log = RotatingFileHandler(
            filename=os.path.join(logs_dir, "debug.log"),
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding="utf-8",
        )
        debug_log.setLevel(logging.DEBUG)
        debug_log.setFormatter(ChineseFormatter())
        root_logger.addHandler(debug_log)

        # 避免日志向上传播
        root_logger.propagate = False

        LoggerManager._initialized = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """获取带中文日志的Logger

    Args:
        name: Logger名称，默认使用调用模块名

    Returns:
        配置好的Logger实例
    """
    if not LoggerManager._initialized:
        # 尝试加载配置
        try:
            from pathlib import Path
            import yaml

            config_path = Path(__file__).resolve().parent.parent / "config" / "settings.yaml"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}

                log_config = config.get("logging", {})
                logs_dir = log_config.get("logs_dir", "runtime/logs")
                console_level = log_config.get("levels", {}).get("console", "INFO")
                file_level = log_config.get("levels", {}).get("file", "DEBUG")

                LoggerManager.init(
                    logs_dir=logs_dir,
                    console_level=console_level,
                    file_level=file_level
                )
            else:
                # 使用默认配置
                LoggerManager.init()
        except Exception:
            # 如果配置加载失败，使用默认配置
            LoggerManager.init()

    # 获取Logger
    if not name:
        import inspect
        frame = inspect.stack()[1]
        name = frame.frame.f_globals.get('__name__', 'unknown')

    return logging.getLogger(name)


def log_function_call(func: Callable) -> Callable:
    """记录函数调用的装饰器

    自动记录函数的调用、参数、返回值和异常信息。
    支持同步和异步函数。

    Args:
        func: 要装饰的函数

    Returns:
        装饰后的函数

    使用示例:
        @log_function_call
        async def my_function(x, y):
            return x + y
    """
    logger = get_logger(func.__module__)

    if not callable(func):
        raise TypeError("func must be a callable")

    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        """异步函数包装器"""
        # 记录调用开始
        args_str = _truncate_args(str(args), 300)
        kwargs_str = _truncate_args(str(kwargs), 300)

        logger.info(
            f"▶ 开始执行函数 | {func.__name__} | "
            f"参数args={args_str} | 参数kwargs={kwargs_str}"
        )

        start_time = time.time()
        try:
            # 执行函数
            result = await func(*args, **kwargs)

            # 记录成功
            duration = time.time() - start_time
            result_str = _truncate_args(str(result), 500)
            logger.info(
                f"✔ 函数执行成功 | {func.__name__} | "
                f"耗时={duration:.3f}秒 | 返回值={result_str}"
            )
            return result

        except Exception as e:
            # 记录异常
            duration = time.time() - start_time
            logger.error(
                f"✖ 函数执行失败 | {func.__name__} | "
                f"耗时={duration:.3f}秒 | "
                f"异常={type(e).__name__}: {str(e)[:200]}"
            )
            raise

    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        """同步函数包装器"""
        # 记录调用开始
        args_str = _truncate_args(str(args), 300)
        kwargs_str = _truncate_args(str(kwargs), 300)

        logger.info(
            f"▶ 开始执行函数 | {func.__name__} | "
            f"参数args={args_str} | 参数kwargs={kwargs_str}"
        )

        start_time = time.time()
        try:
            # 执行函数
            result = func(*args, **kwargs)

            # 记录成功
            duration = time.time() - start_time
            result_str = _truncate_args(str(result), 500)
            logger.info(
                f"✔ 函数执行成功 | {func.__name__} | "
                f"耗时={duration:.3f}秒 | 返回值={result_str}"
            )
            return result

        except Exception as e:
            # 记录异常
            duration = time.time() - start_time
            logger.error(
                f"✖ 函数执行失败 | {func.__name__} | "
                f"耗时={duration:.3f}秒 | "
                f"异常={type(e).__name__}: {str(e)[:200]}"
            )
            raise

    # 检查是否为异步函数
    import inspect
    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def _truncate_args(text: str, max_len: int) -> str:
    """截断参数字符串"""
    if not text or len(text) <= max_len:
        return text

    return text[:max_len] + f"...(省略{len(text) - max_len}字符)"