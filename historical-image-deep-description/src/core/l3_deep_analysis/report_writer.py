# -*- coding: utf-8 -*-
"""
最终报告撰写：调用 llm_api 生成 {row_id}_deep.md
"""
import json
import os
from typing import Dict, Any, List, Optional
from src.utils import llm_api


def _safe_str(val: Any) -> str:
    """将任意对象安全转换为字符串，避免 None/对象拼接异常。"""
    try:
        return "" if val is None else str(val)
    except Exception:
        return ""


def _find_child_for_question(children: List[dict], question: str, idx: int) -> Optional[dict]:
    """
    为给定问题在 children 中找到对应子节点：
    1) 优先通过 question 文本匹配
    2) 若无匹配则回退 index 对齐
    """
    if not isinstance(children, list) or not children:
        return None
    # 文本匹配
    for ch in children:
        if (ch or {}).get("question") == question:
            return ch
    # 索引回退
    if 0 <= idx < len(children):
        return children[idx]
    return None


def write_report(row_id: str, deep_json_path: str, settings: Dict[str, Any], md_path: str) -> None:
    """
    根据 deep.json 的有效节点撰写报告并保存 Markdown

    Args:
        row_id: 编号
        deep_json_path: deep.json 路径
        settings: 配置
        md_path: 输出 md 文件路径
    """
    # 幂等控制：默认跳过已存在文件，除非明确覆盖
    overwrite = (settings.get("deep_analysis", {}).get("report", {}) or {}).get("overwrite_report", False)
    if not overwrite and os.path.exists(md_path):
        # 已存在则跳过
        return

    with open(deep_json_path, "r", encoding="utf-8") as f:
        deep_data = json.load(f)

    summary = _safe_str(deep_data.get("summary"))
    theme = _safe_str(deep_data.get("report_theme"))
    subs = deep_data.get("subtopics", []) or []

    lines: List[str] = []
    lines.append(f"主题：{theme}")
    lines.append(f"概要：{summary}\n")

    for s in subs:
        name = _safe_str(s.get("name"))
        lines.append(f"## 子主题：{name}")

        # 问题清单（确保完整展示 questions，哪怕无任何检索内容也保留）
        questions = s.get("questions", []) or []
        if questions:
            lines.append("### 待回答问题")
            for q in questions:
                lines.append(f"- {q}")
        else:
            lines.append("### 待回答问题")
            lines.append("- （无显式问题，后续段落将按数据可用性输出）")

        # 子主题级别 GLM 兜底内容（当问题级 GLM 缺失时可引用）
        subtopic_glm = s.get("glm") or {}
        subtopic_glm_ok = isinstance(subtopic_glm, dict) and (subtopic_glm.get("meta", {}) or {}).get("status") == "success"
        subtopic_glm_content = _safe_str(subtopic_glm.get("content")) if subtopic_glm_ok else ""

        # 问题级 children
        children = s.get("children", []) or []

        # 逐问题输出“事实信息（Dify）/背景信息（GLM/Web）”
        # 即便内容缺失也要显式标注，保证 LLM 感知缺失并按系统提示词生成说明
        if questions:
            for idx, q in enumerate(questions):
                lines.append("")
                lines.append(f"### 问题：{_safe_str(q)}")

                ch = _find_child_for_question(children, q, idx) if children else None

                # 事实信息（Dify）
                dify_text = ""
                if ch and isinstance(ch.get("dify"), dict):
                    dify_node = ch["dify"]
                    # 不再强制要求 status=success，直接尝试内容；为空则标注缺失
                    dify_text = _safe_str(dify_node.get("content"))

                lines.append("#### 事实信息（Dify）")
                lines.append(dify_text if dify_text.strip() else "（无有效Dify）")

                # 背景信息（GLM/Web）
                glm_text = ""
                if ch and isinstance(ch.get("glm"), dict):
                    glm_node = ch["glm"]
                    # 同样直接尝试内容；为空则回退到子主题级 GLM；仍为空则标注缺失
                    glm_text = _safe_str(glm_node.get("content"))

                if not glm_text.strip() and subtopic_glm_content:
                    glm_text = subtopic_glm_content

                lines.append("#### 背景信息（GLM/Web）")
                lines.append(glm_text if glm_text.strip() else "（无有效GLM）")
        else:
            # 无显式问题时，尽量给出子主题层面的信息概览
            lines.append("")
            lines.append("### 信息概览")
            # 尝试 children 汇总
            any_info = False
            if children:
                for ch in children:
                    q = _safe_str((ch or {}).get("question", "（未标注问题）"))
                    lines.append(f"- 问题：{q}")
                    any_info = True
            if not any_info:
                lines.append("- （无 children 数据）")

            # 仍提供事实/背景两个区块，以子主题级兜底
            lines.append("")
            lines.append("#### 事实信息（Dify）")
            lines.append("（无有效Dify）")  # 无问题级锚点时不做聚合，以缺失呈现
            lines.append("#### 背景信息（GLM/Web）")
            lines.append(subtopic_glm_content if subtopic_glm_content else "（无有效GLM）")

        lines.append("")

    user_prompt = "\n".join(lines) if lines else "无有效检索结果。"

    # 读取系统提示词文件（来自 deep_analysis.report.system_prompt_file）
    report_conf = (settings.get("deep_analysis", {}).get("report", {}) or {})
    sys_file = report_conf.get("system_prompt_file", "l3_deep_analysis_report.md")

    # prompts 目录
    PROMPTS_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "prompts"
    )

    def _read_text(p: str) -> str:
        with open(p, "r", encoding="utf-8") as f:
            return f.read()

    system_text = _read_text(os.path.join(PROMPTS_DIR, sys_file))

    # 构造 messages 并调用统一 API
    messages = [
        {"role": "system", "content": system_text},
        {"role": "user", "content": user_prompt},
    ]

    # 任务名选择：优先使用配置且存在于 tasks，其次使用 deep_analysis_report（若已注册），否则回退 l1_extraction
    tasks_conf = (settings.get("tasks") or {})
    preferred_task = report_conf.get("llm_task_name")
    if preferred_task and preferred_task in tasks_conf:
        llm_task = preferred_task
    elif "deep_analysis_report" in tasks_conf:
        llm_task = "deep_analysis_report"
    else:
        llm_task = "l1_extraction"

    # 统一从 tasks[llm_task] 读取系统提示词，避免与 deep_analysis.report 重复
    try:
        sys_file = tasks_conf[llm_task]["system_prompt_file"]
        system_text = _read_text(os.path.join(PROMPTS_DIR, sys_file))
        messages[0]["content"] = system_text
    except Exception:
        # 若 tasks 未配置 system_prompt_file，则保留此前从 report_conf 读取的 system_text
        pass

    # 直接使用 tasks[llm_task] 的参数，并允许 report 层覆盖请求超时
    request_timeout = None
    try:
        request_timeout = int(report_conf.get("timeout_seconds")) if report_conf.get("timeout_seconds") is not None else None
    except Exception:
        request_timeout = None

    md_text = llm_api.invoke_model(
        llm_task,
        messages,
        settings,
        request_timeout_seconds=request_timeout
    )

    # 写入结果
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_text)