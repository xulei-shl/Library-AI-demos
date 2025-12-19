#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""字段归一化工具."""

from __future__ import annotations

import math
import re
from typing import Any


def _is_nan(value: Any) -> bool:
    """判断值是否为NaN."""
    if isinstance(value, float):
        return math.isnan(value)
    return False


def normalize_barcode(value: Any) -> str:
    """标准化条码，去除Excel自动附带的.0后缀."""
    if value is None:
        return ""

    if isinstance(value, float):
        if _is_nan(value):
            return ""
        if value.is_integer():
            return str(int(value))
        return str(value).strip()

    if isinstance(value, int):
        return str(value)

    value_str = str(value).strip()
    if not value_str or value_str.lower() == "nan":
        return ""

    if value_str.endswith(".0") and value_str[:-2].isdigit():
        return value_str[:-2]
    return value_str


def normalize_call_no(value: Any) -> str:
    """标准化索书号，忽略大小写与多余空格."""
    if value is None:
        return ""

    if isinstance(value, float) and _is_nan(value):
        return ""

    value_str = str(value).strip()
    if not value_str:
        return ""

    if value_str.lower() in {"nan", "none"}:
        return ""

    collapsed = re.sub(r"\s+", " ", value_str)
    return collapsed.upper()
