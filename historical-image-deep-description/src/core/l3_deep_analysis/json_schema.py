# -*- coding: utf-8 -*-
"""
deep.json 结构校验与幂等检查工具
"""
from typing import Dict, Any, List

REQUIRED_KEYS = ["row_id", "summary", "report_theme", "subtopics"]

def is_planning_complete(data: Dict[str, Any]) -> bool:
    """
    判断规划阶段的必需节点是否齐备
    - row_id 非空
    - summary 非空
    - report_theme 非空
    - subtopics 为非空列表，且每项包含 name 与 questions（questions 非空列表）
    """
    try:
        if not data.get("row_id"):
            return False
        if not data.get("summary"):
            return False
        if not data.get("report_theme"):
            return False
        subs = data.get("subtopics")
        if not isinstance(subs, list) or not subs:
            return False
        for s in subs:
            if not s.get("name"):
                return False
            qs = s.get("questions")
            if not isinstance(qs, list) or not qs:
                return False
        return True
    except Exception:
        return False

def subtask_has_success(subtopic: Dict[str, Any], key: str) -> bool:
    """
    检查子任务（glm/dify）是否已完成，作为“是否跳过执行”的幂等判断依据。
    规则：
    - 对 glm：仅检查 subtopic['glm'].meta.status == 'success'
    - 对 dify：若存在逐题 children，则只有当每个 children[*].dify.meta.status ∈ {'success','timeout_recovered'} 才视为“已完成”；
              若无 children，则视为未完成（需要执行以补齐逐题结构）。
    - 任何缺失或为 None 的情况均视为未完成。
    """
    node = subtopic.get(key)
    if not isinstance(node, dict):
        return False

    # 针对 Dify 采用“逐题全成功才算完成”的严格判定
    if key == "dify":
        children = subtopic.get("children")
        if isinstance(children, list) and children:
            for ch in children:
                if not isinstance(ch, dict):
                    return False
                d = ch.get("dify") or {}
                m = d.get("meta") or {}
                st = m.get("status")
                if st not in ("success", "timeout_recovered"):
                    return False
            # 所有子题均成功
            return True
        # 没有 children 时，强制返回未完成，促使进入逐题执行流程
        return False

    # 其他任务（如 GLM）走原有简化语义：meta.status == 'success'
    meta = node.get("meta", {}) if isinstance(node, dict) else {}
    return meta.get("status") == "success"