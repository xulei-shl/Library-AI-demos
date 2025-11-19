"""提示词加载辅助。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from src.utils.logger import get_logger

from .exceptions import PromptError

logger = get_logger(__name__)

try:
    from langfuse import Langfuse

    LANGFUSE_SDK_AVAILABLE = True
except Exception:  # pragma: no cover - 可选依赖
    Langfuse = None  # type: ignore
    LANGFUSE_SDK_AVAILABLE = False


class PromptLoader:
    """根据配置加载 md/langfuse/dict 提示词。"""

    def __init__(self) -> None:
        self._cache: Dict[str, str] = {}
        self._prompt_object_cache: Dict[str, Any] = {}  # 缓存 Langfuse prompt 对象

    def load(self, prompt_config: Dict[str, Any]) -> str:
        """加载提示词文本内容"""
        prompt_type = prompt_config.get("type", "md")
        cache_key = repr(prompt_config)
        if cache_key in self._cache:
            return self._cache[cache_key]

        if prompt_type == "md":
            result = self._load_from_md(prompt_config)
        elif prompt_type == "langfuse":
            result = self._load_from_langfuse(prompt_config)
        elif prompt_type == "dict":
            content = prompt_config.get("content")
            if isinstance(content, dict):
                result = str(content.get("content", ""))
            else:
                result = str(content or "")
        else:
            raise PromptError(
                prompt_source=str(prompt_config),
                prompt_type=prompt_type,
                error_message="未知的提示词类型",
            )

        self._cache[cache_key] = result
        return result

    def get_langfuse_prompt_object(self, prompt_config: Dict[str, Any]) -> Optional[Any]:
        """获取 Langfuse prompt 对象，用于传递给 OpenAI client"""
        if prompt_config.get("type") != "langfuse":
            return None

        langfuse_name = prompt_config.get("langfuse_name")
        if not langfuse_name:
            return None

        # 检查缓存
        if langfuse_name in self._prompt_object_cache:
            return self._prompt_object_cache[langfuse_name]

        if not LANGFUSE_SDK_AVAILABLE:
            return None

        try:
            assert Langfuse is not None
            client = Langfuse()
            prompt = client.get_prompt(langfuse_name)
            self._prompt_object_cache[langfuse_name] = prompt
            return prompt
        except Exception as exc:
            logger.warning(
                "无法获取 Langfuse prompt 对象，名称=%s，错误=%s",
                langfuse_name,
                exc,
            )
            return None

    def _load_from_md(self, prompt_config: Dict[str, Any]) -> str:
        source = prompt_config.get("source")
        if not source:
            raise PromptError("unknown", "md", "缺少 source 配置")
        path = Path(source)
        if not path.exists():
            raise PromptError(str(path), "md", "文件不存在")
        content = path.read_text(encoding="utf-8")
        logger.info("已加载提示词: %s", path)
        return content

    def _load_from_langfuse(self, prompt_config: Dict[str, Any]) -> str:
        langfuse_name = prompt_config.get("langfuse_name")
        if not langfuse_name:
            raise PromptError("langfuse", "langfuse", "缺少 langfuse_name")

        fallback_path = prompt_config.get("fallback") or Path("prompts") / f"{langfuse_name}.md"

        if not LANGFUSE_SDK_AVAILABLE:
            logger.warning("Langfuse SDK 未安装，使用本地提示词作为回退: %s", fallback_path)
            return self._load_langfuse_fallback(langfuse_name, fallback_path)

        try:
            assert Langfuse is not None  # 为类型检查准备
            client = Langfuse()
            prompt = client.get_prompt(langfuse_name)
            compiled = prompt.compile()
            if isinstance(compiled, dict):
                content = compiled.get("messages") or compiled.get("prompt")
                if isinstance(content, list):
                    message_text = []
                    for m in content:
                        value = m.get("content") if isinstance(m, dict) else ""
                        if isinstance(value, list):
                            value = " ".join(
                                block.get("text", "") for block in value if isinstance(block, dict)
                            )
                        message_text.append(str(value))
                    compiled_text = "\n".join([t for t in message_text if t])
                else:
                    compiled_text = str(content or "")
            else:
                compiled_text = str(compiled or "")

            logger.info("已从 Langfuse 加载提示词: %s", langfuse_name)
            return compiled_text
        except Exception as exc:  # pragma: no cover - 网络/远程问题
            logger.warning(
                "Langfuse 提示词加载失败，尝试使用本地回退。名称=%s，错误=%s",
                langfuse_name,
                exc,
            )
            return self._load_langfuse_fallback(langfuse_name, fallback_path)

    def _load_langfuse_fallback(self, langfuse_name: str, fallback: Path | str) -> str:
        fallback_path = Path(fallback)
        if not fallback_path.is_absolute():
            fallback_path = Path.cwd() / fallback_path
        if not fallback_path.exists():
            raise PromptError(str(fallback_path), "langfuse", "本地回退提示词不存在")
        content = fallback_path.read_text(encoding="utf-8")
        logger.info("已使用本地回退提示词: %s", fallback_path)
        return content
