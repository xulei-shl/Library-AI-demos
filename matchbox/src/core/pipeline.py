# -*- coding: utf-8 -*-
"""
Pipeline orchestration module.
Coordinates multi-stage processing by composing independent stage modules.
"""
import os
import json
from typing import Any, Dict, List, Optional

from src.utils.logger import get_logger
from src.utils.llm_api import load_settings
from src.core.image_grouping import discover_image_groups
from src.core.pipeline_utils import (
    ensure_dir,
    write_json,
    should_skip_output,
    make_meta,
    merge_series_name_into_object,
    read_series_consensus,
    write_series_consensus,
    merge_series_consensus_into_object,
)
from src.core.stages import fact_description, function_type, series, correction, art_style
from src.core.orchestration.no_series_processor import process_no_series_groups
from src.core.orchestration.series_processor import process_series_groups
from src.core.consensus.manager import ensure_consensus_for_series
from src.core.updates.json_consensus_update import update_jsons_with_consensus
from src.utils.json_to_csv import export_json_to_csv

logger = get_logger(__name__)


def run_pipeline(settings: Optional[Dict[str, Any]] = None) -> None:
    """
    Main pipeline orchestration.

    Workflow:
    - Discover and group images (type a/type b, series priority)
    - Group by series and check/generate consensus
    - Execute stages: fact description → art style → function type → correction → series
    - Merge series-level consensus fields into object JSON
    - Output JSON files and CSV summary

    Args:
        settings: Pipeline configuration (loads from file if not provided)
    """
    settings = settings or load_settings()
    input_root = settings.get("paths", {}).get("input_image_dir", "pic")
    outputs_dir = settings.get("paths", {}).get("outputs_dir", "runtime/outputs")
    ensure_dir(outputs_dir)

    groups = discover_image_groups(input_root)
    logger.info(f"pipeline_start input={input_root} outputs={outputs_dir} groups={len(groups)}")

    # Series context storage for merging into object records
    series_ctx_by_object_dir: Dict[str, Dict[str, Any]] = {}
    # Series consensus storage (keyed by consensus file path)
    consensus_by_path: Dict[str, Dict[str, Any]] = {}

    # Group by series for consensus processing
    from collections import defaultdict
    series_groups: Dict[str, List[Any]] = defaultdict(list)

    for g in groups:
        # 按系列分组（通过 consensus file path）
        consensus_path = g.get_consensus_file_path()
        if consensus_path:
            series_groups[consensus_path].append(g)
        else:
            # 没有系列的组（理论上不应该发生）
            series_groups["_no_series_"].append(g)

    # Process each series
    # 新处理流程：先生成每个系列和对象的JSON，记录路径，稍后再统一生成共识并更新
    series_object_json_paths: Dict[str, List[str]] = {}
    for consensus_path, series_group_list in series_groups.items():
        if consensus_path == "_no_series_":
            # 使用专用处理器处理 C 类型（根目录扁平 b 组），在尾部执行 correction
            logger.info(f"process_groups_no_series count={len(series_group_list)}")
            json_paths, _ = process_no_series_groups(series_group_list, settings, outputs_dir)
            series_object_json_paths[consensus_path] = json_paths
            continue

        # 使用专用处理器处理 A/B 类型（生成 JSON，不在此阶段合并共识）
        json_paths_for_series, _, series_ctx = process_series_groups(
            series_group_list, consensus_path, settings, outputs_dir, series_ctx_by_object_dir
        )
        series_object_json_paths[consensus_path] = json_paths_for_series

        # 统一通过共识管理器生成/读取系列共识
        consensus_data = ensure_consensus_for_series(
            series_group_list, consensus_path, settings, series_ctx=series_ctx
        )
        if consensus_data:
            consensus_by_path[consensus_path] = consensus_data

    # 批量合并系列共识字段至对象 JSON
    update_jsons_with_consensus(
        series_object_json_paths, consensus_by_path, series_groups, settings
    )

    # 导出 JSON 到 CSV（分别导出系列和对象）
    series_csv_path = os.path.join(outputs_dir, "series_results.csv")
    object_csv_path = os.path.join(outputs_dir, "object_results.csv")
    series_count, object_count = export_json_to_csv(
        outputs_dir, series_csv_path, object_csv_path
    )
    logger.info(
        f"pipeline_done series_csv={series_csv_path} ({series_count} records), "
        f"object_csv={object_csv_path} ({object_count} records)"
    )


# Allow running as script
if __name__ == "__main__":
    run_pipeline()
