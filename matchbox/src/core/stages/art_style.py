# -*- coding: utf-8 -*-
"""
Art style detection stage: Identify the artistic style of matchbox labels.
Uses standardized vocabulary to ensure consistency.
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
    Execute art style detection stage.

    Args:
        image_paths: List of image file paths to process
        settings: Pipeline configuration settings
        context: Optional context dict; when context.get("use_candidate_vocab", True) is True,
                 include candidate vocabulary into user_text to constrain outputs.

    Returns:
        (result_json, metadata): JSON with art_style and art_style_raw fields and execution metadata
    """
    context = context or {}
    user_text: Optional[str] = None

    # If instructed, load candidate vocabulary to enforce standardized tags
    use_vocab = bool(context.get("use_candidate_vocab", False))
    if use_vocab:
        try:
            import os
            # Resolve docs/metadata/艺术风格词表.md relative to project root
            vocab_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "docs", "metadata", "艺术风格词表.md"))
            with open(vocab_path, "r", encoding="utf-8") as f:
                vocab_text = f.read()
            user_text = (
                "请严格仅从下述候选词表中选择艺术风格标签，并返回标准化字段：\n\n"
                + vocab_text
                + "\n\n输出必须使用候选词表中的词汇；若无法判定请返回 null。"
            )
        except Exception:
            # Fallback to a simple instruction if vocab file not found
            user_text = "请仅从预定义候选词表中选择艺术风格标签，若无法判定请返回 null。"

    try:
        messages = build_messages_for_task(
            "art_style", settings, user_text=user_text, image_paths=image_paths, as_data_url=True
        )
        raw = invoke_model(
            task_name="art_style",
            messages=messages,
            settings=settings,
            provider_type=settings["tasks"]["art_style"]["provider_type"],
            temperature=settings["tasks"]["art_style"].get("temperature"),
            top_p=settings["tasks"]["art_style"].get("top_p"),
        )
        parsed = fix_or_parse_json(raw)
        if parsed is None:
            meta = make_meta(
                "art_style",
                settings,
                error="model_output_not_valid_json",
                provider_type=settings["tasks"]["art_style"]["provider_type"]
            )
            return None, meta

        meta = make_meta(
            "art_style",
            settings,
            provider_type=settings["tasks"]["art_style"]["provider_type"]
        )
        return parsed, meta

    except Exception as e:
        meta = make_meta(
            "art_style",
            settings,
            error=str(e),
            provider_type=settings["tasks"]["art_style"]["provider_type"]
        )
        return None, meta
