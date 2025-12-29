"""
主题解析器
将自然语言主题解析为检索条件
"""

import json
import yaml
from typing import Dict, List, Optional
from pathlib import Path

from src.utils.logger import get_logger
from src.utils.llm.client import UnifiedLLMClient

logger = get_logger(__name__)


class ThemeParser:
    """将自然语言主题解析为检索条件"""

    def __init__(self, vocabulary_file: Optional[str] = None):
        """
        初始化主题解析器

        Args:
            vocabulary_file: 标签词表文件路径，默认为 config/literary_tags_vocabulary.yaml
        """
        self.llm_client = UnifiedLLMClient()

        # 默认词表文件路径
        if vocabulary_file is None:
            vocabulary_file = "config/literary_tags_vocabulary.yaml"

        # 加载词表
        self.vocabulary = self._load_vocabulary(vocabulary_file)

    def parse(self, theme_text: str) -> Dict:
        """
        解析主题文本为检索条件

        Args:
            theme_text: 用户输入的情境主题描述

        Returns:
            {
                "conditions": {
                    "reading_context": [...],
                    "reading_load": [...],
                    ...
                },
                "min_confidence": 0.65,
                "reason": "解析理由..."
            }
        """
        try:
            # 1. 构建用户提示词（包含词表）
            user_prompt = self._build_user_prompt(theme_text)

            # 2. 调用LLM
            response = self.llm_client.call(
                task_name='literary_theme_parse',
                user_prompt=user_prompt
            )

            # 3. 解析响应
            result = self._parse_response(response)

            logger.info(f"主题解析成功: {theme_text} -> {result.get('reason', '')[:50]}...")
            return result

        except Exception as e:
            logger.error(f"主题解析失败: {str(e)}")
            # 返回空条件作为兜底
            return {
                "conditions": {},
                "min_confidence": 0.65,
                "reason": f"解析失败: {str(e)}"
            }

    def _load_vocabulary(self, vocabulary_file: str) -> dict:
        """
        加载标签词表

        Args:
            vocabulary_file: 词表文件路径

        Returns:
            dict: 词表数据
        """
        vocab_path = Path(vocabulary_file)
        if not vocab_path.exists():
            raise FileNotFoundError(f"标签词表文件不存在: {vocabulary_file}")

        with open(vocab_path, 'r', encoding='utf-8') as f:
            vocabulary = yaml.safe_load(f)

        logger.info(f"✓ 标签词表加载成功: {vocabulary_file}")
        return vocabulary

    def _build_user_prompt(self, theme_text: str) -> str:
        """
        构建用户提示词（动态注入词表）

        Args:
            theme_text: 用户输入的情境主题

        Returns:
            str: 完整的用户提示词
        """
        # 1. 构建标签词表部分
        tags_section = self._build_tags_section()

        # 2. 构建用户提示词
        user_prompt = f"""这是当前的【候选标签词表】：

{tags_section}

用户的"情境主题"输入为：
"{theme_text}"

请开始解析。"""

        return user_prompt

    def _build_tags_section(self) -> str:
        """
        构建标签候选词部分

        Returns:
            str: 格式化的标签词表文本
        """
        dimensions = self.vocabulary.get('tag_dimensions', {})
        prompt_config = self.vocabulary.get('prompt_config', {})
        include_desc = prompt_config.get('include_descriptions', True)

        sections = []

        for dim_key, dim_data in dimensions.items():
            section_lines = [f"### {dim_data['description']}"]
            section_lines.append("")

            for candidate in dim_data.get('candidates', []):
                label = candidate.get('label', '')
                desc = candidate.get('description', '')

                if include_desc and desc:
                    section_lines.append(f"- **{label}**: {desc}")
                else:
                    section_lines.append(f"- {label}")

            sections.append("\n".join(section_lines))

        return "\n\n".join(sections)

    def _parse_response(self, response: str) -> Dict:
        """解析LLM响应"""
        # 尝试提取JSON
        try:
            if isinstance(response, str):
                # 尝试解析JSON
                result = json.loads(response)
            else:
                result = response

            # 验证必要字段
            if 'conditions' not in result:
                result['conditions'] = {}
            if 'min_confidence' not in result:
                result['min_confidence'] = 0.65
            if 'reason' not in result:
                result['reason'] = "未提供解析理由"

            return result

        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败，尝试提取: {str(e)}")
            # 尝试从文本中提取JSON
            return self._extract_json_from_text(response)

    def _extract_json_from_text(self, text: str) -> Dict:
        """从文本中提取JSON"""
        import re

        # 查找JSON块
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, text)

        for match in matches:
            try:
                result = json.loads(match)
                if 'conditions' in result:
                    return result
            except json.JSONDecodeError:
                continue

        # 无法解析，返回空条件
        logger.warning(f"无法从响应中提取JSON: {text[:100]}...")
        return {
            "conditions": {},
            "min_confidence": 0.65,
            "reason": "无法解析LLM响应"
        }
