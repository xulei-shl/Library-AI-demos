#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VIAF (Virtual International Authority File) API 示例代码

参考来源: lib/strategies_viaf.py

API 文档: https://www.viaf.org/viaf/api/

功能描述:
    - 搜索权威名称记录（人名、地名、作品名等）
    - 支持名称搜索和工作搜索
    - 返回跨多个国家图书馆的权威数据

注意:
    - 这是公共 API，无需认证
    - 使用 POST 请求，JSON 格式的查询体
    - 支持名称类型（个人、团体、作品等）
"""

import requests
import html
import json
from thefuzz import fuzz
from typing import Dict, List, Any, Optional


# =============================================================================
# 配置信息
# =============================================================================
VIAF_SEARCH_URL = "https://viaf.org/api/search"

# 请求头
HEADERS = {
    'User-Agent': 'Openrefine Post 45 Reconcilation Client',
    'Content-Type': 'application/json'
}


def search_names(name: str, name_type: str = "VIAF_Personal", limit: int = 50) -> Dict[str, Any]:
    """
    搜索 VIAF 名称记录

    参数:
        name: 要搜索的名称
        name_type: 名称类型 ('VIAF_Personal', 'VIAF_Corporate', 'VIAF_Geographic', 'VIAF_Work')
        limit: 最大返回结果数（默认 50）

    返回:
        VIAF API 响应
    """
    # 根据类型选择搜索字段
    field = 'local.personalNames' if name_type == 'VIAF_Personal' else 'local.names'

    query = {
        "meta": {
            "env": "prod",
            "pageIndex": 0,
            "pageSize": limit
        },
        "reqValues": {
            "field": field,
            "index": "VIAF",
            "searchTerms": name
        }
    }

    try:
        response = requests.post(
            VIAF_SEARCH_URL,
            json=query,
            headers=HEADERS,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        data['successful'] = True
        data['error'] = None
        return data
    except requests.exceptions.RequestException as e:
        return {
            "message": "/api/search Successfully reached!",
            "queryResult": {
                "version": {"value": 1.1, "type": "xsd:string"},
                "numberOfRecords": {"value": 0, "type": "xsd:nonNegativeInteger"},
                "resultSetIdleTime": {"value": 1, "type": "xsd:positiveInteger"},
                "records": {"record": []}
            },
            "successful": False,
            "error": str(e)
        }


def search_works(author: str, title: str, limit: int = 50) -> Dict[str, Any]:
    """
    搜索 VIAF 作品记录

    参数:
        author: 作者名称
        title: 作品标题
        limit: 最大返回结果数（默认 50）

    返回:
        VIAF API 响应
    """
    query = {
        "meta": {
            "env": "prod",
            "pageIndex": 0,
            "pageSize": limit
        },
        "reqValues": {
            "field": "local.uniformTitleWorks",
            "index": "VIAF",
            "searchTerms": f"{author} {title}".strip()
        }
    }

    try:
        response = requests.post(
            VIAF_SEARCH_URL,
            json=query,
            headers=HEADERS,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {
            "message": "/api/search Successfully reached!",
            "queryResult": {
                "version": {"value": 1.1, "type": "xsd:string"},
                "numberOfRecords": {"value": 0, "type": "xsd:nonNegativeInteger"},
                "resultSetIdleTime": {"value": 1, "type": "xsd:positiveInteger"},
                "records": {"record": []}
            },
            "successful": False,
            "error": str(e)
        }


def parse_name_results(data: Dict, query_name: str,
                       birth_year: str = None) -> List[Dict[str, Any]]:
    """
    解析名称搜索结果并计算分数

    参数:
        data: VIAF API 响应数据
        query_name: 查询的名称
        birth_year: 出生年份（用于辅助匹配）

    返回:
        包含分数的解析结果列表
    """
    results = []

    if 'records' not in data.get('queryResult', {}):
        return results

    for record in data['queryResult']['records']['record']:
        viaf_cluster = record.get('recordData', {}).get('VIAFCluster', {})

        # 提取 VIAF ID
        viaf_id = viaf_cluster.get('viafID')
        uri = f"http://viaf.org/viaf/{viaf_id}"

        # 提取主要标目
        auth_label = viaf_id
        if 'mainHeadings' in viaf_cluster:
            main_headings = viaf_cluster['mainHeadings'].get('data', [])
            if main_headings:
                auth_label = html.unescape(str(main_headings[0]['text']))

        # 提取关联作品
        titles = []
        if 'titles' in viaf_cluster and 'work' in viaf_cluster['titles']:
            for work in viaf_cluster['titles']['work']:
                titles.append(html.unescape(str(work.get('title', ''))))

        # 计算分数
        score = calculate_name_score(query_name, auth_label, birth_year)

        result = {
            'uri': uri,
            'viaf_id': viaf_id,
            'auth_label': auth_label,
            'titles': titles,
            'score': score['final_score'],
            'title_score': score['title_score'],
            'author_score': score['author_score'],
            'was_reconciled_using_birthday': score['used_birth_year']
        }

        results.append(result)

    # 按分数排序
    results.sort(key=lambda x: x['score'], reverse=True)

    return results


def parse_work_results(data: Dict, query_title: str,
                       query_author: str = "") -> List[Dict[str, Any]]:
    """
    解析作品搜索结果并计算分数

    参数:
        data: VIAF API 响应数据
        query_title: 查询的作品标题
        query_author: 查询的作者名称

    返回:
        包含分数的解析结果列表
    """
    results = []

    if 'records' not in data.get('queryResult', {}):
        return results

    for record in data['queryResult']['records']['record']:
        viaf_cluster = record.get('recordData', {}).get('VIAFCluster', {})

        viaf_id = viaf_cluster.get('viafID')

        # 提取主要标目
        main_headings = viaf_cluster.get('mainHeadings', {}).get('data', [])
        headings_text = []
        for heading in main_headings:
            if isinstance(heading, dict) and 'text' in heading:
                headings_text.append(html.unescape(heading['text']))

        # 解析标题和作者（格式通常为 "作者 | 标题"）
        heading_author = ""
        heading_title = ""
        for heading in headings_text:
            if '|' in heading:
                parts = heading.split('|', 1)
                heading_author = parts[0].strip()
                heading_title = parts[1].strip()
            elif ', by ' in heading.lower():
                parts = heading.split(', by ', 1)
                heading_title = parts[0].strip()
                heading_author = parts[1].strip() if len(parts) > 1 else ""
            else:
                heading_title = heading

        # 计算分数
        score = calculate_work_score(query_title, query_author, heading_title, heading_author)

        result = {
            'uri': f"http://viaf.org/viaf/{viaf_id}",
            'viaf_id': viaf_id,
            'heading': heading,
            'heading_author': heading_author,
            'heading_title': heading_title,
            'score': score['final_score'],
            'title_score': score['title_score'],
            'author_score': score['author_score']
        }

        results.append(result)

    # 按分数排序
    results.sort(key=lambda x: x['score'], reverse=True)

    return results


def calculate_name_score(query_name: str, result_name: str,
                         birth_year: str = None) -> Dict[str, Any]:
    """
    计算名称匹配分数

    参数:
        query_name: 查询的名称
        result_name: 结果名称
        birth_year: 出生年份

    返回:
        包含分数的字典
    """
    # 基础分数
    score = 0.25

    # 模糊匹配
    fuzz_score = fuzz.token_sort_ratio(query_name, result_name) / 100 - 0.5
    score += fuzz_score

    # 如果提供了出生年份，检查是否匹配
    used_birth_year = False
    if birth_year and birth_year in result_name:
        if fuzz_score >= 0.15:  # 名称相似度阈值
            score = 1.0
            used_birth_year = True

    return {
        'final_score': min(max(score, 0), 1),
        'title_score': 0,
        'author_score': fuzz_score * 100 + 50,
        'used_birth_year': used_birth_year
    }


def calculate_work_score(query_title: str, query_author: str,
                         result_title: str, result_author: str) -> Dict[str, Any]:
    """
    计算作品匹配分数

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


def get_wikidata_from_viaf_search(search_results: Dict) -> Optional[str]:
    """
    从 VIAF 搜索结果中提取 Wikidata ID

    参数:
        search_results: VIAF search_names() 返回的原始结果

    返回:
        Wikidata ID (如 Q692) 或 None
    """
    import re

    json_str = json.dumps(search_results)
    # VIAF 搜索结果中 Wikidata 格式: "WKP|Q692"
    qids = re.findall(r"WKP\|Q[0-9]{2,}", json_str)

    if qids:
        return qids[0].split("|")[1]

    return None


def get_wikidata_from_viaf_cluster(viaf_id: str) -> Optional[str]:
    """
    获取 VIAF 集群的 Wikidata ID

    由于 VIAF 网站改版，/viaf.json 和 /clusters.json 端点已下线。
    此函数使用 /api/search 端点重新查询获取数据。

    参数:
        viaf_id: VIAF ID

    返回:
        Wikidata ID 或 None
    """
    # 使用 /api/search 重新查询该 VIAF ID
    url = "https://viaf.org/api/search"
    query = {
        "meta": {"env": "prod", "pageIndex": 0, "pageSize": 1},
        "reqValues": {
            "field": "local.viafID",
            "index": "VIAF",
            "searchTerms": viaf_id
        }
    }

    try:
        response = requests.post(url, json=query, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()
        return get_wikidata_from_viaf_search(data)
    except requests.exceptions.RequestException:
        return None


# =============================================================================
# 使用示例
# =============================================================================
if __name__ == "__main__":
    # 示例 1: 搜索个人名称
    print("=" * 60)
    print("示例 1: 搜索 'Shakespeare, William'")
    print("=" * 60)

    results = search_names("Shakespeare, William", name_type="VIAF_Personal")
    print(f"找到 {results.get('queryResult', {}).get('numberOfRecords', {}).get('value', 0)} 条记录")

    if results.get('queryResult', {}).get('records', {}).get('record'):
        parsed = parse_name_results(results, "Shakespeare, William", birth_year="1564")
        for p in parsed[:3]:
            print(f"  - {p['auth_label']}")
            print(f"    URI: {p['uri']}, 分数: {p['score']:.2f}")

    # 示例 2: 搜索作品
    print("\n" + "=" * 60)
    print("示例 2: 搜索 'Hamlet'")
    print("=" * 60)

    work_results = search_works("Shakespeare, William", "Hamlet")
    if work_results.get('queryResult', {}).get('records', {}).get('record'):
        parsed_works = parse_work_results(work_results, "Hamlet", "Shakespeare, William")
        for p in parsed_works[:3]:
            print(f"  - {p['heading']}")
            print(f"    标题分数: {p['title_score']}, 作者分数: {p['author_score']}")

    # 示例 3: 获取完整集群数据
    print("\n" + "=" * 60)
    print("示例 3: 获取 VIAF 集群详情")
    print("=" * 60)

    # 确保 parsed 已定义且不为空
    try:
        if 'parsed' in dir() and parsed:
            viaf_id = parsed[0]['viaf_id']
            print(f"  VIAF ID: {viaf_id}")
            print(f"  主要标目: {parsed[0]['auth_label']}")
            print(f"  关联作品数: {len(parsed[0]['titles'])}")

            # 显示一些关联作品
            if parsed[0]['titles'][:5]:
                print(f"  关联作品示例: {parsed[0]['titles'][:3]}")

            # 通过搜索 API 获取完整数据
            print("\n  通过搜索 API 获取完整数据...")
            search_result = search_names("Shakespeare, William", name_type="VIAF_Personal", limit=1)
            if search_result.get('successful'):
                main_headings = search_result.get('queryResult', {}).get('records', {}).get('record', [])
                if main_headings:
                    cluster = main_headings[0].get('recordData', {}).get('VIAFCluster', {})
                    print(f"  数据来源数: {len(cluster.get('mainHeadings', {}).get('data', []))}")
        else:
            print("  没有可用的 VIAF ID (parsed 变量未定义或为空)")
    except NameError as e:
        print(f"  错误: 变量未定义 - {e}")
    except Exception as e:
        print(f"  错误: {e}")

    # 示例 4: 从 VIAF 获取 Wikidata ID
    print("\n" + "=" * 60)
    print("示例 4: 从 VIAF 获取关联的 Wikidata ID")
    print("=" * 60)

    try:
        if 'parsed' in dir() and parsed:
            viaf_id = parsed[0]['viaf_id']
            print(f"  正在从 VIAF ID {viaf_id} 获取 Wikidata ID...")

            # 方法1: 从已有搜索结果提取
            if 'search_result' in dir() and search_result:
                wikidata_id = get_wikidata_from_viaf_search(search_result)
                if wikidata_id:
                    print(f"  Wikidata ID (从搜索结果): {wikidata_id}")
                    print(f"  Wikidata URI: https://www.wikidata.org/wiki/{wikidata_id}")

            # 方法2: 重新查询 VIAF ID 获取
            wikidata_id2 = get_wikidata_from_viaf_cluster(viaf_id)
            if wikidata_id2:
                print(f"  Wikidata ID (重新查询): {wikidata_id2}")
                print(f"  Wikidata URI: https://www.wikidata.org/wiki/{wikidata_id2}")
        else:
            print("  没有可用的 VIAF ID (parsed 变量未定义或为空)")
    except NameError as e:
        print(f"  错误: 变量未定义 - {e}")
    except Exception as e:
        print(f"  错误: {e}")
