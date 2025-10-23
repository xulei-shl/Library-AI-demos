# -*- coding: utf-8 -*-
"""
No-series processor: handle C type (flat 'b' groups without series consensus).
Encapsulates fact_description, art_style, function_type, and tail correction.
"""
import os
from typing import Any, Dict, List, Tuple

from src.utils.logger import get_logger
from src.core.pipeline_utils import write_json, should_skip_output, make_meta
from src.core.output_formatter import flatten_record_for_excel
from src.core.stages import fact_description, function_type, art_style, correction
from src.core.correction_service import apply_corrections_to_json

logger = get_logger(__name__)


def process_no_series_groups(
    groups: List[Any],
    settings: Dict[str, Any],
    outputs_dir: str,
) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    处理无系列共识的 C 类型（根目录扁平的 b 组）。

    顺序：
      1) fact_description（noseries=True）
      2) art_style
      3) function_type
      4) correction（置于尾部执行，修复原有不可达问题）

    返回:
      (json_paths, excel_records)
    """
    json_paths: List[str] = []
    excel_records: List[Dict[str, str]] = []

    logger.info(f"process_no_series start count={len(groups)} outputs_dir={outputs_dir}")

    for g in groups:
        out_json_path = os.path.join(outputs_dir, f"{g.group_id}.json")
        if should_skip_output(out_json_path, settings):
            logger.info(f"skip_existing id={g.group_id} path={out_json_path}")
            continue

        # Stage 1: Fact description（无系列，统一按 noseries=True 处理）
        fact_json, fact_meta = fact_description.execute_stage(
            g.image_paths, settings, context={"noseries": True}
        )

        if fact_json is None:
            # Stage 1 failed - 记录失败并跳过后续阶段
            fact_json = {}
            fact_json["fact_meta"] = make_meta("fact_description", settings, error="stage1_failed")
            fact_json["id"] = g.group_id
            write_json(out_json_path, fact_json)
            excel_records.append(flatten_record_for_excel(fact_json))
            json_paths.append(out_json_path)
            logger.info(f"fact_failed_saved id={g.group_id} path={out_json_path}")
            continue

        # 基本元信息
        fact_json["id"] = g.group_id
        fact_json["fact_meta"] = fact_meta

        # Stage 1.5: Art style（仅基于图像 + 候选词表约束）
        art_result, art_meta = art_style.execute_stage(
            g.image_paths, settings, context={"use_candidate_vocab": True}
        )
        fact_json["art_style_meta"] = art_meta
        if isinstance(art_result, dict):
            if "art_style" in art_result:
                fact_json["art_style"] = art_result.get("art_style")
            if "art_style_raw" in art_result:
                fact_json["art_style_raw"] = art_result.get("art_style_raw")

        # Stage 2: Function type（使用上一阶段 JSON + 图像 + 候选词表约束）
        type_json, type_meta = function_type.execute_stage(
            g.image_paths, settings, context={
                "previous_json": fact_json,
                "use_candidate_vocab": True
            }
        )
        fact_json["type_meta"] = type_meta
        if isinstance(type_json, dict) and "function_type" in type_json:
            fact_json["function_type"] = type_json.get("function_type")

        # Stage 3: Correction（置于尾部）
        try:
            corr_json, corr_meta = correction.execute_stage(
                g.image_paths, settings, context={"input_json": fact_json}
            )
            fact_json["correction_meta"] = corr_meta
            if isinstance(corr_json, dict):
                try:
                    apply_corrections_to_json(fact_json, corr_json)
                except Exception as e:
                    logger.warning(f"apply_corrections_failed id={g.group_id} err={str(e)[:200]}")
        except Exception as e:
            logger.warning(f"correction_stage_exception id={g.group_id} err={str(e)[:200]}")

        # 写出与汇总
        write_json(out_json_path, fact_json)
        excel_records.append(flatten_record_for_excel(fact_json))
        json_paths.append(out_json_path)
        logger.info(f"object_or_group_saved type={g.group_type} id={g.group_id} path={out_json_path}")

    logger.info(f"process_no_series done written={len(json_paths)}")
    return json_paths, excel_records