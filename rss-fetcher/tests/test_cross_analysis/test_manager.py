"""CrossAnalysisManager 单元测试"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.core.cross_analysis.manager import CrossAnalysisManager


def test_manager_pipeline(tmp_path):
    """完整流程成功并输出报告路径。"""
    clusterer = MagicMock()
    analyzer = MagicMock()
    reporter = MagicMock()

    prepared_article = {
        "id": "id-1",
        "title": "AI 改造课堂",
        "llm_score": 95,
        "llm_thematic_essence": "人工智能赋能教育",
        "llm_summary": '{"summary_long": "AI 带来课堂变革"}',
    }

    clusterer.cluster.return_value = [[prepared_article]]
    analyzer.analyze_group = AsyncMock(
        return_value={
            "success": True,
            "main_theme": {"name": "AI 教育革命", "keywords": ["AI"], "summary": "课堂革新"},
            "candidate_themes": [],
            "insights": [],
        }
    )
    expected_path = str(tmp_path / "report.md")
    reporter.generate.return_value = expected_path

    manager = CrossAnalysisManager(
        config={"cross_analysis": {"min_score": 90}},
        clusterer=clusterer,
        analyzer=analyzer,
        reporter=reporter,
    )

    articles = [
        prepared_article,
        {
            "id": "low",
            "title": "无关文章",
            "llm_score": 20,
            "llm_thematic_essence": "",
        },
    ]

    result = asyncio.run(manager.run(articles, output_dir=str(tmp_path)))

    assert result == [expected_path]
    clusterer.cluster.assert_called_once()
    reporter.generate.assert_called_once()


def test_manager_no_articles():
    """没有高质量文章时直接返回空列表。"""
    manager = CrossAnalysisManager(config={"cross_analysis": {"min_score": 95}})
    result = asyncio.run(manager.run([]))
    assert result == []
