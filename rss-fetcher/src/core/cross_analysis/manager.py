"""交叉分析流程协调器。"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from typing import Any, Dict, List, Optional, Sequence

from src.utils.logger import get_logger

from .analysis import Analyzer
from .clustering import Clusterer
from .report import Reporter


class CrossAnalysisManager:
    """负责 orchestrate 聚类、分析与报告生成。"""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        clusterer: Optional[Clusterer] = None,
        analyzer: Optional[Analyzer] = None,
        reporter: Optional[Reporter] = None,
    ):
        """
        Args:
            config: 主流程配置，需包含 cross_analysis 节点。
            clusterer: 自定义聚类器，便于测试注入。
            analyzer: 自定义分析器。
            reporter: 自定义报告生成器。
        """
        cross_conf = (config or {}).get("cross_analysis", {}) or {}
        self.min_score = int(cross_conf.get("min_score", cross_conf.get("score_threshold", 92)))
        self.distance_threshold = float(cross_conf.get("distance_threshold", 0.8))
        self.batch_size = max(1, int(cross_conf.get("batch_size", 6)))  # 保留用于降级
        self.output_dir = cross_conf.get("output_dir", os.path.join("runtime", "outputs", "cross_analysis"))

        self.clusterer = clusterer or Clusterer(
            distance_threshold=self.distance_threshold,
            batch_size=self.batch_size,
        )
        self.analyzer = analyzer or Analyzer(task_name=cross_conf.get("task_name", "article_cross_analysis"))
        self.reporter = reporter or Reporter(base_output_dir=self.output_dir)

        self.logger = get_logger(__name__)

    async def run(self, articles: Sequence[Dict[str, Any]], output_dir: Optional[str] = None) -> List[str]:
        """
        Args:
            articles: 分析阶段输出的文章列表。
            output_dir: 自定义报告输出目录。

        Returns:
            生成的 Markdown 报告路径列表。
        """
        if not articles:
            self.logger.warning("未提供任何文章，终止交叉分析")
            return []

        high_quality = self._filter_articles(articles)
        if not high_quality:
            self.logger.warning("没有满足评分阈值的文章，终止交叉分析")
            return []

        prepared = [self._prepare_article(article) for article in high_quality]

        groups = self.clusterer.cluster(prepared)

        report_dir = output_dir or self.output_dir
        os.makedirs(report_dir, exist_ok=True)

        report_paths: List[str] = []
        for idx, group in enumerate(groups, 1):
            analysis_result = await self.analyzer.analyze_group(group)
            if not analysis_result.get("success"):
                self.logger.warning(f"第 {idx} 组分析失败，跳过: {analysis_result.get('error')}")
                continue

            report_path = self.reporter.generate(group, analysis_result, report_dir, group_index=idx)
            report_paths.append(report_path)

        self.logger.info(f"交叉分析完成，成功生成 {len(report_paths)} 份报告")
        return report_paths

    def _filter_articles(self, articles: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """依据评分阈值过滤文章。"""
        filtered = [
            deepcopy(article)
            for article in articles
            if article.get("llm_score", 0) >= self.min_score and article.get("llm_thematic_essence")
        ]
        self.logger.info(f"筛选后保留 {len(filtered)} 篇文章 (阈值: {self.min_score})")
        return filtered

    def _prepare_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """解析 llm_summary 等字段，补充长摘要信息。"""
        parsed = deepcopy(article)
        parsed["summary_long"] = self._extract_summary_long(parsed.get("llm_summary"))
        parsed["llm_tags"] = self._normalize_list_field(parsed.get("llm_tags"))
        parsed["llm_mentioned_books"] = self._normalize_list_field(parsed.get("llm_mentioned_books"))
        parsed.setdefault("id", parsed.get("article_id") or parsed.get("url"))
        return parsed

    def _extract_summary_long(self, summary_payload: Any) -> str:
        """解析 summary_long 节点。"""
        if isinstance(summary_payload, dict):
            return str(summary_payload.get("summary_long", "")).strip()
        if isinstance(summary_payload, str) and summary_payload.strip():
            try:
                data = json.loads(summary_payload)
                if isinstance(data, dict):
                    return str(data.get("summary_long", "")).strip()
            except json.JSONDecodeError:
                self.logger.debug("llm_summary 字段不是合法 JSON，直接作为纯文本使用")
                return summary_payload.strip()
        return ""

    def _normalize_list_field(self, field_value: Any) -> List[str]:
        """将标签、书籍字段转换为字符串列表。"""
        if isinstance(field_value, list):
            return [str(item) for item in field_value]
        if isinstance(field_value, str):
            try:
                data = json.loads(field_value)
                if isinstance(data, list):
                    return [str(item) for item in data]
            except json.JSONDecodeError:
                return [item.strip() for item in field_value.split(",") if item.strip()]
        return []
