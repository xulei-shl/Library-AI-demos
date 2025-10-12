from typing import Any, Dict, List, Optional
import os
import re
import time

def _load_wikidata_preferred() -> str:
    """
    从环境变量读取 Wikidata 首选实现：
    - 默认 "lc"
    - 若存在环境变量 WD_USE_LC：
        * "1" -> "lc"
        * "0" -> "api"
    返回值始终为 "lc" 或 "api"
    """
    # 默认优先 LC
    preferred = "lc"

    # 直接使用环境变量
    env_val = os.getenv("WD_USE_LC", "").strip()
    if env_val == "0":
        preferred = "api"
    elif env_val == "1":
        preferred = "lc"

    return preferred

def search_wikidata(entity_label: str, lang: str = "zh", type_hint: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Wikidata 搜索（简化实现）：
    - 默认使用官方 wbsearchentities API
    - 若设置环境变量 WD_USE_LC=1，则使用 LangChain WikidataQueryRun
    """
    t0 = time.time()
    preferred = _load_wikidata_preferred()
    use_lc = (preferred == "lc")

    # 使用 LangChain 实现
    if use_lc:
        try:
            from langchain_community.tools.wikidata.tool import WikidataAPIWrapper, WikidataQueryRun
            
            # 简化初始化，直接使用官方示例的方式
            wikidata = WikidataQueryRun(api_wrapper=WikidataAPIWrapper(lang=lang))
            text = wikidata.run(entity_label) or ""
            
            if "No good Wikidata Search Result was found" in text:
                print(f"wikidata_no_result label={entity_label}")
                return []
            # 解析 LC 返回文本为"段落"，每段以 "Result Qxxxx:" 开始，包含后续 Label/Description/属性等行
            lines = text.splitlines()
            results: List[Dict[str, Any]] = []
            current_qid: Optional[str] = None
            current_buf: List[str] = []

            def _flush_segment():
                # 将当前段落入列（保留完整原文）
                nonlocal current_qid, current_buf, results
                if current_qid and current_buf:
                    segment = "".join([ln.rstrip() for ln in current_buf]).strip()
                    results.append({
                        "id": current_qid,
                        "url": f"https://www.wikidata.org/wiki/{current_qid}",
                        "raw": segment,
                    })

            for ln in lines:
                m = re.match(r"\s*Result\s+(Q\d+):", ln)
                if m:
                    # 新段落开始：先提交上一段
                    if current_qid is not None:
                        _flush_segment()
                        if len(results) >= 2:
                            break
                    current_qid = m.group(1)
                    current_buf = [ln.strip()]
                else:
                    # 段落内追加
                    if current_qid is not None:
                        current_buf.append(ln.strip())

            # 文末提交最后一段
            if len(results) < 2 and current_qid is not None and current_buf:
                _flush_segment()

            # 限制结果数量为前2段
            if len(results) > 2:
                results = results[:2]
            
            elapsed = int((time.time() - t0) * 1000)
            print(f"wikidata_search_ok label={entity_label} count={len(results)} elapsed_ms={elapsed}")
            return results
            
        except Exception as e:
            print(f"wikidata_search_failed label={entity_label} err={e}")
            return []

    # 使用官方 API 实现
    try:
        import httpx
    except Exception as e:
        print(f"httpx_import_failed err={e}")
        return []

    params = {
        "action": "wbsearchentities",
        "search": entity_label,
        "language": lang,
        "limit": 2,
        "format": "json",
    }
    url = "https://www.wikidata.org/w/api.php"
    try:
        with httpx.Client(timeout=httpx.Timeout(10.0)) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("search") or []
            results: List[Dict[str, Any]] = []
            for it in items[:2]:
                qid = it.get("id")
                label = it.get("label") or ""
                desc = it.get("description") or ""
                if not qid:
                    continue
                results.append({
                    "id": qid,
                    "url": f"https://www.wikidata.org/wiki/{qid}",
                    "raw": f"{label} | {desc}".strip(" |"),
                })
            elapsed = int((time.time() - t0) * 1000)
            print(f"wikidata_search_ok label={entity_label} count={len(results)} elapsed_ms={elapsed}")
            return results
    except Exception as e:
        print(f"wikidata_search_failed label={entity_label} err={e}")
        return []

if __name__ == "__main__":
    # 简单测试入口：检索"欧阳予倩"
    query = "欧阳予倩"
    results = search_wikidata(query, lang="en")
    print("查询词：", query)
    print("返回数量：", len(results))
    for i, r in enumerate(results, 1):
        print(f"[{i}] id={r.get('id')} url={r.get('url')} raw={r.get('raw')}")