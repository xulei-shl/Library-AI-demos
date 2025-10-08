import time
from typing import Any, Dict, List, Optional

from ...utils.logger import get_logger

logger = get_logger(__name__)


def _now_iso() -> str:
    """获取当前ISO格式时间戳"""
    import datetime as _dt
    return _dt.datetime.now().astimezone().isoformat()


def process_internal_api_entity(
    ent: Dict[str, Any],
    label: str,
    ent_type: Optional[str],
    context_hint: str,
    settings: Dict[str, Any],
    internal_api_router,
    rate_limit: Dict[str, Any],
    _should_skip: callable,
    _ensure_metadata: callable
) -> bool:
    """
    处理内部API实体检索和匹配（增强：支持别名检索备份机制）
    
    Returns:
        bool: 是否更新了实体数据
    """
    if ent_type and not _should_skip("shl_data", ent):
        # 检查当前实体类型对应的API是否启用
        api_name = internal_api_router.get_api_name(ent_type)
        if not api_name:
            logger.debug(f"internal_api_no_mapping type={ent_type} label={label}")
            return False
        
        # 检查API是否启用
        api_enabled = settings.get("tools", {}).get(api_name, {}).get("enabled", True)
        if not api_enabled:
            logger.debug(f"internal_api_disabled api={api_name} type={ent_type} label={label}")
            return False
        try:
            # 使用支持别名检索的新方法：优先原始检索 + LLM 判定，不匹配时触发别名循环
            alias_search_result = internal_api_router.route_to_api_with_aliases(
                ent_type, label, "zh", ent_type, context_hint, ent.get("wikipedia")
            )

            if alias_search_result.get("matched"):
                sel = alias_search_result.get("selected") or {}
                uri = sel.get("uri")
                description = sel.get("description")

                # 根据配置构建 attributes（按映射后的键名）
                # 1) 确定来源 API 名（在解析阶段注入至候选项）
                api_from_sel = sel.get("__api_name")
                if not api_from_sel:
                    try:
                        api_from_sel = internal_api_router.get_api_name(ent_type)
                    except Exception:
                        api_from_sel = None

                # 2) 读取该 API 的字段配置（用于映射集合）
                tools_cfg = settings.get("tools", {}) or {}
                api_cfg = tools_cfg.get(api_from_sel or "", {}) if isinstance(tools_cfg, dict) else {}
                fields_cfg = api_cfg.get("fields", {}) if isinstance(api_cfg, dict) else {}
                mapping_cfg = fields_cfg.get("mapping", {}) if isinstance(fields_cfg, dict) else {}
                # 已映射后的键集合（mapping 右值）
                mapped_keys = set(mapping_cfg.values()) if isinstance(mapping_cfg, dict) else set()
                # 反向映射（映射后的键 -> 原始字段），用于 _raw 回退填充
                inverse_map = {v: k for k, v in (mapping_cfg.items() if isinstance(mapping_cfg, dict) else [])}

                # 统一行为：不再读取 per-API 输出白名单，全部采用映射后的键集合
                include = mapped_keys or set()

                # 固定顶层键，避免重复放入 attributes
                fixed_top = {"label", "description", "uri"}
                attributes = {}
                for k in include:
                    if k in fixed_top:
                        continue
                    v = sel.get(k)
                    if v is None:
                        raw = sel.get("_raw")
                        if isinstance(raw, dict):
                            orig = inverse_map.get(k)
                            if orig:
                                rv = raw.get(orig)
                                if rv is not None:
                                    v = rv
                    if v is not None:
                        attributes[k] = v

                ent["shl_data"] = {
                    "api": api_from_sel,
                    "uri": uri,
                    "description": description,
                    "label": sel.get("label") or label,
                    "attributes": attributes,
                    "meta": {
                        "executed_at": _now_iso(),
                        "status": "success",
                        "alias_used": alias_search_result.get("alias_used"),
                        "llm": {
                            "matched": True,
                            "confidence": float(alias_search_result.get("confidence") or 0.0),
                            "reason": alias_search_result.get("reason") or "",
                            "selected_label": sel.get("label"),
                            "selected_uri": sel.get("uri"),
                            "model": alias_search_result.get("model"),
                        },
                    },
                }

                # 记录别名检索成功日志
                alias_used = alias_search_result.get("alias_used")
                if alias_used:
                    logger.info(f"internal_api_alias_match_success label={label} alias={alias_used} uri={uri}")
                else:
                    logger.info(f"internal_api_match_success label={label} uri={uri}")
                
                return True
            else:
                # 未匹配：记录尝试次数
                ent["shl_data"] = None
                md = _ensure_metadata(ent)
                md["shl_data"] = {
                    "executed_at": _now_iso(),
                    "status": "not_matched",
                    "error": None,
                    "alias_attempts": alias_search_result.get("alias_attempts", 0),
                }

                logger.info(f"internal_api_not_matched label={label} attempts={alias_search_result.get('alias_attempts', 0)}")
                return True
        except Exception as e:
            ent["shl_data"] = None
            md = _ensure_metadata(ent)
            md["shl_data"] = {
                "executed_at": _now_iso(),
                "status": "error",
                "error": str(e),
            }
            logger.error(f"internal_api_error label={label} err={e}")
            return True
        finally:
            # 添加延迟（如果配置了）
            delay = int(rate_limit.get("internal_api_ms", 1000))
            if delay > 0:
                try:
                    time.sleep(delay / 1000.0)
                except Exception:
                    pass
    return False