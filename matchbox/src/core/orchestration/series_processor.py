# -*- coding: utf-8 -*-
"""
Series processor: handle A/B type groups.
负责系列样本执行（a_series）和对象组 JSON 生成。
不在此阶段合并系列信息，所有共识合并逻辑在 json_consensus_update 中统一处理。
"""
import os
import json
from typing import Any, Dict, List, Tuple

from src.utils.logger import get_logger
from src.core.pipeline_utils import write_json, should_skip_output, merge_series_name_into_object, make_meta
from src.core.output_formatter import flatten_record_for_excel
from src.core.stages import fact_description, function_type, art_style, series

logger = get_logger(__name__)


def process_series_groups(
    series_group_list: List[Any],
    consensus_path: str,
    settings: Dict[str, Any],
    outputs_dir: str,
    series_ctx_by_object_dir: Dict[str, Dict[str, Any]],
) -> Tuple[List[str], List[Dict[str, str]], Dict[str, Any]]:
    """
    处理 A/B 类型的组：
      1) a_series 样本生成 JSON（不做共识更新）
      2) 对象组生成 JSON（不合并系列信息，不做共识更新）
      3) 所有共识合并操作在 json_consensus_update 中统一处理

    返回:
      (json_paths_for_series, excel_records, series_ctx)
    """
    a_series_groups = [g for g in series_group_list if g.group_type == "a_series"]
    object_groups = [g for g in series_group_list if g.group_type in ("a_object", "b")]

    series_ctx = None
    excel_records: List[Dict[str, str]] = []
    json_paths_for_series: List[str] = []

    # 先处理 a_series
    for g in a_series_groups:
        out_json_path = os.path.join(outputs_dir, f"{g.group_id}.json")
        if should_skip_output(out_json_path, settings):
            logger.info(f"skip_existing id={g.group_id} path={out_json_path}")
            try:
                with open(out_json_path, "r", encoding="utf-8") as f:
                    existing_series = json.load(f)
                series_ctx_by_object_dir[g.object_dir or ""] = existing_series
                series_ctx = existing_series
                # 设置 json_path 以便共识生成时使用
                g.json_path = out_json_path
            except Exception:
                pass
            continue

        # 重构：拆分 fact_description + art_style 两步调用并合并
        fact_json, fact_meta = fact_description.execute_stage(
            g.image_paths, settings, context={"noseries": False, "series_fact_only": True}
        )
        if fact_json is None:
            fact_json = {"name": None}
            fact_meta = make_meta("fact_description", settings, error="series_fact_stage_failed")

        art_json, art_meta = art_style.execute_stage(
            g.image_paths, settings, context={"use_candidate_vocab": True}
        )
        if art_json is None:
            art_json = {}
            art_meta = make_meta("art_style", settings, error="series_art_stage_failed")

        # 合并结果
        series_json = {**fact_json, **art_json}
        series_json["series_meta"] = {"fact": fact_meta, "art": art_meta}
        series_json["id"] = g.group_id

        write_json(out_json_path, series_json)
        series_ctx_by_object_dir[g.object_dir or ""] = series_json
        series_ctx = series_json
        # 设置 json_path 以便共识生成时使用
        g.json_path = out_json_path
        excel_records.append(flatten_record_for_excel(series_json))
        logger.info(f"series_saved id={g.group_id} path={out_json_path}")

    # 对象组处理
    for g in object_groups:
        out_json_path = os.path.join(outputs_dir, f"{g.group_id}.json")
        if should_skip_output(out_json_path, settings):
            logger.info(f"skip_existing id={g.group_id} path={out_json_path}")
            # 设置 json_path 以便共识生成时使用
            g.json_path = out_json_path
            continue

        # 判断是否需要识别系列信息:
        # - 有 series 子文件夹的 a_object: noseries=True (系列名已从 series 样本提取)
        # - 无 series 子文件夹的 a_object/b: noseries=False (需要从对象自己识别系列名)
        has_series_folder = g.series_dir is not None
        use_noseries = g.group_type == "a_object" and has_series_folder

        fact_json, fact_meta = fact_description.execute_stage(
            g.image_paths, settings, context={"noseries": use_noseries}
        )

        if fact_json is None:
            fact_json = {}
            fact_json["fact_meta"] = make_meta("fact_description", settings, error="stage1_failed")
            # 系列信息将在共识更新阶段合并，这里不再提前合并
            fact_json["id"] = g.group_id
            write_json(out_json_path, fact_json)
            # 设置 json_path 以便共识生成时使用
            g.json_path = out_json_path
            excel_records.append(flatten_record_for_excel(fact_json))
            logger.info(f"fact_failed_saved id={g.group_id} path={out_json_path}")
            continue

        fact_json["id"] = g.group_id
        fact_json["fact_meta"] = fact_meta

        art_result, art_meta = art_style.execute_stage(
            g.image_paths, settings, context={"use_candidate_vocab": True}
        )
        fact_json["art_style_meta"] = art_meta
        if isinstance(art_result, dict):
            if "art_style" in art_result:
                fact_json["art_style"] = art_result.get("art_style")
            if "art_style_raw" in art_result:
                fact_json["art_style_raw"] = art_result.get("art_style_raw")

        type_json, type_meta = function_type.execute_stage(
            g.image_paths, settings, context={
                "previous_json": fact_json,
                "use_candidate_vocab": True
            }
        )
        fact_json["type_meta"] = type_meta
        if isinstance(type_json, dict) and "function_type" in type_json:
            fact_json["function_type"] = type_json.get("function_type")

        # 系列信息将在共识更新阶段统一合并，不再在此处提前合并
        # 这样可以确保合并的是已经被共识更新过的最新系列数据

        write_json(out_json_path, fact_json)
        # 设置 json_path 以便共识生成时使用
        g.json_path = out_json_path
        excel_records.append(flatten_record_for_excel(fact_json))
        logger.info(f"object_or_group_saved type={g.group_type} id={g.group_id} path={out_json_path}")

    # 返回所有 JSON 路径（包括系列样本和对象组）
    # 系列样本的 JSON 会在共识更新阶段被 merge_series_consensus_into_series_json 更新 4 个字段
    # 对象组的 JSON 会在共识更新阶段：
    #   1. 合并已更新的系列样本 JSON（如果是 a_object）
    #   2. 被 merge_series_consensus_into_object 更新顶层 5 个字段
    all_json_paths = []
    # 添加系列样本的 JSON 路径
    for g in a_series_groups:
        json_path = os.path.join(outputs_dir, f"{g.group_id}.json")
        if os.path.exists(json_path):
            all_json_paths.append(json_path)
    # 添加对象组的 JSON 路径
    all_json_paths.extend(
        [os.path.join(outputs_dir, f"{g.group_id}.json") for g in object_groups]
    )

    return all_json_paths, excel_records, series_ctx