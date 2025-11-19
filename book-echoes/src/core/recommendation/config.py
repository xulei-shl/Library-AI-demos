import math
import os
from functools import lru_cache

from src.utils.logger import get_logger
from src.utils.llm.config_loader import ConfigLoader

logger = get_logger(__name__)

MAX_BATCH_SIZE = 20
OTHER_CATEGORY = "Other"
DEFAULT_QUOTA = {
    "gt20": 6,
    "g15_20": 5,
    "g10_15": 4,
    "g5_10": 3,
    "lt5": 2,
}
LLM_CONFIG_PATH = os.getenv("THEME_LLM_CONFIG", "config/llm.yaml")

# 主题内决选配额（每个主题最多晋级几本进入终评）
# 这是代码层的兜底默认值，当配置文件读取失败时使用
THEME_FINALIST_QUOTA = 8




@lru_cache()
def _get_quota_config():
    try:
        loader = ConfigLoader(LLM_CONFIG_PATH)
        settings = loader.load()
        task_cfg = settings.get("tasks", {}).get("theme_initial", {})
        params = task_cfg.get("parameters", {})
        quota = params.get("recommend_quota", {})
        merged = DEFAULT_QUOTA.copy()
        for key, value in quota.items():
            try:
                merged[key] = int(value)
            except (TypeError, ValueError):
                logger.warning("推荐配额配置项 %s=%s 无法解析，使用默认值", key, value)
        return merged
    except Exception as exc:
        logger.warning("加载推荐配额配置失败，使用默认值: %s", exc)
        return DEFAULT_QUOTA

def recommend_quota(group_size: int) -> int:
    quota_cfg = _get_quota_config()
    if group_size > 20:
        return quota_cfg["gt20"]
    if 15 <= group_size <= 20:
        return quota_cfg["g15_20"]
    if 10 <= group_size < 15:
        return quota_cfg["g10_15"]
    if 5 <= group_size < 10:
        return quota_cfg["g5_10"]
    return quota_cfg["lt5"]

def normalize_theme(code: str) -> str:
    if not code:
        return OTHER_CATEGORY
    ch = str(code).strip()[0]
    if ch.isalpha():
        return ch.upper()
    return OTHER_CATEGORY

def even_batches(total: int, max_batch_size: int = MAX_BATCH_SIZE) -> list:
    if total <= 0:
        return []
    num_batches = math.ceil(total / max_batch_size)
    base = total // num_batches
    rem = total % num_batches
    sizes = []
    for i in range(num_batches):
        sizes.append(base + (1 if i < rem else 0))
    return sizes

def get_theme_finalist_quota() -> int:
    """
    从配置文件加载主题决选配额

    优先级：
    1. config/llm.yaml 中的 tasks.theme_runoff.parameters.finalist_quota（可动态修改）
    2. 代码默认值 THEME_FINALIST_QUOTA（配置文件读取失败时的兜底值）

    这种设计的好处：
    - 可通过修改 yaml 文件动态调整配额，无需修改代码
    - 配置文件缺失或格式错误时不会导致程序崩溃
    """
    try:
        loader = ConfigLoader(LLM_CONFIG_PATH)
        settings = loader.load()
        # 从yaml读取，若不存在则使用代码默认值
        quota = settings.get("tasks", {}).get("theme_runoff", {}).get("parameters", {}).get("finalist_quota", THEME_FINALIST_QUOTA)
        return int(quota)
    except Exception as e:
        logger.warning("加载主题决选配额失败，使用默认值 %d: %s", THEME_FINALIST_QUOTA, e)
        return THEME_FINALIST_QUOTA



# 终评目标数量（最终推荐多少本书）
# 这是代码层的兜底默认值，当配置文件读取失败时使用
FINAL_TOP_N = 10

def get_final_top_n() -> int:
    """
    从配置文件加载终评目标数量

    优先级：
    1. config/llm.yaml 中的 tasks.theme_final.parameters.top_n（可动态修改）
    2. 代码默认值 FINAL_TOP_N（配置文件读取失败时的兜底值）

    这种设计的好处：
    - 可通过修改 yaml 文件动态调整终评目标数量，无需修改代码
    - 配置文件缺失或格式错误时不会导致程序崩溃
    """
    try:
        loader = ConfigLoader(LLM_CONFIG_PATH)
        settings = loader.load()
        top_n = settings.get("tasks", {}).get("theme_final", {}).get("parameters", {}).get("top_n", FINAL_TOP_N)
        return int(top_n)
    except Exception as e:
        logger.warning("加载终评目标数量失败，使用默认值 %d: %s", FINAL_TOP_N, e)
        return FINAL_TOP_N

def get_initial_batch_size() -> int:
    """
    从配置文件加载初评阶段的批次大小

    优先级：
    1. config/llm.yaml 中的 tasks.theme_initial.parameters.max_batch_size（可动态修改）
    2. 代码默认值 MAX_BATCH_SIZE（配置文件读取失败时的兜底值）

    这种设计的好处：
    - 可通过修改 yaml 文件动态调整批次大小，无需修改代码
    - 配置文件缺失或格式错误时不会导致程序崩溃
    """
    try:
        loader = ConfigLoader(LLM_CONFIG_PATH)
        settings = loader.load()
        batch_size = settings.get("tasks", {}).get("theme_initial", {}).get("parameters", {}).get("max_batch_size", MAX_BATCH_SIZE)
        return int(batch_size)
    except Exception as e:
        logger.warning("加载初评批次大小失败，使用默认值 %d: %s", MAX_BATCH_SIZE, e)
        return MAX_BATCH_SIZE

def get_final_batch_size() -> int:
    """
    从配置文件加载终评阶段的批次大小

    优先级：
    1. config/llm.yaml 中的 tasks.theme_final.parameters.max_batch_size（可动态修改）
    2. 代码默认值 MAX_BATCH_SIZE（配置文件读取失败时的兜底值）

    这种设计的好处：
    - 可通过修改 yaml 文件动态调整批次大小，无需修改代码
    - 配置文件缺失或格式错误时不会导致程序崩溃
    """
    try:
        loader = ConfigLoader(LLM_CONFIG_PATH)
        settings = loader.load()
        batch_size = settings.get("tasks", {}).get("theme_final", {}).get("parameters", {}).get("max_batch_size", MAX_BATCH_SIZE)
        return int(batch_size)
    except Exception as e:
        logger.warning("加载终评批次大小失败，使用默认值 %d: %s", MAX_BATCH_SIZE, e)
        return MAX_BATCH_SIZE
