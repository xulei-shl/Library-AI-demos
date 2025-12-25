#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wikidata SPARQL API 示例代码

参考来源: lib/strategies_wikidata.py

API 文档: https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service

功能描述:
    - 通过 SPARQL 查询 Wikidata 数据库
    - 使用 EntitySearch API 搜索实体
    - 返回作品的作者、标题等元数据

注意:
    - 这是公共 API，无需认证
    - 使用 SPARQL 查询语言
    - 返回 JSON 格式的查询结果
"""

import requests
from urllib.parse import quote
from thefuzz import fuzz
from typing import Dict, List, Any, Optional


# =============================================================================
# 配置信息
# =============================================================================
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"

# 请求头
HEADERS = {
    'Accept': 'application/sparql-results+json',
    'User-Agent': 'Openrefine Post 45 Reconciliation Client'
}


def entity_search(title: str, author: str = "", language: str = "en",
                  limit: int = 50) -> Dict[str, Any]:
    """
    使用 Wikidata EntitySearch API 搜索实体

    参数:
        title: 要搜索的标题
        author: 作者名称（可选）
        language: 语言代码（默认 "en"）
        limit: 最大返回结果数（默认 50）

    返回:
        SPARQL 查询结果
    """
    # 构建 SPARQL 查询
    # 使用 mwapi 服务进行实体搜索
    search_term = title.replace('"', '\\"')

    sparql_query = f"""
    SELECT ?item ?itemLabel ?author ?authorLabel ?creator ?creatorLabel WHERE {{
      SERVICE wikibase:mwapi {{
        bd:serviceParam wikibase:api "EntitySearch" .
        bd:serviceParam wikibase:endpoint "www.wikidata.org" .
        bd:serviceParam mwapi:search "{search_term}" .
        bd:serviceParam mwapi:language "{language}" .
        ?item wikibase:apiOutputItem mwapi:item .
        ?num wikibase:apiOrdinal true .
      }}
      OPTIONAL {{
        ?item wdt:P50 ?author .
      }}
      OPTIONAL {{
        ?item wdt:P170 ?creator .
      }}

      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en" . }}
    }}
    LIMIT {limit}
    """

    url = f"{WIKIDATA_SPARQL_URL}?query={quote(sparql_query)}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {'successful': False, 'error': str(e), 'results': {}}


def search_works(title: str, author: str = "", limit: int = 50) -> Dict[str, Any]:
    """
    搜索 Wikidata 作品实体

    参数:
        title: 作品标题
        author: 作者名称（可选）
        limit: 最大返回结果数

    返回:
        包含搜索结果的字典
    """
    # 构建 SPARQL 查询 - 搜索书籍作品 (Q571)
    search_term = title.replace('"', '\\"')

    sparql_query = f"""
    SELECT ?item ?itemLabel ?authorLabel ?creatorLabel ?work_typeLabel WHERE {{
      SERVICE wikibase:mwapi {{
        bd:serviceParam wikibase:api "EntitySearch" .
        bd:serviceParam wikibase:endpoint "www.wikidata.org" .
        bd:serviceParam mwapi:search "{search_term}" .
        bd:serviceParam mwapi:language "en" .
        ?item wikibase:apiOutputItem mwapi:item .
        ?num wikibase:apiOrdinal true .
      }}

      # 筛选文学作品
      OPTIONAL {{ ?item wdt:P31/wdt:P279* wd:Q571 . }}

      # 获取作者
      OPTIONAL {{
        ?item wdt:P50 ?author .
      }}
      OPTIONAL {{
        ?item wdt:P170 ?creator .
      }}

      # 获取作品类型
      OPTIONAL {{
        ?item wdt:P31 ?work_type .
      }}

      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
    }}
    LIMIT {limit}
    """

    url = f"{WIKIDATA_SPARQL_URL}?query={quote(sparql_query)}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {'successful': False, 'error': str(e), 'results': {}}


def get_work_details(wikidata_id: str) -> Dict[str, Any]:
    """
    获取 Wikidata 实体的详细信息

    参数:
        wikidata_id: Wikidata ID (例如 Q42)

    返回:
        实体详细信息
    """
    # 构建 SPARQL 查询获取实体属性
    sparql_query = f"""
    SELECT ?prop ?propLabel ?valueLabel WHERE {{
      wd:{wikidata_id} ?prop ?value .
      ?prop a wikibase:Property .
      FILTER(STRSTARTS(STR(?prop), "http://www.wikidata.org/prop/P"))

      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
    }}
    """

    url = f"{WIKIDATA_SPARQL_URL}?query={quote(sparql_query)}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {'error': str(e)}


def calculate_fuzzy_score(query_title: str, query_author: str,
                          result_title: str, result_author: str) -> Dict[str, Any]:
    """
    计算模糊匹配分数

    参数:
        query_title: 查询标题
        query_author: 查询作者
        result_title: 结果标题
        result_author: 结果作者

    返回:
        包含分数的字典
    """
    # 标题评分
    title_score = 0
    if query_title and result_title:
        title_score = fuzz.token_sort_ratio(query_title, result_title)

    # 作者评分
    author_score = 0
    if query_author and result_author:
        author_score = fuzz.token_sort_ratio(query_author, result_author)

    # 计算最终分数
    if query_author:
        if title_score >= 80 and author_score >= 80:
            final_score = 0.95
        elif title_score >= 70 and author_score >= 90:
            final_score = 0.90
        elif title_score >= 60 and author_score >= 85:
            final_score = 0.85
        elif title_score >= 50 and author_score >= 80:
            final_score = 0.75
        elif title_score >= 60 or author_score >= 60:
            final_score = 0.60
        else:
            final_score = 0.30
    else:
        if title_score >= 90:
            final_score = 0.95
        elif title_score >= 80:
            final_score = 0.85
        elif title_score >= 70:
            final_score = 0.70
        elif title_score >= 60:
            final_score = 0.60
        elif title_score >= 50:
            final_score = 0.50
        else:
            final_score = 0.30

    return {
        'final_score': final_score,
        'title_score': title_score,
        'author_score': author_score
    }


def parse_search_results(data: Dict, query_title: str,
                         query_author: str = "") -> List[Dict[str, Any]]:
    """
    解析 SPARQL 查询结果并计算分数

    参数:
        data: SPARQL 查询结果
        query_title: 查询标题
        query_author: 查询作者

    返回:
        包含分数的解析结果列表
    """
    results = []

    bindings = data.get('results', {}).get('bindings', [])

    for binding in bindings:
        # 提取数据
        item_uri = binding.get('item', {}).get('value', '')
        item_label = binding.get('itemLabel', {}).get('value', '')

        # 跳过纯 Q-ID（没有标签）
        if item_label.startswith('Q') and not any(c.isalpha() for c in item_label[1:]):
            continue

        # 提取作者（优先使用 authorLabel）
        result_author = ""
        if 'authorLabel' in binding:
            result_author = binding['authorLabel'].get('value', '')
        elif 'creatorLabel' in binding:
            result_author = binding['creatorLabel'].get('value', '')

        # 计算分数
        score = calculate_fuzzy_score(query_title, query_author, item_label, result_author)

        # 提取 Wikidata ID
        wikidata_id = item_uri.replace('http://www.wikidata.org/entity/', '')

        result = {
            'wikidata_id': wikidata_id,
            'uri': item_uri,
            'label': item_label,
            'author': result_author,
            'score': score['final_score'],
            'title_score': score['title_score'],
            'author_score': score['author_score']
        }

        results.append(result)

    # 按分数排序
    results.sort(key=lambda x: x['score'], reverse=True)

    return results


def get_entity_properties(wikidata_id: str, property_ids: List[str] = None) -> Dict[str, Any]:
    """
    获取实体的指定属性值

    参数:
        wikidata_id: Wikidata ID
        property_ids: 要获取的属性 ID 列表（例如 ['P31', 'P50', 'P577']）

    返回:
        属性值字典
    """
    if property_ids is None:
        # 默认获取一些常用属性
        property_ids = ['P31', 'P50', 'P170', 'P577', 'P123', 'P136', 'P1476']

    # 构建 SPARQL 查询
    properties_where = " . \n      ".join([f'OPTIONAL {{ wd:{wikidata_id} wdt:{p} ?{p} }}' for p in property_ids])
    labels_select = " ".join([f"?{p}Label" for p in property_ids])

    sparql_query = f"""
    SELECT ?itemLabel {labels_select} WHERE {{
      wd:{wikidata_id} ?prop ?value .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
    }}
    """

    url = f"{WIKIDATA_SPARQL_URL}?query={quote(sparql_query)}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {'error': str(e)}


def search_by_isbn(isbn: str) -> List[Dict[str, str]]:
    """
    通过 ISBN 搜索 Wikidata 实体

    参数:
        isbn: ISBN 号码

    返回:
        匹配的实体列表
    """
    sparql_query = f"""
    SELECT ?item ?itemLabel ?authorLabel ?pubDate WHERE {{
      ?item wdt:P212 ?isbn13 .
      FILTER(?isbn13 = "{isbn}" || STR(?isbn13) = "{isbn}")
    }}
    UNION
    {{
      ?item wdt:P957 ?isbn10 .
      FILTER(?isbn10 = "{isbn}")
    }}

      OPTIONAL {{ ?item wdt:P50 ?author . }}
      OPTIONAL {{ ?item wdt:P577 ?pubDate . }}

      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
    }}
    """

    url = f"{WIKIDATA_SPARQL_URL}?query={quote(sparql_query)}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=60)
        response.raise_for_status()
        data = response.json()

        results = []
        for binding in data.get('results', {}).get('bindings', []):
            item_uri = binding.get('item', {}).get('value', '')
            results.append({
                'wikidata_id': item_uri.replace('http://www.wikidata.org/entity/', ''),
                'label': binding.get('itemLabel', {}).get('value', ''),
                'author': binding.get('authorLabel', {}).get('value', ''),
                'pub_date': binding.get('pubDate', {}).get('value', '')
            })

        return results

    except requests.exceptions.RequestException as e:
        return []


# =============================================================================
# 使用示例
# =============================================================================
if __name__ == "__main__":
    # 示例 1: 实体搜索
    print("=" * 60)
    print("示例 1: 搜索 '1984'")
    print("=" * 60)

    results = entity_search("1984", limit=10)
    print(f"找到 {len(results.get('results', {}).get('bindings', []))} 条结果")

    if results.get('results', {}).get('bindings'):
        parsed = parse_search_results(results, "1984", "George Orwell")
        for p in parsed[:5]:
            print(f"  - {p['label']} / {p['author']}")
            print(f"    Wikidata: {p['wikidata_id']}, 分数: {p['score']:.2f}")

    # 示例 2: 搜索作品实体
    print("\n" + "=" * 60)
    print("示例 2: 搜索 'Pride and Prejudice'")
    print("=" * 60)

    work_results = search_works("Pride and Prejudice", "Jane Austen")
    if work_results.get('results', {}).get('bindings'):
        parsed = parse_search_results(work_results, "Pride and Prejudice", "Jane Austen")
        for p in parsed[:5]:
            print(f"  - {p['label']} / {p['author']}")
            print(f"    分数: {p['score']:.2f}")

    # 示例 3: 通过 ISBN 搜索
    print("\n" + "=" * 60)
    print("示例 3: 通过 ISBN 搜索")
    print("=" * 60)

    isbn_results = search_by_isbn("9780743273565")  # Great Gatsby
    for r in isbn_results:
        print(f"  - {r['label']} / {r['author']}")
        print(f"    Wikidata: {r['wikidata_id']}")

    # 示例 4: 获取实体详情
    print("\n" + "=" * 60)
    print("示例 4: 获取实体详情")
    print("=" * 60)

    if parsed:
        details = get_work_details(parsed[0]['wikidata_id'])
        if 'error' not in details:
            print(f"  Wikidata ID: {parsed[0]['wikidata_id']}")
            print(f"  标签: {parsed[0]['label']}")
