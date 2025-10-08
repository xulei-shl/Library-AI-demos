# -*- coding: utf-8 -*-
"""
规划阶段：调用 llm_api 生成 deep.json（row_id、summary、report_theme、subtopics）
"""
import json
import os
from typing import Dict, Any
from datetime import datetime, timezone, timedelta

from src.utils import llm_api  # 复用公共LLM调用
from src.core.l3_deep_analysis.json_schema import is_planning_complete

def plan_deep_json(row_id: str, user_prompt: str, settings: Dict[str, Any], output_dir: str) -> Dict[str, Any]:
    """
    调用 LLM 生成规划 JSON，并写入 {row_id}_deep.json

    Args:
        row_id: 编号（如 "2202_001"）
        user_prompt: 用户提示文本
        settings: 全局配置字典
        output_dir: 输出目录（与原实体 JSON 同目录）

    Returns:
        Dict[str, Any]: 生成的 deep.json 数据
    """
    # 统一走 invoke_model(task_name, messages, settings) 调用约定
    # 从 deep_analysis.planning 读取提示词文件，不依赖 tasks 注册
    sys_file = (settings.get("deep_analysis", {}).get("planning", {}) or {}).get(
        "system_prompt_file", "l3_deep_analysis_planning.md"
    )

    # 读取系统提示词文件
    PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "prompts")
    def _read_text(p: str) -> str:
        with open(p, "r", encoding="utf-8") as f:
            return f.read()
    system_text = _read_text(os.path.join(PROMPTS_DIR, sys_file))

    # 构造 messages 并调用统一 API
    messages = [
        {"role": "system", "content": system_text},
        {"role": "user", "content": user_prompt},
    ]
    # 任务名选择：优先 deep_analysis.planning.llm_task_name，否则回退 l1_extraction
    llm_task = (settings.get("deep_analysis", {}).get("planning", {}) or {}).get("llm_task_name") or "l1_extraction"

    # 统一从 tasks[llm_task] 读取系统提示词，避免与 deep_analysis.planning 重复
    try:
        tasks_conf = settings.get("tasks") or {}
        sys_file2 = tasks_conf[llm_task]["system_prompt_file"]
        system_text2 = _read_text(os.path.join(PROMPTS_DIR, sys_file2))
        messages[0]["content"] = system_text2
    except Exception:
        # 若 tasks 未配置 system_prompt_file，则保留此前从 planning 配置读取的 system_text
        pass

    # 不再透传 provider_type/temperature 等覆盖参数，统一依赖 tasks
    result_text = llm_api.invoke_model(llm_task, messages, settings)
    try:
        data = json.loads(result_text)
    except Exception:
        data = {"row_id": row_id, "summary": None, "report_theme": None, "subtopics": []}

    # 强制设置 row_id
    data["row_id"] = row_id

    # 写入自身 meta 信息
    now = datetime.now(timezone(timedelta(hours=8))).isoformat()
    data["meta"] = {
        "executed_at": now,
        "status": "success" if is_planning_complete(data) else "partial",
        "llm": {
            "model": settings.get("api_providers", {}).get("text", {}).get("primary", {}).get("model", "unknown")
        }
    }

    out_path = f"{output_dir}/{row_id}_deep.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data