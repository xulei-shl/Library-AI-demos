"""交叉分析器测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.core.cross_analysis.analyzer import CrossAnalyzer


class TestCrossAnalyzer:
    """交叉分析器测试类"""

    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        config = {"score_threshold": 80}
        return CrossAnalyzer(config=config)

    @pytest.fixture
    def sample_articles(self):
        """示例文章数据"""
        return [
            {
                "title": "AI教育应用研究",
                "url": "http://example.com/1",
                "llm_score": 90,
                "llm_thematic_essence": "探索人工智能在教育领域的创新应用"
            },
            {
                "title": "机器学习基础",
                "url": "http://example.com/2",
                "llm_score": 85,
                "llm_thematic_essence": "介绍机器学习的基本概念和算法"
            },
            {
                "title": "深度学习框架",
                "url": "http://example.com/3",
                "llm_score": 70,
                "llm_thematic_essence": "主流深度学习框架的比较和使用"
            }
        ]

    @pytest.fixture
    def mock_cluster_result(self):
        """模拟主题聚类结果"""
        return {
            "success": True,
            "has_common_theme": True,
            "main_theme": {
                "name": "人工智能教育",
                "description": "AI在教育领域的应用",
                "confidence": 0.8,
                "article_count": 2,
                "articles": [
                    {"index": 1, "title": "AI教育应用研究", "score": 90},
                    {"index": 2, "title": "机器学习基础", "score": 85}
                ]
            },
            "candidate_themes": []
        }

    @pytest.mark.asyncio
    async def test_analyze_success(self, analyzer, sample_articles, mock_cluster_result, tmp_path):
        """测试分析成功场景"""
        # Mock主题聚类和报告生成
        analyzer.theme_cluster.cluster_themes = AsyncMock(return_value=mock_cluster_result)
        analyzer.report_generator.generate_report = AsyncMock(
            return_value=str(tmp_path / "test_report.md")
        )

        result = await analyzer.analyze(sample_articles)

        assert result["success"] is True
        assert result["has_common_theme"] is True
        assert result["main_theme"]["name"] == "人工智能教育"
        assert result["report_path"] == str(tmp_path / "test_report.md")
        assert result["metadata"]["article_count"] == 3
        assert result["metadata"]["filtered_count"] == 2  # 评分>=80的文章

    @pytest.mark.asyncio
    async def test_analyze_cluster_failure(self, analyzer, sample_articles):
        """测试主题聚类失败场景"""
        # Mock聚类失败
        analyzer.theme_cluster.cluster_themes = AsyncMock(return_value={
            "success": False,
            "error": "聚类失败"
        })

        result = await analyzer.analyze(sample_articles)

        assert result["success"] is False
        assert result["has_common_theme"] is False
        assert result["main_theme"] is None
        assert result["candidate_themes"] == []
        assert "聚类失败" in result["metadata"]["error"]

    @pytest.mark.asyncio
    async def test_analyze_exception(self, analyzer, sample_articles):
        """测试异常场景"""
        # Mock主题聚类抛出异常
        analyzer.theme_cluster.cluster_themes = AsyncMock(
            side_effect=Exception("系统错误")
        )

        result = await analyzer.analyze(sample_articles)

        assert result["success"] is False
        assert "系统错误" in result["metadata"]["error"]
        assert result["metadata"]["article_count"] == 3

    @pytest.mark.asyncio
    async def test_analyze_no_articles(self, analyzer):
        """测试空文章列表"""
        result = await analyzer.analyze([])

        assert result["success"] is False
        assert result["metadata"]["article_count"] == 0

    @pytest.mark.asyncio
    async def test_analyze_with_config(self, sample_articles, mock_cluster_result, tmp_path):
        """测试使用配置的分析"""
        config = {"score_threshold": 70, "custom_param": "value"}
        analyzer = CrossAnalyzer(config=config)

        analyzer.theme_cluster.cluster_themes = AsyncMock(return_value=mock_cluster_result)
        analyzer.report_generator.generate_report = AsyncMock(
            return_value=str(tmp_path / "test_report.md")
        )

        result = await analyzer.analyze(sample_articles)

        assert result["success"] is True
        assert result["metadata"]["config"] == config