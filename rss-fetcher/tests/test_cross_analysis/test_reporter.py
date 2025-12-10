"""Reporter 单元测试"""

import os
from pathlib import Path

from src.core.cross_analysis.report import Reporter


def _sample_articles():
    return [
        {
            "title": "AI 改造课堂",
            "llm_score": 95,
            "llm_tags": ["AI", "教育"],
            "summary_long": "人工智能如何帮助教师个性化教学。",
        }
    ]


def _sample_analysis():
    return {
        "success": True,
        "main_theme": {"name": "AI 教育革命", "keywords": ["AI"], "summary": "智能化课堂"},
        "candidate_themes": [{"name": "教育公平", "support_reason": "算法降低成本"}],
        "insights": ["需关注教师培训"],
    }


def test_reporter_generate(tmp_path):
    """生成 Markdown 并校验内容。"""
    reporter = Reporter(base_output_dir=str(tmp_path))
    path = reporter.generate(_sample_articles(), _sample_analysis())

    assert os.path.exists(path)
    content = Path(path).read_text(encoding="utf-8")
    assert "交叉主题分析报告" in content
    assert "AI 教育革命" in content
    assert "| 1 | AI 改造课堂" in content


def test_reporter_filename_sanitization(tmp_path):
    """特殊主题名需被清洗后写入文件名。"""
    reporter = Reporter(base_output_dir=str(tmp_path))
    analysis = _sample_analysis()
    analysis["main_theme"]["name"] = "AI/教育?革命"

    path = reporter.generate(_sample_articles(), analysis)

    assert "AI_教育_革命" in Path(path).name
