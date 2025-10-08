import json
import os
from typing import Dict, List, Optional

from ...utils.logger import get_logger
from ...utils.llm_api import load_settings, invoke_model
from ...utils.excel_io import ExcelIO, ExcelConfig
from ...utils.metadata_context import build_metadata_context

logger = get_logger(__name__)

PROMPTS_DIR = os.path.join("src", "prompts")


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _norm_id(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    return s.strip().lower()


def _scan_images(images_dir: str, exts: List[str]) -> Dict[str, str]:
    m: Dict[str, str] = {}
    if not os.path.isdir(images_dir):
        logger.warning(f"图片目录未找到 dir={images_dir}")
        return m
    for name in os.listdir(images_dir):
        p = os.path.join(images_dir, name)
        if not os.path.isfile(p):
            continue
        _, ext = os.path.splitext(name)
        if ext.lower() in [e.lower() for e in exts]:
            key = _norm_id(os.path.splitext(name)[0])
            if key:
                m[key] = p
    logger.info(f"图片扫描完成 count={len(m)} dir={images_dir}")
    return m


def _build_vision_messages(system_prompt: str, image_b64: str, user_text: str) -> list:
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": image_b64}},
            {"type": "text", "text": user_text}
        ]},
    ]


def _strip_json_code_fence(s: str) -> str:
    t = s.strip()
    if t.startswith("```") and "{" in t and "}" in t:
        start = t.find("{")
        end = t.rfind("}")
        if start != -1 and end != -1 and end > start:
            return t[start:end+1]
    return t


def run(excel_path: Optional[str] = None, images_dir: Optional[str] = None, limit: Optional[int] = None) -> None:
    """
    L1 结构化信息抽取（MVP）
    - 读取 Excel 行数据，构建元数据上下文，调用纯文本模型输出结构化 JSON
    - 若目标列已有值且策略为 skip_if_present 则跳过该行
    - 目标列若不存在则创建
    """
    settings = load_settings()
    data_cfg = settings["data"]
    excel_cfg = data_cfg["excel"]
    cols_cfg = excel_cfg["columns"]
    write_policy = {
        "skip_if_present": settings["write_policy"]["skip_if_present"],
        "create_backup": settings["write_policy"]["create_backup"],
    }

    # 目标输出列名（可从配置覆盖）
    outputs = cols_cfg.get("outputs", {}) or {}
    out_col_header = outputs.get("l1_structured_json", "L1结构化JSON")

    excel_path = excel_path or data_cfg["paths"]["metadata_excel"]


    # Excel IO
    xio = ExcelIO(
        excel_path,
        ExcelConfig(
            sheet_name=excel_cfg.get("sheet_name", ""),
            columns=cols_cfg,
            skip_if_present=write_policy["skip_if_present"],
            create_backup=write_policy["create_backup"],
        )
    )
    # 确保输出列存在（首行表头）
    xio.ensure_column(out_col_header)



    # 读取系统提示词
    task_name = "l1_extraction"
    sys_prompt_file = settings["tasks"][task_name]["system_prompt_file"]
    system_prompt = _read_text(os.path.join(PROMPTS_DIR, sys_prompt_file))

    processed = 0
    for row_idx, row in xio.iter_rows():
        row_cells = row["cells"]
        # 读编号列（兼容旧配置键）
        id_header = cols_cfg.get("id_col") or cols_cfg.get("metadata", {}).get("id") or "编号"
        rid = xio.get_value(row_cells, id_header)
        rid_norm = _norm_id(rid)
        if not rid_norm:
            logger.warning(f"行跳过（无编号） row={row_idx}")
            continue



        # 按行跳过策略
        cur_val = xio.get_value(row_cells, out_col_header)
        if cur_val and write_policy["skip_if_present"]:
            logger.info(f"跳过L1结构化处理 id={rid_norm} reason=已存在")
            continue

        # 限制处理数量
        if limit is not None and processed >= limit:
            break



        # 元数据上下文
        meta_ctx = build_metadata_context(row_cells, cols_cfg, xio, settings)
        user_text_parts: List[str] = []
        if meta_ctx:
            user_text_parts.append(meta_ctx)
        # 明确要求输出 JSON
        user_text_parts.append("请仅基于上述元数据抽取结构化信息，并仅输出JSON（无多余说明/无Markdown围栏）。")
        user_text = "\n\n".join(user_text_parts)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ]
        out = invoke_model(task_name, messages, settings)
        # 结果清理与日志
        cleaned = _strip_json_code_fence(out)
        safe_preview = cleaned.replace("\r", " ").replace("\n", " ").strip()
        if len(safe_preview) > 2000:
            safe_preview = safe_preview[:2000] + "...(truncated)"
        model_name = settings["tasks"][task_name]["model"]
        logger.info(f'LLM原始输出 task={task_name} model={model_name} id={rid_norm} output="{safe_preview}"')

        # 简单校验 JSON，失败则原样写入
        to_write = cleaned
        try:
            json.loads(cleaned)
        except Exception:
            logger.warning(f"L1 JSON解析失败 id={rid_norm}")

        # 写回 Excel（列不存在会自动创建）
        xio.set_value(row_cells, out_col_header, to_write or "")
        processed += 1

    # 保存 Excel
    xio.save()