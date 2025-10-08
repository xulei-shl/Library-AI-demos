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