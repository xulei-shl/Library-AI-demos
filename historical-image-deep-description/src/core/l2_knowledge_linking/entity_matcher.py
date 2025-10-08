from typing import Any, Dict, List, Optional, Literal
import json
import os
import time
from datetime import datetime

from ...utils.logger import get_logger
from ...utils.llm_api import invoke_model
from ...utils.json_repair import repair_json_output

logger = get_logger(__name__)

PROMPTS_DIR = os.path.join("src", "prompts")
DIS_PROMPT_PATH = os.path.join(PROMPTS_DIR, "l2_entity_disambiguation.md")
INTERNAL_API_DIS_PROMPT_PATH = os.path.join(PROMPTS_DIR, "l2_internal_api_disambiguation.md")


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _build_messages(label: str, ent_type: Optional[str], context_hint: str,
                    source: Literal["wikipedia", "wikidata", "internal_api"],
                    candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    构造给大模型的消息：
    - system: 根据source选择不同的提示词
    - user: 提供 metadata_context、entity 与对应源的 candidates
    """
    # 根据source选择不同的提示词
    if source == "internal_api":
        sys_prompt = _read_text(INTERNAL_API_DIS_PROMPT_PATH)
        # 内部API使用不同的payload格式
        candidates_text = "\n".join([
            f"{i+1}. 标签: {c.get('label', 'N/A')}\n"
            f"   描述: {c.get('description', 'N/A')}\n"
            f"   URI: {c.get('uri', 'N/A')}\n"
            for i, c in enumerate(candidates)
        ])
        user_content = f"""## 实体信息
- 实体名称：{label}
- 实体类型：{ent_type}
- 上下文：{context_hint}

## 候选实体列表
{candidates_text}

请按照提示词要求进行分析并输出JSON格式的结果。"""
    else:
        sys_prompt = _read_text(DIS_PROMPT_PATH)
        payload = {
            "metadata_context": context_hint or "",
            "entity": {"label": label, "type_hint": ent_type or None},
            "candidates": {
                source: candidates
            },
        }
        user_content = json.dumps(payload, ensure_ascii=False)
    
    return [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_content},
    ]


def _parse_llm_output(txt: str, source: Literal["wikipedia", "wikidata", "internal_api"]) -> Dict[str, Any]:
    """
    解析大模型输出，输出统一结构：
    {
      "matched": bool,
      "confidence": float,
      "reason": str,
      "selected": dict | None
    }
    解析优先级：
    - reason: 顶层 reasons/reason -> reasons_by_source[source] -> choices[source].reason -> 默认
    - confidence: 顶层 confidence -> choices[source].confidence -> 默认(匹配0.7/不匹配0.2)
    - selected: choices[source] -> *_uri/QID 推断
    """
    def _clamp_conf(v: Any) -> float:
        try:
            x = float(v)
            if x < 0.0:
                return 0.0
            if x > 1.0:
                return 1.0
            # 保留两位小数的表现交由写入方/前端，内部保留原值
            return x
        except Exception:
            return 0.0

    try:
        data = json.loads(txt)
    except Exception:
        # 尝试使用 JSON 修复工具
        logger.info("attempting_json_repair")
        repaired_data = repair_json_output(txt)
        if repaired_data is not None:
            logger.info("json_repair_success")
            data = repaired_data
        else:
            logger.warning("llm_output_not_json")
            return {"matched": False, "confidence": 0.0, "reason": "输出解析失败", "selected": None}

    # 兼容顶层 selection（当前协议），优先使用
    sel: Optional[Dict[str, Any]] = None
    top_selection = data.get("selection")
    if isinstance(top_selection, dict):
        # 顶层选择对象直接作为已选候选
        sel = top_selection

    # 优先解析 choices.{source}（旧格式）
    ch = None
    choices = data.get("choices") or {}
    if isinstance(choices, dict):
        ch = choices.get(source)
        if isinstance(ch, dict):
            sel = ch

    # 从 *_uri / QID 回退推断
    if not sel:
        if source == "wikipedia":
            uri = data.get("wikipedia_uri")
            if uri:
                sel = {"canonicalurl": uri}
        elif source == "internal_api":
            # 内部API使用selected中的uri字段
            selected = data.get("selected")
            logger.info(f"internal_api_parsing selected={selected}")
            if isinstance(selected, dict):
                uri = selected.get("uri")
                if uri:
                    sel = {"uri": uri, "label": selected.get("label"), "description": selected.get("description")}
                    logger.info(f"internal_api_parsed_successfully uri={uri} label={selected.get('label')}")
        else:
            # 优先 data.wikidata_uri 提取 QID；兼容 data.wikidata_qid
            qid = None
            wuri = data.get("wikidata_uri")
            if isinstance(wuri, str):
                try:
                    # 形如 https://www.wikidata.org/wiki/Q56042396
                    import re
                    m = re.search(r"/wiki/(Q[0-9]+)", wuri)
                    if m:
                        qid = m.group(1)
                except Exception:
                    qid = None
            if not qid:
                qid = data.get("wikidata_qid")
            if qid:
                sel = {"id": qid}

    # 优先使用顶层 matched（若存在），否则依据是否选中候选
    top_matched = data.get("matched")
    if isinstance(top_matched, bool):
        matched = bool(top_matched) or (sel is not None)
    else:
        matched = sel is not None

    # 解析 reason（顶层优先）
    top_reason = data.get("reasons") or data.get("reason") or ""
    reasons_by_source = data.get("reasons_by_source") or {}
    src_reason = ""
    if isinstance(reasons_by_source, dict):
        sr = reasons_by_source.get(source)
        if isinstance(sr, str):
            src_reason = sr
    ch_reason = ""
    if isinstance(ch, dict):
        r = ch.get("reason")
        if isinstance(r, str):
            ch_reason = r
    reason = (top_reason or src_reason or ch_reason or "").strip()

    # 解析 confidence（顶层优先）
    top_conf = data.get("confidence")
    ch_conf = None
    if isinstance(ch, dict):
        ch_conf = ch.get("confidence")
    conf = None
    if top_conf is not None:
        conf = _clamp_conf(top_conf)
    elif ch_conf is not None:
        conf = _clamp_conf(ch_conf)
    else:
        # 默认：有匹配时中等置信，未匹配低置信
        conf = 0.7 if matched else 0.2

    # 兜底理由
    if not reason:
        reason = "已选择候选" if matched else "未匹配到合适候选"

    result = {
        "matched": bool(matched),
        "confidence": float(conf),
        "reason": reason,
        "selected": sel if matched else None,
    }
    logger.info(f"parse_llm_output_result source={source} matched={matched} confidence={conf} has_selected={sel is not None}")
    return result


def judge_best_match(
    *,
    label: str,
    ent_type: Optional[str],
    context_hint: str,
    source: Literal["wikipedia", "wikidata", "internal_api"],
    candidates: List[Dict[str, Any]],
    settings: Dict[str, Any],
) -> Dict[str, Any]:
    """
    使用统一的大模型接口对指定源的候选进行判定与筛选。
    返回：
      { matched: bool, confidence: float, reason: str, selected: dict | None }
    """
    if not candidates:
        return {"matched": False, "confidence": 0.0, "reason": "无候选", "selected": None}

    # 获取执行时间戳
    executed_at = datetime.now().isoformat()
    
    try:
        messages = _build_messages(label, ent_type, context_hint, source, candidates)
        out = invoke_model("l2_disambiguation", messages, settings)
        parsed = _parse_llm_output(out, source)

        # 内部API选择项充实：将 LLM 返回的最小 selected 映射回原候选，保留 __api_name 与 _raw 等字段
        if source == "internal_api" and isinstance(parsed, dict):
            sel = parsed.get("selected")
            if isinstance(sel, dict):
                sel_uri = sel.get("uri")
                matched_candidate = None
                if sel_uri:
                    for c in candidates:
                        try:
                            if c.get("uri") == sel_uri:
                                matched_candidate = c
                                break
                        except Exception:
                            pass
                if not matched_candidate:
                    sel_label = sel.get("label")
                    if sel_label:
                        for c in candidates:
                            try:
                                if c.get("label") == sel_label:
                                    matched_candidate = c
                                    break
                            except Exception:
                                pass
                if matched_candidate:
                    parsed["selected"] = matched_candidate
                    logger.info(
                        f"internal_api_selected_enriched uri={matched_candidate.get('uri')} "
                        f"has_raw={matched_candidate.get('_raw') is not None} "
                        f"api={matched_candidate.get('__api_name')}"
                    )

        # 将所用模型名和执行时间附加到判定结果，便于下游写入 meta
        try:
            task_cfg = settings.get("tasks", {}).get("l2_disambiguation") or {}
            provider_type = task_cfg.get("provider_type")
            if provider_type:
                model_name = settings.get("api_providers", {}).get(provider_type, {}).get("primary", {}).get("model")
            else:
                model_name = None
        except Exception:
            model_name = None
        if isinstance(parsed, dict):
            parsed["model"] = model_name
            parsed["executed_at"] = executed_at
        return parsed
    except Exception as e:
        logger.warning(f"llm_judge_failed source={source} label={label} err={e}")
        return {"matched": False, "confidence": 0.0, "reason": f"异常: {e}", "selected": None}