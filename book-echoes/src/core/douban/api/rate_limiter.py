#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简单的异步并发 + QPS 限流器."""

from __future__ import annotations

import asyncio
import time

__all__ = ["AsyncRateLimiter"]


class AsyncRateLimiter:
    """基于 asyncio 的限流器，控制并发和每秒请求数."""

    def __init__(self, max_concurrent: int = 5, qps: float = 2.0):
        self._semaphore = asyncio.Semaphore(max(1, int(max_concurrent or 1)))
        self._qps = max(qps or 0, 0)
        self._last_ts = 0.0
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        await self._semaphore.acquire()
        await self._throttle()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._semaphore.release()

    async def _throttle(self):
        if self._qps <= 0:
            return
        async with self._lock:
            now = time.monotonic()
            wait = (1.0 / self._qps) - (now - self._last_ts)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_ts = time.monotonic()
