from typing import Any, Dict, List, Optional
import time


def search_wikipedia(entity_label: str, lang: str = "zh", type_hint: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Wikipedia 搜索（函数式）：
    - 使用 wikipediaapi（user_agent='HPD (wzjlxy@gmail.com)'）
    - 返回 title、canonicalurl、summary(<=1000) 与 _page（供上层写 MD），工具自身不进行任何文件写入。
    """
    try:
        import wikipediaapi  # noqa: F401
        available = True
    except Exception as e:
        print(f"wikipedia_import_failed err={e}")
        available = False
    if not available:
        return []

    t0 = time.time()
    try:
        import wikipediaapi
        wiki = wikipediaapi.Wikipedia(user_agent='HPD (wzjlxy@gmail.com)', language=lang)
        page = wiki.page(entity_label)
        results: List[Dict[str, Any]] = []
        if page.exists():
            title = page.title or entity_label
            canonicalurl = getattr(page, "canonicalurl", None)
            if not canonicalurl:
                # canonicalurl 兼容性兜底
                from .common import sanitize_filename
                canonicalurl = f"https://{lang}.wikipedia.org/wiki/{sanitize_filename(title)}"
            summary = (page.summary or "")
            if len(summary) > 1000:
                summary = summary[:1000]
            results.append({
                "title": title,
                "canonicalurl": canonicalurl,
                "summary": summary,
                "_page": page,
            })
        elapsed = int((time.time() - t0) * 1000)
        print(f"wikipedia_search_ok label={entity_label} count={len(results)} elapsed_ms={elapsed}")
        return results
    except Exception as e:
        print(f"wikipedia_search_failed label={entity_label} err={e}")
        return []

if __name__ == "__main__":
    # 可独立运行的测试入口：默认检索"上海戏剧工作社"，可通过命令行参数覆盖
    # 说明：仅进行标准输出与日志记录，不进行任何文件写入
    import argparse

    parser = argparse.ArgumentParser(description="Wikipedia 搜索测试入口")
    parser.add_argument("-q", "--query", default="欧阳予倩", help="检索关键词，默认：上海戏剧工作社")
    parser.add_argument("-l", "--lang", default="zh", help="语言代码（如 zh/en），默认：zh")
    args = parser.parse_args()

    t0 = time.time()
    results = search_wikipedia(args.query, lang=args.lang)
    elapsed_ms = int((time.time() - t0) * 1000)

    # 打印总体信息
    print(f"查询关键词：{args.query} | 语言：{args.lang} | 命中条数：{len(results)} | 耗时：{elapsed_ms}ms")

    # 打印每条结果的关键信息（摘要截断至300字符，确保输出简洁）
    for i, item in enumerate(results, start=1):
        title = item.get("title", "")
        url = item.get("canonicalurl", "")
        summary = (item.get("summary", "") or "")
        if len(summary) > 300:
            summary = summary[:300] + "..."
        print(f"[{i}] 标题：{title}URL：{url}摘要：{summary}")