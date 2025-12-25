#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HathiTrust API 示例代码

参考来源: lib/strategies_hathitrust.py

功能描述:
    - HathiTrust 没有公共 API，需要使用本地数据库转储
    - 使用 SQLite FTS5 (Full-Text Search) 进行搜索
    - 返回书目记录和访问链接

注意:
    - 无公共 API，需要预先下载数据库转储文件
    - 使用 SQLite FTS5 进行全文搜索
    - 数据库包含 author_title 表（用于搜索）和 records 表（用于获取完整记录）

前提准备:
    1. 从 HathiTrust 下载数据库转储文件
    2. 放入指定目录（默认为 ./hathitrust_data）
    3. 数据库文件名为 hathitrust.db
"""

import sqlite3
import json
import os
import string
import re
from thefuzz import fuzz
from typing import Dict, List, Any, Optional


# =============================================================================
# 配置信息
# =============================================================================

# HathiTrust 数据库目录
HATHI_DATA_DIR = "./hathitrust_data"
DEFAULT_DB_PATH = os.path.join(HATHI_DATA_DIR, "hathitrust.db")

# HathiTrust 目录 URL
HATHI_COVER_BASE = "https://babel.hathitrust.org/cgi/imgsrv/cover"
HATHI_RECORD_BASE = "https://catalog.hathitrust.org/Record"


def escape_fts5_string(query: str) -> str:
    """
    转义 FTS5 查询字符串

    参数:
        query: 原始查询字符串

    返回:
        转义后的查询字符串
    """
    escaped_query = query.replace('"', '""')
    return f'"{escaped_query}"'


def remove_punctuation(text: str) -> str:
    """
    移除标点符号

    参数:
        text: 原始文本

    返回:
        移除标点后的文本
    """
    translator = str.maketrans(string.punctuation, ' ' * len(string.punctuation))
    text = text.translate(translator)
    # 移除多余的空格
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def remove_subtitle(title: str) -> str:
    """
    移除副标题

    参数:
        title: 原始标题

    返回:
        移除副标题后的标题
    """
    # 按常见分隔符分割
    for sep in [':', ';', '/', '-']:
        if sep in title:
            title = title.split(sep)[0].strip()
            break
    return title


def search_local_hathi_db(title: str, author: str = "",
                          db_path: str = None) -> List[Dict[str, Any]]:
    """
    在本地 HathiTrust 数据库中搜索

    参数:
        title: 作品标题
        author: 作者名称（可选）
        db_path: 数据库路径（默认使用 HATHI_DATA_DIR 中的 hathitrust.db）

    返回:
        匹配的记录列表
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    if not os.path.exists(db_path):
        print(f"警告: 数据库文件不存在: {db_path}")
        print("请先下载 HathiTrust 数据库转储文件")
        return []

    conn = None
    results = []

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # FTS5 搜索
        fts_query = """
        SELECT rowid
        FROM author_title
        WHERE title MATCH ? AND author MATCH ?
        ORDER BY rank;
        """

        cursor.execute(fts_query, (remove_punctuation(title), remove_punctuation(author)))
        rowids = [row[0] for row in cursor.fetchall()]

        if not rowids:
            print("未找到匹配记录")
            return []

        # 获取完整记录
        placeholders = ','.join('?' for _ in rowids)
        records_query = f"SELECT * FROM records WHERE ht_bib_key IN ({placeholders});"

        cursor.execute(records_query, rowids)
        column_names = [description[0] for description in cursor.description]

        for row in cursor.fetchall():
            results.append(dict(zip(column_names, row)))

    except sqlite3.Error as e:
        print(f"数据库错误: {e}")
    finally:
        if conn:
            conn.close()

    return results


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
    # 提取主标题（移除作者和责任说明）
    hathi_main_title = result_title.split("/")[0]
    hathi_main_title = remove_subtitle(hathi_main_title)

    # 标题评分
    title_scores = []
    if query_title and hathi_main_title:
        ratio = fuzz.token_sort_ratio(hathi_main_title, query_title)
        title_scores.append(ratio)

    best_title_score = max(title_scores) if title_scores else 0

    # 作者评分
    author_scores = []
    if query_author and result_author:
        ratio = fuzz.token_sort_ratio(result_author, query_author)
        author_scores.append(ratio)

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


def search_and_score(title: str, author: str = "",
                     db_path: str = None,
                     quality_threshold: str = None) -> List[Dict[str, Any]]:
    """
    搜索 HathiTrust 数据库并评分

    参数:
        title: 作品标题
        author: 作者名称（可选）
        db_path: 数据库路径
        quality_threshold: 质量阈值过滤

    返回:
        按分数排序的匹配结果列表
    """
    # 执行搜索
    records = search_local_hathi_db(title, author, db_path)

    if not records:
        return []

    scored_records = []

    for record in records:
        # 计算分数
        scores = calculate_fuzzy_score(
            title, author,
            record.get('title', ''),
            record.get('author', '')
        )

        # 提取标识符
        identifiers = extract_identifiers(record)

        # 构建结果
        result = {
            'ht_bib_key': record.get('ht_bib_key'),
            'title': record.get('title'),
            'author': record.get('author'),
            'identifiers': identifiers,
            'pub_date': record.get('pub_date'),
            'rights_date_used': record.get('rights_date_used'),
            'score': scores['fuzzy_score'],
            'title_score': scores['title_score'],
            'author_score': scores['author_score'],
            'record_url': f"{HATHI_RECORD_BASE}/{record.get('ht_bib_key')}"
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


def extract_identifiers(record: Dict) -> Dict[str, List[str]]:
    """
    从记录中提取标识符

    参数:
        record: HathiTrust 记录

    返回:
        标识符字典
    """
    identifiers = {}

    # HDL (HathiTrust 标识符)
    if record.get('htid'):
        identifiers['hdl'] = record['htid'].split("|")

    # LCCN
    if record.get('lccn'):
        identifiers['LCCN'] = record['lccn'].split(",")

    # ISBN
    if record.get('isbn'):
        identifiers['ISBN'] = record['isbn'].split(",")

    # OCLC
    if record.get('oclc_num'):
        identifiers['OCLC'] = record['oclc_num'].split(",")

    # 出版日期
    if record.get('rights_date_used'):
        dates = [int(s) for s in record['rights_date_used'].split(",") if s.isdigit()]
        if dates:
            identifiers['rights_dates'] = dates

    return identifiers


def get_thumbnail_url(htid: str, width: int = 250) -> str:
    """
    获取封面缩略图 URL

    参数:
        htid: HathiTrust 标识符
        width: 缩略图宽度

    返回:
        缩略图 URL
    """
    return f"{HATHI_COVER_BASE}?id={htid};width={width}"


def cluster_records(records: List[Dict], query_title: str,
                    query_author: str) -> Dict[str, List[Dict]]:
    """
    将记录聚类为匹配和非匹配两组

    参数:
        records: 记录列表
        query_title: 查询标题
        query_author: 查询作者

    返回:
        包含 cluster 和 cluster_excluded 的字典
    """
    all_clusters = {
        'cluster': [],
        'cluster_excluded': []
    }

    for record in records:
        scores = calculate_fuzzy_score(
            query_title, query_author,
            record.get('title', ''),
            record.get('author', '')
        )

        if query_author:
            if scores['title_score'] > 80 and scores['author_score'] > 80:
                all_clusters['cluster'].append(record)
            elif scores['title_score'] > 70 and scores['author_score'] > 95:
                all_clusters['cluster'].append(record)
            elif scores['title_score'] > 50 and scores['author_score'] >= 100:
                all_clusters['cluster'].append(record)
            else:
                all_clusters['cluster_excluded'].append(record)
        else:
            if scores['title_score'] > 80:
                all_clusters['cluster'].append(record)
            else:
                all_clusters['cluster_excluded'].append(record)

    return all_clusters


def build_db_from_files(data_dir: str = None, db_path: str = None) -> bool:
    """
    从 HathiTrust 数据文件构建 SQLite 数据库

    参数:
        data_dir: 数据文件目录
        db_path: 输出数据库路径

    返回:
        是否构建成功
    """
    import glob

    if data_dir is None:
        data_dir = HATHI_DATA_DIR
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    # 检查数据文件
    data_files = glob.glob(os.path.join(data_dir, "*.dat"))
    if not data_files:
        print(f"警告: 在 {data_dir} 中未找到数据文件")
        return False

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 创建 author_title FTS5 虚拟表
        cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS author_title USING fts5(
            title,
            author,
            tokenize='porter'
        )
        """)

        # 创建 records 表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS records (
            ht_bib_key TEXT PRIMARY KEY,
            title TEXT,
            author TEXT,
            isbn TEXT,
            lccn TEXT,
            oclc_num TEXT,
            pub_date TEXT,
            rights_date_used TEXT,
            htid TEXT
        )
        """)

        # 解析数据文件并插入
        for data_file in data_files:
            print(f"处理文件: {data_file}")
            with open(data_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    # 解析 TSV 格式
                    parts = line.split('\t')
                    if len(parts) < 9:
                        continue

                    record = {
                        'ht_bib_key': parts[0],
                        'title': parts[1],
                        'author': parts[2],
                        'isbn': parts[3],
                        'lccn': parts[4],
                        'oclc_num': parts[5],
                        'pub_date': parts[6],
                        'rights_date_used': parts[7],
                        'htid': parts[8]
                    }

                    # 插入 records 表
                    cursor.execute("""
                    INSERT OR REPLACE INTO records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record['ht_bib_key'], record['title'], record['author'],
                        record['isbn'], record['lccn'], record['oclc_num'],
                        record['pub_date'], record['rights_date_used'], record['htid']
                    ))

                    # 插入 FTS 表
                    cursor.execute("""
                    INSERT INTO author_title VALUES (?, ?)
                    """, (record['title'], record['author']))

        conn.commit()
        print(f"数据库构建完成: {db_path}")
        return True

    except sqlite3.Error as e:
        print(f"数据库错误: {e}")
        return False
    finally:
        if conn:
            conn.close()


# =============================================================================
# 使用示例
# =============================================================================
if __name__ == "__main__":
    # 示例 1: 搜索
    print("=" * 60)
    print("示例 1: 搜索 'Moby Dick'")
    print("=" * 60)

    results = search_local_hathi_db("Moby Dick", "Herman Melville")
    print(f"找到 {len(results)} 条记录")

    for record in results[:3]:
        print(f"  - {record.get('title', 'N/A')}")
        print(f"    作者: {record.get('author', 'N/A')}")
        print(f"    HathiTrust ID: {record.get('ht_bib_key', 'N/A')}")

    # 示例 2: 搜索并评分
    print("\n" + "=" * 60)
    print("示例 2: 搜索并评分 'Pride and Prejudice'")
    print("=" * 60)

    scored = search_and_score("Pride and Prejudice", "Jane Austen",
                              quality_threshold='medium')

    for r in scored[:5]:
        print(f"  分数: {r['score']:.2f} | {r['title']}")
        print(f"    标题分数: {r['title_score']}, 作者分数: {r['author_score']}")
        print(f"    封面: {get_thumbnail_url(r.get('ht_bib_key', ''))}")

    # 示例 3: 提取标识符
    print("\n" + "=" * 60)
    print("示例 3: 提取标识符")
    print("=" * 60)

    if results:
        identifiers = extract_identifiers(results[0])
        print(f"  HDL: {identifiers.get('hdl', [])}")
        print(f"  LCCN: {identifiers.get('LCCN', [])}")
        print(f"  ISBN: {identifiers.get('ISBN', [])}")
        print(f"  OCLC: {identifiers.get('OCLC', [])}")

    # 示例 4: 构建数据库
    print("\n" + "=" * 60)
    print("示例 4: 构建本地数据库")
    print("=" * 60)
    print("  使用 build_db_from_files() 从数据文件构建 SQLite 数据库")
    print("  数据文件格式: TSV，包含以下字段:")
    print("    ht_bib_key, title, author, isbn, lccn, oclc_num, pub_date, rights_date_used, htid")
