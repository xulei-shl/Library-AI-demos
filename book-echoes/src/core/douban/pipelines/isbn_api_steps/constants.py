#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ISBN API 流水线常量定义."""


class ProcessStatus:
    """处理状态常量."""

    PENDING = "待处理"
    DONE = "完成"
    NOT_FOUND = "未找到"
    INVALID_ISBN = "ISBN无效"
    FROM_DB = "数据库已有"
