#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Subject API 数据映射工具."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

__all__ = [
    "extract_subject_id",
    "map_subject_payload",
]

_SUBJECT_ID_PATTERN = re.compile(r"/subject/(\d+)/")


def extract_subject_id(douban_url: Optional[str]) -> Optional[str]:
    """从豆瓣链接提取 subject_id."""
    if not douban_url:
        return None
    match = _SUBJECT_ID_PATTERN.search(str(douban_url))
    return match.group(1) if match else None


def _first_item(value: Any) -> str:
    if isinstance(value, list) and value:
        return str(value[0]).strip()
    if value in (None, [], {}):
        return ""
    return str(value).strip()


def _join(values: Any) -> str:
    if isinstance(values, list):
        return " / ".join(str(item).strip() for item in values if item)
    return str(values or "").strip()


def map_subject_payload(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """将 subject API 数据映射成统一逻辑字段."""
    if not payload:
        return {}

    rating = payload.get("rating") or {}
    book_series = payload.get("book_series") or {}

    data = {
        "rating": rating.get("value") or 0,
        "rating_count": rating.get("count") or 0,
        "title": payload.get("title") or "",
        "subtitle": _join(payload.get("subtitle") or []),
        "original_title": payload.get("origin_title") or "",
        "author": _join(payload.get("author") or []),
        "translator": _join(payload.get("translator") or []),
        "publisher": _first_item(payload.get("press")),
        "producer": _first_item(payload.get("producers")),
        "series": book_series.get("title") or "",
        "series_link": book_series.get("url") or "",
        "price": _first_item(payload.get("price")),
        "isbn": payload.get("isbn") or "",
        "pages": _first_item(payload.get("pages")),
        "binding": payload.get("binding") or "",
        "pub_year": _first_item(payload.get("pubdate")),
        "cover_image": payload.get("cover_url") or "",
        "summary": payload.get("intro") or "",
        "author_intro": payload.get("author_intro") or "",
        "catalog": payload.get("catalog") or "",
    }

    try:
        data["rating"] = float(data["rating"])
    except (TypeError, ValueError):
        data["rating"] = 0
    try:
        data["rating_count"] = int(data["rating_count"])
    except (TypeError, ValueError):
        data["rating_count"] = 0

    return data
