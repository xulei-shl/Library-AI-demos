"""交叉分析 LLM 调用器。"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Sequence

from src.utils.logger import get_logger
from src.utils.llm import UnifiedLLMClient


class Analyzer:
    """负责与 LLM 交互，完成单个文章分组的交叉分析。"""

    def __init__(self, task_name: str = "article_cross_analysis"):
        """
        Args:
            task_name: config/llm.yaml 中定义的任务名。
        """
        self.task_name = task_name
        self.llm_client = UnifiedLLMClient()
        self.logger = get_logger(__name__)

    async def analyze_group(self, articles: Sequence[Dict]) -> Dict[str, Any]:
        """
        Args:
            articles: 同簇文章列表。

        Returns:
            包含 LLM 分析结果的字典。
        """
        if not articles:
            return {"success": False, "error": "文章分组为空"}

        prompt = self._build_prompt(articles)

        try:
            raw_response = await asyncio.to_thread(
                self.llm_client.call,
                self.task_name,
                prompt,
            )
        except Exception as exc:
            self.logger.error(f"调用交叉分析 LLM 失败: {exc}")
            return {"success": False, "error": str(exc)}

        return self._parse_response(raw_response)

    def _build_prompt(self, articles: Sequence[Dict]) -> str:
        """组装交叉分析提示词。"""
        header = [
            "你是负责交叉主题分析的研究员，请基于多篇文章洞察共同母题。",
            "请保持结构化输出，字段需使用 JSON 严格命名。",
        ]
        lines = []
        for idx, article in enumerate(articles, 1):
            summary = article.get("summary_long") or ""
            tags = article.get("llm_tags") or ""
            line = (
                f"- idx: {idx}\n"
                f"  id: {article.get('id', '')}\n"
                f"  title: {article.get('title', '')}\n"
                f"  tags: {tags}\n"
                f"  summary: {summary}\n"
                f"  thematic_essence: {article.get('llm_thematic_essence', '')}"
            )
            lines.append(line)

        output_spec = [
            "请输出 JSON，字段包括:",
            "success: bool",
            "main_theme: {name, keywords, summary}",
            "candidate_themes: [{name, support_reason}]",
            "insights: [string]",
        ]

        sections = [
            "\n".join(header),
            "## 文章资料",
            "\n\n".join(lines),
            "## 输出要求",
            "\n".join(output_spec),
        ]
        return "\n\n".join(sections)

    def _parse_response(self, response: Any) -> Dict[str, Any]:
        """解析 LLM 返回结果。"""
        if isinstance(response, dict):
            data = response
        else:
            try:
                data = json.loads(str(response))
            except json.JSONDecodeError as exc:
                self.logger.error(f"交叉分析结果 JSON 解析失败: {exc}")
                return {"success": False, "error": f"解析响应失败: {exc}"}

        result = {
            "success": bool(data.get("success", True)),
            "main_theme": data.get("main_theme") or {},
            "candidate_themes": data.get("candidate_themes") or [],
            "insights": data.get("insights") or [],
        }
        return result
