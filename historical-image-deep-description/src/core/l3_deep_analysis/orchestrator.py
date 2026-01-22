# -*- coding: utf-8 -*-
"""
深度分析编排器：三阶段流程
- 阶段1：规划 deep.json
- 阶段2：对子问题执行 GLM 与 Dify 检索（各自独立 meta / 错误 metadata）
- 阶段3：撰写最终报告 {row_id}_deep.md
"""
import os
import json
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta
import time

from src.core.l3_deep_analysis.prompt_builder import build_prompt_from_entity_json
from src.core.l3_deep_analysis.planner import plan_deep_json
from src.core.l3_deep_analysis.json_schema import is_planning_complete, subtask_has_success
from src.core.l3_deep_analysis.executors.glm_executor import call_glm
from src.core.l3_deep_analysis.executors.dify_executor import call_dify
from src.core.l3_deep_analysis.report_writer import write_report
from src.core.l3_deep_analysis.result_relevance_analyzer import ResultRelevanceAnalyzer
from src.utils.logger import get_logger

logger = get_logger(__name__)

def _deep_json_path(output_dir: str, row_id: str) -> str:
    return f"{output_dir}/{row_id}_deep.json"

def _entity_json_path(output_dir: str, row_id: str) -> str:
    return f"{output_dir}/{row_id}.json"

def run_row(row_id: str, settings: Dict[str, Any]) -> None:
    """
    运行单个编号的三阶段流程
    幂等规则：
    - 阶段1：仅当必需节点齐备才跳过；否则执行并覆盖。若执行后节点为 null，则记录但视作跳过。
    - 阶段2：对每个子问题分别检查 Jina/Dify 成功状态；已成功或为 null 均跳过。
    - 阶段3：md 存在且 overwrite_report=false 则跳过。
    """
    output_dir = settings.get("deep_analysis", {}).get("output_dir", "runtime/outputs")
    entity_path = _entity_json_path(output_dir, row_id)
    deep_path = _deep_json_path(output_dir, row_id)

    # 阶段1：规划
    user_prompt = build_prompt_from_entity_json(entity_path)
    deep_data: Dict[str, Any] = {}
    if os.path.exists(deep_path):
        with open(deep_path, "r", encoding="utf-8") as f:
            deep_data = json.load(f)
    if not is_planning_complete(deep_data):
        deep_data = plan_deep_json(row_id, user_prompt, settings, output_dir)

    # 阶段2：检索
    subs: List[Dict[str, Any]] = deep_data.get("subtopics", []) or []
    changed = False

    # 初始化相关性分析器
    relevance_analyzer = ResultRelevanceAnalyzer(settings)

    for i, s in enumerate(subs):
        # GLM（逐题执行 + 题目级幂等 + 聚合写回）
        # 初始化存储结构：仅用于聚合 meta，避免与 children 冲突
        if not isinstance(s.get("glm"), dict):
            s["glm"] = {"meta": {}}

        questions = s.get("questions", []) or []
        # 初始化 children：与 questions 一一对应
        children = s.get("children")
        if not isinstance(children, list):
            children = []
            s["children"] = children
        child_map: Dict[str, Dict[str, Any]] = {}
        for ch in children:
            q0 = ch.get("question")
            if isinstance(q0, str) and q0:
                child_map[q0] = ch
        for q0 in questions:
            if q0 not in child_map:
                ch = {"question": q0}
                children.append(ch)
                child_map[q0] = ch

        successes = 0
        non_success_seen = False
        error_happened = False
        subtopic_name = s.get("name", "")

        for q in questions:
            ch = child_map.get(q) or {}
            prev_status = ((ch.get("glm") or {}).get("meta") or {}).get("status")
            # 题目级幂等：已成功或超时恢复则跳过
            if prev_status in ("success", "timeout_recovered"):
                successes += 1
                continue
            try:
                # 日志：开始调用 GLM
                idx = (questions.index(q) if q in questions else 0)
                total = len(questions)
                qp = (q or "")[:80].replace("\n", " ")
                t0 = time.perf_counter()
                logger.info(f'phase=deep_glm action=call_start row_id={row_id} subtopic="{subtopic_name}" index={idx+1}/{total} question_preview="{qp}"')
                result = call_glm(q, settings)
                meta = (result.get("meta", {}) or {})
                status = meta.get("status")
                content = result.get("content", "")

                # 相关性评估（GLM）
                if status == "success" and content and relevance_analyzer.is_enabled("glm"):
                    # 检查是否已评估
                    existing_meta = ((ch.get("glm") or {}).get("meta") or {})
                    if not relevance_analyzer.should_skip_assessment(existing_meta, "glm"):
                        assessment = relevance_analyzer.assess_result(
                            question=q,
                            content=content,
                            subtopic_name=subtopic_name,
                            executor_type="glm"
                        )
                        if assessment:
                            threshold = relevance_analyzer.get_threshold("glm")
                            result = relevance_analyzer.update_result_meta(
                                result=result,
                                assessment=assessment,
                                threshold=threshold
                            )
                            # 更新 meta 和 status
                            meta = result.get("meta", {})
                            status = meta.get("status")

                ch["glm"] = {
                    "content": content if status in ("success", "timeout_recovered") else None,
                    "meta": meta
                }
                if status in ("success", "timeout_recovered"):
                    successes += 1
                    # 日志：结束本题（成功）
                    elapsed_ms = int((time.perf_counter() - t0) * 1000)
                    content_len = len(content) if isinstance(content, str) else 0
                    logger.info(f'phase=deep_glm action=call_done row_id={row_id} subtopic="{subtopic_name}" index={idx+1}/{total} status={status} elapsed_ms={elapsed_ms} content_len={content_len}')
                    # 进入下一题提示
                    if (idx + 1) < total:
                        logger.info(f'phase=deep_glm action=next row_id={row_id} subtopic="{subtopic_name}" next_index={idx+2}/{total}')
                else:
                    # 日志：结束本题（非成功）
                    elapsed_ms = int((time.perf_counter() - t0) * 1000)
                    logger.info(f'phase=deep_glm action=call_done row_id={row_id} subtopic="{subtopic_name}" index={idx+1}/{total} status={status} elapsed_ms={elapsed_ms} content_len=0 error={meta.get("error")!r}')
                    non_success_seen = True
                    # 将非成功写入 metadata.glm（数组聚合）
                    md = deep_data.setdefault("metadata", {})
                    jarr = md.setdefault("glm", [])
                    jarr.append({
                        "executed_at": meta.get("executed_at"),
                        "status": status or "error",
                        "error": meta.get("error"),
                        "task_type": "web_search",
                        "question": q,
                        "subtopic": subtopic_name
                    })
            except Exception as e:
                # 日志：结束本题（异常）
                try:
                    elapsed_ms = int((time.perf_counter() - t0) * 1000)
                except Exception:
                    elapsed_ms = -1
                idx = (questions.index(q) if q in questions else 0)
                total = len(questions)
                logger.error(f'phase=deep_glm action=call_done row_id={row_id} subtopic="{subtopic_name}" index={idx+1}/{total} status=error elapsed_ms={elapsed_ms} content_len=0 error={str(e)!r}')
                non_success_seen = True
                error_happened = True
                now = datetime.now(timezone(timedelta(hours=8))).isoformat()
                ch["glm"] = {
                    "content": None,
                    "meta": {
                        "executed_at": now,
                        "status": "error",
                        "task_type": "web_search",
                        "search_query": q,
                        "llm_model": "glm-4-assistant",
                        "error": str(e)
                    }
                }
                md = deep_data.setdefault("metadata", {})
                jarr = md.setdefault("glm", [])
                jarr.append({
                    "executed_at": now,
                    "status": "error",
                    "error": str(e),
                    "task_type": "web_search",
                    "question": q,
                    "subtopic": subtopic_name
                })

        # 子主题级聚合：至少一条成功 => success；否则 error/not_found
        s["glm"]["meta"] = {
            "executed_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
            "status": ("success" if successes > 0 else ("error" if error_happened else ("not_found" if non_success_seen else "not_found"))),
            "task_type": "web_search"
        }
        # 子主题聚合日志
        try:
            agg_status = s.get("glm", {}).get("meta", {}).get("status")
            logger.info(f'phase=deep_glm action=subtopic_agg row_id={row_id} subtopic="{subtopic_name}" status={agg_status} successes={successes}')
        except Exception:
            pass
        changed = True

        # Dify（逐题执行 + 题目级幂等 + 配置开关）——保持原有实现不变
        dify_conf = settings.get("deep_analysis", {}).get("dify", {}) or {}
        if dify_conf.get("enabled", True):
            # 初始化存储结构
            if not isinstance(s.get("dify"), dict):
                # 初始化 Dify 存储结构：仅保留专题级摘要 meta，去除冗余 results
                s["dify"] = {"meta": {}}

            # 兼容旧结构迁移：若检测到顶层合并 content 且无 results，则清除 content 以触发逐题重跑
            dify_obj = s.get("dify")
            legacy_combined = isinstance(dify_obj, dict) and ("content" in dify_obj) and (not dify_obj.get("results"))
            # 迁移清理：删除旧的 results 键，统一以 children[*].dify 为唯一入口
            if isinstance(dify_obj, dict) and ("results" in dify_obj):
                try:
                    dify_obj.pop("results", None)
                except Exception:
                    pass
            # 构建已执行题目索引（从 children[*].dify.meta.status 读取，保持题目级幂等）
            done_map: Dict[str, str] = {}
            for ch0 in s.get("children", []) or []:
                q = ch0.get("question")
                st = (ch0.get("dify") or {}).get("meta", {}).get("status")
                if isinstance(q, str) and q:
                    done_map[q] = st
            if legacy_combined:
                # 清除旧的合并内容，避免回退使用；并清空执行索引以触发逐题执行
                try:
                    dify_obj.pop("content", None)
                except Exception:
                    pass
                done_map = {}

            skip_if_executed = bool(dify_conf.get("skip_if_executed", False))
            questions = s.get("questions", []) or []
            # 初始化 children：按问题建立一一对应的子节点，便于后续逐题更新
            children = s.get("children")
            if not isinstance(children, list):
                children = []
                s["children"] = children
            # 建立 question -> child 映射，已存在的直接复用
            child_map: Dict[str, Dict[str, Any]] = {}
            for ch in children:
                q0 = ch.get("question")
                if isinstance(q0, str) and q0:
                    child_map[q0] = ch
            # 确保所有问题都有子节点占位
            for q0 in questions:
                if q0 not in child_map:
                    ch = {"question": q0}
                    children.append(ch)
                    child_map[q0] = ch

            subtopic_name = s.get("name", "")
            successes = 0
            non_success_seen = False
            error_happened = False

            for q in questions:
                # 题目级幂等：已执行则按策略跳过
                if q in done_map:
                    if skip_if_executed or done_map[q] in ("success", "timeout_recovered"):
                        continue
                try:
                    result = call_dify(
                        question=q,
                        subtopic_name=subtopic_name,
                        summary=deep_data.get("summary"),
                        report_theme=deep_data.get("report_theme"),
                        settings=settings
                    )
                    status = result.get("meta", {}).get("status")
                    if status in ("success", "timeout_recovered"):
                        # 同步写入对应子节点的 dify 结果（问题级子节点，唯一承载处）
                        ch = child_map.get(q) or {}
                        ch["dify"] = {
                            "content": result.get("content", ""),
                            "meta": result.get("meta", {})
                        }
                        successes += 1
                    else:
                        non_success_seen = True
                        # 将非成功结果写入 metadata 聚合
                        md = deep_data.setdefault("metadata", {})
                        dify_md = md.setdefault("dify", [])
                        dify_md.append({
                            "executed_at": result.get("meta", {}).get("executed_at"),
                            "status": status,
                            "error": result.get("meta", {}).get("error"),
                            "task_type": "deep_rag_interpretation",
                            "dify_response_id": result.get("meta", {}).get("dify_response_id"),
                            "question": q,
                            "subtopic": subtopic_name
                        })
                        # 同步写入对应子节点的 dify 非成功占位（统一数据入口）
                        ch = child_map.get(q) or {}
                        ch["dify"] = {
                            "content": result.get("content", None),
                            "meta": result.get("meta", {})
                        }
                except Exception as e:
                    non_success_seen = True
                    error_happened = True
                    now = datetime.now(timezone(timedelta(hours=8))).isoformat()
                    # 将错误写入全局 metadata 聚合
                    md = deep_data.setdefault("metadata", {})
                    dify_md = md.setdefault("dify", [])
                    dify_md.append({
                        "executed_at": now,
                        "status": "error",
                        "error": str(e),
                        "task_type": "deep_rag_interpretation",
                        "dify_response_id": None,
                        "question": q,
                        "subtopic": subtopic_name
                    })
                    # 同步写入对应子节点的 dify 错误占位（便于后续更新）
                    ch = child_map.get(q) or {}
                    ch["dify"] = {
                        "content": None,
                        "meta": {
                            "executed_at": now,
                            "status": "error",
                            "task_type": "deep_rag_interpretation",
                            "dify_response_id": None,
                            "error": str(e)
                        }
                    }

            # 聚合元信息：至少一条成功 => success；否则 error/not_found
            agg_status = "success" if successes > 0 else ("error" if error_happened else ("not_found" if non_success_seen else "not_found"))
            s["dify"]["meta"] = {
                "executed_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
                "status": agg_status,
                "task_type": "deep_rag_interpretation"
            }
            changed = True

    if changed:
        with open(deep_path, "w", encoding="utf-8") as f:
            json.dump(deep_data, f, ensure_ascii=False, indent=2)

    # 阶段3：报告
    overwrite = settings.get("deep_analysis", {}).get("overwrite_report", False)
    md_path = f"{output_dir}/{row_id}_deep.md"
    if os.path.exists(md_path) and not overwrite:
        return
    write_report(row_id, deep_path, settings, md_path)