"""报告生成器模块

负责生成主题交叉分析的Markdown报告
"""

import os
from datetime import datetime
from typing import Dict, Any, List
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ReportGenerator:
    """报告生成器

    生成文章交叉主题分析的Markdown格式报告
    """

    def __init__(self, output_dir: str = "runtime/outputs"):
        """初始化报告生成器

        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir
        self._ensure_output_dir()

    def _ensure_output_dir(self):
        """确保输出目录存在"""
        os.makedirs(self.output_dir, exist_ok=True)

    async def generate_report(
        self,
        articles: List[Dict[str, Any]],
        analysis_result: Dict[str, Any]
    ) -> str:
        """生成分析报告

        Args:
            articles: 原始文章列表
            analysis_result: 主题聚类结果

        Returns:
            报告文件路径
        """
        try:
            # 生成报告文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"主题报告_{timestamp}.md"
            filepath = os.path.join(self.output_dir, filename)

            # 生成报告内容
            content = self._generate_content(articles, analysis_result)

            # 写入文件
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"报告生成成功: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"生成报告失败: {str(e)}")
            raise

    def _generate_content(
        self,
        articles: List[Dict[str, Any]],
        analysis_result: Dict[str, Any]
    ) -> str:
        """生成Markdown报告内容

        Args:
            articles: 文章列表
            analysis_result: 分析结果

        Returns:
            Markdown格式的报告内容
        """
        # 报告头部
        content = [
            "# 文章交叉主题分析报告\n",
            f"- **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **分析文章数**: {len(articles)}",
            f"- **共同主题**: {analysis_result.get('has_common_theme', False) and '是' or '否'}\n"
        ]

        # 分析概览
        content.extend([
            "## 分析概览\n",
            f"本次分析共处理了 {len(articles)} 篇文章，通过主题聚类识别其中的共同母题。"
        ])

        # 主要主题
        main_theme = analysis_result.get("main_theme")
        if main_theme:
            content.extend([
                "\n## 主要主题\n",
                f"### {main_theme.get('name', '未命名')}\n",
                f"**描述**: {main_theme.get('description', '无描述')}\n",
                f"**置信度**: {main_theme.get('confidence', 0):.2f}\n",
                f"**相关文章数**: {main_theme.get('article_count', 0)}\n"
            ])

            # 添加相关文章列表
            content.extend(self._render_article_table(main_theme.get("articles", [])))

        # 候选主题
        candidate_themes = analysis_result.get("candidate_themes", [])
        if candidate_themes:
            content.extend([
                "\n## 候选主题\n",
                "除了主要主题外，还识别到以下潜在主题：\n"
            ])

            for theme in candidate_themes:
                content.extend([
                    f"### {theme.get('name', '未命名')}\n",
                    f"- **描述**: {theme.get('description', '无描述')}\n",
                    f"- **支持度**: {theme.get('support', 0):.2f}\n",
                ])
                content.extend(self._render_article_table(theme.get("articles", [])))
                content.append("")

        # 文章列表
        content.extend([
            "\n## 分析文章列表\n",
            "| ID | 标题 | 评分 | 母题描述 |",
            "|----|------|------|----------|"
        ])

        for article in articles:
            article_id = article.get("id", "")
            title = article.get("title", "无标题")
            score = article.get("llm_score", 0)
            essence = article.get("llm_thematic_essence", "无")
            # 截断过长的内容
            essence = essence[:100] + "..." if len(essence) > 100 else essence
            content.append(f"| {article_id} | {title} | {score} | {essence} |")

        # 分析说明
        content.extend([
            "\n## 分析说明\n",
            "- 共同主题识别基于多篇文章的母题描述进行聚类分析",
            "- 主要主题指在多篇文章中反复出现的核心主题",
            "- 候选主题是潜在的次要主题，可能在更多文章中出现",
            "- 报告生成时间：", datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ])

        return "\n".join(content)

    def _render_article_table(self, articles: List[Dict[str, Any]]) -> List[str]:
        """渲染主题关联文章表格"""
        if not articles:
            return ["**相关文章**: 暂无关联文章\n"]

        rows = [
            "**相关文章**:\n",
            "| ID | 标题 | 来源 | 发布时间 | URL |",
            "|----|------|------|----------|-----|"
        ]

        for article in articles:
            article_id = article.get("id", "")
            title = article.get("title", "无标题")
            source = article.get("source", "未知来源")
            published_date = article.get("published_date", "")
            url = article.get("url", "") or ""
            rows.append(f"| {article_id} | {title} | {source} | {published_date} | {url} |")

        rows.append("")
        return rows
