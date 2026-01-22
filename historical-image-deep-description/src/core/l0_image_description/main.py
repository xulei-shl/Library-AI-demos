import json
import os
from typing import Dict, List, Optional, Tuple

from ...utils.logger import get_logger
from ...utils.llm_api import load_settings, invoke_model, image_to_base64
from ...utils.excel_io import ExcelIO, ExcelConfig
from ...utils.metadata_context import build_metadata_context as _shared_build_metadata_context

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

def _strip_json_code_fence(s: str) -> str:
    t = s.strip()
    if t.startswith("```"):
        # 简单剥离 ```json ... ```
        t = t.strip("`")
        # 更稳妥：查找代码块内容
        if "{" in s and "}" in s:
            start = s.find("{")
            end = s.rfind("}")
            if start != -1 and end != -1 and end > start:
                return s[start:end+1]
    return s

def _build_vision_messages(system_prompt: str, image_b64: str, user_text: str) -> list:
    # 智谱AI要求完整的data URI格式
    image_data_uri = f"data:image/jpeg;base64,{image_b64}"
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": image_data_uri}},
            {"type": "text", "text": user_text}
        ]},
    ]

def _build_text_messages(system_prompt: str, user_text: str) -> list:
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]

def _get_metadata_columns_map(settings: Dict) -> Dict[str, str]:
    """
    获取元数据列键到显示名的映射。
    优先使用 settings['data']['excel']['columns']['metadata']；
    若不存在则回退到旧扁平键（id_col、title_col、desc_col、persons_col、topic_col）。
    """
    excel_cfg = settings.get("data", {}).get("excel", {})
    cols = excel_cfg.get("columns", {}) or {}
    meta = cols.get("metadata")
    if isinstance(meta, dict) and meta:
        # 直接返回新结构
        return {k: str(v) for k, v in meta.items()}
    # 旧结构回退
    fallback: Dict[str, str] = {}
    map_old = {
        "id": cols.get("id_col"),
        "title": cols.get("title_col"),
        "desc": cols.get("desc_col"),
        "persons": cols.get("persons_col"),
        "topic": cols.get("topic_col"),
    }
    for k, v in map_old.items():
        if v:
            fallback[k] = str(v)
    return fallback

def _recommended_order() -> List[str]:
    return ["id", "title", "desc", "persons", "topic", "year", "location", "author", "source"]

def build_metadata_context(row_cells, cols: Dict[str, str], xio: ExcelIO, settings: Dict) -> str:
    """
    构建元数据上下文文本块。
    - 读取 columns.metadata（或旧键回退）形成键->列头映射
    - 根据 tasks.long_description.metadata_fields（如有）或推荐顺序遍历
    - 通过 xio.get_value 读取非空值，渲染为分层文本
    """
    # 键->列头
    key2header = _get_metadata_columns_map(settings)
    if not key2header:
        return ""  # 无可用元数据时返回空

    # 字段选择与顺序
    fields_cfg = settings.get("tasks", {}).get("long_description", {}).get("metadata_fields")
    if isinstance(fields_cfg, list) and fields_cfg:
        ordered_keys = [k for k in fields_cfg if k in key2header]
        skipped = [k for k in fields_cfg if k not in key2header]
        if skipped:
            logger.info(f"元数据字段已跳过 keys={skipped}")
    else:
        rec = _recommended_order()
        # 先按推荐顺序取存在于 key2header 的键
        ordered_keys = [k for k in rec if k in key2header]
        # 追加其余未在推荐序列中的键（保持字典自然顺序）
        for k in key2header.keys():
            if k not in ordered_keys:
                ordered_keys.append(k)

    # 渲染
    lines: List[str] = ["[元数据]"]
    non_empty_keys: List[str] = []
    for k in ordered_keys:
        header = key2header[k]
        val = xio.get_value(row_cells, header)
        if val:
            non_empty_keys.append(k)
            # 标签显示使用列头名，更贴近 Excel
            lines.append(f"- {header}: {val}")

    if non_empty_keys:
        logger.info(f"元数据上下文包含字段 count={len(non_empty_keys)} keys={non_empty_keys}")
    else:
        logger.info("元数据上下文不含字段 count=0")

    return "\n".join(lines) if len(lines) > 1 else ""

def build_unified_context(row_cells, cols: Dict[str, str], xio: ExcelIO, settings: Dict, include_reference: bool = False, reference_priority: Optional[List[str]] = None) -> str:
    """
    统一上下文拼装：始终包含元数据块；当 include_reference=True 时，根据优先级追加 [参考描述] 块。
    reference_priority: 列键优先序列，如 ["long_desc_col", "alt_text_col"]。
    """
    metadata_block = _shared_build_metadata_context(row_cells, cols, xio, settings)
    blocks: List[str] = []
    if metadata_block:
        blocks.append(metadata_block)

    if include_reference:
        prio = reference_priority or ["long_desc_col", "alt_text_col"]
        ref_text: Optional[str] = None
        for key in prio:
            header = cols.get(key)
            if header:
                val = xio.get_value(row_cells, header)
                if val:
                    ref_text = val
                    break
        if ref_text:
            blocks.append("[参考描述]\n" + ref_text)

    return "\n\n".join(blocks)

def run(excel_path: Optional[str] = None, images_dir: Optional[str] = None, tasks: Optional[List[str]] = None, limit: Optional[int] = None) -> None:
    settings = load_settings()
    data_cfg = settings["data"]
    excel_cfg = data_cfg["excel"]
    cols = excel_cfg["columns"]
    write_policy = {"skip_if_present": settings["write_policy"]["skip_if_present"], "create_backup": settings["write_policy"]["create_backup"]}
    outputs_cfg = data_cfg.get("outputs") or settings.get("data", {}).get("outputs")
    if not outputs_cfg:
        outputs_cfg = settings.get("outputs", {"enabled": True, "dir": "runtime/outputs"})

    excel_path = excel_path or data_cfg["paths"]["metadata_excel"]
    images_dir = images_dir or data_cfg["paths"]["images_dir"]
    supported_exts = data_cfg["paths"]["supported_exts"]
    tasks = tasks or ["long_description", "alt_text", "keywords"]

    # Excel IO
    xio = ExcelIO(
        excel_path,
        ExcelConfig(
            sheet_name=excel_cfg.get("sheet_name", ""),
            columns=cols,
            skip_if_present=write_policy["skip_if_present"],
            create_backup=write_policy["create_backup"],
        )
    )

    # 扫描图片映射
    id2img = _scan_images(images_dir, supported_exts)

    # 读取提示词
    sys_prompts = {
        "long_description": _read_text(os.path.join(PROMPTS_DIR, settings["tasks"]["long_description"]["system_prompt_file"])),
        "alt_text": _read_text(os.path.join(PROMPTS_DIR, settings["tasks"]["alt_text"]["system_prompt_file"])),
        "keywords": _read_text(os.path.join(PROMPTS_DIR, settings["tasks"]["keywords"]["system_prompt_file"])),
    }

    def _run_long_description(row_cells, rid_norm, image_b64):
        # 统一上下文：仅元数据块，不追加参考描述
        context_block = build_unified_context(row_cells, cols, xio, settings, include_reference=False)
        user_text = f"{context_block}\n\n请生成详尽、客观、分层的图像长描述。" if context_block else "请生成详尽、客观、分层的图像长描述。"
        task_name = "long_description"
        messages = _build_vision_messages(
            sys_prompts[task_name],
            image_b64,
            user_text
        )
        out = invoke_model(task_name, messages, settings)
        # 获取实际使用的模型名称用于日志
        task_config = settings["tasks"][task_name]
        provider_type = task_config["provider_type"]
        provider_config = settings["api_providers"][provider_type]["primary"]
        model_name = provider_config["model"]
        safe_out = str(out).replace("\r", " ").replace("\n", " ").strip()
        if len(safe_out) > 2000:
            safe_out = safe_out[:2000] + "...(truncated)"
        logger.info(f'LLM原始输出 task={task_name} model={model_name} id={rid_norm} output="{safe_out}"')
        xio.set_value(row_cells, cols["long_desc_col"], out or "")

    def _run_alt_text(row_cells, rid_norm, image_b64):
        # 统一上下文：元数据 + [参考描述]（优先长描述）
        context_block = build_unified_context(row_cells, cols, xio, settings, include_reference=True, reference_priority=["long_desc_col"])
        parts = ["请基于下方图像与上下文，生成高质量的替代文本（Alt Text），适合无障碍与SEO，同时提取图像中的可见文本（OCR）。"]
        if context_block:
            parts.append(context_block)
        user_text = "\n\n".join(parts)

        task_name = "alt_text"
        messages = _build_vision_messages(
            sys_prompts[task_name],
            image_b64,
            user_text
        )
        out = invoke_model(task_name, messages, settings)
        # 获取实际使用的模型名称用于日志
        task_config = settings["tasks"][task_name]
        provider_type = task_config["provider_type"]
        provider_config = settings["api_providers"][provider_type]["primary"]
        model_name = provider_config["model"]
        safe_out = str(out).replace("\r", " ").replace("\n", " ").strip()
        if len(safe_out) > 2000:
            safe_out = safe_out[:2000] + "...(truncated)"
        logger.info(f'LLM原始输出 task={task_name} model={model_name} id={rid_norm} output="{safe_out}"')

        # 解析 JSON 输出
        alt_text_to_write = ""
        ocr_text_to_write = ""
        try:
            cleaned = _strip_json_code_fence(out)
            data = json.loads(cleaned)
            alt_text_to_write = data.get("alt_text", "")
            ocr_text_to_write = data.get("ocr_text", "")
        except Exception:
            logger.warning(f"Alt Text JSON解析失败 id={rid_norm}，使用原始输出")
            alt_text_to_write = out or ""

        xio.set_value(row_cells, cols["alt_text_col"], alt_text_to_write)
        # 写入 OCR 文本（如列存在）
        ocr_col = cols.get("outputs", {}).get("ocr_text")
        if ocr_col:
            xio.set_value(row_cells, ocr_col, ocr_text_to_write)

    def _run_keywords(row_cells, rid_norm):
        # 关键词使用文本模型：输入为统一上下文（元数据 + 参考文本）
        context = build_unified_context(row_cells, cols, xio, settings, include_reference=True, reference_priority=["long_desc_col", "alt_text_col"])
        task_name = "keywords"
        messages = _build_text_messages(
            sys_prompts[task_name],
            f"以下为图像上下文，请提取关键词并仅输出JSON：\n{context}"
        )
        out = invoke_model(task_name, messages, settings)
        # 获取实际使用的模型名称用于日志
        task_config = settings["tasks"][task_name]
        provider_type = task_config["provider_type"]
        provider_config = settings["api_providers"][provider_type]["primary"]
        model_name = provider_config["model"]
        safe_out = str(out).replace("\r", " ").replace("\n", " ").strip()
        if len(safe_out) > 2000:
            safe_out = safe_out[:2000] + "...(truncated)"
        logger.info(f'LLM原始输出 task={task_name} model={model_name} id={rid_norm} output="{safe_out}"')
        to_write = out
        # 解析校验
        try:
            cleaned = _strip_json_code_fence(out)
            json.loads(cleaned)
            to_write = cleaned
        except Exception:
            logger.warning(f"关键词JSON解析失败 id={rid_norm}")
        xio.set_value(row_cells, cols["keywords_col"], to_write or "")

    processed = 0
    for row_idx, row in xio.iter_rows():
        row_cells = row["cells"]
        rid = xio.get_value(row_cells, cols["id_col"])
        rid_norm = _norm_id(rid)
        if not rid_norm:
            logger.warning(f"行记录因缺少ID被跳过 row={row_idx}")
            continue

        img_path = id2img.get(rid_norm)
        if not img_path:
            logger.warning(f"未找到匹配的图片 id={rid_norm} row={row_idx}")
            continue

        # 限流处理
        if limit is not None and processed >= limit:
            break

        # 读取已有值，提前检查是否需要处理
        cur_long = xio.get_value(row_cells, cols["long_desc_col"])
        cur_alt = xio.get_value(row_cells, cols["alt_text_col"])
        ocr_col = cols.get("outputs", {}).get("ocr_text")
        cur_ocr = xio.get_value(row_cells, ocr_col) if ocr_col else None
        cur_kw = xio.get_value(row_cells, cols["keywords_col"])

        # 判断是否需要图像处理任务
        need_vision_tasks = (
            ("long_description" in tasks and (not cur_long or not settings["write_policy"]["skip_if_present"])) or
            ("alt_text" in tasks and (not cur_alt or not settings["write_policy"]["skip_if_present"]))
        )

        # base64编码（仅在需要时进行）
        image_b64 = None
        if need_vision_tasks:
            try:
                image_b64 = image_to_base64(img_path)
            except Exception as e:
                logger.error(f"图片Base64编码失败 id={rid_norm} err={e}")
                continue

        # 任务：长描述（仅在需要时调用）
        if "long_description" in tasks and (not cur_long or not settings["write_policy"]["skip_if_present"]):
            logger.info(f"开始生成长描述 id={rid_norm}")
            _run_long_description(row_cells, rid_norm, image_b64)
        elif "long_description" in tasks:
            logger.info(f"跳过长描述生成 id={rid_norm} 原因=值已存在")

        # 任务：Alt Text（仅在需要时调用）
        # 如果 OCR 列存在但为空，也视为需要重新生成
        need_alt = "alt_text" in tasks and (not cur_alt or not settings["write_policy"]["skip_if_present"])
        if not need_alt and cur_ocr is not None and not cur_ocr:
            need_alt = True

        if need_alt:
            logger.info(f"开始生成替代文本 id={rid_norm}")
            _run_alt_text(row_cells, rid_norm, image_b64)
        elif "alt_text" in tasks:
            logger.info(f"跳过替代文本生成 id={rid_norm} 原因=值已存在")

        # 任务：关键词（严格JSON）
        if "keywords" in tasks and (not cur_kw or not settings["write_policy"]["skip_if_present"]):
            logger.info(f"开始生成关键词 id={rid_norm}")
            _run_keywords(row_cells, rid_norm)
        elif "keywords" in tasks:
            logger.info(f"跳过关键词生成 id={rid_norm} 原因=值已存在")

        processed += 1

    # 保存
    xio.save()

    # 结果单独保存为json（每图一个JSON）
    """
    处理过程中为每张图片生成的数据（如长描述、替代文本、关键词等）保存为独立的
  JSON 文件，存放到一个指定的目录中。
  这段代码的功能是一个占位符或脚手架。完整功能未实现
    """
    outputs = settings.get("data", {}).get("outputs") or settings.get("outputs", {})
    if outputs.get("enabled", True):
        out_dir = outputs.get("dir", "runtime/outputs")
        os.makedirs(out_dir, exist_ok=True)
        # 简单导出：仅记录在 Excel 中已有的新值，避免再次读取整表，此处略（MVP保留后续扩展点）
        logger.info(f"结果独立输出已启用 dir={out_dir}")

def process_image(image_path: str) -> Dict[str, str]:
    """
    单图处理（便于后续独立调用/测试），当前保留占位：由 run 的批处理主流程承担主要逻辑。
    """
    return {}