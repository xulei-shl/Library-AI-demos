#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自定义异常定义

用于协调豆瓣评分异步流程中的跨任务错误处理。
"""

from typing import Optional


class DoubanFatalError(RuntimeError):
    """豆瓣爬虫在多次恢复后仍失败时抛出的致命异常。"""


class FolioFatalError(RuntimeError):
    """FOLIO/ISBN 流程在多次恢复后仍失败时抛出的致命异常。"""


class FolioNeedsRestart(RuntimeError):
    """FOLIO 浏览器需要整体重启时抛出的信号异常。"""

    def __init__(self, message: str, barcode: Optional[str] = None):
        super().__init__(message)
        self.barcode = barcode
