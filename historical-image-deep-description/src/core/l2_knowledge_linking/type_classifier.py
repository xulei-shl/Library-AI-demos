import os
import json
import glob
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ...utils.logger import get_logger
from ...utils.llm_api import load_settings, invoke_model

logger = get_logger(__name__)

PROMPTS_DIR = os.path.join("src", "prompts")
DEFAULT_OUTPUT_DIR = os.path.join("runtime", "outputs")

def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def _find_target_jsons(output_dir: str) -> List[str]:
    """
    扫描输出目录，按命名规则优先匹配形如 *.json 的任务清单文件。
    约定：task_builder 已将行编号-题名前5-行号 的 JSON 写入 runtime/outputs。
    """
    pattern = os.path.join(output_dir, "*.json")
    paths = sorted(glob.glob(pattern))
    # 过滤掉聚合清单 task_list.json，仅返回行级 JSON 目标
    return [p for p in paths if os.path.isfile(p) and os.path.basename(p) != "task_list.json"]

def _atomic_write(path: str, data: Dict[str, Any]) -> None:
    """原子化写入，避免中断造成文件损坏。"""
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def _classify_one(label: str, context_hint: str, settings: Dict[str, Any]) -> Tuple[Optional[str], Optional[float], Optional[str], Optional[str], Optional[str]]:
    """
    调用大模型进行类型判断。
    返回：(type, confidence, reason, executed_at, model)
    """
    # 获取执行时间戳和模型名称
    executed_at = datetime.now().isoformat()
    task_config = settings.get("tasks", {}).get("l2_classification", {}) or {}
    # 模型名应从 api_providers 获取，而非 task 配置
    provider_type = task_config.get("provider_type") or "text"
    provider_cfg = settings.get("api_providers", {}).get(provider_type, {}) or {}
    # 优先取 primary 的模型名，若无则回退 secondary，最后回退 "unknown"
    model_name = (
        (provider_cfg.get("primary") or {}).get("model")
        or (provider_cfg.get("secondary") or {}).get("model")
        or "unknown"
    )
    
    prompt_path = os.path.join(PROMPTS_DIR, "l2_entity_classification.md")
    cls_prompt = _read_text(prompt_path)
    messages = [
        {"role": "system", "content": cls_prompt},
        {"role": "user", "content": f"{context_hint or ''}\n\n待分类实体: {label}\n类型提示: 忽略原值，请根据上下文重判\n请仅输出JSON。"},
    ]
    try:
        result = invoke_model("l2_classification", messages, settings)
        parsed = json.loads(result)
        t = parsed.get("type")
        conf = parsed.get("confidence")
        reason = parsed.get("reason")
        if isinstance(t, str) and t.strip():
            t = t.strip()
        else:
            t = None
        if isinstance(conf, (int, float)):
            conf = float(conf)
        else:
            conf = None
        if isinstance(reason, str):
            reason = reason.strip()
        else:
            reason = None
        return t, conf, reason, executed_at, model_name
    except Exception as e:
        logger.warning(f"类型判断失败 label={label} err={e}")
        return None, None, None, None, None

def classify_types(json_paths: Optional[List[str]] = None, settings: Optional[Dict[str, Any]] = None, output_dir: Optional[str] = None, write_meta: bool = True) -> List[str]:
    """
    扫描并更新实体类型：
    - 不管原 type 是否有值，都用大模型结果覆盖
    - 同时可写入 _type_meta 审计字段（confidence, reason）
    返回：成功更新的文件路径列表
    """
    settings = settings or load_settings()
    out_dir = output_dir or settings.get("data", {}).get("outputs", {}).get("dir", DEFAULT_OUTPUT_DIR) or DEFAULT_OUTPUT_DIR
    targets = list(json_paths) if json_paths else _find_target_jsons(out_dir)
    updated: List[str] = []
    for path in targets:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.warning(f"读取JSON失败 path={path} err={e}")
            continue

        # 兼容两种结构：{row_id, entities} 或 {items: [...]}
        entities: Optional[List[Dict[str, Any]]] = None
        if isinstance(data, dict):
            if "entities" in data and isinstance(data["entities"], list):
                entities = data["entities"]
            elif "items" in data and isinstance(data["items"], list):
                # 任务清单结构
                entities = data["items"]
        if entities is None:
            logger.warning(f"未识别的JSON结构，跳过 path={path}")
            continue

        changed = False
        for ent in entities:
            label = (ent.get("label") or "").strip()
            if not label:
                continue
            context_hint = ent.get("context_hint") or ""
            new_type, conf, reason, executed_at, model_name = _classify_one(label, context_hint, settings)
            if new_type:
                ent["type"] = new_type
                if write_meta:
                    ent["_type_meta"] = {
                        "confidence": conf, 
                        "reason": reason,
                        "executed_at": executed_at,
                        "model": model_name
                    }
                changed = True

        if changed:
            try:
                _atomic_write(path, data)
                updated.append(path)
                logger.info(f"实体类型已更新 path={path}")
            except Exception as e:
                logger.error(f"写回失败 path={path} err={e}")
        else:
            logger.info(f"无可更新实体类型 path={path}")
    return updated