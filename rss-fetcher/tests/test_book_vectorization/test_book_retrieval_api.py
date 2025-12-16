#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""FastAPI 图书检索接口测试。"""

import pytest
from fastapi.testclient import TestClient

import scripts.api.book_retrieval_api as api_module


@pytest.fixture
def client(monkeypatch):
    """构建注入桩服务的 TestClient。"""

    class DummyService:
        def __init__(self):
            self.text_calls = []
            self.multi_calls = []

        def text_search(self, **kwargs):
            self.text_calls.append(kwargs)
            return {
                "results": [{"title": "Stub"}],
                "metadata": {"mode": "text_search", "response_format": "json"},
            }

        def multi_query_search(self, **kwargs):
            self.multi_calls.append(kwargs)
            return {
                "results": [{"title": "StubMulti"}],
                "metadata": {"mode": "multi_query", "response_format": "json"},
            }

    dummy_service = DummyService()
    monkeypatch.setattr(api_module, "service", dummy_service)
    test_client = TestClient(api_module.app)
    return test_client, dummy_service


def test_text_search_endpoint(client):
    """验证文本检索端点成功返回。"""
    test_client, dummy_service = client
    response = test_client.post(
        "/api/books/text-search",
        json={"query": "AI 伦理", "top_k": 3},
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["title"] == "Stub"
    assert dummy_service.text_calls[0]["query"] == "AI 伦理"


def test_multi_query_endpoint(client):
    """验证多子查询端点参数传递。"""
    test_client, dummy_service = client
    response = test_client.post(
        "/api/books/multi-query",
        json={"markdown_text": "# 标题", "response_format": "plain_text"},
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["title"] == "StubMulti"
    assert dummy_service.multi_calls[0]["response_format"] == "plain_text"


def test_invalid_response_format(client):
    """非法响应格式应返回 422。"""
    test_client, _ = client
    response = test_client.post(
        "/api/books/text-search",
        json={"query": "AI", "response_format": "xml"},
    )
    assert response.status_code == 422

