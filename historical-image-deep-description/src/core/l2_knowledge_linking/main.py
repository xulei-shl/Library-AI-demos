import os
from typing import Optional, Any, Dict, List

from ...utils.logger import get_logger
from ...utils.llm_api import load_settings
from dotenv import load_dotenv
from ...utils.excel_io import ExcelIO, ExcelConfig
from .task_builder import build_task_list, _safe_filename
from .entity_processor import process_entities
from .result_writer import write_results
from .type_classifier import classify_types

logger = get_logger(__name__)

def _norm_id(s: Optional[str]) -> Optional[str]:
    """规范化编号ID：去空格、转小写。"""
    if s is None:
        return None
    return str(s).strip().lower()

def _resolve_id_header(settings: dict) -> str:
    """
    解析编号列显示名：
    - 优先 data.excel.columns.id_col
    - 其次 data.excel.columns.metadata.id
    - 回退默认“编号”
    """
    excel_cfg = settings.get("data", {}).get("excel", {})
    cols = excel_cfg.get("columns", {}) or {}
    id_col = cols.get("id_col")
    if isinstance(id_col, str) and id_col.strip():
        return id_col.strip()
    meta = cols.get("metadata") or {}
    meta_id = meta.get("id")
    if isinstance(meta_id, str) and meta_id.strip():
        return meta_id.strip()
    return "编号"

def _l2_get_phase_config(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    获取 L2 阶段注册信息与默认顺序，支持从 settings 覆盖触发词与顺序。
    返回：
      {
        "phases": {
          "build": {"id":"build","func":"build_task_list","triggers":[...], "requires":[]},
          "link":  {"id":"link","func":"process_entities","triggers":[...], "requires":["build"]},
          "write": {"id":"write","func":"write_results","triggers":[...], "requires":["link"]},
        },
        "default_order": ["build","link","write"]
      }
    """
    # 默认触发词
    default = {
        "phases": {
            "build": {"id": "build", "func": "build_task_list", "triggers": ["build","entities","tasks","构建","实体"], "requires": []},
            "classify": {"id": "classify", "func": "classify_types", "triggers": ["classify","type","分类","类型"], "requires": ["build"]},
            "link":  {"id": "link",  "func": "process_entities", "triggers": ["link","resolve","disambiguate","关联","消歧"], "requires": ["classify"]},
            "write": {"id": "write", "func": "write_results", "triggers": ["write","emit","save","写回","输出"], "requires": ["link"]},
        },
        "default_order": ["build","classify","link","write"],
    }
    cfg = settings.get("l2_knowledge_linking", {}) or {}
    # 允许通过 settings 覆盖触发词与默认顺序
    phases_override = cfg.get("phases")
    if isinstance(phases_override, list):
        temp = {}
        for item in phases_override:
            if not isinstance(item, dict):
                continue
            pid = item.get("id")
            if not isinstance(pid, str) or not pid.strip():
                continue
            pid = pid.strip()
            if pid not in default["phases"]:
                logger.warning(f"L2配置包含未知阶段，已忽略 id={pid}")
                continue
            triggers = item.get("triggers")
            if isinstance(triggers, list) and triggers:
                default["phases"][pid]["triggers"] = [str(t).strip() for t in triggers if isinstance(t, (str,int))]
    order_override = cfg.get("default_order")
    if isinstance(order_override, list) and order_override:
        # 仅保留合法阶段
        default["default_order"] = [pid for pid in order_override if pid in default["phases"]]
        if not default["default_order"]:
            default["default_order"] = ["build","link","write"]
    return default

def _l2_parse_tasks(tasks: Optional[List[str]], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    将传入的 tasks（阶段触发词列表）解析为阶段ID序列。
    返回：{"selected": [阶段ID...], "unknown": [无法识别的词...]}
    规则：大小写不敏感；匹配阶段 id 或任一触发词；去重保序。
    """
    if not tasks:
        return {"selected": [], "unknown": []}
    # 构造触发表
    trig2pid: Dict[str, str] = {}
    for pid, info in config["phases"].items():
        trig2pid[pid.lower()] = pid
        for t in info.get("triggers", []):
            if isinstance(t, (str,int)):
                trig2pid[str(t).strip().lower()] = pid
    selected: List[str] = []
    unknown: List[str] = []
    seen = set()
    for raw in tasks:
        if raw is None:
            continue
        key = str(raw).strip().lower()
        pid = trig2pid.get(key)
        if not pid:
            unknown.append(str(raw))
            continue
        if pid not in seen:
            selected.append(pid)
            seen.add(pid)
    return {"selected": selected, "unknown": unknown}

def _l2_expand_with_deps(pids: List[str], config: Dict[str, Any]) -> List[str]:
    """
    依据依赖关系自动补齐所需的前置阶段，返回最终执行序列（去重保序）。
    依赖：link->build，write->link（从默认定义读取）
    """
    result: List[str] = []
    seen = set()
    def add_with_deps(pid: str):
        if pid in seen:
            return
        # 先补依赖
        for dep in config["phases"][pid].get("requires", []) or []:
            if dep in config["phases"]:
                add_with_deps(dep)
        if pid not in seen:
            result.append(pid)
            seen.add(pid)
    for pid in pids:
        if pid in config["phases"]:
            add_with_deps(pid)
    return result

def run_l2(excel_path: Optional[str] = None, images_dir: Optional[str] = None, limit: Optional[int] = None, tasks: Optional[List[str]] = None) -> None:
    """
    Step 0：行级前置检查与遍历
    - 仅检查 L2 列是否存在与是否已有值
    - 非空则记录INFO并跳过；空则记录INFO进入后续处理队列（但本步不做处理）
    - 若列不存在则记录WARNING（不创建、不写回）
    """
    settings = load_settings()
    data_cfg = settings["data"]
    excel_cfg = data_cfg["excel"]
    cols_cfg = excel_cfg["columns"]
    write_policy = {
        "skip_if_present": settings["write_policy"]["skip_if_present"],
        "create_backup": settings["write_policy"]["create_backup"],
    }

    # L2 输出列名（固定为反馈指定）
    l2_col_header = "L2知识关联JSON"

    excel_path = excel_path or data_cfg["paths"]["metadata_excel"]

    # Excel IO（首次执行若列不存在则创建该列表头）
    xio = ExcelIO(
        excel_path,
        ExcelConfig(
            sheet_name=excel_cfg.get("sheet_name", ""),
            columns=cols_cfg,
            skip_if_present=write_policy["skip_if_present"],
            create_backup=write_policy["create_backup"],
        )
    )
    # 确保 L2 列存在（仅创建表头，不写入任何行值）
    xio.ensure_column(l2_col_header)

    # Step 0：前置检查（不论选择何阶段，均执行，用于输出队列提示）
    id_header = _resolve_id_header(settings)
    processed = 0
    for row_idx, row in xio.iter_rows():
        row_cells = row["cells"]
        rid = xio.get_value(row_cells, id_header)
        rid_norm = _norm_id(rid)
        if not rid_norm:
            logger.warning(f"L2前置检查跳过（无编号） row={row_idx}")
            continue
        if limit is not None and processed >= limit:
            break
        cur_l2 = xio.get_value(row_cells, l2_col_header)
        if cur_l2:
            logger.info(f"L2已存在，跳过 id={rid_norm} row={row_idx}")
        else:
            logger.info(f"L2待处理队列加入 id={rid_norm} row={row_idx}")
        processed += 1

    # 阶段解析与依赖补齐
    cfg = _l2_get_phase_config(settings)
    parsed = _l2_parse_tasks(tasks, cfg)
    selected = parsed["selected"]
    unknown = parsed["unknown"]
    if unknown:
        logger.warning(f"L2未知触发词: {unknown}")
    if not selected:
        selected = cfg["default_order"]
        logger.info(f"L2未指定阶段，使用默认顺序: {selected}")
    # 当用户显式仅请求 link 时，不自动补齐依赖（避免全量重跑）
    if selected == ["link"]:
        exec_plan = ["link"]
    else:
        exec_plan = _l2_expand_with_deps(selected, cfg)
    logger.info(f"L2最终执行阶段: {exec_plan}")

    # 执行上下文
    task_list: Optional[List[Dict[str, Any]]] = None
    enriched: Optional[List[Dict[str, Any]]] = None

    # 执行阶段（按计划顺序）
    for pid in exec_plan:
        if pid == "build":
            # 若后续包含 classify 阶段，则先检查行级 JSON 是否已存在；全部存在则跳过 builder，部分缺失则仅补缺且不写 task_list.json
            classify_planned = "classify" in exec_plan
            if classify_planned:
                outputs_cfg = settings.get("data", {}).get("outputs", {}) or {}
                out_dir = outputs_cfg.get("dir") or os.path.join("runtime", "outputs")
                ids_to_check: List[str] = []
                processed_check = 0
                for row_idx, row in xio.iter_rows():
                    row_cells = row["cells"]
                    raw_id = xio.get_value(row_cells, id_header)
                    if isinstance(raw_id, str):
                        raw_id = raw_id.strip()
                    elif raw_id is not None:
                        raw_id = str(raw_id)
                    else:
                        raw_id = ""
                    if not raw_id:
                        continue
                    ids_to_check.append(raw_id)
                    processed_check += 1
                    if limit is not None and processed_check >= limit:
                        break
                expected_files = [os.path.join(out_dir, f"{_safe_filename(rid)}.json") for rid in ids_to_check]
                missing = [p for p in expected_files if not os.path.isfile(p)]
                if not missing:
                    logger.info(f"L2构建阶段跳过：检测到所有目标行级JSON已存在 count={len(expected_files)}")
                    task_list = None
                else:
                    logger.info(f"L2构建阶段按需补齐缺失行级JSON missing={len(missing)} dir={out_dir}")
                    task_list = build_task_list(xio, settings, skip_list_write=True, only_missing_row_json=True)
                    if limit is not None and task_list is not None:
                        task_list = task_list[:max(0, int(limit))]
                    logger.info(f"L2任务清单构建完成 tasks={0 if task_list is None else len(task_list)}")
            else:
                task_list = build_task_list(xio, settings)
                if limit is not None and task_list is not None:
                    task_list = task_list[:max(0, int(limit))]
                logger.info(f"L2任务清单构建完成 tasks={0 if task_list is None else len(task_list)}")
        elif pid == "classify":
            # 分类仅针对与 Excel 行编号匹配的行级 JSON 执行，避免误处理聚合清单
            outputs_cfg = settings.get("data", {}).get("outputs", {}) or {}
            out_dir = outputs_cfg.get("dir") or os.path.join("runtime", "outputs")
            json_paths: List[str] = []
            processed_cls = 0
            for row_idx, row in xio.iter_rows():
                row_cells = row["cells"]
                raw_id = xio.get_value(row_cells, id_header)
                if isinstance(raw_id, str):
                    raw_id = raw_id.strip()
                elif raw_id is not None:
                    raw_id = str(raw_id)
                else:
                    raw_id = ""
                if not raw_id:
                    continue
                p = os.path.join(out_dir, f"{_safe_filename(raw_id)}.json")
                if os.path.isfile(p):
                    json_paths.append(p)
                processed_cls += 1
                if limit is not None and processed_cls >= limit:
                    break
            if json_paths:
                classify_types(json_paths=json_paths, settings=settings)
                logger.info(f"L2类型分类完成（按行级JSON处理） files={len(json_paths)}")
            else:
                logger.info("分类阶段未发现匹配行级JSON，已跳过")
        elif pid == "link":
            # 在显式 link-only 模式下，不强制补齐 build/classify
            # 若 outputs 下缺少行级 JSON，process_entities 内部将自动调用 builder 进行补全
            enriched = process_entities(task_list or [], xio, settings)
            logger.info(f"L2实体处理完成 enriched={0 if enriched is None else len(enriched)}")
        elif pid == "write":
            # 依赖：link -> build
            if enriched is None:
                logger.info("检测到缺少前置产物 enriched，自动执行 link（将按需补齐 build）")
                if task_list is None:
                    task_list = build_task_list(xio, settings)
                    if limit is not None and task_list is not None:
                        task_list = task_list[:max(0, int(limit))]
                enriched = process_entities(task_list or [], xio, settings)
            write_results(enriched or [], xio, settings)
            logger.info(f"L2写回完成 tasks={0 if task_list is None else len(task_list)} enriched={0 if enriched is None else len(enriched)} header={l2_col_header}")
        else:
            logger.warning(f"未实现的阶段 id={pid}，已跳过")

    # 若未包含 write 阶段，输出整体流水日志汇总
    if "write" not in exec_plan:
        logger.info(f"L2阶段执行完成 plan={exec_plan}（未执行写回）")

def _tb_load_settings(config_path: str) -> Dict[str, Any]:
    """加载配置文件（支持 YAML/JSON）。用于 task_builder 的 CLI 支持。"""
    import os, json
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    try:
        if config_path.lower().endswith((".yaml", ".yml")):
            try:
                import yaml  # 需要 PyYAML
            except Exception:
                logger.error("未安装 PyYAML，无法解析 YAML。请先安装: pip install pyyaml")
                raise
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        else:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f) or {}
    except Exception as e:
        logger.error(f"配置解析失败 path={config_path} err={e}")
        raise

def _tb_build_excel_io_from_settings(settings: Dict[str, Any], excel_override: Optional[str] = None, sheet_override: Optional[str] = None) -> ExcelIO:
    """根据 settings 构造 ExcelIO（task_builder CLI 辅助）。"""
    data_paths = settings.get("data", {}).get("paths", {}) or {}
    excel_cfg = settings.get("data", {}).get("excel", {}) or {}
    write_policy = settings.get("write_policy", {}) or {}

    excel_path = excel_override or data_paths.get("metadata_excel") or "metadata.xlsx"
    sheet_name = sheet_override if (sheet_override is not None) else (excel_cfg.get("sheet_name") or "")
    columns = excel_cfg.get("columns", {}) or {}
    skip_if_present = bool(write_policy.get("skip_if_present", True))
    create_backup = bool(write_policy.get("create_backup", True))

    cfg = ExcelConfig(
        sheet_name=sheet_name,
        columns=columns,
        skip_if_present=skip_if_present,
        create_backup=create_backup,
    )
    return ExcelIO(excel_path, cfg)

def _tb_preview_print(task_list: List[Dict[str, Any]], limit: int = 20) -> None:
    """控制台预览任务列表（集中到 main.py）。"""
    n = len(task_list)
    logger.info(f"实体总数: {n}")
    print("=== 任务列表预览 ===")
    for i, item in enumerate(task_list[:max(0, limit)]):
        label = item.get("label")
        typ = item.get("type")
        rows = item.get("rows", [])
        sources = item.get("sources", [])
        print(f"{i+1}. label={label} type={typ} rows={rows} sources={sources}")
    if n > limit:
        print(f"... 已省略 {n - limit} 项")

def _tb_write_output(task_list: List[Dict[str, Any]], settings: Dict[str, Any], output_override: Optional[str] = None) -> Optional[str]:
    """按配置写入任务列表到 runtime/outputs/task_list.json。"""
    import os, json
    from datetime import datetime
    outputs_cfg = settings.get("data", {}).get("outputs", {}) or settings.get("outputs", {}) or {}
    enabled = outputs_cfg.get("enabled", True)
    out_dir = outputs_cfg.get("dir", "runtime/outputs")
    if output_override:
        out_path = output_override
        out_dir = os.path.dirname(out_path) or "."
    else:
        out_path = os.path.join(out_dir, "task_list.json")
    if not enabled and not output_override:
        logger.info("输出写入已禁用（enabled=false），仅控制台预览。")
        return None
    os.makedirs(out_dir, exist_ok=True)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "count": len(task_list),
        "items": task_list,
    }
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        logger.info(f"任务列表已写入: {out_path}")
        return out_path
    except Exception as e:
        logger.error(f"写入任务列表失败 path={out_path} err={e}")
        return None

# 保留原有 run_l2 的 __main__ CLI，不新增新的入口，任务构建的 CLI 由主入口统一编排时调用上述 _tb_* 辅助。
if __name__ == "__main__":
    """
    简易CLI用于本模块独立调试：
    - 实际任务编排应由仓库主入口统一管理（参见主入口任务编排文档）
    - 支持环境变量 L2_LIMIT 控制遍历上限
    """
    import argparse
    # 加载 .env 环境变量，避免在独立运行L2时出现 missing_env_key
    load_dotenv(dotenv_path=".env", override=False)

    parser = argparse.ArgumentParser(description="L2知识关联调试入口（支持阶段触发）")
    parser.add_argument("--excel", dest="excel_path", type=str, default=None, help="Excel路径（默认读取配置）")
    parser.add_argument("--limit", dest="limit", type=int, default=None, help="处理行数上限")
    parser.add_argument("--l2", dest="l2_tasks", type=str, default=None, help="L2阶段列表，逗号分隔，如: build,link,write")
    args = parser.parse_args()

    env_limit = os.getenv("L2_LIMIT")
    limit = args.limit
    if limit is None and env_limit:
        try:
            limit = int(env_limit)
        except Exception:
            limit = None

    # 解析 --l2 阶段参数
    tasks = None
    if args.l2_tasks:
        tasks = [seg.strip() for seg in str(args.l2_tasks).split(",") if seg.strip()]
    run_l2(excel_path=args.excel_path, images_dir=None, limit=limit, tasks=tasks)