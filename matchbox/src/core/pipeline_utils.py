# -*- coding: utf-8 -*-
"""
Pipeline utility functions for directory operations, JSON handling, and metadata generation.
Extracted from pipeline.py to enable reuse across stage modules.
"""
import os
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.utils.logger import get_logger
from src.utils.json_repair import repair_json_output, is_valid_json

logger = get_logger(__name__)


def ensure_dir(path: str) -> None:
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)


def now_iso() -> str:
    """Return current local time as ISO8601 timestamp."""
    return datetime.now().astimezone().isoformat()


def write_json(path: str, obj: Dict[str, Any]) -> None:
    """Write JSON object to file with UTF-8 encoding."""
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def should_skip_output(out_path: str, settings: Dict[str, Any]) -> bool:
    """Check if output file should be skipped based on overwrite settings."""
    overwrite = bool(settings.get("execution", {}).get("overwrite_existing", False))
    if overwrite:
        return False
    return os.path.exists(out_path)


def fix_or_parse_json(raw: str) -> Optional[Dict[str, Any]]:
    """
    Attempt to repair and parse JSON from LLM output.
    First tries repair (removing ```json markers, trailing text, etc.),
    falls back to direct parsing if valid.
    """
    try:
        fixed = repair_json_output(raw)
        if fixed is not None:
            return fixed
        if is_valid_json(raw):
            return json.loads(raw)
    except Exception as e:
        logger.warning(f"json_parse_failed err={str(e)[:200]}")
    return None


def make_meta(task_type: str, settings: Dict[str, Any], *, error: Optional[str] = None, provider_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate metadata for a pipeline stage execution.
    Records status, timestamp, task type, model, and any errors.
    """
    ptype = provider_type or settings.get("tasks", {}).get(task_type, {}).get("provider_type", "vision")
    prov = (settings.get("api_providers", {}).get(ptype, {}) or {}).get("primary", {}) or {}
    return {
        "status": "fail" if error else "success",
        "executed_at": now_iso(),
        "task_type": task_type,
        "llm_model": prov.get("model") or "unknown",
        "error": (error or None)
    }


def merge_series_name_into_object(obj_json: Dict[str, Any], series_json: Optional[Dict[str, Any]]) -> None:
    """
    Merge series JSON into object JSON's 'series' node.
    If series_json is a dict, place it as-is; otherwise set to None.
    """
    if isinstance(series_json, dict):
        obj_json["series"] = series_json
    else:
        obj_json["series"] = None


def read_series_consensus(consensus_path: str) -> Optional[Dict[str, Any]]:
    """
    读取系列共识文件并验证格式。

    Args:
        consensus_path: 共识文件的完整路径

    Returns:
        共识数据字典，验证失败或文件不存在时返回 None
    """
    if not os.path.exists(consensus_path):
        return None

    try:
        with open(consensus_path, "r", encoding="utf-8") as f:
            consensus = json.load(f)

        # 验证必需字段
        if not isinstance(consensus, dict):
            logger.warning(f"consensus_invalid_format path={consensus_path} reason=not_dict")
            return None

        if "consensus_meta" not in consensus or "consensus_source" not in consensus:
            logger.warning(f"consensus_invalid_format path={consensus_path} reason=missing_required_fields")
            return None

        return consensus

    except Exception as e:
        logger.warning(f"consensus_read_failed path={consensus_path} err={str(e)[:200]}")
        return None


def write_series_consensus(consensus_path: str, consensus_data: Dict[str, Any]) -> bool:
    """
    写入系列共识文件。

    Args:
        consensus_path: 共识文件的完整路径
        consensus_data: 要写入的共识数据

    Returns:
        写入是否成功
    """
    try:
        ensure_dir(os.path.dirname(consensus_path))
        with open(consensus_path, "w", encoding="utf-8") as f:
            json.dump(consensus_data, f, ensure_ascii=False, indent=2)
        logger.info(f"consensus_written path={consensus_path}")
        return True
    except Exception as e:
        logger.warning(f"consensus_write_failed path={consensus_path} err={str(e)[:200]}")
        return False


def merge_series_consensus_into_series_json(series_json: Dict[str, Any], consensus: Dict[str, Any]) -> None:
    """
    将系列共识字段合并到系列样本 JSON 中。
    系列样本只更新以下字段（不包括 inferred_era）：
      - name ← consensus.series_name
      - manufacturer ← consensus.manufacturer
      - country ← consensus.country
      - art_style ← consensus.art_style

    Args:
        series_json: 系列样本 JSON（会被就地修改）
        consensus: 共识数据字典
    """
    # 系列样本的字段映射（不包括 inferred_era）
    field_mapping = {
        "series_name": "name",  # 共识中的 series_name 对应系列样本的 name
        "manufacturer": "manufacturer",
        "country": "country",
        "art_style": "art_style",
    }

    for consensus_field, series_field in field_mapping.items():
        if consensus_field in consensus:
            value = consensus[consensus_field]
            if value is not None:  # 只有非空值才更新
                series_json[series_field] = value


def merge_series_consensus_into_object(obj_json: Dict[str, Any], consensus: Dict[str, Any]) -> None:
    """
    将系列共识的系列级字段合并到对象 JSON 中。
    系列级字段：series_name, manufacturer, country, art_style, inferred_era

    Args:
        obj_json: 对象 JSON（会被就地修改）
        consensus: 共识数据字典
    """
    # 系列级字段列表（包括 inferred_era）
    series_level_fields = ["manufacturer", "country", "art_style", "inferred_era"]

    # 合并顶层系列级字段
    for field in series_level_fields:
        if field in consensus:
            obj_json[field] = consensus[field]

    # 处理 series_name（可能在 consensus 的顶层）
    # 仅当共识给出非空的 series_name 时才写入，避免生成空的 {} 节点
    if "series_name" in consensus:
        series_name_val = consensus["series_name"]
        if series_name_val is not None:
            if "series" not in obj_json or obj_json["series"] is None:
                obj_json["series"] = {}
            if isinstance(obj_json["series"], dict):
                obj_json["series"]["name"] = series_name_val
