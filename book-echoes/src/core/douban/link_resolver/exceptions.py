#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""豆瓣链接解析异常定义."""

class LinkResolveError(RuntimeError):
    """链接解析失败."""


class LoginExpiredError(LinkResolveError):
    """登录态失效."""
