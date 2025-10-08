import os
import time
from typing import Any, Dict, List, Optional

from ...utils.logger import get_logger
from ...utils.llm_api import load_settings, invoke_model
from ...utils.excel_io import ExcelIO
from ...utils.metadata_context import build_metadata_context
from .tools.registry import get_tool, initialize_internal_apis, get_internal_api_router
from .task_builder import build_task_list
from .tools.common import sanitize_filename
from .entity_matcher import judge_best_match
from .wiki_api_processor import process_wikipedia_entity, process_wikidata_entity, _write_wikipedia_md
from .internal_api_processor import process_internal_api_entity
from .related_event_searcher import RelatedEventSearcher

logger = get_logger(__name__)

PROMPTS_DIR = os.path.join("src", "prompts")


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _norm_row_id(s: Optional[str], fallback: str) -> str:
    """
    规范化行标识：
    - 优先使用编号列值（非空）
    - 缺失时使用 fallback（如 row:12）
    - 用于日志与MD文件命名
    """
    if s is None:
        return fallback
    t = str(s).strip()
    return t if t else fallback


def process_entities(task_list: List[Dict[str, Any]], xio: ExcelIO, settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    从 runtime/outputs 下的逐行 JSON 文件读取实体，并针对每个实体执行：
    - Wikipedia 检索 -> 大模型判定 -> 成功则写入 {wikipedia_uri, description, meta}，失败则将实体.wikipedia 置为 null 并在 metadata.wikipedia 记录状态
    - Wikidata 检索 -> 大模型判定 -> 成功则写入 {wikidata_uri, description, meta}，失败则将实体.wikidata 置为 null 并在 metadata.wikidata 记录状态
    - 终态跳过：当对应 meta.status in {"success","not_found","not_matched"} 时默认跳过；可通过 settings.overwrite=True 强制重跑
    - 所有写回在原 JSON 文件内完成（原地覆盖）
    返回：处理概要信息列表（row_id、label、各源状态）
    """
    # 配置
    outputs_cfg = settings.get("data", {}).get("outputs", {}) or settings.get("outputs", {"dir": "runtime/outputs"})
    out_dir = outputs_cfg.get("dir", "runtime/outputs")
    overwrite = bool(settings.get("overwrite", False))
    rate_limit = settings.get("rate_limit", {}) or {}
    # 合并内部API速率限制配置
    internal_rate_limits = settings.get("internal_api_rate_limits", {}) or {}
    rate_limit = {**rate_limit, **internal_rate_limits}
    top_k = int(settings.get("top_k", 5))
    terminal_status = {"success", "not_found", "not_matched"}
    # 工具启用配置：从 settings['tools'] 读取每个工具的 enabled 开关，默认 True
    tools_cfg = settings.get("tools") or {}
    
    # 初始化内部API
    initialize_internal_apis(settings)
    internal_api_router = get_internal_api_router(settings)
    
    # 初始化相关事件检索器
    related_event_searcher = RelatedEventSearcher(settings)

    def _is_tool_enabled(name: str) -> bool:
        """
        判断工具是否启用；默认启用。
        Args:
            name: 工具名称，例如 'wikipedia' 或 'wikidata'
        Returns:
            bool: 是否启用
        """
        node = tools_cfg.get(name)
        if isinstance(node, dict):
            val = node.get("enabled")
            if isinstance(val, bool):
                return val
        return True

    wikidata_enabled = _is_tool_enabled("wikidata")
    wikipedia_enabled = _is_tool_enabled("wikipedia")
    
    # 检查内部API是否启用 - 从新的配置结构中检查是否有任何内部API启用
    internal_apis_enabled = any(
        api_config.get("enabled", False)
        for api_name, api_config in settings.get("tools", {}).items()
        if api_name.endswith("_api")
    )

    # 工具注册表（按配置启用/禁用）
    wikidata_search = get_tool("wikidata") if wikidata_enabled else None
    wikipedia_search = get_tool("wikipedia") if wikipedia_enabled else None
    if not wikidata_enabled:
        logger.info("wikidata 工具在配置中被禁用，本次将跳过 Wikidata 查询")
        wikidata_search = lambda label, lang="zh", type_hint=None: []  # noqa: E731
    elif wikidata_search is None:
        logger.warning("wikidata 工具未注册，所有 Wikidata 查询将返回空列表")
        wikidata_search = lambda label, lang="zh", type_hint=None: []  # noqa: E731
    if not wikipedia_enabled:
        logger.info("wikipedia 工具在配置中被禁用，本次将跳过 Wikipedia 查询")
        wikipedia_search = lambda label, lang="zh", type_hint=None: []  # noqa: E731
    elif wikipedia_search is None:
        logger.warning("wikipedia 工具未注册，所有 Wikipedia 查询将返回空列表")
        wikipedia_search = lambda label, lang="zh", type_hint=None: []  # noqa: E731

    # LLM 判定

    def _now_iso() -> str:
        import datetime as _dt
        return _dt.datetime.now().astimezone().isoformat()

    def _should_skip(source_key: str, entity: Dict[str, Any]) -> bool:
        if overwrite:
            return False
        node = entity.get(source_key)
        if isinstance(node, dict):
            meta = node.get("meta") or {}
            st = str(meta.get("status") or "").lower()
            if st in terminal_status:
                return True
        meta_root = (entity.get("metadata") or {}).get(source_key) or {}
        st2 = str(meta_root.get("status") or "").lower()
        return st2 in terminal_status

    def _ensure_metadata(entity: Dict[str, Any]) -> Dict[str, Any]:
        md = entity.get("metadata")
        if not isinstance(md, dict):
            md = {}
            entity["metadata"] = md
        return md

    processed_summary: List[Dict[str, Any]] = []

    # 遍历 outputs_dir 下的 JSON 文件
    try:
        files = [f for f in os.listdir(out_dir) if f.lower().endswith(".json")]
    except Exception as e:
        logger.error(f"outputs_dir_unreadable dir={out_dir} err={e}")
        return []

    # 若没有任何行级JSON，按需补全：调用 builder 生成（命名规则与内容均由 builder 保证）
    if not files:
        try:
            build_task_list(xio, settings)
            files = [f for f in os.listdir(out_dir) if f.lower().endswith(".json")]
            logger.info(f"outputs_json_built_by_builder count={len(files)} dir={out_dir}")
        except Exception as _e:
            logger.error(f"outputs_json_build_failed dir={out_dir} err={_e}")
            return []

    for fname in files:
        fpath = os.path.join(out_dir, fname)
        try:
            import json
            with open(fpath, "r", encoding="utf-8") as rf:
                data = json.load(rf)
        except Exception as e:
            logger.warning(f"json_read_failed file={fpath} err={e}")
            continue

        row_id = str(data.get("row_id") or os.path.splitext(fname)[0])
        entities = data.get("entities") or []
        updated = False

        for idx, ent in enumerate(entities):
            label = ent.get("label") or ""
            ent_type = ent.get("type")
            context_hint = ent.get("context_hint") or ent.get("context") or ""
            # 确保存在元数据容器：即使成功路径也保持 metadata 字段，便于审计与测试约束
            _ensure_metadata(ent)

            # Wikipedia 流程（按配置启用/禁用）
            if wikipedia_enabled:
                if process_wikipedia_entity(
                    ent, label, ent_type, context_hint, settings,
                    wikipedia_search, top_k, rate_limit, _should_skip, _ensure_metadata
                ):
                    updated = True

            # Wikidata 流程（按配置启用/禁用）
            if wikidata_enabled:
                if process_wikidata_entity(
                    ent, label, ent_type, context_hint, settings,
                    wikidata_search, top_k, rate_limit, _should_skip, _ensure_metadata
                ):
                    updated = True
    
            # 内部API流程（增强：支持别名检索备份机制）
            if internal_apis_enabled:
                if process_internal_api_entity(
                    ent, label, ent_type, context_hint, settings,
                    internal_api_router, rate_limit, _should_skip, _ensure_metadata
                ):
                    updated = True
                    
            # 相关事件检索流程
            if related_event_searcher.is_enabled_for_entity_type(ent_type):
                if process_related_events(
                    ent, label, ent_type, context_hint,
                    related_event_searcher, _should_skip, _ensure_metadata
                ):
                    updated = True
     
            processed_summary.append({
                "row_id": row_id,
                "label": label,
                "wikipedia_status": (ent.get("wikipedia") or {}).get("meta", {}).get("status")
                                            if isinstance(ent.get("wikipedia"), dict) else
                                            ((ent.get("metadata") or {}).get("wikipedia") or {}).get("status"),
                "wikidata_status": (ent.get("wikidata") or {}).get("meta", {}).get("status")
                                            if isinstance(ent.get("wikidata"), dict) else
                                            ((ent.get("metadata") or {}).get("wikidata") or {}).get("status"),
                "internal_api_status": (ent.get("shl_data") or {}).get("meta", {}).get("status")
                                            if isinstance(ent.get("shl_data"), dict) else
                                            ((ent.get("metadata") or {}).get("shl_data") or {}).get("status"),
                "related_events_status": (ent.get("related_events") or {}).get("meta", {}).get("status")
                                            if isinstance(ent.get("related_events"), dict) else
                                            ((ent.get("metadata") or {}).get("related_events") or {}).get("status"),
            })

        # 写回文件
        if updated:
            try:
                import json
                with open(fpath, "w", encoding="utf-8") as wf:
                    json.dump(data, wf, ensure_ascii=False, indent=2)
                logger.info(f"json_updated file={fpath} row_id={row_id}")
            except Exception as e:
                logger.error(f"json_write_failed file={fpath} err={e}")

    logger.info(f"entities_processed_from_json files={len(files)}")
    return processed_summary


def process_related_events(
    ent: Dict[str, Any],
    label: str,
    ent_type: str,
    context_hint: str,
    related_event_searcher: 'RelatedEventSearcher',
    _should_skip: callable,
    _ensure_metadata: callable
) -> bool:
    """
    处理实体的相关事件检索与匹配
    
    Args:
        ent: 实体对象
        label: 实体标签
        ent_type: 实体类型
        context_hint: 上下文提示
        related_event_searcher: 相关事件检索器
        _should_skip: 跳过检查函数
        _ensure_metadata: 元数据确保函数
        
    Returns:
        bool: 是否更新了实体数据
    """
    # 检查是否应该跳过处理
    if _should_skip("related_events", ent):
        logger.debug(f"related_events_skipped label={label} type={ent_type}")
        return False
    
    try:
        # 执行相关事件检索
        search_result = related_event_searcher.search_related_events(
            entity_label=label,
            entity_type=ent_type,
            context_hint=context_hint
        )
        
        events = search_result.get("events", [])
        metadata = search_result.get("metadata", {})
        
        if events:
            # 有相关事件，保存到实体
            ent["related_events"] = {
                "events": events,
                "meta": {
                    "executed_at": metadata.get("executed_at"),
                    "status": "success",
                    "search_keyword": metadata.get("search_keyword"),
                    "keyword_extracted": metadata.get("keyword_extracted", False),
                    "total_candidates": metadata.get("total_candidates", 0),
                    "filtered_candidates": metadata.get("filtered_candidates", 0),
                    "events_count": len(events),
                    "model": metadata.get("model")
                }
            }
            logger.info(f"related_events_found label={label} type={ent_type} count={len(events)} keyword={metadata.get('search_keyword')}")
        else:
            # 未找到相关事件
            ent["related_events"] = None
            md = _ensure_metadata(ent)
            md["related_events"] = {
                "executed_at": metadata.get("executed_at"),
                "status": "not_found",
                "reason": metadata.get("reason", "未找到相关事件"),
                "search_keyword": metadata.get("search_keyword"),
                "keyword_extracted": metadata.get("keyword_extracted", False),
                "total_candidates": metadata.get("total_candidates", 0),
                "filtered_candidates": metadata.get("filtered_candidates", 0)
            }
            logger.info(f"related_events_not_found label={label} type={ent_type} keyword={metadata.get('search_keyword')}")
        
        return True
        
    except Exception as e:
        # 处理失败
        ent["related_events"] = None
        md = _ensure_metadata(ent)
        md["related_events"] = {
            "executed_at": _now_iso(),
            "status": "error",
            "error": str(e)
        }
        logger.error(f"related_events_error label={label} type={ent_type} error={e}")
        return True