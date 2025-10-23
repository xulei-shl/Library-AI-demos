# -*- coding: utf-8 -*-
"""
Function type classification stage: Determine the function type of an item.
Requires prior fact description JSON in context.
"""
import json
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
    Execute function type classification stage.

    Args:
        image_paths: List of image file paths to process
        settings: Pipeline configuration settings
        context: Must contain 'previous_json' with fact description results;
                 when context.get("use_candidate_vocab", True) is True,
                 include candidate vocabulary into user_text to constrain outputs.

    Returns:
        (result_json, metadata): JSON with function_type field and execution metadata
    """
    context = context or {}
    previous_json = context.get("previous_json")

    if not previous_json:
        meta = make_meta(
            "function_type",
            settings,
            error="missing_previous_json",
            provider_type=settings["tasks"]["function_type"]["provider_type"]
        )
        return None, meta

    # Construct user text with previous stage JSON
    prev_txt = json.dumps(previous_json, ensure_ascii=False)
    user_text = (
        "以下为已提取的第一阶段元数据 JSON,请根据《功能类型定义》判断该火花的功能类型。"
        "仅输出一个包含 function_type 字段的 JSON 对象。\n\n"
        f"{prev_txt}"
    )

    # If instructed, load candidate vocabulary to enforce standardized function types
    use_vocab = bool(context.get("use_candidate_vocab", False))
    if use_vocab:
        try:
            import os
            # Resolve docs/metadata/功能类型词表.md relative to project root
            vocab_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "docs", "metadata", "功能类型词表.md"))
            with open(vocab_path, "r", encoding="utf-8") as f:
                vocab_text = f.read()
            user_text += (
                "\n\n请严格仅从下述候选词表中选择功能类型，并返回标准化字段：\n\n"
                + vocab_text
                + "\n\n输出必须使用候选词表中的词汇；若无法判定请返回 null。"
            )
        except Exception:
            # Fallback to a simple instruction if vocab file not found
            user_text += "\n\n请仅从预定义候选词表中选择功能类型，若无法判定请返回 null。"

    try:
        messages = build_messages_for_task(
            "function_type", settings, user_text=user_text, image_paths=image_paths, as_data_url=True
        )
        raw = invoke_model(
            task_name="function_type",
            messages=messages,
            settings=settings,
            provider_type=settings["tasks"]["function_type"]["provider_type"],
            temperature=settings["tasks"]["function_type"].get("temperature"),
            top_p=settings["tasks"]["function_type"].get("top_p"),
        )
        parsed = fix_or_parse_json(raw)
        if parsed is None:
            meta = make_meta(
                "function_type",
                settings,
                error="model_output_not_valid_json",
                provider_type=settings["tasks"]["function_type"]["provider_type"]
            )
            return None, meta

        meta = make_meta(
            "function_type",
            settings,
            provider_type=settings["tasks"]["function_type"]["provider_type"]
        )
        return parsed, meta

    except Exception as e:
        meta = make_meta(
            "function_type",
            settings,
            error=str(e),
            provider_type=settings["tasks"]["function_type"]["provider_type"]
        )
        return None, meta
