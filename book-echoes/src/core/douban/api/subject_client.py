#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""豆瓣 Subject API 客户端."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import httpx

from src.utils.logger import get_logger
from .rate_limiter import AsyncRateLimiter

logger = get_logger(__name__)


class SubjectApiError(RuntimeError):
    """Subject API 调用失败."""


@dataclass
class RetryConfig:
    max_times: int = 3
    backoff: Optional[List[float]] = None

    def next_delay(self, attempt: int) -> float:
        if not self.backoff:
            return min(attempt, 5)
        idx = min(max(attempt - 1, 0), len(self.backoff) - 1)
        return float(self.backoff[idx])


class SubjectApiClient:
    """封装豆瓣 Subject API 访问，提供限流与重试."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        max_concurrent: int = 5,
        qps: float = 2.0,
        retry: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        retry = retry or {}
        self.retry = RetryConfig(
            max_times=int(retry.get("max_times", 3) or 3),
            backoff=list(retry.get("backoff", [1, 3, 5])),
        )
        default_headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)"
            " AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
            "Referer": "https://m.douban.com/",
        }
        if headers:
            default_headers.update(headers)
        self._client = httpx.AsyncClient(timeout=timeout, headers=default_headers)
        self._rate_limiter = AsyncRateLimiter(max_concurrent=max_concurrent, qps=qps)

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "SubjectApiClient":
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def fetch_subject(self, subject_id: str) -> Optional[Dict[str, Any]]:
        subject_id = str(subject_id or "").strip()
        if not subject_id:
            raise ValueError("subject_id 为空")

        attempt = 0
        while attempt < self.retry.max_times:
            attempt += 1
            start = time.monotonic()
            try:
                async with self._rate_limiter:
                    response = await self._client.get(
                        f"{self.base_url}/{subject_id}",
                    )
            except httpx.HTTPError as exc:
                logger.warning(
                    "Subject API 请求异常 - subject_id=%s attempt=%s err=%s",
                    subject_id,
                    attempt,
                    exc,
                )
                await asyncio.sleep(self.retry.next_delay(attempt))
                continue

            latency = (time.monotonic() - start) * 1000
            logger.debug(
                "Subject API 响应 - subject_id=%s status=%s latency=%.0fms",
                subject_id,
                response.status_code,
                latency,
            )

            if response.status_code == 200:
                try:
                    data = response.json()
                except Exception:
                    return None
                try:
                    code = int(data.get("code", 0) or 0)
                    msg = str(data.get("msg", "") or "")
                except Exception:
                    code = 0
                    msg = ""
                if code in {1287, 1284} or (msg and "invalid_request" in msg):
                    logger.warning("Subject API 返回业务错误 - subject_id=%s code=%s msg=%s", subject_id, code, msg)
                    return None
                return data
            if response.status_code == 404:
                return None
            if response.status_code in {429, 500, 502, 503}:
                await asyncio.sleep(self.retry.next_delay(attempt))
                continue

            raise SubjectApiError(
                f"Subject API 返回异常状态 {response.status_code}"
            )

        raise SubjectApiError("Subject API 多次重试仍失败")

    async def fetch_batch(self, subject_ids: Iterable[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        ids = list(dict.fromkeys(str(s).strip() for s in subject_ids if str(s).strip()))
        results: Dict[str, Optional[Dict[str, Any]]] = {}

        async def _runner(sid: str):
            try:
                results[sid] = await self.fetch_subject(sid)
            except Exception as exc:  # noqa: BLE001
                logger.error("Subject API fetch %s failed: %s", sid, exc)
                results[sid] = None

        await asyncio.gather(*[_runner(sid) for sid in ids])
        return results
