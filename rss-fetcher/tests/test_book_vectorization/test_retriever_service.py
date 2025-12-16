#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""RetrieverService 单元测试。"""

from pathlib import Path

import pytest

from scripts.api.services.retriever_service import QueryPackage, RetrieverService
import scripts.api.services.retriever_service as service_module


@pytest.fixture
def service_with_stubs(monkeypatch):
    """构建带桩对象的服务实例。"""
    calls = {
        "text": [],
        "multi": [],
        "saved": [],
        "pkg_contents": [],
    }

    class DummyRetriever:
        def __init__(self, config_path: str):
            self.config_path = config_path

        def search_by_text(self, query_text, top_k, min_rating):
            calls["text"].append(
                {"query": query_text, "top_k": top_k, "min_rating": min_rating}
            )
            return [
                {
                    "title": "测试书籍",
                    "author": "作者甲",
                    "rating": 9.1,
                    "summary": "简介",
                }
            ]

        def search_multi_query(self, **kwargs):
            calls["multi"].append(kwargs)
            return [
                {
                    "title": "融合书籍",
                    "author": "作者乙",
                    "rating": 8.8,
                    "summary": "融合摘要",
                }
            ]

    class DummyFormatter:
        def __init__(self, config):
            self.enabled = True

        def save_results(self, results, metadata):
            calls["saved"].append(metadata)
            return {"json": "runtime/outputs/test.json"}

    def fake_build_query_package(md_path: str, **_kwargs):
        content = Path(md_path).read_text(encoding="utf-8")
        calls["pkg_contents"].append(content)
        package = QueryPackage(primary=["主查询"])
        package.metadata = {"dummy": "1"}
        return package

    monkeypatch.setattr(service_module, "BookRetriever", DummyRetriever)
    monkeypatch.setattr(service_module, "OutputFormatter", DummyFormatter)
    monkeypatch.setattr(
        service_module, "build_query_package_from_md", fake_build_query_package
    )

    service = RetrieverService(config_path="config/book_vectorization.yaml")
    return service, calls


def test_text_search_plain_text(service_with_stubs):
    """验证文本检索 plain_text 模式。"""
    service, calls = service_with_stubs
    payload = service.text_search(
        query="人工智能",
        response_format="plain_text",
        llm_hint={"provider": "openai-compatible"},
    )

    assert payload["metadata"]["response_format"] == "plain_text"
    assert "context_plain_text" in payload
    assert payload["metadata"]["llm_hint"]["provider"] == "openai-compatible"
    assert calls["text"][0]["top_k"] == service.default_text_top_k


def test_multi_query_saves_files(service_with_stubs):
    """验证多查询路径写入临时文件与落盘行为。"""
    service, calls = service_with_stubs
    payload = service.multi_query_search(
        markdown_text="# 报告\n内容",
        save_to_file=True,
        enable_rerank=True,
        disable_exact_match=True,
    )

    assert payload["metadata"]["enable_rerank"] is True
    assert payload["metadata"]["disable_exact_match"] is True
    assert payload["saved_files"]["json"].endswith("test.json")
    assert calls["pkg_contents"][0].startswith("# 报告")
    assert calls["multi"][0]["rerank"] is True

