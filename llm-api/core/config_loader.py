"""
统一配置加载器

负责加载、解析和验证YAML配置文件，支持环境变量注入和默认配置应用。
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigLoader:
    """统一配置加载器

    特性：
    1. 支持环境变量注入 (env:KEY_NAME)
    2. 自动应用默认配置
    3. 配置验证和错误提示
    4. 配置热更新支持
    """

    def __init__(self, config_path: str = "config/settings.yaml"):
        """初始化配置加载器

        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self._config = None

    def load(self) -> Dict[str, Any]:
        """加载配置

        Returns:
            配置字典

        Raises:
            FileNotFoundError: 配置文件不存在
            yaml.YAMLError: YAML格式错误
        """
        if self._config is not None:
            return self._config

        # 检查文件是否存在
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        # 加载YAML配置
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"配置文件格式错误: {e}")

        # 解析环境变量
        config = self._resolve_env_vars(config)

        # 应用默认配置
        config = self._apply_defaults(config)

        # 验证必需的配置项
        self._validate_config(config)

        self._config = config
        return config

    def _resolve_env_vars(self, config: Any) -> Any:
        """递归解析环境变量

        支持格式：
        - env:KEY_NAME
        - "env:KEY_NAME:default_value"

        Args:
            config: 配置对象（dict, list, str, number, bool）

        Returns:
            解析后的配置对象
        """
        if isinstance(config, dict):
            return {k: self._resolve_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._resolve_env_vars(item) for item in config]
        elif isinstance(config, str) and config.startswith("env:"):
            # 解析 env:KEY 或 env:KEY:default
            parts = config.split(":", 2)
            env_key = parts[1] if len(parts) > 1 else ""
            default_value = parts[2] if len(parts) > 2 else ""

            env_value = os.getenv(env_key, default_value)
            return env_value
        return config

    def _apply_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """应用默认配置

        从 defaults 节读取全局默认值，应用到任务配置中缺失的字段。

        Args:
            config: 配置字典

        Returns:
            应用默认配置后的字典
        """
        defaults = config.get("defaults", {})

        # 任务配置应用默认
        for task_name, task_config in config.get("tasks", {}).items():
            for key, default_value in defaults.items():
                if key not in task_config:
                    task_config[key] = default_value

        return config

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """验证配置完整性

        检查必需的配置项是否存在并有效。

        Args:
            config: 配置字典

        Raises:
            ValueError: 配置缺失或无效
        """
        # 检查api_providers配置
        if "api_providers" not in config:
            raise ValueError("配置缺少必需部分: api_providers")

        for provider_type, providers in config["api_providers"].items():
            # 检查primary和secondary
            for provider_name in ["primary", "secondary"]:
                if provider_name not in providers:
                    continue  # 允许只有primary没有secondary

                provider = providers[provider_name]
                required_fields = ["api_key", "base_url", "model"]

                for field in required_fields:
                    if field not in provider:
                        raise ValueError(
                            f"api_providers.{provider_type}.{provider_name} "
                            f"缺少必需字段: {field}"
                        )

        # 检查tasks配置
        if "tasks" not in config:
            raise ValueError("配置缺少必需部分: tasks")

        for task_name, task_config in config["tasks"].items():
            # 检查provider_type
            if "provider_type" not in task_config:
                raise ValueError(f"任务 {task_name} 缺少 provider_type 配置")

            # 检查prompt配置
            if "prompt" not in task_config:
                raise ValueError(f"任务 {task_name} 缺少 prompt 配置")

            prompt_config = task_config["prompt"]
            if "type" not in prompt_config:
                raise ValueError(f"任务 {task_name}.prompt 缺少 type 配置")

            prompt_type = prompt_config["type"]

            # 根据类型验证相应字段
            if prompt_type == "md":
                if "source" not in prompt_config:
                    raise ValueError(f"任务 {task_name}.prompt 缺少 source 配置")
                source_path = Path(prompt_config["source"])
                if not source_path.exists():
                    raise FileNotFoundError(
                        f"提示词文件不存在: {source_path.absolute()}"
                    )
            elif prompt_type == "langfuse":
                if "langfuse_name" not in prompt_config:
                    raise ValueError(f"任务 {task_name}.prompt 缺少 langfuse_name 配置")
            elif prompt_type == "dict":
                if "content" not in prompt_config:
                    raise ValueError(f"任务 {task_name}.prompt 缺少 content 配置")
            else:
                raise ValueError(f"任务 {task_name}.prompt.type 无效: {prompt_type}")

    def reload(self) -> None:
        """重新加载配置（清除缓存）"""
        self._config = None

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值

        支持点号分隔的路径，如 "tasks.fact_description.temperature"

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        config = self.load()
        keys = key.split(".")
        value = config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value