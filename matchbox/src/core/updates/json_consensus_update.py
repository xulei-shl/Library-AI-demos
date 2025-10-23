# -*- coding: utf-8 -*-
"""
JSON consensus updater:
- 批量将系列共识字段合并到对象 JSON 和系列样本 JSON
- 统一异常与日志处理，复用 merge_series_consensus_into_object 和 merge_series_consensus_into_series_json
- 不在此模块中生成/读取共识，仅消费由 consensus.manager 提供的共识数据
- 按类型规则执行校正：
  - A/B 类型不在此阶段执行 correction（遵循设计解耦）
  - C 类型的 correction 已在 no_series_processor 尾部执行，此模块不重复执行
- A 类型系列样本 JSON 从共识更新 4 个字段：name, manufacturer, country, art_style
"""
import os
import json
from typing import Any, Dict, List, Tuple

from src.utils.logger import get_logger
from src.core.pipeline_utils import (
    merge_series_consensus_into_object,
    merge_series_consensus_into_series_json,
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
    批量合并系列共识字段：
      - 对每个系列（consensus_path != "_no_series_"），逐文件合并系列级字段
      - A 类型系列样本（以 S_ 开头）：使用 merge_series_consensus_into_series_json 更新 4 个字段
      - 对象 JSON：使用 merge_series_consensus_into_object 更新 5 个字段（包括 inferred_era）
      - A/B 类型不在此阶段执行 correction
      - C 类型不参与此函数（其共识为空；correction 已在 no_series_processor 尾部执行）

    Args:
      json_paths_by_consensus: {consensus_path: [json_file_path, ...]}
      consensus_by_path: {consensus_path: consensus_data}
      series_groups: {consensus_path: [Group, ...]} 用于类型判断与日志
      settings: 管线配置（当前函数不读取/生成共识，仅用于日志策略）

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
        for g in series_group_list:
            if g.group_type == "a_series" and hasattr(g, "json_path") and g.json_path:
                series_json_paths.add(g.json_path)

        # 合并系列级字段
        for jp in json_paths:
            try:
                basename = os.path.basename(jp)
                gid = os.path.splitext(basename)[0]

                # 判断是否为系列样本 JSON
                is_series_json = jp in series_json_paths or gid.startswith("S_")

                with open(jp, "r", encoding="utf-8") as f:
                    json_data = json.load(f)

                if is_series_json:
                    # A 类型系列样本：更新 4 个字段（不包括 inferred_era）
                    merge_series_consensus_into_series_json(json_data, consensus_data)
                    logger.info(
                        f"series_json_updated_with_consensus path={jp} "
                        f"consensus_path={consensus_path} type=a_series "
                        f"fields=name,manufacturer,country,art_style"
                    )
                else:
                    # 对象 JSON：更新 5 个字段（包括 inferred_era）
                    merge_series_consensus_into_object(json_data, consensus_data)

                    # 记录类型信息（仅用于日志）
                    group_type = None
                    type_index = group_type_index.get(consensus_path) or {}
                    group_type = type_index.get(gid)
                    logger.info(
                        f"object_json_updated_with_consensus path={jp} "
                        f"consensus_path={consensus_path} group_type={group_type}"
                    )

                # 保存更新后的 JSON
                with open(jp, "w", encoding="utf-8") as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)

                updated_count += 1
                updated_paths.append(jp)

            except Exception as e:
                logger.warning(
                    f"update_json_with_consensus_failed path={jp} err={str(e)[:200]} consensus_path={consensus_path}"
                )

    logger.info(f"consensus_bulk_update_done updated={updated_count}")
    return updated_count, updated_paths