"""Analyzer 单元测试"""

import asyncio
import json
from unittest.mock import MagicMock

import pytest

from src.core.cross_analysis.analysis import Analyzer


@pytest.fixture(autouse=True)
def patch_to_thread(monkeypatch):
    """避免测试期间真正启动线程。"""

    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr("src.core.cross_analysis.analysis.asyncio.to_thread", fake_to_thread)


@pytest.fixture
def analyzer():
    """创建 Analyzer 实例。"""
    instance = Analyzer(task_name="article_cross_analysis")
    instance.llm_client.call = MagicMock()
    return instance


@pytest.fixture
def group_articles():
    """示例文章列表。"""
    return [
        {
            "id": "a1",
            "title": "AI 教育改革",
            "summary_long": "聚焦人工智能赋能课堂。",
            "llm_tags": ["AI", "教育"],
            "llm_thematic_essence": "人工智能助力教育",
        }
    ]


def test_analyzer_success(analyzer, group_articles):
    """成功解析 JSON 的场景。"""
    payload = {
        "success": True,
        "main_theme": {"name": "AI 教育", "keywords": ["AI"], "summary": "人工智能革新课堂"},
        "candidate_themes": [],
        "insights": ["需要政策支持"],
    }
    analyzer.llm_client.call.return_value = json.dumps(payload)

    result = asyncio.run(analyzer.analyze_group(group_articles))

    assert result["success"] is True
    assert result["main_theme"]["name"] == "AI 教育"
    assert result["insights"] == ["需要政策支持"]


def test_analyzer_invalid_json(analyzer, group_articles):
    """LLM 返回非 JSON 文本时应报错。"""
    analyzer.llm_client.call.return_value = "not json"

    result = asyncio.run(analyzer.analyze_group(group_articles))

    assert result["success"] is False
    assert "解析响应失败" in result["error"]


def test_analyzer_llm_exception(analyzer, group_articles):
    """LLM 调用异常时返回错误信息。"""
    analyzer.llm_client.call.side_effect = RuntimeError("network down")

    result = asyncio.run(analyzer.analyze_group(group_articles))

    assert result["success"] is False
    assert "network down" in result["error"]


def test_analyzer_empty_group(analyzer):
    """空分组返回失败。"""
    result = asyncio.run(analyzer.analyze_group([]))
    assert result["success"] is False
    assert result["error"] == "文章分组为空"
