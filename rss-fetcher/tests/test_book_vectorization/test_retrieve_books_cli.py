#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
向量检索命令行脚本测试
"""

import os
import sys
from types import SimpleNamespace
from typing import List

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scripts.retrieve_books as retrieve_cli  # noqa: E402


class DummyRetriever:
    """用于替换真实 BookRetriever 的测试桩"""

    instances: List['DummyRetriever'] = []  # type: ignore

    def __init__(self, config_path: str):
        DummyRetriever.instances.append(self)
        self.config_path = config_path
        self.closed = False
        self.last_query = None
        self.last_top_k = None
        self.last_min_rating = None
        self.last_category = None
        self.multi_query_calls = []

    def search_by_text(self, query_text: str, top_k: int, min_rating: float = None):
        """记录文本检索调用"""
        self.last_query = query_text
        self.last_top_k = top_k
        self.last_min_rating = min_rating
        return [
            {
                'book_id': 1,
                'title': '测试书籍',
                'author': '测试作者',
                'rating': 9.1,
                'summary': '这是一段摘要',
                'call_no': 'H123',
                'similarity_score': 0.9123,
                'embedding_id': 'book_1'
            }
        ]

    def search_by_category(self, call_no_prefix: str, top_k: int):
        """记录分类检索调用"""
        self.last_category = call_no_prefix
        self.last_top_k = top_k
        return [
            {
                'douban_title': '分类书籍',
                'douban_author': '作者A',
                'douban_rating': 8.8,
                'call_no': f'{call_no_prefix}001',
                'douban_pub_year': '2020'
            }
        ]

    def search_multi_query(self, **kwargs):
        """记录多子查询检索调用"""
        self.multi_query_calls.append(kwargs)
        return [
            {
                'book_id': 2,
                'title': '多轮候选',
                'author': '作者B',
                'rating': 8.9,
                'summary': '融合后的结果',
                'call_no': 'G001',
                'similarity_score': 0.95,
                'fused_score': 0.91,
            }
        ]

    def close(self):
        """模拟资源释放"""
        self.closed = True


@pytest.fixture(autouse=True)
def patch_retriever(monkeypatch):
    """将 BookRetriever 替换为 DummyRetriever"""
    DummyRetriever.instances.clear()
    monkeypatch.setattr(retrieve_cli, 'BookRetriever', DummyRetriever)


def test_run_cli_with_query_file(tmp_path, capsys):
    """验证提供查询文件时能够执行文本检索"""
    query_file = tmp_path / 'query.txt'
    query_file.write_text('  测试查询文本  ', encoding='utf-8')

    args = SimpleNamespace(
        config='config/book_vectorization.yaml',
        query=None,
        query_file=str(query_file),
        category=None,
        top_k=3,
        min_rating=8.5,
        query_mode='single',
        from_md=None,
        per_query_top_k=None,
        enable_rerank=False,
        final_top_k=None,
    )

    context = retrieve_cli.run_cli(args)

    assert context['mode'] == 'text'
    assert context['query'] == '测试查询文本'
    captured = capsys.readouterr()
    assert '文本相似度检索结果' in captured.out


def test_run_cli_with_category(capsys):
    """验证分类检索路径"""
    args = SimpleNamespace(
        config='config/book_vectorization.yaml',
        query=None,
        query_file=None,
        category='h',
        top_k=2,
        min_rating=None,
        query_mode='single',
        from_md=None,
        per_query_top_k=None,
        enable_rerank=False,
        final_top_k=None,
    )

    context = retrieve_cli.run_cli(args)

    assert context['mode'] == 'category'
    assert context['category'] == 'H'
    captured = capsys.readouterr()
    assert '分类检索结果' in captured.out


def test_run_cli_multi_from_md(tmp_path, capsys):
    """验证 Markdown 多子查询流程能够被触发。"""
    md_file = tmp_path / 'report.md'
    md_file.write_text(
        """# 报告\n\n## 共同母题\n- 名称: 测试母题\n- 关键词: 关键词A, 关键词B\n- 摘要: 这是摘要\n\n## 文章列表\n| 字段 | 内容 |\n| 标签 | ['科幻'、'未来'] |\n| 提及书籍 | 《时间简史》、《三体》 |\n\n## 深度洞察\n- 洞察一句\n""",
        encoding='utf-8',
    )

    args = SimpleNamespace(
        config='config/book_vectorization.yaml',
        query=None,
        query_file=None,
        category=None,
        top_k=5,
        min_rating=None,
        query_mode='multi',
        from_md=str(md_file),
        per_query_top_k=2,
        enable_rerank=False,
        final_top_k=2,
    )

    context = retrieve_cli.run_cli(args)

    assert context['mode'] == 'multi'
    assert context['from_md'] == str(md_file)
    assert context['query_package']['primary']
    dummy = DummyRetriever.instances[-1]
    assert dummy.multi_query_calls
    captured = capsys.readouterr()
    assert '文本相似度检索结果' in captured.out
