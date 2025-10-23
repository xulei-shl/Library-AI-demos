# -*- coding: utf-8 -*-
"""
Correction stage: Validate and correct structured fields.
Wraps the existing correction service with the standard stage interface.
"""
from typing import Any, Dict, List, Optional, Tuple

from src.core.correction_service import stage_correction

__all__ = ["execute_stage"]


def execute_stage(
    image_paths: List[str],
    settings: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    Execute correction stage.

    Args:
        image_paths: List of image file paths (unused, correction uses text only)
        settings: Pipeline configuration settings
        context: Must contain 'input_json' with fact description results

    Returns:
        (result_json, metadata): Correction JSON and execution metadata
    """
    context = context or {}
    input_json = context.get("input_json")

    if not input_json:
        from src.core.pipeline_utils import make_meta
        meta = make_meta(
            "correction",
            settings,
            error="missing_input_json",
            provider_type=settings["tasks"]["correction"]["provider_type"]
        )
        return None, meta

    # Delegate to existing correction module
    return stage_correction(settings, input_json)
