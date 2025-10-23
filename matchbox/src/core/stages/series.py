# -*- coding: utf-8 -*-
"""
Series analysis stage: Extract series information from series sample images.
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
    Execute series analysis stage.

    Args:
        image_paths: List of series sample image file paths
        settings: Pipeline configuration settings
        context: Optional context (unused in series stage)

    Returns:
        (result_json, metadata): Series JSON with 'name' field and execution metadata
    """
    try:
        messages = build_messages_for_task(
            "series", settings, user_text=None, image_paths=image_paths, as_data_url=True
        )
        raw = invoke_model(
            task_name="series",
            messages=messages,
            settings=settings,
            provider_type=settings["tasks"]["series"]["provider_type"],
            temperature=settings["tasks"]["series"].get("temperature"),
            top_p=settings["tasks"]["series"].get("top_p"),
        )
        parsed = fix_or_parse_json(raw)
        if parsed is None:
            meta = make_meta(
                "series",
                settings,
                error="model_output_not_valid_json",
                provider_type=settings["tasks"]["series"]["provider_type"]
            )
            return None, meta

        meta = make_meta(
            "series",
            settings,
            provider_type=settings["tasks"]["series"]["provider_type"]
        )
        return parsed, meta

    except Exception as e:
        meta = make_meta(
            "series",
            settings,
            error=str(e),
            provider_type=settings["tasks"]["series"]["provider_type"]
        )
        return None, meta
