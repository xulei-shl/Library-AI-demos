import json
from typing import Any, Dict, List, Optional

from ...utils.logger import get_logger
from ...utils.excel_io import ExcelIO, ExcelConfig  # ExcelConfig 仅为类型提示一致性
# 说明：本模块仅写回，不修改 L1；L2 列名固定为“L2知识关联JSON”

logger = get_logger(__name__)


def _resolve_id_header(settings: Dict[str, Any]) -> str:
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


def _row_identifier(xio: ExcelIO, row_cells, id_header: str, row_idx: int) -> str:
    """
    行标识生成：
    - 优先使用编号列的非空值
    - 缺失时使用 "row:{row_idx}"
    """
    rid = xio.get_value(row_cells, id_header)
    if isinstance(rid, str):
        rid = rid.strip()
    if rid:
        return str(rid)
    return f"row:{row_idx}"


def _entity_to_row_json(ent: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    过滤并构建写回 JSON 的实体对象（不包含 Wikipedia FullText）。
    - 保持现有 Wikidata/Wikipedia 摘要字段不变；
    - 新增可按配置输出的 shl_data 摘要（原 internal_api），不影响两者写入。
      统一策略：Excel 写回不使用 per-API 白名单；与运行时一致，直接写回 attributes。
    """
    obj: Dict[str, Any] = {
        "label": ent.get("label"),
        "type": ent.get("type"),
        "wikidata_uri": ent.get("wikidata_uri"),
        "wikipedia_uri": ent.get("wikipedia_uri"),
        "status": ent.get("status"),
        "_raw_api_responses": {
            # 保留上游提供的要点；不包含全文
            "wikidata": ent.get("_raw_api_responses", {}).get("wikidata") or [],
            "wikipedia": ent.get("_raw_api_responses", {}).get("wikipedia") or [],
        },
    }

    # 可选：按配置输出 shl_data 摘要（不影响 wiki 字段）
    sa = ent.get("shl_data")
    if isinstance(sa, dict) and sa:
        api_name = sa.get("api")
        # 统一行为：不再读取 per-API 白名单；Excel 写回与运行时一致，直接写回 attributes
        attrs_src = sa.get("attributes") or {}
        attrs_out: Dict[str, Any] = {}
        if isinstance(attrs_src, dict):
            attrs_out = dict(attrs_src)

        obj["shl_data"] = {
            "api": api_name,
            "label": sa.get("label"),
            "uri": sa.get("uri"),
            "description": sa.get("description"),
            "attributes": attrs_out,
            # 精简元信息；如需可在此追加状态等
        }

    return obj


def write_results(enriched_entities: List[Dict[str, Any]], xio: ExcelIO, settings: Dict[str, Any]) -> None:
    """
    Step 3：将 enriched 实体按行聚合并写回 L2 列（“L2知识关联JSON”）。
    - 不修改 L1；仅基于 enriched_entities 的 rows 匹配当前行。
    - 若无实体匹配则写回 {"entities": []}
    """
    # 固定 L2 列名（按反馈）
    l2_col_header = "L2知识关联JSON"
    # 创建列（若不存在则新增到表头）
    xio.ensure_column(l2_col_header)

    id_header = _resolve_id_header(settings)
    total_rows = 0
    rows_written = 0

    # 为加速匹配，先将 enriched_entities 建索引：row_id -> [entities...]
    row_index: Dict[str, List[Dict[str, Any]]] = {}
    for ent in enriched_entities or []:
        for rid in ent.get("rows") or []:
            if not isinstance(rid, str):
                rid = str(rid)
            row_index.setdefault(rid, []).append(ent)

    # 遍历 Excel 行并写回
    for row_idx, row in xio.iter_rows():
        total_rows += 1
        row_cells = row["cells"]
        rid = _row_identifier(xio, row_cells, id_header, row_idx)

        ents = row_index.get(rid, [])
        payload = {
            "entities": [_entity_to_row_json(e, settings) for e in ents]
        }

        # 写回（覆盖旧值）
        try:
            s = json.dumps(payload, ensure_ascii=False)
            # 预览日志（截断）
            preview = s.replace("\r", " ").replace("\n", " ")
            if len(preview) > 500:
                preview = preview[:500] + "...(truncated)"
            logger.info(f"L2写回 row_id={rid} entities={len(ents)} preview={preview}")
            xio.set_value(row_cells, l2_col_header, s)
            rows_written += 1
        except Exception as e:
            logger.error(f"L2写回失败 row_id={rid} err={e}")

    # 保存 Excel
    try:
        xio.save()
        logger.info(f"L2写回完成 rows_written={rows_written} total_rows={total_rows} column={l2_col_header}")
    except Exception as e:
        logger.error(f"L2保存失败 err={e}")