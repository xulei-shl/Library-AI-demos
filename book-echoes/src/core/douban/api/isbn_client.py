#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""豆瓣 ISBN API 客户端.

通过 ISBN 直接调用豆瓣移动版 API 获取图书信息，
无需经过爬虫搜索获取链接的步骤。
"""

from __future__ import annotations

import asyncio
import random
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx

from src.utils.logger import get_logger
from .rate_limiter import AsyncRateLimiter

logger = get_logger(__name__)

__all__ = ["IsbnApiClient", "IsbnApiError", "IsbnApiConfig", "normalize_isbn", "preprocess_excel_isbn"]


class IsbnApiError(RuntimeError):
    """ISBN API 调用失败."""


@dataclass
class RetryConfig:
    """重试配置."""
    max_times: int = 3
    backoff: Optional[List[float]] = None

    def next_delay(self, attempt: int) -> float:
        if not self.backoff:
            return min(attempt, 5)
        idx = min(max(attempt - 1, 0), len(self.backoff) - 1)
        return float(self.backoff[idx])


@dataclass
class IsbnApiConfig:
    """ISBN API 配置."""
    base_url: str = "https://m.douban.com/rexxar/api/v2/book/isbn"
    timeout: float = 15.0
    max_concurrent: int = 2
    qps: float = 0.5
    # 随机延迟配置
    random_delay_enabled: bool = True
    random_delay_min: float = 1.5
    random_delay_max: float = 3.5
    # 批次冷却配置
    batch_cooldown_enabled: bool = True
    batch_cooldown_interval: int = 20
    batch_cooldown_min: float = 30.0
    batch_cooldown_max: float = 60.0
    # 重试配置
    retry_max_times: int = 3
    retry_backoff: Optional[List[float]] = None

    def __post_init__(self):
        if self.retry_backoff is None:
            self.retry_backoff = [2, 5, 10]


# User-Agent 池 - 移动端 UA
USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; Pixel 4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Mobile Safari/537.36",
]

# ISBN 格式正则
ISBN_PATTERN = re.compile(r"^(\d{10}|\d{13})$")


def preprocess_excel_isbn(value) -> str:
    """预处理 Excel 中的 ISBN 值，将各种格式转换为文本.

    处理以下 Excel 格式问题：
    - 数字类型存储导致前导零丢失
    - 科学计数法（如 9.78712E+12）
    - 浮点数格式（如 9787121123456.0）
    - None 或 NaN 值

    Args:
        value: Excel 单元格原始值（可能是 int, float, str, None）

    Returns:
        标准化的字符串格式，空值返回空字符串
    """
    if value is None:
        return ""

    # 处理 pandas NaN
    try:
        import pandas as pd
        if pd.isna(value):
            return ""
    except (ImportError, TypeError):
        pass

    # 处理浮点数（科学计数法或带小数点）
    if isinstance(value, float):
        try:
            # 转换为整数再转字符串，避免小数点和科学计数法
            int_value = int(value)
            return str(int_value)
        except (ValueError, OverflowError):
            return str(value)

    # 处理整数
    if isinstance(value, int):
        return str(value)

    # 字符串：去除首尾空格
    return str(value).strip()


def normalize_isbn(isbn) -> Optional[str]:
    """标准化 ISBN：去除分隔符，保留纯数字.

    Args:
        isbn: ISBN 值（支持任意类型，会先进行 Excel 格式预处理）

    Returns:
        标准化后的 ISBN（10位或13位纯数字），无效则返回 None
    """
    # 先进行 Excel 格式预处理
    preprocessed = preprocess_excel_isbn(isbn)
    if not preprocessed:
        return None
    # 去除所有非数字字符
    cleaned = re.sub(r"[^0-9]", "", preprocessed)
    # 校验格式（10位或13位数字）
    if ISBN_PATTERN.match(cleaned):
        return cleaned
    return None


class IsbnApiClient:
    """豆瓣 ISBN API 客户端.

    封装豆瓣 ISBN API 的调用逻辑，包含：
    - 限流控制（QPS 和并发）
    - 随机延迟（模拟人类操作）
    - User-Agent 轮换
    - 重试机制（指数退避）
    - 批次冷却（避免触发反爬）
    """

    def __init__(
        self,
        config: Optional[IsbnApiConfig] = None,
        # 兼容直接传参
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_concurrent: Optional[int] = None,
        qps: Optional[float] = None,
        retry: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """初始化 ISBN API 客户端.

        Args:
            config: IsbnApiConfig 配置对象
            base_url: API 基础 URL（兼容旧接口）
            timeout: 请求超时时间（兼容旧接口）
            max_concurrent: 最大并发数（兼容旧接口）
            qps: 每秒请求数（兼容旧接口）
            retry: 重试配置字典（兼容旧接口）
            headers: 自定义请求头（兼容旧接口）
        """
        # 使用配置对象或默认配置
        if config:
            self._config = config
        else:
            self._config = IsbnApiConfig()
            if base_url:
                self._config.base_url = base_url
            if timeout is not None:
                self._config.timeout = timeout
            if max_concurrent is not None:
                self._config.max_concurrent = max_concurrent
            if qps is not None:
                self._config.qps = qps
            if retry:
                self._config.retry_max_times = int(retry.get("max_times", 3) or 3)
                self._config.retry_backoff = list(retry.get("backoff", [2, 5, 10]))

        self.retry = RetryConfig(
            max_times=self._config.retry_max_times,
            backoff=self._config.retry_backoff,
        )

        # 构建请求头
        default_headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": random.choice(USER_AGENTS),
            "Referer": "https://m.douban.com/",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        if headers:
            default_headers.update(headers)

        self._client = httpx.AsyncClient(
            timeout=self._config.timeout,
            headers=default_headers,
        )
        self._rate_limiter = AsyncRateLimiter(
            max_concurrent=self._config.max_concurrent,
            qps=self._config.qps,
        )
        self._request_count = 0
        self._ua_index = 0

    async def close(self) -> None:
        """关闭客户端连接."""
        await self._client.aclose()

    async def __aenter__(self) -> "IsbnApiClient":
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    def _rotate_user_agent(self) -> None:
        """轮换 User-Agent."""
        self._ua_index = (self._ua_index + 1) % len(USER_AGENTS)
        self._client.headers["User-Agent"] = USER_AGENTS[self._ua_index]

    async def _random_delay(self) -> None:
        """执行随机延迟."""
        if not self._config.random_delay_enabled:
            return
        delay = random.uniform(
            self._config.random_delay_min,
            self._config.random_delay_max,
        )
        await asyncio.sleep(delay)

    async def _batch_cooldown(self) -> None:
        """批次冷却：每处理 N 条后休息较长时间."""
        if not self._config.batch_cooldown_enabled:
            return
        if self._request_count > 0 and self._request_count % self._config.batch_cooldown_interval == 0:
            cooldown = random.uniform(
                self._config.batch_cooldown_min,
                self._config.batch_cooldown_max,
            )
            logger.info(f"批次冷却：已处理 {self._request_count} 条，休息 {cooldown:.1f} 秒...")
            await asyncio.sleep(cooldown)

    async def fetch_by_isbn(self, isbn: str) -> Optional[Dict[str, Any]]:
        """根据 ISBN 获取图书信息.

        Args:
            isbn: ISBN 号（支持带分隔符的格式，会自动标准化）

        Returns:
            图书信息字典，如果未找到或失败则返回 None
        """
        normalized = normalize_isbn(isbn)
        if not normalized:
            logger.warning(f"无效的 ISBN 格式: {isbn}")
            return None

        self._request_count += 1
        self._rotate_user_agent()

        # 执行随机延迟
        await self._random_delay()

        # 检查是否需要批次冷却
        await self._batch_cooldown()

        attempt = 0
        while attempt < self.retry.max_times:
            attempt += 1
            start = time.monotonic()

            try:
                async with self._rate_limiter:
                    response = await self._client.get(
                        f"{self._config.base_url}/{normalized}",
                    )
            except httpx.HTTPError as exc:
                logger.warning(
                    "ISBN API 请求异常 - isbn=%s attempt=%s err=%s",
                    normalized,
                    attempt,
                    exc,
                )
                await asyncio.sleep(self.retry.next_delay(attempt))
                continue

            latency = (time.monotonic() - start) * 1000
            logger.debug(
                "ISBN API 响应 - isbn=%s status=%s latency=%.0fms",
                normalized,
                response.status_code,
                latency,
            )

            if response.status_code == 200:
                try:
                    data = response.json()
                except Exception:
                    logger.warning(f"ISBN API JSON 解析失败 - isbn={normalized}")
                    return None

                # 检查业务错误码
                try:
                    code = int(data.get("code", 0) or 0)
                    msg = str(data.get("msg", "") or "")
                except Exception:
                    code = 0
                    msg = ""

                if code in {1287, 1284} or (msg and "invalid_request" in msg):
                    logger.warning(
                        "ISBN API 返回业务错误 - isbn=%s code=%s msg=%s",
                        normalized,
                        code,
                        msg,
                    )
                    return None

                logger.info(f"ISBN API 成功获取图书信息 - isbn={normalized}")
                return data

            if response.status_code == 404:
                logger.info(f"ISBN API 未找到图书 - isbn={normalized}")
                return None

            if response.status_code in {429, 500, 502, 503}:
                delay = self.retry.next_delay(attempt)
                logger.warning(
                    f"ISBN API 状态码 {response.status_code}，等待 {delay}s 后重试 - isbn={normalized}"
                )
                await asyncio.sleep(delay)
                continue

            logger.error(f"ISBN API 返回异常状态 {response.status_code} - isbn={normalized}")
            return None

        logger.error(f"ISBN API 多次重试仍失败 - isbn={normalized}")
        return None

    async def fetch_batch(
        self,
        isbn_list: Iterable[str],
        progress_callback: Optional[callable] = None,
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """批量获取图书信息.

        Args:
            isbn_list: ISBN 列表
            progress_callback: 进度回调函数，签名 (current, total, isbn, success) -> None

        Returns:
            字典，键为标准化后的 ISBN，值为图书信息（失败则为 None）
        """
        # 去重并标准化
        isbn_mapping: Dict[str, str] = {}  # 标准化 ISBN -> 原始 ISBN
        for isbn in isbn_list:
            normalized = normalize_isbn(isbn)
            if normalized and normalized not in isbn_mapping:
                isbn_mapping[normalized] = isbn

        results: Dict[str, Optional[Dict[str, Any]]] = {}
        total = len(isbn_mapping)

        if total == 0:
            logger.info("没有有效的 ISBN 需要处理")
            return results

        logger.info(f"开始批量获取图书信息，共 {total} 条有效 ISBN")

        # 顺序处理（保持反爬策略的有效性）
        for idx, (normalized, original) in enumerate(isbn_mapping.items(), 1):
            try:
                data = await self.fetch_by_isbn(normalized)
                results[normalized] = data
                success = data is not None

                if progress_callback:
                    progress_callback(idx, total, original, success)

            except Exception as exc:
                logger.error(f"ISBN API fetch {normalized} failed: {exc}")
                results[normalized] = None

                if progress_callback:
                    progress_callback(idx, total, original, False)

        success_count = sum(1 for v in results.values() if v is not None)
        logger.info(f"批量获取完成：{success_count}/{total} 成功")

        return results
