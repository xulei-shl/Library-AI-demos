"""
配置加载模块
"""

import yaml
from pathlib import Path
from typing import Dict, Any


def load_config() -> Dict[str, Any]:
    """
    加载文学检索配置文件

    Returns:
        配置字典
    """
    # 配置文件路径：项目根目录/config/literature_fm_vector.yaml
    # 从 literaturefm-api/config.py 到项目根需要向上5级：
    # config.py -> literaturefm-api -> literature_fm -> core -> src -> book-echoes
    root_dir = Path(__file__).parent.parent.parent.parent.parent
    config_path = root_dir / "config" / "literature_fm_vector.yaml"

    if not config_path.exists():
        # 如果配置文件不存在，返回默认配置
        return get_default_config()

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f) or {}

    # 将相对路径转换为绝对路径
    config = _resolve_paths(config, root_dir)
    return config


def _resolve_paths(config: Dict[str, Any], root_dir: Path) -> Dict[str, Any]:
    """
    将配置中的相对路径转换为绝对路径

    Args:
        config: 原始配置
        root_dir: 项目根目录

    Returns:
        路径解析后的配置
    """
    # 解析数据库路径
    if 'database' in config and 'path' in config['database']:
        db_path = config['database']['path']
        if not Path(db_path).is_absolute():
            config['database']['path'] = str(root_dir / db_path)

    # 解析向量数据库路径
    if 'vector_db' in config and 'persist_directory' in config['vector_db']:
        persist_dir = config['vector_db']['persist_directory']
        if not Path(persist_dir).is_absolute():
            config['vector_db']['persist_directory'] = str(root_dir / persist_dir)

    return config


def get_default_config() -> Dict[str, Any]:
    """
    获取默认配置

    Returns:
        默认配置字典
    """
    return {
        "database": {
            "path": "runtime/database/books_history.db",
            "table": "literary_tags"
        },
        "vector_db": {
            "type": "chromadb",
            "persist_directory": "runtime/vector_db/literature_fm",
            "collection_name": "literature_fm_contexts",
            "distance_metric": "cosine"
        },
        "embedding": {
            "provider": "SiliconFlow",
            "model": "BAAI/bge-m3",
            "dimensions": 4096
        },
        "bm25": {
            "enabled": True,
            "k1": 1.5,
            "b": 0.75,
            "field_weights": {
                "title": 2.0,
                "author": 1.0,
                "summary": 1.5
            },
            "randomness": 0.15,
            "score_threshold": None
        },
        "rrf": {
            "k": 60
        },
        "reranker": {
            "enabled": False,
            "model": "BAAI/bge-reranker-v2-m3",
            "top_k": 50,
            "batch_size": 32
        },
        "default": {
            "use_vector": True,
            "use_bm25": True,
            "use_rrf": True,
            "min_confidence": 0.80,
            "vector_top_k": 50,
            "bm25_top_k": 50,
            "final_top_k": 30
        }
    }
