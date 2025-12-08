"""报告生成器测试"""

import pytest
import os
import tempfile
import shutil
from src.core.cross_analysis.report_generator import ReportGenerator


class TestReportGenerator:
    """报告生成器测试类"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def report_generator(self, temp_dir):
        """创建报告生成器实例"""
        return ReportGenerator(output_dir=temp_dir)

    @pytest.fixture
    def sample_articles(self):
        """示例文章数据"""
        return [
            {
                "title": "AI教育应用研究",
                "url": "http://example.com/1",
                "llm_score": 90,
                "llm_thematic_essence": "探索人工智能在教育领域的创新应用和实践"
            },
            {
                "title": "机器学习算法优化",
                "url": "http://example.com/2",
                "llm_score": 85,
                "llm_thematic_essence": "研究和优化机器学习算法的性能"
            }
        ]

    @pytest.fixture
    def sample_analysis_result(self):
        """示例分析结果"""
        return {
            "success": True,
            "has_common_theme": True,
            "main_theme": {
                "name": "AI教育应用",
                "description": "人工智能在教育领域的创新应用",
                "confidence": 0.85,
                "article_count": 2,
                "articles": [
                    {"index": 1, "title": "AI教育应用研究", "score": 90}
                ]
            },
            "candidate_themes": [
                {
                    "name": "算法优化",
                    "description": "机器学习算法的优化方法",
                    "support": 0.6,
                    "articles": [2]
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_generate_report_success(self, report_generator, sample_articles, sample_analysis_result, temp_dir):
        """测试生成报告成功"""
        report_path = await report_generator.generate_report(sample_articles, sample_analysis_result)

        # 验证文件存在
        assert os.path.exists(report_path)
        assert report_path.startswith(temp_dir)
        assert report_path.endswith(".md")

        # 验证文件内容
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "# 文章交叉主题分析报告" in content
        assert "AI教育应用" in content
        assert "算法优化" in content
        assert "AI教育应用研究" in content
        assert "机器学习算法优化" in content

    @pytest.mark.asyncio
    async def test_generate_report_no_common_theme(self, report_generator, sample_articles, temp_dir):
        """测试没有共同主题的报告生成"""
        analysis_result = {
            "success": True,
            "has_common_theme": False,
            "main_theme": None,
            "candidate_themes": [
                {
                    "name": "独立主题1",
                    "description": "第一个独立主题",
                    "support": 0.5,
                    "articles": [1]
                }
            ]
        }

        report_path = await report_generator.generate_report(sample_articles, analysis_result)

        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "共同主题: 否" in content
        assert "主要主题" not in content
        assert "独立主题1" in content

    def test_generate_content_with_main_theme(self, report_generator, sample_articles, sample_analysis_result):
        """测试生成包含主要主题的内容"""
        content = report_generator._generate_content(sample_articles, sample_analysis_result)

        assert "# 文章交叉主题分析报告" in content
        assert "## 主要主题" in content
        assert "AI教育应用" in content
        assert "## 候选主题" in content
        assert "算法优化" in content
        assert "## 分析文章列表" in content

    def test_generate_content_without_main_theme(self, report_generator, sample_articles):
        """测试生成不包含主要主题的内容"""
        analysis_result = {
            "success": True,
            "has_common_theme": False,
            "main_theme": None,
            "candidate_themes": []
        }

        content = report_generator._generate_content(sample_articles, analysis_result)

        assert "# 文章交叉主题分析报告" in content
        assert "## 主要主题" not in content
        assert "## 候选主题" in content  # 即使是空列表也应该显示标题

    def test_ensure_output_dir(self, temp_dir):
        """测试确保输出目录存在"""
        output_dir = os.path.join(temp_dir, "subdir", "nested")
        generator = ReportGenerator(output_dir=output_dir)

        assert os.path.exists(output_dir)
        assert os.path.isdir(output_dir)