# -*- coding: utf-8 -*-
"""
Fact description stage: Extract basic metadata from images.
Handles series-aware, series-less (noseries), and series-fact-only processing.
"""
from typing import Any, Dict, List, Optional, Tuple

from src.utils.llm_api import invoke_model
from src.core.messages import build_messages_for_task
from src.core.pipeline_utils import fix_or_parse_json, make_meta

__all__ = ["execute_stage"]


def execute_stage(
    image_paths: List[str],
    settings: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    Execute fact description stage.

    Args:
        image_paths: List of image file paths to process
        settings: Pipeline configuration settings
        context: Optional context dict with the following keys:
          - noseries (bool): If True, use fact_description_noseries task
          - series_fact_only (bool): If True, use series task (for A-type series samples)

    Returns:
        (result_json, metadata): Parsed JSON result and execution metadata
    """
    context = context or {}
    noseries = context.get("noseries", False)
    series_fact_only = context.get("series_fact_only", False)

    # 优先级: series_fact_only > noseries > 默认 fact_description
    if series_fact_only:
        task_name = "series"
    elif noseries:
        task_name = "fact_description_noseries"
    else:
        task_name = "fact_description"

    try:
        messages = build_messages_for_task(
            task_name, settings, user_text=None, image_paths=image_paths, as_data_url=True
        )
        raw = invoke_model(
            task_name=task_name,
            messages=messages,
            settings=settings,
            provider_type=settings["tasks"][task_name]["provider_type"],
            temperature=settings["tasks"][task_name].get("temperature"),
            top_p=settings["tasks"][task_name].get("top_p"),
        )
        parsed = fix_or_parse_json(raw)
        if parsed is None:
            meta = make_meta(
                "fact_description",
                settings,
                error="model_output_not_valid_json",
                provider_type=settings["tasks"][task_name]["provider_type"]
            )
            return None, meta

        meta = make_meta(
            "fact_description",
            settings,
            provider_type=settings["tasks"][task_name]["provider_type"]
        )
        return parsed, meta

    except Exception as e:
        meta = make_meta(
            "fact_description",
            settings,
            error=str(e),
            provider_type=settings["tasks"][task_name]["provider_type"]
        )
        return None, meta
