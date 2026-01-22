from typing import Dict, List, Optional
from .logger import get_logger
from .excel_io import ExcelIO

logger = get_logger(__name__)

def get_metadata_columns_map(settings: Dict) -> Dict[str, str]:
    """
    获取元数据列键到显示名的映射。
    优先使用 settings['data']['excel']['columns']['metadata']；
    若不存在则回退到旧扁平键（id_col、title_col、desc_col、persons_col、topic_col）。
    """
    excel_cfg = settings.get("data", {}).get("excel", {})
    cols = excel_cfg.get("columns", {}) or {}
    meta = cols.get("metadata")
    if isinstance(meta, dict) and meta:
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

def recommended_metadata_order() -> List[str]:
    """推荐的元数据键顺序。"""
    return ["id", "title", "desc", "persons", "topic", "year", "location", "author", "source"]

def build_metadata_context(row_cells, cols: Dict[str, str], xio: ExcelIO, settings: Dict) -> str:
    """
    构建元数据上下文文本块。
    - 读取 columns.metadata（或旧键回退）形成键->列头映射
    - 根据 tasks.long_description.metadata_fields（如有）或推荐顺序遍历
    - 通过 xio.get_value 读取非空值，渲染为分层文本
    """
    # 键->列头
    key2header = get_metadata_columns_map(settings)
    if not key2header:
        return ""  # 无可用元数据时返回空

    # 字段选择与顺序
    fields_cfg = settings.get("tasks", {}).get("long_description", {}).get("metadata_fields")
    if isinstance(fields_cfg, list) and fields_cfg:
        ordered_keys = [k for k in fields_cfg if k in key2header]
        skipped = [k for k in fields_cfg if k not in key2header]
        if skipped:
            logger.info(f"metadata_fields_skipped keys={skipped}")
    else:
        rec = recommended_metadata_order()
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
        logger.info(f"metadata_context_fields count={len(non_empty_keys)} keys={non_empty_keys}")
    else:
        logger.info("metadata_context_fields count=0")

    return "\n".join(lines) if len(lines) > 1 else ""


def build_unified_context_with_outputs(
    row_cells,
    cols: Dict[str, str],
    xio: ExcelIO,
    settings: Dict,
    include_long_desc: bool = False,
    include_ocr_text: bool = False,
    long_desc_label: str = "[图像长描述]"
) -> str:
    """
    构建包含元数据和可选长描述/OCR文本的统一上下文。

    参数:
        row_cells: Excel 行数据
        cols: 列配置字典（包含 metadata 和 outputs）
        xio: ExcelIO 实例
        settings: 配置字典
        include_long_desc: 是否包含长描述
        include_ocr_text: 是否包含 OCR 文本
        long_desc_label: 长描述块的标签文本

    返回:
        格式化的上下文字符串，各块用双换行分隔
    """
    blocks: List[str] = []

    # 1. 元数据块（复用现有逻辑）
    metadata_block = build_metadata_context(row_cells, cols, xio, settings)
    if metadata_block:
        blocks.append(metadata_block)

    # 2. OCR文本块（优先级高于长描述）
    if include_ocr_text:
        outputs = cols.get("outputs", {}) or {}
        ocr_text_header = outputs.get("ocr_text", "OCR文本")
        ocr_text = xio.get_value(row_cells, ocr_text_header)
        if ocr_text:
            blocks.append(f"[OCR文本]\n{ocr_text}")
    # 3. 长描述块（可选，作为回退）
    elif include_long_desc:
        outputs = cols.get("outputs", {}) or {}
        long_desc_header = outputs.get("long_desc", "长描述")
        long_desc = xio.get_value(row_cells, long_desc_header)
        if long_desc:
            blocks.append(f"{long_desc_label}\n{long_desc}")

    return "\n\n".join(blocks)