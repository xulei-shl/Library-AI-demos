"""主题聚类器测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.core.cross_analysis.theme_cluster import ThemeCluster


class TestThemeCluster:
    """主题聚类器测试类"""

    @pytest.fixture
    def theme_cluster(self):
        """创建主题聚类器实例"""
        return ThemeCluster()

    @pytest.fixture
    def sample_articles(self):
        """示例文章数据"""
        return [
            {
                "title": "文章1",
                "url": "http://example.com/1",
                "llm_score": 90,
                "llm_thematic_essence": "探索人工智能在教育领域的应用前景"
            },
            {
                "title": "文章2",
                "url": "http://example.com/2",
                "llm_score": 85,
                "llm_thematic_essence": "AI技术如何改变传统教学模式"
            },
            {
                "title": "文章3",
                "url": "http://example.com/3",
                "llm_score": 75,
                "llm_thematic_essence": "机器学习算法优化方法研究"
            },
            {
                "title": "文章4",
                "url": "http://example.com/4",
                "llm_score": 60,
                "llm_thematic_essence": ""  # 空母题
            }
        ]

    def test_filter_articles(self, theme_cluster, sample_articles):
        """测试文章筛选逻辑"""
        # 使用默认阈值90
        filtered = theme_cluster._filter_articles(sample_articles)
        assert len(filtered) == 1
        assert filtered[0]["llm_score"] >= 90

        # 使用自定义阈值70
        filtered = theme_cluster._filter_articles(sample_articles, score_threshold=70)
        assert len(filtered) == 3

    def test_prepare_llm_input(self, theme_cluster, sample_articles):
        """测试LLM输入准备"""
        input_str = theme_cluster._prepare_llm_input(sample_articles[:2])
        assert "文章1" in input_str
        assert "文章2" in input_str
        assert "探索人工智能在教育领域的应用前景" in input_str

    @pytest.mark.asyncio
    async def test_cluster_themes_success(self, theme_cluster, sample_articles):
        """测试主题聚类成功场景"""
        # Mock LLM响应
        mock_response = """
        {
            "success": true,
            "has_common_theme": true,
            "main_theme": {
                "name": "AI教育应用",
                "description": "探索人工智能在教育领域的创新应用",
                "confidence": 0.85,
                "article_count": 2,
                "articles": [
                    {"index": 1, "title": "文章1", "score": 90},
                    {"index": 2, "title": "文章2", "score": 85}
                ]
            },
            "candidate_themes": [
                {
                    "name": "机器学习算法",
                    "description": "研究机器学习算法的优化方法",
                    "support": 0.6,
                    "articles": [3]
                }
            ]
        }
        """
        theme_cluster.llm_client.ainvoke = AsyncMock(return_value=mock_response)

        result = await theme_cluster.cluster_themes(sample_articles, score_threshold=80)

        assert result["success"] is True
        assert result["has_common_theme"] is True
        assert result["main_theme"]["name"] == "AI教育应用"
        assert len(result["candidate_themes"]) == 1

    @pytest.mark.asyncio
    async def test_cluster_themes_no_high_quality_articles(self, theme_cluster):
        """测试没有高质量文章的场景"""
        low_quality_articles = [
            {
                "title": "文章1",
                "llm_score": 60,
                "llm_thematic_essence": "低质量文章"
            }
        ]

        result = await theme_cluster.cluster_themes(low_quality_articles)

        assert result["success"] is False
        assert "没有高质量的文章" in result["error"]

    @pytest.mark.asyncio
    async def test_cluster_themes_llm_error(self, theme_cluster, sample_articles):
        """测试LLM调用失败场景"""
        theme_cluster.llm_client.ainvoke = AsyncMock(side_effect=Exception("LLM错误"))

        result = await theme_cluster.cluster_themes(sample_articles, score_threshold=80)

        assert result["success"] is False
        assert "LLM错误" in result["error"]

    def test_parse_response_valid_json(self, theme_cluster):
        """测试解析有效JSON响应"""
        response = """
        {
            "success": true,
            "has_common_theme": false,
            "main_theme": null,
            "candidate_themes": []
        }
        """
        result = theme_cluster._parse_response(response)

        assert result["success"] is True
        assert result["has_common_theme"] is False
        assert result["main_theme"] is None
        assert result["candidate_themes"] == []

    def test_parse_response_invalid_json(self, theme_cluster):
        """测试解析无效JSON响应"""
        response = "这不是有效的JSON"
        result = theme_cluster._parse_response(response)

        assert result["success"] is False
        assert "解析响应失败" in result["error"]
