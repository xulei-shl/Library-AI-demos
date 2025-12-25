#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Open Library API 示例代码

参考来源: lib/strategies_openlibrary.py

API 文档: https://openlibrary.org/dev/docs/api/search

功能描述:
    - 通过标题和作者搜索 Open Library 作品
    - 返回作品的元数据和版本信息
    - 支持获取单个作品和版本的详细信息

注意:
    - 这是公共 API，无需认证
    - 有速率限制，建议每次请求最多获取 50 条结果
    - 可通过 /works/{key}.json 获取作品详情
    - 可通过 /works/{key}/editions.json 获取所有版本
"""

import requests
from urllib.parse import quote
from thefuzz import fuzz
from typing import Dict, List, Any, Optional


# =============================================================================
# 配置信息
# =============================================================================
OPENLIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
OPENLIBRARY_WORK_URL = "https://openlibrary.org/works"
OPENLIBRARY_API_URL = "https://openlibrary.org"

# 请求头
HEADERS = {
    'Accept': 'application/json',
    'User-Agent': 'Openrefine Post 45 Reconciliation Client'
}


def search_works(title: str, author: str = "", limit: int = 50) -> Dict[str, Any]:
    """
    搜索 Open Library 作品

    参数:
        title: 作品标题
        author: 作者名称（可选）
        limit: 最大返回结果数（默认 50）

    返回:
        搜索结果字典
    """
    params = {}

    if title:
        params['title'] = title
    if author:
        params['author'] = author

    params['limit'] = str(limit)

    try:
        response = requests.get(
            OPENLIBRARY_SEARCH_URL,
            params=params,
            headers=HEADERS,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {'docs': [], 'error': str(e)}


def get_work(work_key: str) -> Dict[str, Any]:
    """
    获取单个作品的详细信息

    参数:
        work_key: 作品 key (例如 'OL45804W')

    返回:
        作品详细信息
    """
    # 确保 key 格式正确
    if not work_key.startswith('OL'):
        work_key = f"OL{work_key}W"

    url = f"{OPENLIBRARY_WORK_URL}/{work_key}.json"

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {'error': str(e)}


def get_work_editions(work_key: str) -> List[Dict[str, Any]]:
    """
    获取作品的所有版本

    参数:
        work_key: 作品 key

    返回:
        版本列表
    """
    # 确保 key 格式正确
    if not work_key.startswith('OL'):
        work_key = f"OL{work_key}W"

    url = f"{OPENLIBRARY_WORK_URL}/{work_key}/editions.json"

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get('entries', [])
    except requests.exceptions.RequestException as e:
        return []


def get_edition(edition_key: str) -> Dict[str, Any]:
    """
    获取单个版本的详细信息

    参数:
        edition_key: 版本 key (例如 'OL12345M')

    返回:
        版本详细信息
    """
    # 确保 key 格式正确
    if not edition_key.startswith('OL'):
        edition_key = f"OL{edition_key}M"

    url = f"{OPENLIBRARY_API_URL}/books/{edition_key}.json"

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {'error': str(e)}


def calculate_fuzzy_score(query_title: str, query_author: str,
                          result_title: str, result_authors: List[str]) -> Dict[str, Any]:
    """
    计算模糊匹配分数

    参数:
        query_title: 查询标题
        query_author: 查询作者
        result_title: 结果标题
        result_authors: 结果作者列表

    返回:
        包含分数的字典
    """
    # 标题评分
    title_scores = []
    if query_title and result_title:
        title_ratio = fuzz.token_sort_ratio(query_title, result_title)
        title_scores.append(title_ratio)

    best_title_score = max(title_scores) if title_scores else 0

    # 作者评分
    author_scores = []
    if query_author and result_authors:
        for result_author in result_authors:
            author_ratio = fuzz.token_sort_ratio(result_author, query_author)
            author_scores.append(author_ratio)

    best_author_score = max(author_scores) if author_scores else 0

    # 计算最终分数
    if query_author:
        if best_title_score >= 80 and best_author_score >= 80:
            final_score = 0.95
        elif best_title_score >= 70 and best_author_score >= 90:
            final_score = 0.90
        elif best_title_score >= 60 and best_author_score >= 85:
            final_score = 0.85
        elif best_title_score >= 50 and best_author_score >= 80:
            final_score = 0.75
        elif best_title_score >= 60 or best_author_score >= 60:
            final_score = 0.60
        else:
            final_score = 0.30
    else:
        if best_title_score >= 90:
            final_score = 0.95
        elif best_title_score >= 80:
            final_score = 0.85
        elif best_title_score >= 70:
            final_score = 0.70
        elif best_title_score >= 60:
            final_score = 0.60
        elif best_title_score >= 50:
            final_score = 0.50
        else:
            final_score = 0.30

    return {
        'title_score': best_title_score,
        'author_score': best_author_score,
        'fuzzy_score': final_score
    }


def parse_search_results(data: Dict, query_title: str,
                         query_author: str = "") -> List[Dict[str, Any]]:
    """
    解析搜索结果并计算分数

    参数:
        data: Open Library 搜索结果
        query_title: 查询标题
        query_author: 查询作者

    返回:
        包含分数的解析结果列表
    """
    results = []

    for doc in data.get('docs', []):
        # 提取数据
        work_key = doc.get('key', '')
        work_title = doc.get('title', '')
        result_authors = doc.get('author_name', [])

        if not work_title:
            continue

        # 计算分数
        score = calculate_fuzzy_score(query_title, query_author, work_title, result_authors)

        # 构建结果
        result = {
            'work_key': work_key,
            'title': work_title,
            'authors': result_authors,
            'first_publish_year': doc.get('first_publish_year'),
            'edition_count': doc.get('edition_count'),
            'cover_id': doc.get('cover_i'),
            'language': doc.get('language', []),
            'subjects': doc.get('subject', [])[:10],  # 限制主题数量
            'score': score['fuzzy_score'],
            'title_score': score['title_score'],
            'author_score': score['author_score']
        }

        results.append(result)

    # 按分数排序
    results.sort(key=lambda x: x['score'], reverse=True)

    return results


def extend_work_data(work_key: str, properties: List[str] = None) -> Dict[str, Any]:
    """
    扩展作品数据，获取指定属性

    参数:
        work_key: 作品 key
        properties: 要获取的属性列表

    返回:
        包含指定属性的字典
    """
    if properties is None:
        properties = ['description', 'subjects', 'subject_places',
                      'subject_people', 'subject_times', 'covers', 'title']

    work_data = get_work(work_key)
    if 'error' in work_data:
        return work_data

    editions_data = get_work_editions(work_key)

    result = {}

    # 工作级别属性
    for prop in properties:
        if prop == 'description':
            desc = work_data.get('description', '')
            if isinstance(desc, dict):
                desc = desc.get('value', '')
            result['description'] = desc

        elif prop == 'subjects':
            result['subjects'] = work_data.get('subjects', [])

        elif prop == 'subject_places':
            result['subject_places'] = work_data.get('subject_places', [])

        elif prop == 'subject_people':
            result['subject_people'] = work_data.get('subject_people', [])

        elif prop == 'subject_times':
            result['subject_times'] = work_data.get('subject_times', [])

        elif prop == 'covers':
            covers = work_data.get('covers', [])
            covers = [c for c in covers if c != -1]  # 过滤无效封面
            result['covers'] = covers

        elif prop == 'title':
            result['title'] = work_data.get('title', '')

    # 版本级别属性（聚合所有版本）
    if any(p in ['isbn_13', 'isbn_10', 'pagination', 'publishers',
                 'oclc_numbers', 'lc_classifications', 'dewey_decimal_class'] for p in properties):
        all_isbn13 = set()
        all_isbn10 = set()
        all_pagination = set()
        all_publishers = set()
        all_oclc = set()
        all_lcc = set()
        all_dewey = set()

        for edition in editions_data:
            if 'isbn_13' in properties:
                for isbn in edition.get('isbn_13', []):
                    all_isbn13.add(isbn)
            if 'isbn_10' in properties:
                for isbn in edition.get('isbn_10', []):
                    all_isbn10.add(isbn)
            if 'pagination' in properties:
                pagination = edition.get('pagination')
                if pagination:
                    all_pagination.add(pagination)
            if 'publishers' in properties:
                for publisher in edition.get('publishers', []):
                    all_publishers.add(publisher)
            if 'oclc_numbers' in properties:
                for oclc in edition.get('oclc_numbers', []):
                    all_oclc.add(oclc)
            if 'lc_classifications' in properties:
                for lcc in edition.get('lc_classifications', []):
                    all_lcc.add(lcc)
            if 'dewey_decimal_class' in properties:
                for dewey in edition.get('dewey_decimal_class', []):
                    all_dewey.add(dewey)

        result['isbn_13'] = sorted(all_isbn13)
        result['isbn_10'] = sorted(all_isbn10)
        result['pagination'] = sorted(all_pagination)
        result['publishers'] = sorted(all_publishers)
        result['oclc_numbers'] = sorted(all_oclc)
        result['lc_classifications'] = sorted(all_lcc)
        result['dewey_decimal_class'] = sorted(all_dewey)

    return result


def get_author(author_key: str) -> Dict[str, Any]:
    """
    获取作者详细信息

    参数:
        author_key: 作者 key (例如 'OL23919A')

    返回:
        作者详细信息
    """
    # 确保 key 格式正确
    if not author_key.startswith('OL'):
        author_key = f"OL{author_key}A"

    url = f"{OPENLIBRARY_API_URL}/authors/{author_key}.json"

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {'error': str(e)}


def search_authors(name: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    搜索作者

    参数:
        name: 作者名称
        limit: 最大返回结果数

    返回:
        作者列表
    """
    url = f"{OPENLIBRARY_API_URL}/search/authors.json"
    params = {'q': name, 'limit': limit}

    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get('docs', [])
    except requests.exceptions.RequestException as e:
        return []


def get_cover_url(cover_id: int, size: str = 'M') -> str:
    """
    获取封面图片 URL

    参数:
        cover_id: 封面 ID
        size: 尺寸 (S, M, L)

    返回:
        封面图片 URL
    """
    return f"https://covers.openlibrary.org/b/id/{cover_id}-{size}.jpg"


# =============================================================================
# 使用示例
# =============================================================================
if __name__ == "__main__":
    # 示例 1: 搜索作品
    print("=" * 60)
    print("示例 1: 搜索 'The Great Gatsby'")
    print("=" * 60)

    results = search_works("The Great Gatsby", "F. Scott Fitzgerald")
    print(f"找到 {len(results.get('docs', []))} 条结果")

    if results.get('docs'):
        parsed = parse_search_results(results, "The Great Gatsby", "F. Scott Fitzgerald")
        for p in parsed[:3]:
            print(f"  - {p['title']} / {p['authors']}")
            print(f"    出版年份: {p['first_publish_year']}, 版本数: {p['edition_count']}")
            if p['cover_id']:
                print(f"    封面: {get_cover_url(p['cover_id'], 'M')}")

    # 示例 2: 搜索并评分
    print("\n" + "=" * 60)
    print("示例 2: 搜索并评分 '1984'")
    print("=" * 60)

    scored = parse_search_results(results, "1984", "George Orwell")

    for p in scored[:5]:
        print(f"  分数: {p['score']:.2f} | {p['title']} / {p['authors']}")
        print(f"    标题分数: {p['title_score']}, 作者分数: {p['author_score']}")

    # 示例 3: 获取作品详情
    print("\n" + "=" * 60)
    print("示例 3: 获取作品详情")
    print("=" * 60)

    if parsed:
        work_key = parsed[0]['work_key'].replace('/works/', '')
        work_data = get_work(work_key)
        if 'error' not in work_data:
            print(f"  标题: {work_data.get('title', 'N/A')}")

            desc = work_data.get('description', '')
            if isinstance(desc, dict):
                desc = desc.get('value', '')[:200]
            print(f"  描述: {desc}...")

            print(f"  主题: {work_data.get('subjects', [])[:5]}")

    # 示例 4: 获取作品版本
    print("\n" + "=" * 60)
    print("示例 4: 获取作品的所有版本")
    print("=" * 60)

    if parsed:
        work_key = parsed[0]['work_key'].replace('/works/', '')
        editions = get_work_editions(work_key)
        print(f"  找到 {len(editions)} 个版本")

        for edition in editions[:3]:
            isbns = edition.get('isbn_13', [])
            publish_date = edition.get('publish_date', 'N/A')
            publishers = edition.get('publishers', [])
            print(f"  - ISBN: {isbns[0] if isbns else 'N/A'}")
            print(f"    出版日期: {publish_date}")
            print(f"    出版社: {publishers}")

    # 示例 5: 扩展作品数据
    print("\n" + "=" * 60)
    print("示例 5: 扩展作品数据")
    print("=" * 60)

    if parsed:
        work_key = parsed[0]['work_key'].replace('/works/', '')
        extended = extend_work_data(work_key, properties=['description', 'subjects', 'isbn_13', 'isbn_10'])
        print(f"  描述: {extended.get('description', 'N/A')[:100]}...")
        print(f"  ISBN-13: {extended.get('isbn_13', [])[:5]}")
        print(f"  主题: {extended.get('subjects', [])[:5]}")

    # 示例 6: 搜索作者
    print("\n" + "=" * 60)
    print("示例 6: 搜索作者")
    print("=" * 60)

    authors = search_authors("Jane Austen")
    for author in authors[:3]:
        print(f"  - {author.get('name', 'N/A')}")
        print(f"    Key: {author.get('key', 'N/A')}")
        print(f"    作品数: {author.get('work_count', 0)}")
