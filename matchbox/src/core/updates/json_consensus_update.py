# -*- coding: utf-8 -*-
"""
JSON consensus updater:
- 批量将系列共识字段合并到对象 JSON 和系列样本 JSON
- 实现方案1优化流程：
  1. 先用共识更新系列样本 JSON（4个字段）
  2. 将更新后的系列样本 JSON 合并到对象 JSON 的 series 节点
  3. 再用共识更新对象 JSON 的顶层字段（5个字段）
  这样确保对象的 series 节点包含最新的共识数据
- 不在此模块中生成/读取共识，仅消费由 consensus.manager 提供的共识数据
- A 类型系列样本 JSON 从共识更新 4 个字段：name, manufacturer, country, art_style
"""
import os
import json
from typing import Any, Dict, List, Tuple

from src.utils.logger import get_logger
from src.core.pipeline_utils import (
    merge_series_consensus_into_object,
    merge_series_consensus_into_series_json,
    merge_series_name_into_object,
)

logger = get_logger(__name__)


def _build_group_type_index(series_groups: Dict[str, List[Any]]) -> Dict[str, Dict[str, str]]:
    """
    将 series_groups 索引为 {consensus_path: {group_id: group_type}}，用于类型判断。
    """
    index: Dict[str, Dict[str, str]] = {}
    for cpath, groups in series_groups.items():
        sub: Dict[str, str] = {}
        for g in groups:
            try:
                sub[str(g.group_id)] = str(g.group_type)
            except Exception:
                # 容错：若对象不含期望属性，跳过类型索引
                pass
        index[cpath] = sub
    return index


def update_jsons_with_consensus(
    json_paths_by_consensus: Dict[str, List[str]],
    consensus_by_path: Dict[str, Dict[str, Any]],
    series_groups: Dict[str, List[Any]],
    settings: Dict[str, Any],
) -> Tuple[int, List[str]]:
    """
    批量合并系列共识字段（方案1优化流程）：
      第一阶段：先更新所有系列样本 JSON
      第二阶段：将更新后的系列样本合并到对象，并更新对象顶层字段

      这样确保对象的 series 节点包含最新的共识数据。

    Args:
      json_paths_by_consensus: {consensus_path: [json_file_path, ...]}
      consensus_by_path: {consensus_path: consensus_data}
      series_groups: {consensus_path: [Group, ...]} 用于类型判断与日志
      settings: 管线配置

    Returns:
      (updated_count, updated_paths)
    """
    updated_count = 0
    updated_paths: List[str] = []

    group_type_index = _build_group_type_index(series_groups)

    for consensus_path, json_paths in json_paths_by_consensus.items():
        # 跳过 C 类型（根目录扁平的 b 组，无系列共识）
        if consensus_path == "_no_series_":
            logger.info("skip_update_for_no_series C-type: consensus_path=_no_series_")
            continue

        consensus_data = consensus_by_path.get(consensus_path)
        if not consensus_data:
            logger.warning(f"no_consensus_data_for_series path={consensus_path}")
            continue

        # 获取该系列的所有组（包括 a_series 和 a_object/b）
        series_group_list = series_groups.get(consensus_path, [])

        # 收集系列样本的 JSON 路径（a_series 类型）
        series_json_paths = set()
        series_json_map = {}  # 路径到 JSON 数据的映射
        for g in series_group_list:
            if g.group_type == "a_series" and hasattr(g, "json_path") and g.json_path:
                series_json_paths.add(g.json_path)

        # ========== 第一阶段：先更新所有系列样本 JSON ==========
        for jp in json_paths:
            basename = os.path.basename(jp)
            gid = os.path.splitext(basename)[0]
            is_series_json = jp in series_json_paths or gid.startswith("S_")

            if is_series_json:
                try:
                    with open(jp, "r", encoding="utf-8") as f:
                        json_data = json.load(f)

                    # 更新系列样本的 4 个字段
                    merge_series_consensus_into_series_json(json_data, consensus_data)

                    # 保存更新后的系列样本 JSON
                    with open(jp, "w", encoding="utf-8") as f:
                        json.dump(json_data, f, ensure_ascii=False, indent=2)

                    # 缓存更新后的系列样本数据，供对象合并使用
                    series_json_map[jp] = json_data

                    logger.info(
                        f"series_json_updated_with_consensus path={jp} "
                        f"consensus_path={consensus_path} type=a_series "
                        f"fields=name,manufacturer,country,art_style"
                    )

                    updated_count += 1
                    updated_paths.append(jp)

                except Exception as e:
                    logger.warning(
                        f"update_series_json_failed path={jp} err={str(e)[:200]} consensus_path={consensus_path}"
                    )

        # ========== 第二阶段：更新对象 JSON（合并系列 + 更新顶层字段）==========
        # 找到该系列对应的已更新的系列样本数据
        updated_series_json = None
        if series_json_map:
            # 假设一个系列只有一个系列样本，取第一个
            updated_series_json = next(iter(series_json_map.values()))

        for jp in json_paths:
            basename = os.path.basename(jp)
            gid = os.path.splitext(basename)[0]
            is_series_json = jp in series_json_paths or gid.startswith("S_")

            # 只处理对象 JSON
            if not is_series_json:
                try:
                    with open(jp, "r", encoding="utf-8") as f:
                        json_data = json.load(f)

                    # 判断是否为 a_object（有 series 文件夹）
                    type_index = group_type_index.get(consensus_path) or {}
                    group_type = type_index.get(gid)
                    is_a_object_with_series = (group_type == "a_object") and updated_series_json

                    # 如果是 a_object 且有系列样本，先合并已更新的系列样本数据
                    if is_a_object_with_series:
                        merge_series_name_into_object(json_data, updated_series_json)
                        logger.info(
                            f"merged_updated_series_into_object path={jp} "
                            f"consensus_path={consensus_path}"
                        )

                    # 更新对象 JSON 的顶层 5 个字段（包括 inferred_era 和 series.name）
                    merge_series_consensus_into_object(json_data, consensus_data)

                    # 保存更新后的对象 JSON
                    with open(jp, "w", encoding="utf-8") as f:
                        json.dump(json_data, f, ensure_ascii=False, indent=2)

                    logger.info(
                        f"object_json_updated_with_consensus path={jp} "
                        f"consensus_path={consensus_path} group_type={group_type} "
                        f"fields=manufacturer,country,art_style,inferred_era,series.name"
                    )

                    updated_count += 1
                    updated_paths.append(jp)

                except Exception as e:
                    logger.warning(
                        f"update_object_json_failed path={jp} err={str(e)[:200]} consensus_path={consensus_path}"
                    )

    logger.info(f"consensus_bulk_update_done updated={updated_count}")
    return updated_count, updated_paths