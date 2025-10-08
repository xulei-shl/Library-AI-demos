from typing import Any, Dict, List, Optional, Tuple
import json
import os

from ...utils.logger import get_logger
from ...utils.excel_io import ExcelIO
from ...utils.metadata_context import build_metadata_context

logger = get_logger(__name__)


def _norm_label(s: Optional[str]) -> Optional[str]:
    """规范化实体名用于去重键：去空白、全小写。"""
    if s is None:
        return None
    t = str(s).strip()
    return t.lower() if t else None


def _safe_filename(base: str) -> str:
    """
    生成适用于 Windows 的安全文件名：
    - 替换非法字符：<>:"/\\|?* 以及换行
    - 空白替换为下划线
    - 限制最大长度为 64
    """
    if not base:
        return ""
    s = str(base).strip()
    for ch in '<>:"/\\|?*':
        s = s.replace(ch, "_")
    s = s.replace("\n", "_").replace("\r", "_")
    s = s.replace(" ", "_")
    return s[:64] or ""


def _clean_json_text(s: str) -> str:
    """
    清理 Excel 中可能出现的“被额外包裹的字符串/Markdown围栏”的 JSON 文本：
    - 去除首尾反引号围栏（```...```）
    - 若整体被一对引号包裹，尝试去除外层引号
    - 保留内部转义，不做过度替换
    """
    t = s.strip()
    # 剥离简单的 ```json 代码围栏
    if t.startswith("```") and t.endswith("```"):
        inner = t.strip("`")
        # 尝试定位花括号区域
        start = inner.find("{")
        end = inner.rfind("}")
        if start != -1 and end != -1 and end > start:
            t = inner[start : end + 1]
    # 去除整体外层引号包裹：形如 "\"{...}\""
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        t = t[1:-1].strip()
    return t


def _safe_json_loads(s: Optional[str]) -> Optional[Any]:
    """安全解析 JSON，失败返回 None 并记录 WARNING。"""
    if not s:
        return None
    try:
        cleaned = _clean_json_text(s)
        return json.loads(cleaned)
    except Exception as e:
        prev = str(s).replace("\r", " ").replace("\n", " ")
        preview = prev[:200] + ("...(truncated)" if len(prev) > 200 else "")
        logger.warning(f"json_parse_failed preview={preview} err={e}")
        return None


def _add_entity(acc: Dict[str, Dict[str, Any]], label: Optional[str], typ: Optional[str], row_id: str, context_hint: str, source_tag: str) -> None:
    """向聚合映射中加入/合并实体。优先保留已有类型；若新来源提供类型且当前为空则补充。"""
    if not label:
        return
    key = _norm_label(label)
    if not key:
        return
    if key not in acc:
        acc[key] = {
            "label": label.strip(),
            "type": typ if (isinstance(typ, str) and typ.strip()) else None,
            "rows": set([row_id]),
            "sources": set([source_tag]),
            "context_hint": context_hint,  # 取首出现的上下文作为提示
        }
    else:
        acc[key]["rows"].add(row_id)
        acc[key]["sources"].add(source_tag)
        # 类型优先策略：若已有为空而新值明确，则补充；若已有明确则不覆盖
        if not acc[key]["type"] and isinstance(typ, str) and typ.strip():
            acc[key]["type"] = typ.strip()


def _parse_keywords_entities(data: Any, fields: List[str]) -> List[Tuple[str, Optional[str]]]:
    """
    从“关键词JSON”按配置的字段路径抽取实体：
    - 仅处理配置的点号路径，如：
      ["specific_context.location", "specific_context.named_entities"]
    - 匹配规则：
      * 若取值为字符串：加入 (label=该字符串, type=None)
      * 若取值为字符串列表：逐项加入 (label=item, type=None)
    - 忽略其它字段与结构，提升精度与可控性
    返回 (label, type) 列表，type 恒为 None。
    """
    results: List[Tuple[str, Optional[str]]] = []
    if data is None or not isinstance(data, (dict, list)):
        return results

    def _get_by_path(obj: Any, path: str) -> Optional[Any]:
        """按点号路径安全取值，仅支持字典层级。"""
        if not isinstance(obj, dict):
            return None
        cur = obj
        for seg in path.split("."):
            if not isinstance(cur, dict) or seg not in cur:
                return None
            cur = cur.get(seg)
        return cur

    try:
        for p in fields or []:
            val = _get_by_path(data, str(p))
            if isinstance(val, str) and val.strip():
                results.append((val.strip(), None))
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, str) and item.strip():
                        results.append((item.strip(), None))
            # 其它类型忽略（如 dict / 数值），不产生实体
    except Exception as e:
        logger.warning(f"keywords_parse_failed err={e}")
    return results


def _parse_l1_entities(data: Any, field_specs: List[Dict[str, Any]]) -> List[Tuple[str, Optional[str]]]:
    """
    按配置的字段路径从“L1结构化JSON”抽取实体，并为每条路径赋予类型：
    - field_specs 示例：
      [
        {"path": "location", "type": "location"},
        {"path": "architecture", "type": "organization"},
        {"path": "organization", "type": "organization"},
        {"path": "work_title", "type": "work"},
        {"path": "event_title", "type": "event"},
        {"path": "cast.actor", "type": "person"},
        {"path": "persons.name", "type": "person"}
      ]
    - 路径解析支持穿越列表：当遇到 list 时，逐项继续解析剩余段；终值为字符串或字符串列表。
    返回 (label, type) 列表。
    """
    results: List[Tuple[str, Optional[str]]] = []
    if data is None or not isinstance(data, (dict, list)):
        return results

    def _collect_by_path(obj: Any, segs: List[str]) -> List[Any]:
        """递归收集路径对应的终值，支持 dict 和 list 穿越。"""
        if not segs:
            return [obj]
        head, tail = segs[0], segs[1:]
        out: List[Any] = []
        if isinstance(obj, dict):
            if head in obj:
                out.extend(_collect_by_path(obj.get(head), tail))
        elif isinstance(obj, list):
            for el in obj:
                out.extend(_collect_by_path(el, segs))
        return out

    try:
        for spec in field_specs or []:
            path = spec.get("path") if isinstance(spec, dict) else None
            typ = spec.get("type") if isinstance(spec, dict) else None
            if not isinstance(path, str) or not path:
                continue
            values = _collect_by_path(data, path.split("."))
            for v in values:
                if isinstance(v, str) and v.strip():
                    results.append((v.strip(), typ if isinstance(typ, str) and typ.strip() else None))
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, str) and item.strip():
                            results.append((item.strip(), typ if isinstance(typ, str) and typ.strip() else None))
                # 其它类型忽略
    except Exception as e:
        logger.warning(f"l1_parse_failed err={e}")
    return results


def build_task_list(xio: ExcelIO, settings: Dict[str, Any], skip_list_write: bool = False, only_missing_row_json: bool = False) -> List[Dict[str, Any]]:
    """
    构建实体任务列表（Step 1）：
    - 从“关键词JSON”与“L1结构化JSON”两列抽取实体
    - 去重合并，优先采用 L1 的类型；若无类型则置为 None
    - 为每个实体记录出现的行标识 rows 与 context_hint（元数据上下文）
    返回：任务列表（每项至少包含 label, type(Optional), rows, context_hint）
    """
    excel_cfg = settings.get("data", {}).get("excel", {})
    cols_cfg = excel_cfg.get("columns", {}) or {}

    # 列显示名（带默认）
    kw_header = cols_cfg.get("outputs", {}).get("keywords_json", "关键词JSON")
    l1_header = cols_cfg.get("outputs", {}).get("l1_structured_json", "L1结构化JSON")

    # 行标识列（不做缺失跳过判断，缺失时用行号兜底）
    id_header = cols_cfg.get("id_col") or cols_cfg.get("metadata", {}).get("id") or "编号"

    unique_map: Dict[str, Dict[str, Any]] = {}
    processed_rows = 0

    for row_idx, row in xio.iter_rows():
        row_cells = row["cells"]
        row_id_val = xio.get_value(row_cells, id_header)
        row_id = (row_id_val or "").strip() if isinstance(row_id_val, str) else (row_id_val if row_id_val else f"row:{row_idx}")

        # 元数据上下文（供后续模型调用作为提示词的一部分）
        meta_ctx = build_metadata_context(row_cells, cols_cfg, xio, settings)
        context_hint = meta_ctx or ""

        # 解析关键词 JSON（按照配置的字段路径抽取）
        lk_cfg = settings.get("l2_knowledge_linking", {}) or {}
        kw_entity_fields = lk_cfg.get("keywords_entity_fields") or ["specific_context.location", "specific_context.named_entities"]
        kw_text = xio.get_value(row_cells, kw_header)
        kw_data = _safe_json_loads(kw_text)
        kw_entities = _parse_keywords_entities(kw_data, kw_entity_fields)
        if kw_entities:
            logger.info(f"parsed_keywords row={row_idx} count={len(kw_entities)} paths={kw_entity_fields}")

        # 解析 L1 结构化 JSON（按照配置的字段路径与类型抽取）
        lk_cfg = settings.get("l2_knowledge_linking", {}) or {}
        default_l1_specs = [
            {"path": "location", "type": "location"},
            {"path": "architecture", "type": "organization"},
            {"path": "organization", "type": "organization"},
            {"path": "work_title", "type": "work"},
            {"path": "event_title", "type": "event"},
            {"path": "cast.actor", "type": "person"},
            {"path": "persons.name", "type": "person"},
        ]
        l1_specs = lk_cfg.get("l1_entity_fields") or default_l1_specs
        # 规范化：仅保留包含 path 的字典项
        norm_specs = []
        for s in l1_specs:
            if isinstance(s, dict) and isinstance(s.get("path"), str) and s.get("path"):
                norm_specs.append({"path": s["path"], "type": s.get("type")})
        if not norm_specs:
            norm_specs = default_l1_specs

        l1_text = xio.get_value(row_cells, l1_header)
        l1_data = _safe_json_loads(l1_text)
        l1_entities = _parse_l1_entities(l1_data, norm_specs)
        if l1_entities:
            logger.info(f"parsed_l1 row={row_idx} count={len(l1_entities)} paths={[s['path'] for s in norm_specs]}")

        # 合并：先合入关键词，再合入 L1（类型优先）
        for label, typ in kw_entities:
            _add_entity(unique_map, label, None, str(row_id), context_hint, "keywords")
        for label, typ in l1_entities:
            _add_entity(unique_map, label, typ, str(row_id), context_hint, "l1")

        # 将“每行”的实体结果写入单独 JSON 文件（文件名：编号优先；为空用题名前5字符；否则 row_{row_idx}）
        try:
            # 行级聚合（沿用类型优先策略）
            row_acc: Dict[str, Dict[str, Any]] = {}
            for label, _ in kw_entities:
                _add_entity(row_acc, label, None, str(row_id), context_hint, "keywords")
            for label, typ in l1_entities:
                _add_entity(row_acc, label, typ, str(row_id), context_hint, "l1")

            row_entities: List[Dict[str, Any]] = []
            for _, ent in row_acc.items():
                row_entities.append({
                    "label": ent["label"],
                    "type": ent.get("type"),
                    "sources": sorted(list(ent.get("sources", set()))),
                    "context_hint": ent.get("context_hint", ""),
                })

            # 文件名生成：编号 -> 题名前5字符 -> row_{row_idx}
            id_val_raw = xio.get_value(row_cells, id_header)
            id_str = (id_val_raw or "").strip() if isinstance(id_val_raw, str) else (str(id_val_raw) if id_val_raw is not None else "")
            if id_str:
                fname_base = id_str
            else:
                title_val = xio.get_value(row_cells, "题名")
                title_str = (title_val or "").strip() if isinstance(title_val, str) else (str(title_val) if title_val is not None else "")
                fname_base = title_str[:5] if title_str else f"row_{row_idx}"
            fname = _safe_filename(fname_base) or f"row_{row_idx}"

            out_dir = os.path.join("runtime", "outputs")
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, f"{fname}.json")
            
            payload = {
                "row_id": str(row_id),
                "entities": row_entities
            }
            if only_missing_row_json and os.path.exists(out_path):
                logger.info(f"行结果已存在，跳过补写 file={out_path} entities={len(row_entities)}")
            else:
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                logger.info(f"行结果已写入 file={out_path} entities={len(row_entities)}")
        except Exception as e:
            logger.error(f"写入行结果失败 row={row_idx} err={e}")

        processed_rows += 1

    # 输出任务列表：规范化集合类型
    task_list: List[Dict[str, Any]] = []
    for key, ent in unique_map.items():
        task_list.append({
            "label": ent["label"],
            "type": ent.get("type"),
            "rows": sorted(list(ent.get("rows", set()))),
            "sources": sorted(list(ent.get("sources", set()))),
            "context_hint": ent.get("context_hint", ""),
        })

    logger.info(f"task_list_built entities={len(task_list)} rows_processed={processed_rows}")

    # 将任务列表保存到 runtime/outputs/task_list.json（不改变返回结构）
    if skip_list_write:
        logger.info("任务列表写入已跳过（skip_list_write=True）")
    else:
        try:
            out_dir = os.path.join("runtime", "outputs")
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, "task_list.json")
            payload = {"entities": task_list}
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            logger.info(f"任务列表已写入: {out_path}")
        except Exception as e:
            logger.error(f"写入任务列表失败 err={e}")

    return task_list











