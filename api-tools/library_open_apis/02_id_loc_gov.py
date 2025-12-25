#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Library of Congress (id.loc.gov) API 示例代码

参考来源: lib/strategies_id_loc_gov.py

API 文档: https://id.loc.gov/resources/works/suggest2/

功能描述:
    - 通过关键词搜索 Library of Congress 作品资源
    - 支持模糊匹配和评分
    - 可获取丰富的书目元数据（ISBN、LCCN、OCLC、主题词等）

注意:
    - 这是公共 API，无需认证
    - API 返回 JSON 格式的搜索建议
    - 支持通过 CBD (Concise Bounded Description) 获取完整 RDF 数据
"""

import requests
import xml.etree.ElementTree as ET
from thefuzz import fuzz
from typing import Dict, List, Any, Optional


# =============================================================================
# 配置信息
# =============================================================================
ID_LOC_BASE_URL = "https://id.loc.gov/resources/works/suggest2"

# 请求头
HEADERS = {
    'User-Agent': 'Openrefine Post 45 Reconcilation Client'
}

# XML 命名空间
NAMESPACES = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
    'bf': 'http://id.loc.gov/ontologies/bibframe/',
    'bflc': 'http://id.loc.gov/ontologies/bflc/',
}


def search_id_loc(title: str, author: str = "", limit: int = 50,
                  rdftype: str = "Text") -> Dict[str, Any]:
    """
    搜索 id.loc.gov 作品资源

    参数:
        title: 作品标题
        author: 作者名称（可选）
        limit: 最大返回结果数（默认 50）
        rdftype: RDF 类型过滤（默认 "Text"，可设为 False 取消过滤）

    返回:
        包含搜索结果的字典
    """
    # 构建查询字符串：作者 标题
    q_string = f"{author} {title}".strip() if author else title

    params = {
        'q': q_string,
        'searchtype': 'keyword',
        'count': limit,
    }

    # RDF 类型过滤
    if rdftype:
        params['rdftype'] = rdftype

    try:
        response = requests.get(
            ID_LOC_BASE_URL,
            params=params,
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
            'successful': False,
            'error': str(e),
            'q': q_string,
            'count': 0,
            'hits': []
        }


def calculate_fuzzy_score(query_title: str, query_author: str,
                          hit_title: str, hit_authors: List[str]) -> Dict[str, Any]:
    """
    计算模糊匹配分数

    参数:
        query_title: 查询标题
        query_author: 查询作者
        hit_title: 结果标题
        hit_authors: 结果作者列表

    返回:
        包含各部分分数和最终分数的字典
    """
    # 标题评分
    title_scores = []
    if query_title and hit_title:
        title_ratio = fuzz.token_sort_ratio(hit_title, query_title)
        title_scores.append(title_ratio)

    best_title_score = max(title_scores) if title_scores else 0

    # 作者评分
    author_scores = []
    if query_author and hit_authors:
        for hit_author in hit_authors:
            author_ratio = fuzz.token_sort_ratio(hit_author, query_author)
            author_scores.append(author_ratio)

    best_author_score = max(author_scores) if author_scores else 0

    # 计算最终分数
    if query_author:
        if best_title_score > 80 and best_author_score > 80:
            final_score = 0.95
        elif best_title_score > 70 and best_author_score > 95:
            final_score = 0.90
        elif best_title_score > 50 and best_author_score >= 100:
            final_score = 0.85
        elif best_title_score > 60 or best_author_score > 60:
            final_score = 0.60
        else:
            final_score = 0.30
    else:
        if best_title_score > 90:
            final_score = 0.95
        elif best_title_score > 80:
            final_score = 0.85
        elif best_title_score > 70:
            final_score = 0.70
        elif best_title_score > 50:
            final_score = 0.50
        else:
            final_score = 0.30

    return {
        'title_score': best_title_score,
        'author_score': best_author_score,
        'fuzzy_score': final_score
    }


def search_and_score(title: str, author: str = "", quality_threshold: str = None) -> List[Dict[str, Any]]:
    """
    搜索 id.loc.gov 并评分

    参数:
        title: 作品标题
        author: 作者名称（可选）
        quality_threshold: 质量阈值过滤

    返回:
        按分数排序的匹配结果列表
    """
    data = search_id_loc(title, author)

    if not data.get('hits'):
        return []

    scored_hits = []

    for hit in data['hits']:
        # 提取作者信息
        contributors = []
        if 'more' in hit and 'contributors' in hit['more']:
            contributors = hit['more']['contributors']

        # 提取标题
        hit_title = hit.get('aLabel', '')
        if '.' in hit_title:
            # 移除作者部分（通常在句点之前）
            hit_title = hit_title.split('.', 1)[-1].strip()

        # 计算分数
        scores = calculate_fuzzy_score(title, author, hit_title, contributors)

        # 构建结果
        result = {
            'uri': hit.get('uri', ''),
            'label': hit.get('aLabel', ''),
            'title': hit_title,
            'contributors': contributors,
            'score': scores['fuzzy_score'],
            'title_score': scores['title_score'],
            'author_score': scores['author_score'],
            'variant_titles': hit.get('vLabel', '')
        }

        scored_hits.append(result)

    # 按分数排序
    scored_hits.sort(key=lambda x: x['score'], reverse=True)

    # 质量阈值过滤
    if quality_threshold:
        thresholds = {
            'very high': 0.95,
            'high': 0.90,
            'medium': 0.80,
            'low': 0.60,
            'very low': 0.30
        }
        min_score = thresholds.get(quality_threshold, 0)
        scored_hits = [hit for hit in scored_hits if hit['score'] >= min_score]

    return scored_hits


def enrich_with_cbd(instance_uri: str) -> Dict[str, Any]:
    """
    通过 CBD (Concise Bounded Description) 获取完整 RDF 数据

    参数:
        instance_uri: 实例 URI，例如 http://id.loc.gov/resources/instances/2143880

    返回:
        包含丰富元数据的字典
    """
    # 转换为 CBD 端点格式
    cbd_url = f"{instance_uri}.cbd.rdf"

    try:
        response = requests.get(cbd_url, headers=HEADERS, timeout=30)
        response.raise_for_status()

        # 解析 XML
        root = ET.fromstring(response.text)

        # 提取数据
        enriched_data = {}

        # 查找 Work 元素
        work_elem = root.find('.//bf:Work', NAMESPACES)
        if work_elem is not None:
            # 提取出版日期
            origin_date = work_elem.find('.//bf:originDate', NAMESPACES)
            if origin_date is not None:
                enriched_data['originDate'] = origin_date.text

            # 提取语言
            language_elem = work_elem.find('.//bf:language', NAMESPACES)
            if language_elem is not None:
                lang_resource = language_elem.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource')
                if lang_resource:
                    enriched_data['language'] = lang_resource.split('/')[-1]

            # 提取主题词
            subjects = []
            for subject in work_elem.findall('.//bf:subject/bf:Topic/rdfs:label', NAMESPACES):
                if subject.text:
                    subjects.append(subject.text)
            if subjects:
                enriched_data['subjects'] = subjects

            # 提取类型形式
            genre_forms = []
            for genre in work_elem.findall('.//bf:genreForm/bf:GenreForm/rdfs:label', NAMESPACES):
                if genre.text:
                    genre_forms.append(genre.text)
            if genre_forms:
                enriched_data['genreForms'] = genre_forms

        # 查找 Instance 元素
        instance_elem = root.find('.//bf:Instance', NAMESPACES)
        if instance_elem is not None:
            # 提取标识符
            identifiers = []
            for isbn_elem in instance_elem.findall('.//bf:identifiedBy/bf:Isbn', NAMESPACES):
                isbn_value = isbn_elem.find('rdf:value', NAMESPACES)
                if isbn_value is not None and isbn_value.text:
                    identifiers.append({'type': 'ISBN', 'value': isbn_value.text})

            for lccn_elem in instance_elem.findall('.//bf:identifiedBy/bf:Lccn', NAMESPACES):
                lccn_value = lccn_elem.find('rdf:value', NAMESPACES)
                if lccn_value is not None and lccn_value.text:
                    identifiers.append({'type': 'LCCN', 'value': lccn_value.text.strip()})

            for oclc_elem in instance_elem.findall('.//bf:identifiedBy/bf:OclcNumber', NAMESPACES):
                oclc_value = oclc_elem.find('rdf:value', NAMESPACES)
                if oclc_value is not None and oclc_value.text:
                    identifiers.append({'type': 'OCLC', 'value': oclc_value.text.strip()})

            if identifiers:
                enriched_data['identifiers'] = identifiers

            # 提取出版信息
            prov_elem = instance_elem.find('.//bf:provisionActivity/bf:ProvisionActivity', NAMESPACES)
            if prov_elem is not None:
                date_elem = prov_elem.find('bf:date', NAMESPACES)
                if date_elem is not None and date_elem.text:
                    enriched_data['publication_date'] = date_elem.text

            # 提取页数
            extent_elem = instance_elem.find('.//bf:extent/bf:Extent/rdfs:label', NAMESPACES)
            if extent_elem is not None and extent_elem.text:
                enriched_data['extent'] = extent_elem.text

        return enriched_data

    except requests.RequestException as e:
        return {'error': str(e)}
    except ET.ParseError as e:
        return {'error': f'XML parse error: {str(e)}'}
    except Exception as e:
        return {'error': str(e)}


def get_work_json(work_uri: str) -> Dict[str, Any]:
    """
    获取作品的 JSON-LD 格式数据

    参数:
        work_uri: 作品 URI

    返回:
        JSON-LD 数据字典
    """
    json_url = f"{work_uri}.json"

    try:
        response = requests.get(json_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {'error': str(e)}


def get_instance_bibframe(instance_uri: str) -> Dict[str, Any]:
    """
    获取实例的 Bibframe JSON 数据

    参数:
        instance_uri: 实例 URI

    返回:
        Bibframe 数据字典
    """
    bibframe_url = f"{instance_uri}.bibframe.json"

    try:
        response = requests.get(bibframe_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {'error': str(e)}


def extract_identifier_from_jsonld(data: Dict, id_type: str) -> List[Dict[str, str]]:
    """
    从 JSON-LD 数据中提取指定类型的标识符

    参数:
        data: JSON-LD 数据
        id_type: 标识符类型 ('ISBN', 'LCCN', 'OCLC')

    返回:
        标识符列表
    """
    values = []

    # 类型映射
    type_mapping = {
        'ISBN': 'http://id.loc.gov/ontologies/bibframe/Isbn',
        'LCCN': 'http://id.loc.gov/ontologies/bibframe/Lccn',
        'OCLC': 'http://id.loc.gov/ontologies/bibframe/OclcNumber'
    }

    target_type = type_mapping.get(id_type)
    if not target_type:
        return values

    value_key = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#value'

    for g in data:
        if '@type' in g and target_type in g['@type']:
            if value_key in g:
                for v in g[value_key]:
                    if '@value' in v:
                        values.append({'str': v['@value'].strip()})

    return values if values else [{}]


# =============================================================================
# 使用示例
# =============================================================================
if __name__ == "__main__":
    # 示例 1: 简单搜索
    print("=" * 60)
    print("示例 1: 搜索 'Pride and Prejudice'")
    print("=" * 60)

    results = search_id_loc("Pride and Prejudice", "Jane Austen", limit=10)
    print(f"找到 {len(results.get('hits', []))} 条结果")

    for hit in results.get('hits', [])[:3]:
        print(f"  - {hit.get('aLabel', 'N/A')}")
        print(f"    URI: {hit.get('uri', 'N/A')}")

    # 示例 2: 搜索并评分
    print("\n" + "=" * 60)
    print("示例 2: 搜索并评分 'Moby Dick'")
    print("=" * 60)

    scored_results = search_and_score("Moby Dick", "Herman Melville", quality_threshold='medium')

    for result in scored_results[:5]:
        print(f"  分数: {result['score']:.2f} | {result['label']}")
        print(f"    标题分数: {result['title_score']}, 作者分数: {result['author_score']}")

    # 示例 3: CBD 丰富数据
    print("\n" + "=" * 60)
    print("示例 3: 通过 CBD 获取丰富数据")
    print("=" * 60)

    if results.get('hits'):
        first_uri = results['hits'][0].get('uri')
        if first_uri:
            # 尝试获取 instance URI
            instance_uri = first_uri.replace('/works/', '/instances/')
            enriched = enrich_with_cbd(instance_uri)
            print(f"  丰富数据: {enriched}")

    # 示例 4: 提取标识符
    print("\n" + "=" * 60)
    print("示例 4: 从 JSON-LD 提取标识符")
    print("=" * 60)

    # 假设已经获取了 bibframe 数据
    print("  使用 extract_identifier_from_jsonld(data, 'ISBN') 提取 ISBN")
    print("  使用 extract_identifier_from_jsonld(data, 'LCCN') 提取 LCCN")
    print("  使用 extract_identifier_from_jsonld(data, 'OCLC') 提取 OCLC")
