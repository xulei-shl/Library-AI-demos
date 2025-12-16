#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""手动测试图书检索 API。

使用前请先启动 API 服务：
    cd F:\Github\Library-AI-demos\rss-fetcher
    uvicorn scripts.api.book_retrieval_api:app --reload --port 8000
"""

import requests

BASE_URL = "http://localhost:8000"


def test_text_search():
    """测试文本检索接口。"""
    url = f"{BASE_URL}/api/books/text-search"
    payload = {
        "query": "人工智能伦理与社会影响",
        "top_k": 5,
        "response_format": "json",
    }

    print("=" * 60)
    print("测试文本检索接口")
    print("=" * 60)

    response = requests.post(url, json=payload, timeout=30)
    print(f"状态码: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"返回结果数: {len(data.get('results', []))}")
        for i, book in enumerate(data.get("results", [])[:3], 1):
            print(f"\n[{i}] {book.get('title', 'N/A')}")
            print(f"    作者: {book.get('author', 'N/A')}")
            print(f"    评分: {book.get('rating', 'N/A')}")
    else:
        print(f"错误: {response.text}")


def test_multi_query_search():
    """测试多子查询检索接口（深度检索）。"""
    url = f"{BASE_URL}/api/books/multi-query"

    # Markdown 格式需要符合解析器期望的结构：
    # - ## 共同母题：包含名称、关键词、摘要
    # - ## 文章列表：包含标签和提及书籍的表格
    # - ## 深度洞察：包含洞察要点列表
    markdown_text = """# 交叉主题分析报告 - AI技术对现代民主选举的双刃剑作用

## 共同母题

- 名称: AI技术对现代民主选举的双刃剑作用

- 关键词: AI选举, 民主合法性, 政治传播, 算法治理, 虚假信息, 选民行为, 制度规范

- 摘要: 本文聚焦于AI技术在选举中的深度介入，系统分析其在选民偏好形成、表达与认同三个阶段的作用。AI既提升了选举效率与参与度，也带来了操纵、偏见与虚假信息传播等风险，直接挑战民主制度的核心合法性。

## 文章列表

### 文章 1: AI技术如何影响选民行为

| 字段 | 内容 |
| --- | --- |
| 主题聚焦 | AI技术对现代选举过程与民主合法性的影响 |
| 标签 | AI选举, 民主合法性, 政治传播, 算法治理, 虚假信息 |
| 提及书籍 | [{'title': '民主的经济理论', 'author': 'Anthony Downs'}, {'title': '后真相时代', 'author': 'Lee McIntyre'}] |

## 深度洞察

- AI技术已成为现代选举不可或缺的工具，但其带来的操纵和虚假信息风险正深刻挑战民主制度的合法性。
- 技术进步远超制度规范，亟需加强算法透明和虚假信息治理，以维护选举公信力和民主核心价值。
- 选民行为正经历数字化转型，AI工具在提升效率的同时也加剧了偏见与外部干预，需警惕其对公共信任的侵蚀。
"""

    payload = {
        "markdown_text": markdown_text,
        "per_query_top_k": 10,
        "final_top_k": 15,
        "enable_rerank": False,
        "response_format": "json",
        "save_to_file": False,
    }

    print("\n" + "=" * 60)
    print("测试多子查询检索接口（深度检索）")
    print("=" * 60)

    response = requests.post(url, json=payload, timeout=120)
    print(f"状态码: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        results = data.get("results", [])
        metadata = data.get("metadata", {})

        print(f"返回结果数: {len(results)}")
        print(f"元数据: {metadata}")

        print("\n📚 检索结果:")
        for i, book in enumerate(results[:10], 1):
            print(f"\n[{i}] {book.get('title', 'N/A')}")
            print(f"    作者: {book.get('author', 'N/A')}")
            print(f"    评分: {book.get('rating', 'N/A')}")
            if book.get("score"):
                print(f"    相似度: {book.get('score', 'N/A'):.4f}")
    else:
        print(f"错误: {response.text}")


def main():
    """主函数。"""
    print("开始测试图书检索 API...")
    print(f"API 地址: {BASE_URL}\n")

    try:
        # 先检查服务是否运行
        health_check = requests.get(f"{BASE_URL}/docs", timeout=5)
        if health_check.status_code != 200:
            print("警告: API 服务可能未正常运行")
    except requests.exceptions.ConnectionError:
        print("错误: 无法连接到 API 服务")
        print("请先启动服务:")
        print("    uvicorn scripts.api.book_retrieval_api:app --reload --port 8000")
        return

    # 运行测试
    test_text_search()
    test_multi_query_search()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
