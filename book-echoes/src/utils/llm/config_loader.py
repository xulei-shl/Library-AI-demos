"""LLM 专用配置加载器。"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any, Dict

import yaml

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - 可选依赖
    load_dotenv = None  # type: ignore


class ConfigLoader:
    """负责读取并解析 config/llm.yaml。"""

    def __init__(self, config_path: str, env_file: str | None = "config/.env"):
        self.config_path = Path(config_path)
        self.env_file = Path(env_file) if env_file else None
        self._config: Dict[str, Any] | None = None
        self._load_env()

    def _load_env(self) -> None:
        """预加载 .env，确保 API key 就绪。"""
        if not self.env_file or not self.env_file.exists() or load_dotenv is None:
            return
        load_dotenv(self.env_file)  # type: ignore[arg-type]

    def load(self) -> Dict[str, Any]:
        """读取 YAML 并注入默认值。"""
        if self._config is not None:
            return self._config

        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}

        data = self._resolve_env_vars(data)
        data = self._apply_defaults(data)
        self._config = data
        return data

    def reload(self) -> Dict[str, Any]:
        """清除缓存后重新载入。"""
        self._config = None
        return self.load()

    def get(self, key: str, default: Any = None) -> Any:
        """按点号路径读取配置值。"""
        config = self.load()
        current: Any = config
        for part in key.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current

    def _resolve_env_vars(self, item: Any) -> Any:
        """支持 env:KEY 或 env:KEY:default 写法。"""
        if isinstance(item, dict):
            return {k: self._resolve_env_vars(v) for k, v in item.items()}
        if isinstance(item, list):
            return [self._resolve_env_vars(v) for v in item]
        if isinstance(item, str) and item.startswith("env:"):
            parts = item.split(":", 2)
            env_key = parts[1] if len(parts) > 1 else ""
            default_value = parts[2] if len(parts) > 2 else ""
            return os.getenv(env_key, default_value)
        return item

    def _apply_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        defaults = config.get("defaults", {})
        tasks = config.get("tasks", {})
        for task_name, task_config in tasks.items():
            for key, value in defaults.items():
                task_config.setdefault(key, value)
            # 深拷贝，避免运行时被意外修改
            tasks[task_name] = copy.deepcopy(task_config)
        config["tasks"] = tasks
        return config
