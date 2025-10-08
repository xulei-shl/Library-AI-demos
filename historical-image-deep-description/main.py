import argparse
import os
import json
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from src.core.l0_image_description.main import run as run_l0
from src.utils.logger import init_logging, get_logger
from dotenv import load_dotenv

# deep_analysis 任务模块导入
from src.core.l3_deep_analysis.prompt_builder import build_prompt_from_entity_json
from src.core.l3_deep_analysis.planner import plan_deep_json
from src.core.l3_deep_analysis.json_schema import is_planning_complete, subtask_has_success
from src.core.l3_deep_analysis.executors.glm_executor import call_glm
from src.core.l3_deep_analysis.executors.dify_executor import call_dify
from src.core.l3_deep_analysis.report_writer import write_report
from src.core.l3_deep_analysis.orchestrator import run_row as run_deep_all
from src.core.l3_deep_analysis.excel_loader import load_row_ids

try:
    import yaml
except ImportError:
    yaml = None

def parse_args():
    p = argparse.ArgumentParser(description="历史图像处理流水线（L0→L1→L2→L3） & L3 deep_analysis")
    # 原有流水线参数
    p.add_argument("--tasks", type=str, default=None, help="选择要执行的任务（可逗号分隔）。支持：简单名或命名空间名，如 'alt_text,structured' 或 'l0:long_description,l1:structured,l3:rag,l3:deep_planning'")
    p.add_argument("--limit", type=int, default=None, help="处理条数上限（调试用）")
    # 新增 deep_analysis 参数（统一通过 --tasks 调用 deep_*）
    p.add_argument("--row-id", type=str, default=None, help="编号（例如 2202_001）。可选；未提供时将从 Excel 的“编号”列批量处理（可配合 --limit）")
    p.add_argument("--settings", type=str, default="config/settings.yaml", help="配置文件路径")
    return p.parse_args()

# 任务映射与解析
# - 简单名：全局别名映射到对应模块
# - 命名空间名：module:task（module ∈ {l0,l1,l2}）
_L0_TASKS_CANON = ["long_description", "alt_text", "keywords"]
_ALIAS_TO_TARGET = {
    # L0
    "long_description": ("l0", "long_description"),
    "long": ("l0", "long_description"),
    "alt_text": ("l0", "alt_text"),
    "alt": ("l0", "alt_text"),
    "keywords": ("l0", "keywords"),
    "kw": ("l0", "keywords"),
    # L1（整体任务开关）
    "structured": ("l1", "structured"),
    "structured_json": ("l1", "structured"),
    "l1_structured": ("l1", "structured"),
    "l1": ("l1", "structured"),
    # L2（整体任务开关；阶段需使用命名空间 l2:build/classify/link/write）
    "knowledge_linking": ("l2", "knowledge_linking"),
    "l2": ("l2", "knowledge_linking"),
    "l2_link": ("l2", "knowledge_linking"),
    # L3（整体任务开关；阶段需使用命名空间 l3:rag/retrieval/web）
    "context_interpretation": ("l3", "context_interpretation"),
    "l3": ("l3", "context_interpretation"),
    "rag": ("l3", "rag"),
    "l3_rag": ("l3", "rag"),
    "rag+": ("l3", "rag+"),  # 统一的增强RAG检索触发器
    "web": ("l3", "web"),
    "web_search": ("l3", "web_search"),
    "l3_web": ("l3", "web_search"),
}

def _parse_tasks(raw: Optional[str]) -> Tuple[List[str], bool, List[str], bool, List[str], bool, List[str], bool, List[str]]:
    """
    解析 --tasks 字符串。
    返回:
      - l0_tasks: 顺序列表，元素属于 _L0_TASKS_CANON
      - l1_enabled: 是否需要执行 L1
      - unknown: 未识别项（用于告警）
      - l2_enabled: 是否需要执行 L2
      - l2_phases: L2 阶段列表
      - l3_enabled: 是否需要执行 L3
      - l3_phases: L3 阶段列表
    规则：
      - 允许 "name" 或 "module:name" 两种形式
      - module 支持 l0/l1/l2/l3
      - name 可通过 _ALIAS_TO_TARGET 全局别名映射
    """
    if not raw:
        return [], False, [], False, [], False, []
    l0_tasks: List[str] = []
    l1_enabled = False
    unknown: List[str] = []
    l2_enabled = False
    l2_phases: List[str] = []
    l3_enabled = False
    l3_phases: List[str] = []
    deep_enabled = False
    deep_phases: List[str] = []
    parts = [x.strip() for x in raw.split(",") if x.strip()]
    for item in parts:
        if ":" in item:
            mod, name = item.split(":", 1)
            mod = mod.strip().lower()
            name_key = name.strip().lower()
            if mod == "l0":
                # name_key 也支持别名表（映射后要求落在 _L0_TASKS_CANON）
                target = _ALIAS_TO_TARGET.get(name_key)
                if target and target[0] == "l0":
                    canon = target[1]
                    if canon in _L0_TASKS_CANON:
                        l0_tasks.append(canon)
                    else:
                        unknown.append(item)
                elif name_key in _L0_TASKS_CANON:
                    l0_tasks.append(name_key)
                else:
                    unknown.append(item)
            elif mod == "l1":
                # 任意 name 视为开启 L1（L1 当前为整体任务）
                l1_enabled = True
            elif mod == "l2":
                name_key = name_key.lower()
                # 阶段识别：build/classify/link/write
                if name_key in {"build", "classify", "link", "write"}:
                    if name_key not in l2_phases:
                        l2_phases.append(name_key)
                    l2_enabled = True
                # 整体开关：l2:knowledge_linking（或别名）
                elif name_key in {"knowledge_linking", "l2", "l2_link"}:
                    l2_enabled = True
                else:
                    unknown.append(item)
            elif mod == "l3":
                name_key = name_key.lower()
                # L3 deep_analysis 专属阶段：deep_planning/deep_glm/deep_dify/deep_report/deep_all
                if name_key in {"deep_planning", "deep_glm", "deep_dify", "deep_report", "deep_all"}:
                    if name_key not in deep_phases:
                        deep_phases.append(name_key)
                    deep_enabled = True
                # L3 context_interpretation 阶段识别：rag/retrieval/interpretation/enhanced/web/rag+/web+
                elif name_key in {"rag", "retrieval", "interpretation", "enhanced", "enhanced_event", "web", "web_search", "rag+", "web+"}:
                    if name_key not in l3_phases:
                        l3_phases.append(name_key)
                    l3_enabled = True
                # 整体开关：l3:context_interpretation（或别名）
                elif name_key in {"context_interpretation", "l3", "l3_rag", "l3_web"}:
                    l3_enabled = True
                else:
                    unknown.append(item)
            else:
                unknown.append(item)
        else:
            key = item.lower()
            target = _ALIAS_TO_TARGET.get(key)
            if not target:
                unknown.append(item)
                continue
            if target[0] == "l0":
                canon = target[1]
                if canon in _L0_TASKS_CANON:
                    l0_tasks.append(canon)
                else:
                    unknown.append(item)
            elif target[0] == "l1":
                l1_enabled = True
            elif target[0] == "l2":
                # 简名/别名整体启用 L2（不指定阶段）
                l2_enabled = True
            elif target[0] == "l3":
                # 简名/别名整体启用 L3（不指定阶段）
                l3_enabled = True
                # 特殊处理：对于rag+，添加到l3_phases中
                if key == "rag+":
                    if "rag+" not in l3_phases:
                        l3_phases.append("rag+")
            else:
                unknown.append(item)
    return l0_tasks, l1_enabled, unknown, l2_enabled, l2_phases, l3_enabled, l3_phases, deep_enabled, deep_phases

def _deep_load_settings(path: str) -> Dict[str, Any]:
    if yaml is None:
        raise RuntimeError("未安装 pyyaml，无法读取配置。请安装 pyyaml。")
    if not os.path.exists(path):
        raise RuntimeError(f"配置文件不存在：{path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def _deep_json_path(output_dir: str, row_id: str) -> str:
    return os.path.join(output_dir, f"{row_id}_deep.json")

def _entity_json_path(output_dir: str, row_id: str) -> str:
    return os.path.join(output_dir, f"{row_id}.json")

def _task_deep_planning(row_id: str, settings: Dict[str, Any], logger) -> None:
    """阶段1：生成 {row_id}_deep.json"""
    output_dir = settings.get("deep_analysis", {}).get("output_dir", "runtime/outputs")
    epath = _entity_json_path(output_dir, row_id)
    dpath = _deep_json_path(output_dir, row_id)

    # 构建用户提示
    user_prompt = build_prompt_from_entity_json(epath)
    # 如存在且必需节点齐备，则跳过
    existing = {}
    if os.path.exists(dpath):
        with open(dpath, "r", encoding="utf-8") as f:
            existing = json.load(f)
    if is_planning_complete(existing):
        logger.info(f"[SKIP] 规划阶段已完成，跳过：{dpath}")
        return

    data = plan_deep_json(row_id, user_prompt, settings, output_dir)
    logger.info(f"[OK] 规划 JSON 生成：{dpath}")

def _task_deep_glm(row_id: str, settings: Dict[str, Any], logger) -> None:
    """阶段2-1：仅执行 GLM 检索并写回 deep.json（逐题执行 + 题目级幂等 + 聚合与错误数组）"""
    output_dir = settings.get("deep_analysis", {}).get("output_dir", "runtime/outputs")
    dpath = _deep_json_path(output_dir, row_id)
    if not os.path.exists(dpath):
        raise RuntimeError(f"deep.json 不存在，请先执行 deep_planning：{dpath}")
    with open(dpath, "r", encoding="utf-8") as f:
        data = json.load(f)

    subs: List[Dict[str, Any]] = data.get("subtopics", []) or []
    changed = False
    for s in subs:
        # 初始化聚合元信息容器
        if not isinstance(s.get("glm"), dict):
            s["glm"] = {"meta": {}}

        questions = s.get("questions", []) or []
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
            if prev_status in ("success", "timeout_recovered"):
                successes += 1
                continue
            try:
                result = call_glm(q, settings)
                meta = (result.get("meta", {}) or {})
                status = meta.get("status")
                content = result.get("content", "")
                ch["glm"] = {
                    "content": content if status in ("success", "timeout_recovered") else None,
                    "meta": meta
                }
                if status in ("success", "timeout_recovered"):
                    successes += 1
                else:
                    non_success_seen = True
                    md = data.setdefault("metadata", {})
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
                md = data.setdefault("metadata", {})
                jarr = md.setdefault("glm", [])
                jarr.append({
                    "executed_at": now,
                    "status": "error",
                    "error": str(e),
                    "task_type": "web_search",
                    "question": q,
                    "subtopic": subtopic_name
                })

        s["glm"]["meta"] = {
            "executed_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
            "status": ("success" if successes > 0 else ("error" if error_happened else ("not_found" if non_success_seen else "not_found"))),
            "task_type": "web_search"
        }
        changed = True

    if changed:
        with open(dpath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"[OK] GLM 检索写回：{dpath}")
    else:
        logger.info("[SKIP] 所有子问题均已成功或为 null，跳过 GLM 任务。")

def _task_deep_dify(row_id: str, settings: Dict[str, Any], logger) -> None:
    """阶段2-2：仅执行 Dify 检索并写回 deep.json"""
    output_dir = settings.get("deep_analysis", {}).get("output_dir", "runtime/outputs")
    dpath = _deep_json_path(output_dir, row_id)
    if not os.path.exists(dpath):
        raise RuntimeError(f"deep.json 不存在，请先执行 deep_planning：{dpath}")
    with open(dpath, "r", encoding="utf-8") as f:
        data = json.load(f)

    subs: List[Dict[str, Any]] = data.get("subtopics", []) or []
    changed = False
    for s in subs:
        if not subtask_has_success(s, "dify"):
            try:
                # 初始化存储结构
                if not isinstance(s.get("dify"), dict):
                    s["dify"] = {"meta": {}}
                dify_obj = s.get("dify")
                # 兼容旧结构迁移：若检测到顶层合并 content 且无 results，则清除 content 以触发逐题重跑
                legacy_combined = isinstance(dify_obj, dict) and ("content" in dify_obj) and (not dify_obj.get("results"))
                if legacy_combined:
                    try:
                        dify_obj.pop("content", None)
                    except Exception:
                        pass
                # 迁移清理：删除旧的 results 键，统一以 children[*].dify 为唯一入口
                if isinstance(dify_obj, dict) and ("results" in dify_obj):
                    try:
                        dify_obj.pop("results", None)
                    except Exception:
                        pass

                # 建立 children 映射，确保每个问题都有子节点占位
                questions = s.get("questions", []) or []
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

                subtopic_name = s.get("name", "")
                successes = 0
                non_success_seen = False
                error_happened = False

                # 逐题分别调用 Dify
                for q in questions:
                    res = call_dify(
                        question=q,
                        subtopic_name=subtopic_name,
                        summary=data.get("summary"),
                        report_theme=data.get("report_theme"),
                        settings=settings
                    )
                    meta = res.get("meta", {}) or {}
                    status = meta.get("status")
                    content = res.get("content", "")
                    if status == "error":
                        error_happened = True
                    # 停止写入冗余的 results；统一由 children[*].dify 承载每题结果
                    # 同步写入对应子节点（非成功也写入占位 + meta）
                    ch = child_map.get(q) or {}
                    ch["dify"] = {
                        "content": content if status in ("success", "timeout_recovered") else None,
                        "meta": meta
                    }
                    if status in ("success", "timeout_recovered"):
                        successes += 1
                    else:
                        non_success_seen = True
                        # 将非成功结果写入全局 metadata 聚合（便于汇总）
                        md = data.setdefault("metadata", {})
                        dify_md = md.setdefault("dify", [])
                        dify_md.append({
                            "executed_at": meta.get("executed_at"),
                            "status": status,
                            "error": meta.get("error"),
                            "task_type": "deep_rag_interpretation",
                            "dify_response_id": meta.get("dify_response_id"),
                            "question": q,
                            "subtopic": subtopic_name
                        })

                # 聚合元信息：至少一条成功 => success；否则 not_found
                s["dify"]["meta"] = {
                    "executed_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
                    "status": ("success" if successes > 0 else ("error" if error_happened else ("not_found" if non_success_seen else "not_found"))),
                    "task_type": "deep_rag_interpretation"
                }
            except Exception as e:
                s["dify"] = None
                md = data.setdefault("metadata", {})
                md["dify"] = {
                    "executed_at": data.get("meta", {}).get("executed_at"),
                    "status": "error",
                    "error": str(e),
                    "task_type": "deep_rag_interpretation"
                }
            changed = True

    if changed:
        with open(dpath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"[OK] Dify 检索写回：{dpath}")
    else:
        logger.info("[SKIP] 所有子问题均已成功或为 null，跳过 Dify 任务。")

def _task_deep_report(row_id: str, settings: Dict[str, Any], logger) -> None:
    """阶段3：生成 {row_id}_deep.md（遵循覆盖策略）"""
    output_dir = settings.get("deep_analysis", {}).get("output_dir", "runtime/outputs")
    dpath = _deep_json_path(output_dir, row_id)
    if not os.path.exists(dpath):
        raise RuntimeError(f"deep.json 不存在，请先执行 deep_planning：{dpath}")
    md_path = os.path.join(output_dir, f"{row_id}_deep.md")
    overwrite = settings.get("deep_analysis", {}).get("overwrite_report", False)
    if os.path.exists(md_path) and not overwrite:
        logger.info(f"[SKIP] 报告已存在且不覆盖：{md_path}")
        return
    write_report(row_id, dpath, settings, md_path)
    logger.info(f"[OK] 报告生成：{md_path}")

def main():
    logger = get_logger(__name__)
    init_logging()
    load_dotenv(dotenv_path=".env", override=False)
    args = parse_args()



    # 默认行为：无 --tasks 时，依次执行 L0 全部任务 -> L1 -> L2 -> L3（保留原有逻辑）
    if not args.tasks:
        logger.info("pipeline_default start=L0_all_then_L1_then_L2_then_L3")
        run_l0(excel_path=None, images_dir=None, tasks=None, limit=args.limit)
        from src.core.l1_structured_extraction.main import run as run_l1
        run_l1(excel_path=None, images_dir=None, limit=args.limit)
        from src.core.l2_knowledge_linking.main import run_l2
        run_l2(excel_path=None, images_dir=None, limit=args.limit, tasks=None)
        from src.core.l3_context_interpretation.main import run_l3
        run_l3(excel_path=None, images_dir=None, limit=args.limit, tasks=None)
        return

    # 指定任务：解析跨模块任务
    l0_tasks, l1_enabled, unknown, l2_enabled, l2_phases, l3_enabled, l3_phases, deep_enabled, deep_phases = _parse_tasks(args.tasks)
    if unknown:
        logger.warning(f"tasks_unknown items={unknown}")

    if l0_tasks:
        logger.info(f"pipeline_l0_selected tasks={l0_tasks}")
        run_l0(excel_path=None, images_dir=None, tasks=l0_tasks, limit=args.limit)
    else:
        logger.info("pipeline_l0_skipped reason=no_tasks_selected")

    if l1_enabled:
        logger.info("pipeline_l1_enabled true")
        from src.core.l1_structured_extraction.main import run as run_l1
        run_l1(excel_path=None, images_dir=None, limit=args.limit)
    else:
        logger.info("pipeline_l1_skipped reason=not_selected")

    if l2_enabled:
        if l2_phases:
            logger.info(f"pipeline_l2_enabled true phases={l2_phases}")
        else:
            logger.info("pipeline_l2_enabled true")
        from src.core.l2_knowledge_linking.main import run_l2
        run_l2(excel_path=None, images_dir=None, limit=args.limit, tasks=(l2_phases if l2_phases else None))
    else:
        logger.info("pipeline_l2_skipped reason=not_selected")

    if l3_enabled:
        if l3_phases:
            logger.info(f"pipeline_l3_enabled true phases={l3_phases}")
        else:
            logger.info("pipeline_l3_enabled true")
        from src.core.l3_context_interpretation.main import run_l3
        run_l3(excel_path=None, images_dir=None, limit=args.limit, tasks=(l3_phases if l3_phases else None))
    else:
        logger.info("pipeline_l3_skipped reason=not_selected")

    # L3 deep_analysis：当在 --tasks 中选择了 deep_* 时执行
    if deep_enabled:
        # 读取配置
        settings = _deep_load_settings(args.settings)
        # 去重保持顺序
        phases: List[str] = []
        for p in deep_phases:
            if p not in phases:
                phases.append(p)
        # 深度分析执行：不再推断 row-id；按 Excel 编号驱动，严格文件名匹配
        output_dir = settings.get("deep_analysis", {}).get("output_dir", "runtime/outputs")
        explicit_single = bool(args.row_id)
        if explicit_single:
            ids: List[str] = [args.row_id]
            logger.info(f"pipeline_l3_deep_mode=single id={args.row_id} phases={phases}")
        else:
            data_paths = (settings.get("data", {}) or {}).get("paths", {}) or {}
            excel_cfg = (settings.get("data", {}) or {}).get("excel", {}) or {}
            excel_path = data_paths.get("metadata_excel") or "metadata.xlsx"
            id_column = ((excel_cfg.get("columns", {}) or {}).get("id")) or "编号"
            ids: List[str] = load_row_ids(excel_path, id_column)
            if args.limit is not None and args.limit > 0:
                ids = ids[: args.limit]
            logger.info(f"pipeline_l3_deep_mode=excel ids_count={len(ids)} phases={phases} excel={excel_path} id_col={id_column}")
            if not ids:
                logger.warning("deep_no_ids_from_excel: Excel 中未找到有效编号，跳过 deep_* 执行。")
                return

        # 逐个编号执行；严格匹配输入文件，不做任何变体/模糊匹配
        for rid in ids:
            logger.info(f"deep_process_started row_id={rid}")
            try:
                if "deep_all" in phases:
                    # deep_all 依赖实体 JSON 完全匹配：{rid}.json
                    epath = _entity_json_path(output_dir, rid)
                    if not os.path.exists(epath):
                        msg = f"缺少输入文件（严格匹配要求）：{epath}"
                        if explicit_single:
                            raise RuntimeError(msg)
                        else:
                            logger.warning(f"deep_skip_missing_input row_id={rid} expected={epath}")
                            continue
                    run_deep_all(rid, settings)
                    logger.info(f"[OK] deep_all 完成：{rid}")
                else:
                    for phase in phases:
                        if phase == "deep_planning":
                            epath = _entity_json_path(output_dir, rid)
                            if not os.path.exists(epath):
                                msg = f"缺少输入文件（严格匹配要求）：{epath}"
                                if explicit_single:
                                    raise RuntimeError(msg)
                                else:
                                    logger.warning(f"deep_skip_missing_input row_id={rid} expected={epath}")
                                    continue
                            _task_deep_planning(rid, settings, logger)
                        elif phase == "deep_glm":
                            dpath = _deep_json_path(output_dir, rid)
                            if not os.path.exists(dpath):
                                msg = f"缺少输入文件（严格匹配要求）：{dpath}"
                                if explicit_single:
                                    raise RuntimeError(msg)
                                else:
                                    logger.warning(f"deep_skip_missing_input row_id={rid} expected={dpath}")
                                    continue
                            _task_deep_glm(rid, settings, logger)
                        elif phase == "deep_dify":
                            dpath = _deep_json_path(output_dir, rid)
                            if not os.path.exists(dpath):
                                msg = f"缺少输入文件（严格匹配要求）：{dpath}"
                                if explicit_single:
                                    raise RuntimeError(msg)
                                else:
                                    logger.warning(f"deep_skip_missing_input row_id={rid} expected={dpath}")
                                    continue
                            _task_deep_dify(rid, settings, logger)
                        elif phase == "deep_report":
                            dpath = _deep_json_path(output_dir, rid)
                            if not os.path.exists(dpath):
                                msg = f"缺少输入文件（严格匹配要求）：{dpath}"
                                if explicit_single:
                                    raise RuntimeError(msg)
                                else:
                                    logger.warning(f"deep_skip_missing_input row_id={rid} expected={dpath}")
                                    continue
                            _task_deep_report(rid, settings, logger)
                logger.info(f"deep_process_finished row_id={rid}")
            except Exception as e:
                if explicit_single:
                    # 单编号模式：直接抛出，以便用户修正
                    raise
                else:
                    logger.error(f"deep_process_error row_id={rid} error={e}")
                    # 批量模式：不影响其他编号
                    continue

if __name__ == "__main__":
    main()