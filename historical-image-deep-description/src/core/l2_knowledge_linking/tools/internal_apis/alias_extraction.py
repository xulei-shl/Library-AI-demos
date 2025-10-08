import json
import os
from typing import Any, Dict, List

from .....utils.logger import get_logger
from .....utils.llm_api import invoke_model
from .....utils.json_repair import repair_json_output

logger = get_logger(__name__)


class AliasExtractor:
    """别名提取器，从Wikipedia描述中提取实体别名"""

    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self.config = settings.get("alias_search", {}) or {}

    def extract_aliases(
        self,
        entity_label: str,
        entity_type: str,
        context_hint: str,
        wikipedia_description: str,
    ) -> List[Dict[str, Any]]:
        """
        从Wikipedia描述中提取别名

        Args:
            entity_label: 实体标签
            entity_type: 实体类型
            context_hint: 上下文提示
            wikipedia_description: Wikipedia描述文本

        Returns:
            别名列表，每个别名包含alias、reason、confidence字段
        """
        try:
            messages = self._build_extraction_messages(
                entity_label, entity_type, context_hint, wikipedia_description
            )
            output = invoke_model("l2_alias_extraction", messages, self.settings)
            aliases = self._parse_extraction_output(output)
            logger.info(f"alias_extraction_completed label={entity_label} count={len(aliases)}")
            return aliases
        except Exception as e:
            logger.warning(f"alias_extraction_failed label={entity_label} err={e}")
            return []

    def _build_extraction_messages(
        self,
        entity_label: str,
        entity_type: str,
        context_hint: str,
        wikipedia_description: str,
    ) -> List[Dict[str, Any]]:
        """构建别名提取的大模型消息"""
        prompts_dir = os.path.join("src", "prompts")
        prompt_path = os.path.join(prompts_dir, "l2_alias_extraction.md")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except Exception as e:
            logger.error(f"failed_to_read_alias_prompt path={prompt_path} err={e}")
            system_prompt = "请从给定的Wikipedia描述中提取实体的各种别名形式。"

        system_prompt = system_prompt.replace("{entity_label}", entity_label)
        system_prompt = system_prompt.replace("{entity_type}", entity_type)
        system_prompt = system_prompt.replace("{context_hint}", context_hint)
        system_prompt = system_prompt.replace("{wikipedia_description}", wikipedia_description)

        user_content = f"""请从以下Wikipedia描述中为实体"{entity_label}"（类型：{entity_type}）提取别名：

{wikipedia_description}

请按照提示词要求输出JSON格式的结果。"""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    def _parse_extraction_output(self, output: str) -> List[Dict[str, Any]]:
        """解析大模型输出的别名提取结果"""
        try:
            data = json.loads(output)
            aliases = data.get("aliases", []) or []
            valid_aliases: List[Dict[str, Any]] = []
            for alias_data in aliases:
                if isinstance(alias_data, dict):
                    alias = (alias_data.get("alias") or "").strip()
                    reason = (alias_data.get("reason") or "").strip()
                    confidence = alias_data.get("confidence", 0.0)
                    if alias and isinstance(confidence, (int, float)):
                        valid_aliases.append(
                            {
                                "alias": alias,
                                "reason": reason,
                                "confidence": float(confidence),
                            }
                        )
            return valid_aliases
        except Exception as e:
            logger.warning(f"json_parse_failed err={e}, attempting repair")
            repaired_data = repair_json_output(output)
            if repaired_data:
                try:
                    aliases = repaired_data.get("aliases", []) or []
                    valid_aliases = []
                    for alias_data in aliases:
                        if isinstance(alias_data, dict):
                            alias = (alias_data.get("alias") or "").strip()
                            reason = (alias_data.get("reason") or "").strip()
                            confidence = alias_data.get("confidence", 0.0)
                            if alias and isinstance(confidence, (int, float)):
                                valid_aliases.append(
                                    {
                                        "alias": alias,
                                        "reason": reason,
                                        "confidence": float(confidence),
                                    }
                                )
                    return valid_aliases
                except Exception:
                    pass

            logger.error(f"alias_extraction_parse_failed output={output[:200]}...")
            return []