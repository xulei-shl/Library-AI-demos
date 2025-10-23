# -*- coding: utf-8 -*-
"""
系列共识阶段：基于系列级 JSON 和多组对象级 JSON 生成系列共识元数据。

逻辑流程：
1. 从 series JSON 中提取字段（仅 A 类型）：name, country, manufacturer, text_content, art_style
2. 从最多 3 组对象 JSON 中提取字段：country, manufacturer, text_content, inferred_era, art_style, series.name
3. 构建 series_level_data 和 object_level_data 两部分输入
4. 调用 LLM 生成共识字段：series.name, inferred_era, art_style, country, manufacturer, reasoning
5. 将共识 JSON 保存到原始图片对应的路径
6. 返回共识结果用于更新初始 JSON
"""
import os
import json
from typing import Any, Dict, List, Optional, Tuple
from collections import Counter

from src.utils.llm_api import invoke_model
from src.core.messages import build_messages_for_task
from src.core.pipeline_utils import fix_or_parse_json, make_meta, now_iso, write_json
from src.utils.logger import get_logger

logger = get_logger(__name__)

__all__ = ["execute_stage"]


def execute_stage(
    image_paths: List[str],
    settings: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    执行系列共识阶段。

    Args:
        image_paths: 图像路径列表（此阶段不使用图像，仅为保持接口一致）
        settings: 管道配置
        context: 上下文字典，必须包含：
                 - 'series_json_path': series JSON 文件路径（可选，仅 A 类型）
                 - 'object_json_paths': 对象 JSON 文件路径列表（最多 3 个）
                 - 'consensus_output_path': 共识文件保存路径
                 - 'series_type': 'A' 或 'B'

    Returns:
        (result_json, metadata): 共识结果和执行元数据
    """
    context = context or {}
    series_json_path = context.get("series_json_path")
    object_json_paths = context.get("object_json_paths", [])
    consensus_output_path = context.get("consensus_output_path")
    series_type = context.get("series_type", "B")

    # 验证必需参数
    if not object_json_paths:
        meta = make_meta(
            "series_consensus",
            settings,
            error="no_object_json_paths_provided",
            provider_type="text"
        )
        return None, meta

    if not consensus_output_path:
        meta = make_meta(
            "series_consensus",
            settings,
            error="no_consensus_output_path_provided",
            provider_type="text"
        )
        return None, meta

    # 1. 提取 series_level_data（仅 A 类型）
    series_level_data = None
    if series_type == "A" and series_json_path and os.path.exists(series_json_path):
        try:
            with open(series_json_path, "r", encoding="utf-8") as f:
                series_json = json.load(f)
            series_level_data = _extract_series_level_data(series_json)
        except Exception as e:
            logger.warning(f"failed_to_read_series_json path={series_json_path} err={str(e)[:200]}")

    # 2. 提取 object_level_data（最多 3 组）
    object_level_data = []
    for obj_path in object_json_paths[:3]:  # 限制最多 3 组
        if not os.path.exists(obj_path):
            logger.warning(f"object_json_not_found path={obj_path}")
            continue
        try:
            with open(obj_path, "r", encoding="utf-8") as f:
                obj_json = json.load(f)
            obj_data = _extract_object_level_data(obj_json)
            object_level_data.append(obj_data)
        except Exception as e:
            logger.warning(f"failed_to_read_object_json path={obj_path} err={str(e)[:200]}")

    if not object_level_data:
        # 如果没有有效的对象数据，使用本地兜底策略
        consensus_fb = _local_fallback_consensus(series_level_data, [])
        meta = make_meta("series_consensus", settings, provider_type="text")
        meta["consensus_strategy"] = "local_fallback_no_objects"

        # 保存共识文件
        _save_consensus_file(consensus_output_path, consensus_fb, meta, settings)
        return consensus_fb, meta

    # 3. 构建用户提示词
    user_input = _build_user_prompt(series_level_data, object_level_data)

    task_name = "series_consensus"

    # 4. 调用 LLM 生成共识
    try:
        messages = build_messages_for_task(
            task_name, settings, user_text=user_input, image_paths=[], as_data_url=False
        )
        raw = invoke_model(
            task_name=task_name,
            messages=messages,
            settings=settings,
            provider_type="text",
            temperature=settings["tasks"][task_name].get("temperature", 0.2),
            top_p=settings["tasks"][task_name].get("top_p", 0.9),
        )
        parsed = fix_or_parse_json(raw)

        if parsed is None or not isinstance(parsed, dict):
            # LLM 输出不可解析，使用本地兜底
            consensus_fb = _local_fallback_consensus(series_level_data, object_level_data)
            meta = make_meta("series_consensus", settings, provider_type="text")
            meta["consensus_strategy"] = "local_fallback_parse_failed"

            # 保存共识文件
            _save_consensus_file(consensus_output_path, consensus_fb, meta, settings)
            return consensus_fb, meta

        # 验证输出包含必要的共识字段
        required_fields = ["series_name", "manufacturer", "country", "art_style", "inferred_era", "reasoning"]
        if not all(field in parsed for field in required_fields):
            logger.warning(f"llm_output_missing_required_fields missing={[f for f in required_fields if f not in parsed]}")
            consensus_fb = _local_fallback_consensus(series_level_data, object_level_data)
            meta = make_meta("series_consensus", settings, provider_type="text")
            meta["consensus_strategy"] = "local_fallback_missing_fields"

            # 保存共识文件
            _save_consensus_file(consensus_output_path, consensus_fb, meta, settings)
            return consensus_fb, meta

        # 成功解析，保存共识文件
        meta = make_meta("series_consensus", settings, provider_type="text")
        meta["consensus_strategy"] = "llm_vote"

        # 5. 保存共识 JSON 到指定路径
        _save_consensus_file(consensus_output_path, parsed, meta, settings)

        return parsed, meta

    except Exception as e:
        # 异常时启用本地兜底
        logger.warning(f"invoke_exception err={str(e)[:200]}")
        consensus_fb = _local_fallback_consensus(series_level_data, object_level_data)
        meta = make_meta("series_consensus", settings, provider_type="text")
        meta["consensus_strategy"] = "local_fallback_exception"
        meta["error"] = f"invoke_exception: {str(e)[:200]}"

        # 保存共识文件
        _save_consensus_file(consensus_output_path, consensus_fb, meta, settings)
        return consensus_fb, meta


def _normalize_art_style(art_style: Any) -> Any:
    """
    规范化 art_style 字段：
    - 如果是字符串形式的列表（如 "['木刻版画']"），则解析为真正的列表
    - 否则保持原值

    Args:
        art_style: art_style 字段值

    Returns:
        规范化后的值
    """
    if isinstance(art_style, str) and art_style.startswith("[") and art_style.endswith("]"):
        try:
            import ast
            parsed = ast.literal_eval(art_style)
            if isinstance(parsed, list):
                return parsed
        except Exception as e:
            logger.warning(f"failed_to_parse_art_style_string value={art_style} err={str(e)[:100]}")
    return art_style


def _extract_series_level_data(series_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    从 series JSON 中提取系列级字段。

    Args:
        series_json: 完整的 series JSON 数据

    Returns:
        包含 name, country, manufacturer, text_content, art_style 的字典
    """
    return {
        "name": series_json.get("name"),
        "country": series_json.get("country"),
        "manufacturer": series_json.get("manufacturer"),
        "text_content": series_json.get("text_content"),
        "art_style": _normalize_art_style(series_json.get("art_style")),
    }


def _extract_object_level_data(obj_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    从对象 JSON 中提取对象级字段。

    Args:
        obj_json: 完整的对象 JSON 数据

    Returns:
        包含 country, manufacturer, text_content, inferred_era, art_style, series.name 的字典
    """
    series_name = None
    series_obj = obj_json.get("series")
    if isinstance(series_obj, dict):
        series_name = series_obj.get("name")

    return {
        "country": obj_json.get("country"),
        "manufacturer": obj_json.get("manufacturer"),
        "text_content": obj_json.get("text_content"),
        "inferred_era": obj_json.get("inferred_era"),
        "art_style": _normalize_art_style(obj_json.get("art_style")),
        "series_name": series_name,
    }


def _build_user_prompt(
    series_level_data: Optional[Dict[str, Any]],
    object_level_data: List[Dict[str, Any]]
) -> str:
    """
    构建符合 prompt 格式的用户输入文本。

    Args:
        series_level_data: series 级数据（可能为 None）
        object_level_data: 对象级数据列表

    Returns:
        格式化的 JSON 字符串
    """
    prompt_input = {}

    if series_level_data is not None:
        prompt_input["series_level_data"] = series_level_data

    prompt_input["object_level_data"] = object_level_data

    return json.dumps(prompt_input, ensure_ascii=False, indent=2)


def _save_consensus_file(
    output_path: str,
    consensus_data: Dict[str, Any],
    meta: Dict[str, Any],
    settings: Dict[str, Any]
) -> None:
    """
    保存共识文件到指定路径。

    Args:
        output_path: 共识文件输出路径
        consensus_data: 共识数据（包含 LLM 输出的所有字段）
        meta: 执行元数据
        settings: 管道配置
    """
    # 构建完整的共识文件数据
    full_consensus = {
        "series_name": consensus_data.get("series_name"),
        "manufacturer": consensus_data.get("manufacturer"),
        "country": consensus_data.get("country"),
        "art_style": consensus_data.get("art_style"),
        "inferred_era": consensus_data.get("inferred_era"),
        "reasoning": consensus_data.get("reasoning", {}),
        "consensus_meta": {
            "created_at": now_iso(),
            "consensus_strategy": meta.get("consensus_strategy", "unknown"),
            "llm_model": meta.get("llm_model", "unknown"),
            "status": meta.get("status", "success"),
        }
    }

    # 如果有错误信息，添加到 meta 中
    if "error" in meta:
        full_consensus["consensus_meta"]["error"] = meta["error"]

    try:
        write_json(output_path, full_consensus)
        logger.info(f"consensus_saved path={output_path}")
    except Exception as e:
        logger.warning(f"consensus_save_failed path={output_path} err={str(e)[:200]}")


def _normalize_str(val: Any) -> Optional[str]:
    """
    归一化字符串值：去除首尾空白并转换为字符串；空串或 None 返回 None。
    """
    if val is None:
        return None
    s = str(val).strip()
    return s or None


def _local_fallback_consensus(
    series_level_data: Optional[Dict[str, Any]],
    object_level_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    本地兜底共识策略：
    - 优先使用 series_level_data 中的非空值
    - 从 object_level_data 中使用多数投票填充缺失字段
    - 若某字段全部为 None/空，则输出 None

    Args:
        series_level_data: series 级数据（可能为 None）
        object_level_data: 对象级数据列表

    Returns:
        共识字段字典
    """
    # 初始化结果
    result = {
        "series_name": None,
        "manufacturer": None,
        "country": None,
        "art_style": None,
        "inferred_era": None,
        "reasoning": {}
    }

    # 优先使用 series_level_data
    if series_level_data:
        if _normalize_str(series_level_data.get("name")):
            result["series_name"] = _normalize_str(series_level_data.get("name"))
            result["reasoning"]["series_name"] = "采纳自 series_level_data"

        if _normalize_str(series_level_data.get("manufacturer")):
            result["manufacturer"] = _normalize_str(series_level_data.get("manufacturer"))
            result["reasoning"]["manufacturer"] = "采纳自 series_level_data"

        if _normalize_str(series_level_data.get("country")):
            result["country"] = _normalize_str(series_level_data.get("country"))
            result["reasoning"]["country"] = "采纳自 series_level_data"

        if _normalize_str(series_level_data.get("art_style")):
            result["art_style"] = _normalize_str(series_level_data.get("art_style"))
            result["reasoning"]["art_style"] = "采纳自 series_level_data"

    # 从 object_level_data 中补充缺失字段
    if object_level_data:
        # 收集各字段的值
        buckets = {
            "series_name": [],
            "manufacturer": [],
            "country": [],
            "art_style": [],
            "inferred_era": [],
        }

        for obj_data in object_level_data:
            for field in buckets.keys():
                val = _normalize_str(obj_data.get(field))
                if val:
                    buckets[field].append(val)

        # 对每个字段进行多数投票
        for field, values in buckets.items():
            # 如果该字段已经从 series_level_data 中获取，跳过
            if result[field] is not None:
                continue

            if values:
                cnt = Counter(values)
                # 选择最高频；并列时选更长、更规范的字符串，最后按字典序稳定
                picked = sorted(cnt.items(), key=lambda x: (-x[1], -len(x[0]), x[0]))[0][0]
                result[field] = picked

                # 生成 reasoning
                if len(values) == 1:
                    result["reasoning"][field] = f"采纳自唯一的 object_level_data 样本"
                else:
                    count_info = f"{cnt[picked]}/{len(object_level_data)}"
                    result["reasoning"][field] = f"采纳自 object_level_data 中的多数值 ({count_info} 样本)"
            else:
                result["reasoning"][field] = "所有输入源均未提供有效值，设为 null"
    else:
        # 如果没有 object_level_data，为缺失字段生成 reasoning
        for field in ["series_name", "manufacturer", "country", "art_style", "inferred_era"]:
            if result[field] is None and field not in result["reasoning"]:
                result["reasoning"][field] = "所有输入源均未提供有效值，设为 null"

    return result
