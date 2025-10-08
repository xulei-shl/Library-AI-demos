from typing import Any, Dict, List, Optional
import json

from ....utils.logger import get_logger
from ....utils.llm_api import load_settings, invoke_model

logger = get_logger(__name__)

def format_candidates(raw: List[Dict[str, Any]], cfg: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    使用大模型将 Wikidata 检索返回的原始文本转换为统一的候选 JSON。
    输入 raw 列表项至少包含:
      - id: Wikidata QID（若检索阶段可得）
      - raw: 原始文本片段（例如 LangChain段落或 API返回拼接文本）
    解析策略：
      - 不进行任何规则/正则解析，完整交由 LLM 根据提示词生成候选。
    输出项字段固定为：
      - id: 字符串，Wikidata QID
      - label: 字符串或 None
      - desc: 字符串（可为空字符串）
      - context: 字符串（候选的来源/上下文预览）
    """
    if not raw:
        return []

    # 读取全局设置
    settings = load_settings()
    task_name = "l2_wikidata_candidate_formatting"

    # 读取系统提示词
    try:
        with open("src/prompts/l2_wikidata_candidate_formatting.md", "r", encoding="utf-8") as f:
            system_prompt = f.read()
    except Exception:
        system_prompt = (
            "将用户提供的检索原始文本列表，转换为严格的 JSON："
            '{"candidates": [{"id":"Q...","label":null,"desc":"","context":""}] }'
        )

    # 构造用户载荷
    payload = {
        "raw_items": [
            {"id": it.get("id"), "raw": (it.get("raw") or "")}
            for it in (raw or [])
        ]
    }

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]

    # 调用模型
    output = invoke_model(task_name=task_name, messages=messages, settings=settings)

    # 解析模型返回
    candidates: List[Dict[str, Any]] = []
    try:
        data = json.loads(output)
        items = data.get("candidates") or []
        for c in items:
            candidates.append({
                "id": c.get("id"),
                "label": c.get("label"),
                "desc": c.get("desc", ""),
                "context": c.get("context"),
            })
    except Exception:
        logger.warning("wikidata_llm_parser.candidates_parse_error")
        candidates = []

    return candidates


def parse_llm_output(txt: str, candidates: List[Dict[str, Any]], model_name: Optional[str]) -> Dict[str, Any]:
    """
    解析消歧阶段的 LLM 输出（保持与旧版接口兼容）。
    期望输入为 JSON 字符串，含：
      - selected_qid 或 wikidata_qid
      - confidence
      - reason
    在 candidates 列表中按 id 找到对应项，合并 confidence/model/reason 字段后原样返回；
    若未匹配，则返回未匹配结构。
    """
    try:
        logger.debug(f"wikidata_llm_parser.parse_llm_output.input_preview txt={str(txt)[:300]}")
        logger.debug(f"wikidata_llm_parser.parse_llm_output.candidate_ids ids={[c.get('id') for c in (candidates or [])]}")
    except Exception:
        pass

    try:
        data = json.loads(txt)
    except Exception:
        logger.warning("wikidata_llm_parser.llm_output_not_json")
        return {
            "matched": False,
            "confidence": 0.0,
            "model": model_name,
            "reason": "输出解析失败",
        }

    qid = data.get("selected_qid") or data.get("wikidata_qid")

    # 置信度与理由
    conf = data.get("confidence")
    try:
        conf = float(conf)
        if conf < 0.0: conf = 0.0
        if conf > 1.0: conf = 1.0
    except Exception:
        conf = 0.0
    reason = (data.get("reason") or "").strip()

    if not qid:
        return {
            "matched": False,
            "confidence": conf,
            "model": model_name,
            "reason": reason or "未匹配到合适候选",
        }

    selected = None
    for c in candidates or []:
        if c.get("id") == qid:
            selected = dict(c)
            break

    if not selected:
        return {
            "matched": False,
            "confidence": conf,
            "model": model_name,
            "reason": reason or "未匹配到合适候选",
        }

    selected["confidence"] = conf
    selected["model"] = model_name
    selected["reason"] = reason or "已选择候选"
    return selected


def fallback_zero_candidates(label: str, type_hint: Optional[str]) -> Dict[str, Any]:
    """
    空候选时的兜底输出（跳过 LLM）。
    """
    return {
        "matched": False,
        "confidence": 0.0,
        "model": None,
        "reason": "无候选",
    }