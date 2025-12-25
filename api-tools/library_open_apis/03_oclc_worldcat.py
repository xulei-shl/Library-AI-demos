#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCLC WorldCat API 示例代码

参考来源: lib/strategies_oclc.py

API 文档: https://developer.api.oclc.org/worldcat-search-v2

功能描述:
    - 通过作者和标题搜索 WorldCat 书目数据库
    - 返回丰富的书目记录信息
    - 支持作品聚类（Work ID）

注意:
    - 需要 API 密钥（Client ID 和 Secret）
    - 使用 OAuth 2.0 客户端凭证流程认证
    - 认证 token有效期约 20 分钟
"""

import requests
import time
from thefuzz import fuzz
from typing import Dict, List, Any, Optional


# =============================================================================
# 配置信息
# =============================================================================
OCLC_TOKEN_URL = "https://oauth.oclc.org/token"
OCLC_SEARCH_URL = "https://americas.discovery.api.oclc.org/worldcat/search/v2/bibs"


class WorldCatClient:
    """OCLC WorldCat API 客户端"""

    def __init__(self, client_id: str, secret: str):
        """
        初始化客户端

        参数:
            client_id: OCLC Client ID
            secret: OCLC Secret
        """
        self.client_id = client_id
        self.secret = secret
        self.headers = {}
        self.auth_timestamp = None

    def reauth(self) -> bool:
        """
        刷新访问令牌

        返回:
            认证是否成功
        """
        # 检查是否需要重新认证（token 有效期约 20 分钟）
        if self.auth_timestamp is not None:
            sec_elapsed = time.time() - self.auth_timestamp
            sec_remaining = 1199 - 1 - int(sec_elapsed)
            if sec_remaining > 60:
                return True  # Token 仍然有效

        try:
            response = requests.post(
                OCLC_TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    'scope': ['wcapi']
                },
                auth=(self.client_id, self.secret),
                timeout=30
            )
            response.raise_for_status()

            response_data = response.json()
            if "access_token" not in response_data:
                print("ERROR: access token not found (BAD KEY/SECRET?)")
                return False

            self.auth_timestamp = time.time()
            self.headers = {
                'accept': 'application/json',
                'Authorization': f'Bearer {response_data["access_token"]}'
            }
            return True

        except requests.exceptions.RequestException as e:
            print(f"ERROR: {e}")
            return False

    def search_bibs(self, title: str, author: str = "", limit: int = 50) -> Dict[str, Any]:
        """
        搜索书目记录

        参数:
            title: 书籍标题
            author: 作者名称（可选）
            limit: 最大返回结果数（默认 50）

        返回:
            搜索结果字典
        """
        # 确保已认证
        if not self.reauth():
            return {
                'successful': False,
                'error': 'Authentication failed',
                'bibRecords': []
            }

        # 构建查询字符串
        if author:
            q = f"au:{author} AND ti:{title}"
        else:
            q = f"ti:{title}"

        params = {
            'q': q,
            'limit': limit
        }

        try:
            response = requests.get(
                OCLC_SEARCH_URL,
                headers=self.headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            data['successful'] = True
            data['error'] = None

            if data.get('numberOfRecords', 0) == 0:
                data['bibRecords'] = []

            return data

        except requests.exceptions.RequestException as e:
            return {
                'successful': False,
                'error': str(e),
                'numberOfRecords': 0,
                'bibRecords': []
            }


def extract_bib_data(data: Dict) -> List[Dict[str, Any]]:
    """
    从 WorldCat 响应中提取简化书目数据

    参数:
        data: WorldCat API 响应数据

    返回:
        简化后的书目记录列表
    """
    if not isinstance(data, dict) or not isinstance(data.get('bibRecords'), list):
        return []

    simplified_records = []

    for record in data['bibRecords']:
        if not isinstance(record, dict):
            continue

        # 安全获取嵌套数据
        identifier = record.get('identifier') or {}
        title_info = record.get('title') or {}
        contributor_info = record.get('contributor') or {}
        date_info = record.get('date') or {}
        language_info = record.get('language') or {}
        format_info = record.get('format') or {}
        work_info = record.get('work') or {}

        # 提取主标题
        main_titles = title_info.get('mainTitles')
        main_title_text = None
        if isinstance(main_titles, list) and main_titles:
            first_title = main_titles[0]
            if isinstance(first_title, dict):
                main_title_text = first_title.get('text')

        # 提取作者
        creator = get_creator_name(contributor_info)

        # 提取主题词
        subjects_list = record.get('subjects')
        subjects_str_list = None
        if isinstance(subjects_list, list):
            subjects_str_list = []
            for s in subjects_list:
                subject_name = (s or {}).get('subjectName')
                if isinstance(subject_name, dict):
                    text = subject_name.get('text')
                    if text:
                        subjects_str_list.append(text)

        # 构建简化记录
        simplified_record = {
            'oclc_number': identifier.get('oclcNumber'),
            'isbns': identifier.get('isbns', []),
            'merged_oclc_numbers': identifier.get('mergedOclcNumbers', []),
            'lccn': identifier.get('lccn'),
            'creator': creator,
            'main_title': main_title_text,
            'statement_of_responsibility': (contributor_info.get('statementOfResponsibility') or {}).get('text'),
            'classifications': record.get('classification'),
            'subjects': subjects_str_list,
            'publication_date': date_info.get('publicationDate'),
            'item_language': language_info.get('itemLanguage'),
            'general_format': format_info.get('generalFormat'),
            'work_id': work_info.get('id')
        }

        simplified_records.append(simplified_record)

    return simplified_records


def get_creator_name(contributor_info: Dict) -> Optional[str]:
    """
    提取第一作者名称（格式为 "姓, 名"）

    参数:
        contributor_info: 贡献者信息字典

    返回:
        作者名称字符串或 None
    """
    if not isinstance(contributor_info, dict):
        return None

    creators = contributor_info.get('creators')
    if not isinstance(creators, list):
        return None

    # 排除非作者角色
    non_creator_roles = {
        'editor', 'compiler', 'voice actor', 'ed.lit', 'mitwirkender',
        'buchgestalter', 'herausgeber', 'drucker', 'buchbinder', 'issuing body',
        'hörfunkproduzent', 'verlag', 'regisseur', 'synchronsprecher', 'narrator'
    }

    for creator in creators:
        if not isinstance(creator, dict) or creator.get('type') != 'person':
            continue

        is_creator_only = True
        relators = creator.get('relators')
        if isinstance(relators, list):
            for relator in relators:
                term = (relator or {}).get('term', '').lower()
                if term in non_creator_roles:
                    is_creator_only = False
                    break

        if is_creator_only:
            first_name = creator.get('firstName')
            second_name = creator.get('secondName')

            # 处理字典格式的名称
            if isinstance(first_name, dict):
                first_name = first_name.get('text')
            if isinstance(second_name, dict):
                second_name = second_name.get('text')

            # 格式化名称
            if second_name and first_name:
                return f"{second_name}, {first_name}"
            elif second_name:
                return second_name
            elif first_name:
                return first_name

    return None


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
    title_scores = []
    if query_title and result_title:
        title_ratio = fuzz.token_sort_ratio(result_title, query_title)
        title_scores.append(title_ratio)

    best_title_score = max(title_scores) if title_scores else 0

    author_scores = []
    if query_author and result_author:
        author_ratio = fuzz.token_sort_ratio(result_author, query_author)
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


def search_with_scoring(client: WorldCatClient, title: str, author: str = "",
                        quality_threshold: str = None, book_only: bool = False) -> List[Dict[str, Any]]:
    """
    搜索 WorldCat 并评分

    参数:
        client: WorldCatClient 实例
        title: 书籍标题
        author: 作者名称（可选）
        quality_threshold: 质量阈值过滤
        book_only: 是否只返回图书格式

    返回:
        按分数排序的匹配结果列表
    """
    data = client.search_bibs(title, author)

    if not data.get('successful') or not data.get('bibRecords'):
        return []

    # 提取简化数据
    records = extract_bib_data(data)

    scored_records = []
    for record in records:
        # 计算分数
        scores = calculate_fuzzy_score(
            title, author,
            record.get('main_title', ''),
            record.get('creator', '')
        )

        # 过滤非图书格式
        if book_only and record.get('general_format') != 'Book':
            continue

        # 构建结果
        result = {
            'oclc_number': record.get('oclc_number'),
            'title': record.get('main_title'),
            'author': record.get('creator'),
            'isbns': record.get('isbns', []),
            'lccn': record.get('lccn'),
            'publication_date': record.get('publication_date'),
            'language': record.get('item_language'),
            'format': record.get('general_format'),
            'work_id': record.get('work_id'),
            'subjects': record.get('subjects', []),
            'classifications': record.get('classifications'),
            'score': scores['fuzzy_score'],
            'title_score': scores['title_score'],
            'author_score': scores['author_score']
        }

        scored_records.append(result)

    # 按分数排序
    scored_records.sort(key=lambda x: x['score'], reverse=True)

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
        scored_records = [r for r in scored_records if r['score'] >= min_score]

    return scored_records


# =============================================================================
# 使用示例
# =============================================================================
if __name__ == "__main__":
    # 从环境变量获取认证信息
    import os

    client_id = os.environ.get('OCLC_CLIENT_ID', 'your_client_id')
    secret = os.environ.get('OCLC_SECRET', 'your_secret')

    # 创建客户端
    client = WorldCatClient(client_id, secret)

    # 示例 1: 搜索
    print("=" * 60)
    print("示例 1: 搜索 'The Great Gatsby'")
    print("=" * 60)

    results = client.search_bibs("The Great Gatsby", "F. Scott Fitzgerald")
    print(f"找到 {results.get('numberOfRecords', 0)} 条记录")

    if results.get('bibRecords'):
        records = extract_bib_data(results)
        for record in records[:3]:
            print(f"  - {record['main_title']} / {record['creator']}")
            print(f"    OCLC: {record['oclc_number']}, ISBN: {record['isbns']}")

    # 示例 2: 搜索并评分
    print("\n" + "=" * 60)
    print("示例 2: 搜索并评分 '1984'")
    print("=" * 60)

    scored_results = search_with_scoring(client, "1984", "George Orwell",
                                         quality_threshold='medium', book_only=True)

    for result in scored_results[:5]:
        print(f"  分数: {result['score']:.2f} | {result['title']} / {result['author']}")
        print(f"    OCLC: {result['oclc_number']}, 格式: {result['format']}")

    # 示例 3: 获取工作 ID 聚类
    print("\n" + "=" * 60)
    print("示例 3: 获取 Work ID 聚类信息")
    print("=" * 60)

    if scored_results:
        work_id = scored_results[0].get('work_id')
        if work_id:
            print(f"  Work ID: {work_id}")
            print("  (相同的 Work ID 表示同一作品的不同版本/载体类型)")
