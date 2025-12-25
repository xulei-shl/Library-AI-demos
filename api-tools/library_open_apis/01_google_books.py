#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Books API 示例代码

参考来源: lib/strategies_google_books.py

API 文档: https://developers.google.com/books/docs/v1/volumes

功能描述:
    - 通过标题和作者搜索 Google Books 数据库
    - 返回书籍的元数据信息（标题、作者、描述、ISBN 等）
    - 使用 Levenshtein 距离进行模糊匹配评分

注意:
    - 这是公共 API，无需认证
    - 有速率限制，建议每次请求最多获取 40 条结果
"""

import requests
from thefuzz import fuzz
from typing import Dict, List, Any


# =============================================================================
# 配置信息
# =============================================================================
GOOGLE_BOOKS_BASE_URL = "https://www.googleapis.com/books/v1/volumes"

# 请求头
HEADERS = {
    'User-Agent': 'Openrefine Post 45 Reconcilation Client'
}


def search_google_books(title: str, author: str = "", max_results: int = 40) -> Dict[str, Any]:
    """
    搜索 Google Books API

    参数:
        title: 书籍标题
        author: 作者名称（可选）
        max_results: 最大返回结果数（默认 40）

    返回:
        包含搜索结果的字典
    """

    # 构建查询字符串
    # 格式: intitle:标题 inauthor:作者
    q_string = f"intitle:{title}"
    if author:
        q_string += f" inauthor:{author}"

    params = {
        'q': q_string,
        'projection': 'full',  # 获取完整信息
        'maxResults': max_results
    }

    try:
        response = requests.get(
            GOOGLE_BOOKS_BASE_URL,
            params=params,
            headers=HEADERS,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {
            'successful': False,
            'error': str(e),
            'kind': 'books#volumes',
            'totalItems': 0,
            'items': []
        }


def calculate_fuzzy_score(query_title: str, query_author: str,
                          result_title: str, result_authors: List[str]) -> Dict[str, Any]:
    """
    计算模糊匹配分数

    使用 thefuzz 库的 token_sort_ratio 计算标题和作者的相似度

    参数:
        query_title: 查询标题
        query_author: 查询作者
        result_title: 结果标题
        result_authors: 结果作者列表

    返回:
        包含各部分分数和最终分数的字典
    """
    # 标题评分
    title_scores = []
    if query_title and result_title:
        title_ratio = fuzz.token_sort_ratio(result_title, query_title)
        title_scores.append(title_ratio)

    # 最佳标题分数
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
        # 标题和作者都重要
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
        # 只有标题重要
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
    搜索并评分 Google Books 结果

    参数:
        title: 书籍标题
        author: 作者名称（可选）
        quality_threshold: 质量阈值过滤 ('very high', 'high', 'medium', 'low', 'very low')

    返回:
        按分数排序的匹配结果列表
    """
    # 执行搜索
    data = search_google_books(title, author)

    if data.get('totalItems', 0) == 0:
        return []

    scored_items = []

    # 对每个结果进行评分
    for item in data.get('items', []):
        volume_info = item.get('volumeInfo', {})
        item_title = volume_info.get('title', '')
        item_subtitle = volume_info.get('subtitle', '')
        full_title = f"{item_title}: {item_subtitle}" if item_subtitle else item_title
        item_authors = volume_info.get('authors', [])

        # 计算分数
        scores = calculate_fuzzy_score(title, author, full_title, item_authors)

        # 构建结果
        result = {
            'id': f"https://www.googleapis.com/books/v1/volumes/{item['id']}",
            'title': full_title,
            'authors': item_authors,
            'description': volume_info.get('description', '')[:200],
            'isbn': extract_isbn(volume_info),
            'published_date': volume_info.get('publishedDate', ''),
            'language': volume_info.get('language', ''),
            'page_count': volume_info.get('pageCount'),
            'categories': volume_info.get('categories', []),
            'thumbnail': volume_info.get('imageLinks', {}).get('thumbnail', ''),
            'preview_link': volume_info.get('previewLink', ''),
            'title_score': scores['title_score'],
            'author_score': scores['author_score'],
            'fuzzy_score': scores['fuzzy_score']
        }

        scored_items.append(result)

    # 按分数排序
    scored_items.sort(key=lambda x: x['fuzzy_score'], reverse=True)

    # 应用质量阈值过滤
    if quality_threshold:
        thresholds = {
            'very high': 0.95,
            'high': 0.90,
            'medium': 0.80,
            'low': 0.60,
            'very low': 0.30
        }
        min_score = thresholds.get(quality_threshold, 0)
        scored_items = [item for item in scored_items if item['fuzzy_score'] >= min_score]

    return scored_items


def extract_isbn(volume_info: Dict) -> List[str]:
    """
    从 volumeInfo 中提取 ISBN

    参数:
        volume_info: Google Books 返回的 volumeInfo 字典

    返回:
        ISBN 列表
    """
    isbns = []
    for identifier in volume_info.get('industryIdentifiers', []):
        if 'ISBN' in identifier.get('type', ''):
            isbns.append(identifier['identifier'])
    return isbns


def get_book_details(volume_id: str) -> Dict[str, Any]:
    """
    获取单本书籍的详细信息

    参数:
        volume_id: Google Books _volume ID

    返回:
        书籍详细信息字典
    """
    url = f"{GOOGLE_BOOKS_BASE_URL}/{volume_id}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {'error': str(e)}


# =============================================================================
# 使用示例
# =============================================================================
if __name__ == "__main__":
    # 示例 1: 简单搜索
    print("=" * 60)
    print("示例 1: 搜索 'The Great Gatsby'")
    print("=" * 60)

    results = search_google_books("The Great Gatsby", "F. Scott Fitzgerald")
    print(f"找到 {results.get('totalItems', 0)} 条结果")

    for item in results.get('items', [])[:3]:
        info = item['volumeInfo']
        print(f"  - {info.get('title')} by {info.get('authors', [])}")

    # 示例 2: 搜索并评分
    print("\n" + "=" * 60)
    print("示例 2: 搜索并评分 '1984'")
    print("=" * 60)

    scored_results = search_and_score("1984", "George Orwell", quality_threshold='medium')

    for result in scored_results[:5]:
        print(f"  分数: {result['fuzzy_score']:.2f} | {result['title']}")
        print(f"    ISBN: {result['isbn']}")
        print(f"    标题分数: {result['title_score']}, 作者分数: {result['author_score']}")

    # 示例 3: 获取详细信息
    print("\n" + "=" * 60)
    print("示例 3: 获取单本书籍详情")
    print("=" * 60)

    if results.get('items'):
        volume_id = results['items'][0]['id']
        details = get_book_details(volume_id)
        info = details.get('volumeInfo', {})
        print(f"  标题: {info.get('title')}")
        print(f"  作者: {info.get('authors', [])}")
        print(f"  出版日期: {info.get('publishedDate')}")
        print(f"  页数: {info.get('pageCount')}")
        print(f"  ISBN: {extract_isbn(info)}")
