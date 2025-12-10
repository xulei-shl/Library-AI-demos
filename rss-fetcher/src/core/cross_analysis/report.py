"""Markdown 报告生成器。"""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any, Dict, Sequence

from src.utils.logger import get_logger


class Reporter:
    """将交叉分析结果输出为 Markdown 报告。"""

    def __init__(self, base_output_dir: str = "runtime/outputs/cross_analysis"):
        """
        Args:
            base_output_dir: 默认输出目录。
        """
        self.base_output_dir = base_output_dir
        self.logger = get_logger(__name__)

    def generate(
        self,
        articles: Sequence[Dict],
        analysis: Dict[str, Any],
        output_dir: str | None = None,
        group_index: int = 1,
    ) -> str:
        """
        Args:
            articles: 单组文章数据。
            analysis: LLM 分析结果。
            output_dir: 自定义输出目录。
            group_index: 分组序号，用于文件名区分。

        Returns:
            生成的 Markdown 文件路径。
        """
        target_dir = output_dir or self.base_output_dir
        os.makedirs(target_dir, exist_ok=True)

        theme_name = analysis.get("main_theme", {}).get("name") or f"group-{group_index}"
        safe_name = self._sanitize(theme_name)
        filename = f"{datetime.now():%Y%m%d_%H%M%S}_{safe_name}_g{group_index}.md"
        file_path = os.path.join(target_dir, filename)

        content = self._build_markdown(theme_name, articles, analysis)

        with open(file_path, "w", encoding="utf-8") as file_obj:
            file_obj.write(content)

        self.logger.info(f"交叉分析报告已生成: {file_path}")
        return file_path

    def _build_markdown(self, theme_name: str, articles, analysis) -> str:
        """构造 Markdown 文本。"""
        main_theme = analysis.get("main_theme", {}) or {}
        candidate_themes = analysis.get("candidate_themes", []) or []
        insights = analysis.get("insights", []) or []

        article_rows = [
            "| 序号 | 标题 | 评分 | 标签 | 摘要 |",
            "| --- | --- | --- | --- | --- |",
        ]
        for idx, article in enumerate(articles, 1):
            tags = article.get("llm_tags") or ""
            summary = (article.get("summary_long") or "").replace("\n", " ")
            summary = summary[:180] + "..." if len(summary) > 180 else summary
            article_rows.append(
                f"| {idx} | {article.get('title', '')} | {article.get('llm_score', '')} | {tags} | {summary} |"
            )

        candidates_md = "\n".join(
            f"- **{item.get('name', '未命名')}**: {item.get('support_reason', '')}"
            for item in candidate_themes
        ) or "暂无候选主题"

        insights_md = "\n".join(f"- {text}" for text in insights) or "- 暂无额外洞察"

        return "\n\n".join(
            [
                f"# 交叉主题分析报告 - {theme_name}",
                "## 共同母题",
                f"- 名称: {main_theme.get('name', '未命名')}",
                f"- 关键词: {', '.join(main_theme.get('keywords', []) or [])}",
                f"- 摘要: {main_theme.get('summary', '暂无描述')}",
                "## 文章列表",
                "\n".join(article_rows),
                "## 候选主题",
                candidates_md,
                "## 深度洞察",
                insights_md,
            ]
        )

    def _sanitize(self, text: str) -> str:
        """将主题名转换为安全的文件名片段。"""
        cleaned = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]+", "_", text).strip("_")
        return cleaned or "theme"
