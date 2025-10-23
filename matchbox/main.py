# -*- coding: utf-8 -*-
"""
主入口：视觉大模型图像描述项目
流程：
1. 初始化日志
2. 加载 settings.yaml
3. 调用管道执行分阶段任务
"""

import sys
from src.utils.logger import init_logging, get_logger
from src.utils.llm_api import load_settings
from src.core.pipeline import run_pipeline

def main():
    # 预先加载 .env 环境变量（若存在）
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=".env", override=False)
    except Exception:
        # 若未安装 python-dotenv 或加载失败，不影响后续流程
        pass

    # 初始化日志
    from src.utils.llm_api import load_settings as _load_settings_for_logger
    try:
        _settings_for_logger = _load_settings_for_logger()
        logs_dir = _settings_for_logger.get("paths", {}).get("logs_dir")
        log_level = _settings_for_logger.get("logging", {}).get("level")
        init_logging(runtime_dir=logs_dir, level=getattr(__import__("logging"), str(log_level).upper(), None))
    except Exception:
        init_logging()
    logger = get_logger(__name__)
    logger.info("main_start")

    try:
        settings = load_settings()
    except Exception as e:
        logger.error(f"load_settings_failed err={str(e)}")
        sys.exit(1)

    run_pipeline(settings)
    logger.info("main_done")

if __name__ == "__main__":
    main()