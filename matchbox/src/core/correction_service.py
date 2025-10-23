# -*- coding: utf-8 -*-
import copy
import json
from typing import Any, Dict, Optional, Tuple

from src.utils.logger import get_logger
from src.utils.llm_api import invoke_model
from src.core.pipeline_utils import make_meta
from src.core.messages import load_text_file

logger = get_logger(__name__)

def strip_meta_fields(obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    移除 JSON 中的 *_meta 元数据字段，避免影响模型判断。
    """
    cleaned = {}
    for k, v in obj.items():
        if k.endswith("_meta"):
            continue
        if isinstance(v, dict):
            cleaned[k] = strip_meta_fields(v)
        else:
            cleaned[k] = v
    return cleaned

def stage_correction(settings: Dict[str, Any], input_json: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    # 检查 text_content 是否为空
    if not input_json.get("text_content"):
        meta = make_meta("correction", settings, error="text_content_empty", provider_type=settings["tasks"]["correction"]["provider_type"])
        logger.warning("text_content is empty, skipping correction process.")
        return None, meta
    """
    基于输入 JSON（包含 text_content）调用文本大模型进行 manufacturer/country/series 字段校验与纠正。
    返回 (correction_json, correction_meta)。
    """
    try:
        # 清理 JSON，移除元数据字段
        cleaned_json = strip_meta_fields(copy.deepcopy(input_json))
        user_text = json.dumps(cleaned_json, ensure_ascii=False)
        
        from src.core.messages import build_messages
        system_prompt_file = settings["tasks"]["correction"]["system_prompt_file"]
        messages = [
            {"role": "system", "content": load_text_file(system_prompt_file)},
            {"role": "user", "content": [{"type": "text", "text": user_text}]}
        ]
        
        raw = invoke_model(
            task_name="correction",
            messages=messages,
            settings=settings,
            provider_type=settings["tasks"]["correction"]["provider_type"],
            temperature=settings["tasks"]["correction"].get("temperature"),
            top_p=settings["tasks"]["correction"].get("top_p"),
        )
        correction_json = None
        try:
            from src.utils.json_repair import repair_json_output, is_valid_json
            fixed = repair_json_output(raw)
            if fixed is not None:
                correction_json = fixed
            elif is_valid_json(raw):
                correction_json = json.loads(raw)
        except Exception as e:
            logger.warning(f"correction_json_parse_failed err={str(e)[:200]}")
        
        meta = make_meta("correction", settings, error=None if correction_json else "model_output_not_valid_json", provider_type=settings["tasks"]["correction"]["provider_type"])
        return correction_json, meta
    except Exception as e:
        meta = make_meta("correction", settings, error=str(e), provider_type=settings["tasks"]["correction"]["provider_type"])
        return None, meta

def apply_corrections_to_json(obj: Dict[str, Any], corrections: Dict[str, Any]) -> None:
    """
    将修正 JSON 应用到原始对象 JSON 中。
    corrections 格式参考 correction.md 输出。
    """
    # 顶层修正
    if corrections.get("manufacturer_correct") is False and "manufacturer" in corrections.get("corrections", {}):
        obj["manufacturer"] = corrections["corrections"]["manufacturer"]
    if corrections.get("country_correct") is False and "country" in corrections.get("corrections", {}):
        obj["country"] = corrections["corrections"]["country"]
    
    # 系列修正
    series_corr = corrections.get("series")
    if isinstance(series_corr, dict):
        if "series" not in obj or not isinstance(obj["series"], dict):
            obj["series"] = {}
        if series_corr.get("name_correct") is False and "name" in series_corr.get("corrections", {}):
            obj["series"]["name"] = series_corr["corrections"]["name"]
        if series_corr.get("series_no_correct") is False and "series_no" in series_corr.get("corrections", {}):
            obj["series"]["series_no"] = series_corr["corrections"]["series_no"]
        if series_corr.get("manufacturer_correct") is False and "manufacturer" in series_corr.get("corrections", {}):
            obj["series"]["manufacturer"] = series_corr["corrections"]["manufacturer"]
        if series_corr.get("country_correct") is False and "country" in series_corr.get("corrections", {}):
            obj["series"]["country"] = series_corr["corrections"]["country"]