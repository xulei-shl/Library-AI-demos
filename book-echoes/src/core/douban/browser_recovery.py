#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
浏览器恢复追踪工具

用于在异步任务之间共享重启次数，统一触发降级和优雅退出。
"""

from collections import defaultdict
from typing import Dict

from src.utils.logger import get_logger

logger = get_logger(__name__)


class BrowserRecoveryMixin:
    """提供统一的浏览器重启计数工具。"""

    def __init__(self, max_restarts: int = 3):
        self.max_restarts = max_restarts
        self._restart_counters: Dict[str, int] = defaultdict(int)

    def register_restart(self, channel: str, reason: str = "") -> bool:
        """
        记录一次重启请求。

        Args:
            channel: 标识来源（folio/douban等）
            reason: 备注信息

        Returns:
            是否仍允许继续重启
        """
        self._restart_counters[channel] += 1
        logger.warning(
            f"[BrowserRecovery] {channel} 请求重启 "
            f"({self._restart_counters[channel]}/{self.max_restarts}) - {reason}"
        )
        return self._restart_counters[channel] <= self.max_restarts

    def reset_restart_counter(self, channel: str):
        """重置指定通道的重启计数。"""
        if channel in self._restart_counters:
            self._restart_counters[channel] = 0

    def remaining_restarts(self, channel: str) -> int:
        """获取剩余可用次数。"""
        used = self._restart_counters.get(channel, 0)
        return max(self.max_restarts - used, 0)
