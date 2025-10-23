# -*- coding: utf-8 -*-
"""
Consensus manager:
- 统一读取/生成系列共识并执行写入
- 基于新的 series_consensus 逻辑：
  - 从 series JSON 和对象 JSON 中提取字段
  - 调用 series_consensus.execute_stage 生成共识
  - 将共识文件保存到指定路径
- 不在此模块之外写文件，外部请仅调用本模块公开函数
"""
import os
import json
from typing import Any, Dict, List, Optional

from src.utils.logger import get_logger
from src.utils.llm_api import load_settings
from src.core.pipeline_utils import read_series_consensus
from src.core.stages import series_consensus

logger = get_logger(__name__)


def _get_series_json_path(series_group_list: List[Any]) -> Optional[str]:
    """
    从系列组列表中获取 series JSON 文件路径（仅 A 类型系列）。

    Args:
        series_group_list: 系列组列表

    Returns:
        series JSON 路径，如果没有则返回 None
    """
    for g in series_group_list:
        if g.group_type == "a_series" and hasattr(g, "json_path"):
            json_path = g.json_path
            if json_path and os.path.exists(json_path):
                return json_path
    return None


def _get_object_json_paths(series_group_list: List[Any], max_count: int = 3) -> List[str]:
    """
    从系列组列表中获取对象 JSON 文件路径（最多 max_count 个）。

    Args:
        series_group_list: 系列组列表
        max_count: 最多获取的对象数量

    Returns:
        对象 JSON 路径列表
    """
    object_json_paths = []
    for g in series_group_list:
        if g.group_type in ("a_object", "b") and hasattr(g, "json_path"):
            json_path = g.json_path
            if json_path and os.path.exists(json_path):
                object_json_paths.append(json_path)
                if len(object_json_paths) >= max_count:
                    break
    return object_json_paths


def _determine_series_type(series_group_list: List[Any]) -> str:
    """
    判断系列类型：A 或 B。

    Args:
        series_group_list: 系列组列表

    Returns:
        "A" 或 "B"
    """
    for g in series_group_list:
        if g.group_type == "a_series":
            return "A"
    return "B"


def ensure_consensus_for_series(
    series_group_list: List[Any],
    consensus_path: str,
    settings: Optional[Dict[str, Any]] = None,
    *,
    series_ctx: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    读取或生成指定系列的共识文件并写入磁盘。

    策略：
      - 若 force_recalculate=False 且已有有效共识文件，则直接返回
      - 否则从 series JSON（A 类型）和对象 JSON 中提取数据
      - 调用 series_consensus.execute_stage 生成共识
      - 共识文件由 execute_stage 内部保存

    Args:
        series_group_list: 系列组列表
        consensus_path: 共识文件路径
        settings: 配置字典
        series_ctx: 系列上下文（可选）

    Returns:
        共识数据字典，失败时返回 None
    """
    settings = settings or load_settings()

    # 读已存在共识
    force_recalc = bool(settings.get("series_consensus", {}).get("force_recalculate", False))
    if not force_recalc:
        existing = read_series_consensus(consensus_path)
        if existing:
            logger.info(f"consensus_found path={consensus_path}")
            return existing

    # 判断系列类型
    series_type = _determine_series_type(series_group_list)

    # 获取 series JSON 路径（仅 A 类型）
    series_json_path = None
    if series_type == "A":
        series_json_path = _get_series_json_path(series_group_list)

    # 获取对象 JSON 路径（最多 3 个）
    object_json_paths = _get_object_json_paths(series_group_list, max_count=3)

    # 如果没有对象数据，检查是否允许仅从 series 生成
    if not object_json_paths:
        generate_even_without_objects = bool(
            settings.get("series_consensus", {}).get("generate_even_without_objects", True)
        )

        if not generate_even_without_objects or not series_json_path:
            logger.info(
                f"consensus_skipped_no_objects path={consensus_path} "
                f"series_type={series_type} has_series_json={series_json_path is not None}"
            )
            return None

    # 构建 context 传递给 execute_stage
    context = {
        "series_json_path": series_json_path,
        "object_json_paths": object_json_paths,
        "consensus_output_path": consensus_path,
        "series_type": series_type,
    }

    # 调用 series_consensus.execute_stage 生成共识
    try:
        consensus_data, meta = series_consensus.execute_stage(
            image_paths=[],  # series_consensus 不使用图像
            settings=settings,
            context=context
        )

        if consensus_data is None:
            logger.warning(f"consensus_generation_failed path={consensus_path}")
            return None

        logger.info(
            f"consensus_generated path={consensus_path} "
            f"strategy={meta.get('consensus_strategy', 'unknown')}"
        )
        return consensus_data

    except Exception as e:
        logger.warning(f"consensus_generation_exception path={consensus_path} err={str(e)[:200]}")
        return None
