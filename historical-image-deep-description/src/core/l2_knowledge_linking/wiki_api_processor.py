import os
import time
import re
from typing import Any, Dict, List, Optional

from ...utils.logger import get_logger
from .tools.registry import get_tool
from .tools.common import sanitize_filename
from .entity_matcher import judge_best_match

logger = get_logger(__name__)


def _as_wikidata_uri(qid: Optional[str]) -> Optional[str]:
    """将QID转换为Wikidata URI"""
    if isinstance(qid, str) and qid.strip():
        return f"https://www.wikidata.org/wiki/{qid.strip()}"
    return None


def _write_wikipedia_md(out_dir: str, row_id_for_file: str, label: str, page_obj: Any, meta: Dict[str, Any], ent_type: Optional[str]) -> None:
    """
    将 Wikipedia 全文与元信息写入 MD 文件：
    文件名：{row_id}-{实体名}.md （空格转下划线、非法字符剔除）
    内容：标题、URL、摘要（<=1000）、生成时间戳、实体类型、编号/行标识；全文 page.text
    """
    os.makedirs(out_dir, exist_ok=True)
    safe_row = sanitize_filename(row_id_for_file)
    safe_label = sanitize_filename(label)
    fname = f"{safe_row}-{safe_label}.md"
    path = os.path.join(out_dir, fname)

    title = meta.get("title") or label
    url = meta.get("canonicalurl") or ""
    summary = meta.get("summary") or ""
    ts = time.strftime("%Y-%m-%d %H:%M:%S")

    full_text = ""
    try:
        full_text = getattr(page_obj, "text", "") or ""
    except Exception:
        full_text = ""

    lines: List[str] = [
        f"# {title}",
        "",
        f"- URL: {url}",
        f"- 摘要: {summary}",
        f"- 生成时间: {ts}",
        f"- 实体类型: {ent_type or ''}",
        f"- 行标识: {row_id_for_file}",
        "",
        "## 全文",
        full_text,
    ]
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        logger.info(f"wikipedia_md_written file={path}")
    except Exception as e:
        logger.warning(f"wikipedia_md_write_failed file={path} err={e}")


def _now_iso() -> str:
    """获取当前ISO格式时间戳"""
    import datetime as _dt
    return _dt.datetime.now().astimezone().isoformat()


def process_wikipedia_entity(
    ent: Dict[str, Any],
    label: str,
    ent_type: Optional[str],
    context_hint: str,
    settings: Dict[str, Any],
    wikipedia_search,
    top_k: int,
    rate_limit: Dict[str, Any],
    _should_skip: callable,
    _ensure_metadata: callable
) -> bool:
    """
    处理Wikipedia实体检索和匹配
    
    Returns:
        bool: 是否更新了实体数据
    """
    if not _should_skip("wikipedia", ent):
        try:
            # Wikipedia 语言选择：从配置读取，默认使用中文；若无候选则在 zh/en 间回退一次
            wp_lang_cfg = ((settings.get("tools") or {}).get("wikipedia") or {}).get("lang") or "zh"
            wp_candidates = wikipedia_search(label, lang=wp_lang_cfg, type_hint=ent_type) or []
            if not wp_candidates:
                # 常见语言回退（提升命中率）：在 zh 与 en 之间切换
                alt_lang = "en" if wp_lang_cfg == "zh" else "zh"
                try:
                    wp_candidates = wikipedia_search(label, lang=alt_lang, type_hint=ent_type) or []
                except Exception:
                    # 回退失败则维持空候选
                    wp_candidates = wp_candidates or []
            wp_candidates = wp_candidates[:top_k]
            stripped = [{k: v for k, v in c.items() if k != "_page"} for c in wp_candidates]
            judge = judge_best_match(
                label=label,
                ent_type=ent_type,
                context_hint=context_hint,
                source="wikipedia",
                candidates=stripped,
                settings=settings,
            )
            if judge.get("matched"):
                sel = judge.get("selected") or {}
                canonicalurl = sel.get("canonicalurl") or (stripped[0].get("canonicalurl") if stripped else None)
                description = None
                for c in stripped:
                    if canonicalurl and c.get("canonicalurl") == canonicalurl:
                        description = c.get("summary")
                        break
                ent["wikipedia"] = {
                    "wikipedia_uri": canonicalurl,
                    "description": description,
                    "label": (sel.get("title") or label),
                    "meta": {
                        "executed_at": _now_iso(),
                        "status": "success",
                        "llm": {
                            "matched": True,
                            "confidence": float(judge.get("confidence") or 0.0),
                            "reason": judge.get("reason") or "",
                            "selected_title": sel.get("title"),
                            "selected_id": sel.get("id"),
                            "model": judge.get("model"),
                        },
                    },
                }
                return True
            else:
                ent["wikipedia"] = None
                md = _ensure_metadata(ent)
                md["wikipedia"] = {
                    "executed_at": _now_iso(),
                    "status": "not_matched" if stripped else "not_found",
                    "error": None,
                }
                return True
        except Exception as e:
            ent["wikipedia"] = None
            md = _ensure_metadata(ent)
            md["wikipedia"] = {
                "executed_at": _now_iso(),
                "status": "error",
                "error": str(e),
            }
            return True
        finally:
            # 添加延迟（如果配置了）
            delay = int(rate_limit.get("wikipedia_ms", 1000))
            if delay > 0:
                try:
                    time.sleep(delay / 1000.0)
                except Exception:
                    pass
    return False


def process_wikidata_entity(
    ent: Dict[str, Any],
    label: str,
    ent_type: Optional[str],
    context_hint: str,
    settings: Dict[str, Any],
    wikidata_search,
    top_k: int,
    rate_limit: Dict[str, Any],
    _should_skip: callable,
    _ensure_metadata: callable
) -> bool:
    """
    处理Wikidata实体检索和匹配
    
    Returns:
        bool: 是否更新了实体数据
    """
    if not _should_skip("wikidata", ent):
        try:
            from .parsers.wikidata_llm_parser import format_candidates as wd_format_candidates
            from .parsers.wikidata_llm_parser import fallback_zero_candidates as wd_fallback

            raw_candidates = wikidata_search(label, lang="en", type_hint=ent_type) or []
            raw_candidates = raw_candidates[:top_k]
            logger.info(f"wikidata_search_done label={label} type={ent_type} raw_count={len(raw_candidates)}")
            # 先进行候选格式化（JSON安全、限长）
            fmt_cfg = (settings.get("tasks", {}).get("l2_disambiguation") or {}).get("candidate_limits", {})
            wd_candidates = wd_format_candidates(raw_candidates, fmt_cfg)
            try:
                preview = [{"id": c.get("id"), "label": c.get("label"), "desc": (c.get("desc") or "")[:80], "context": (c.get("context") or "")[:80]} for c in wd_candidates]
                logger.info(f"wikidata_candidates_formatted label={label} candidates={preview}")
            except Exception:
                pass

            if not wd_candidates:
                # 零候选：跳过 LLM，直接写入未匹配元数据
                fb = wd_fallback(label, ent_type)
                ent["wikidata"] = None
                md = _ensure_metadata(ent)
                md["wikidata"] = {
                    "executed_at": _now_iso(),
                    "status": "not_found",
                    "error": None,
                }
                return True
            else:
                # 调用 LLM 进行判定（传入格式化后的候选）
                judge = judge_best_match(
                    label=label,
                    ent_type=ent_type,
                    context_hint=context_hint,
                    source="wikidata",
                    candidates=wd_candidates,
                    settings=settings,
                )
                try:
                    logger.info(f"wikidata_llm_judge label={label} matched={judge.get('matched')} confidence={judge.get('confidence')} reason={(judge.get('reason') or '')[:120]} model={judge.get('model')}")
                    logger.debug(f"wikidata_llm_selection raw_selected={judge.get('selected')} raw_selection={judge.get('selection')}")
                except Exception:
                    pass
                model_name = judge.get("model")
                if judge.get("matched"):
                    # 从 LLM 输出中解析出选择，并将完整候选 + 三个字段合并
                    try:
                        # 这里直接复用 invoke 的原始输出已在 judge 内部解析过，
                        # 但为满足"完整候选+3字段"，再按简化规则做一次定位与合并
                        # 通过 selected.id 或 wikidata_uri/qid 匹配候选
                        # 兼容 selected / selection，并稳健提取 QID
                        sel = judge.get("selected") or judge.get("selection") or {}
                        qid = sel.get("id")
                        if not qid:
                            uri = sel.get("wikidata_uri") or sel.get("url")
                            if isinstance(uri, str):
                                m = re.search(r"/wiki/(Q\d+)", uri)
                                if m:
                                    qid = m.group(1)
                        # 合并生成最终实体节点：完整候选 + confidence/model/reason + meta
                        full = None
                        for c in wd_candidates:
                            if c.get("id") == qid:
                                full = dict(c)
                                break
                        if full is None and wd_candidates:
                            # 兜底选择第一项（极端情况下）
                            logger.warning(f"wikidata_full_selection_fallback_first label={label} qid={qid} fallback_id={wd_candidates[0].get('id')}")
                            full = dict(wd_candidates[0])

                        # 兼容历史结构：补充 wikidata_uri 字段（按规则使用 id 拼接）
                        qid_val = full.get("id")
                        full["wikidata_uri"] = f"https://www.wikidata.org/wiki/{qid_val}" if isinstance(qid_val, str) and qid_val else None
                        # 补充 meta（时间与状态）
                        full["meta"] = {
                            "executed_at": _now_iso(),
                            "status": "success",
                            "llm": {
                                "matched": True,
                                "selected_qid": full.get("id"),
                                "confidence": float(judge.get("confidence") or 0.0),
                                "reason": judge.get("reason") or "",
                                "model": model_name,
                            },
                        }
                        ent["wikidata"] = full
                        logger.info(f"wikidata_selected_ok label={label} qid={full.get('id')} confidence={float(judge.get('confidence') or 0.0)} status=success")
                        return True
                    except Exception as _e:
                        # 若合并失败，按不匹配处理
                        ent["wikidata"] = None
                        md = _ensure_metadata(ent)
                        md["wikidata"] = {
                            "executed_at": _now_iso(),
                            "status": "not_matched",
                            "error": str(_e),
                        }
                        return True
                else:
                    ent["wikidata"] = None
                    md = _ensure_metadata(ent)
                    md["wikidata"] = {
                        "executed_at": _now_iso(),
                        "status": "not_matched",
                        "error": None,
                    }
                    logger.info(f"wikidata_judge_not_matched label={label} reason={(judge.get('reason') or '')[:120]}")
                    return True
        except Exception as e:
            ent["wikidata"] = None
            md = _ensure_metadata(ent)
            md["wikidata"] = {
                "executed_at": _now_iso(),
                "status": "error",
                "error": str(e),
            }
            return True
        finally:
            # 添加延迟（如果配置了）
            delay = int(rate_limit.get("wikidata_ms", 1000))
            if delay > 0:
                try:
                    time.sleep(delay / 1000.0)
                except Exception:
                    pass
    return False