#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试双重去重功能的简单脚本 - 基于 book_id 和 call_no
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.book_vectorization.retriever import BookRetriever

def test_deduplication_logic():
    """测试双重去重逻辑（基于 book_id 和 call_no，保留最新记录）"""
    print("测试双重去重逻辑（保留最新记录）...")
    
    # 创建模拟的检索结果，包含重复的 book_id 和 call_no
    mock_results = [
        {
            'book_id': 1,
            'id': 1,
            'title': '人工智能基础',
            'author': '张三',
            'rating': 8.5,
            'summary': '人工智能入门书籍',
            'call_no': 'TP18',
            'similarity_score': 0.95,
            'embedding_id': 'emb_1',
            'source_query_text': '人工智能',
            'embedding_date': '2025-12-01T10:00:00',  # 较早的时间
        },
        {
            'book_id': 2,
            'id': 2,
            'title': '机器学习实战',
            'author': '李四',
            'rating': 9.0,
            'summary': '机器学习实践指南',
            'call_no': 'TP181',
            'similarity_score': 0.88,
            'embedding_id': 'emb_2',
            'source_query_text': '人工智能',
            'embedding_date': '2025-12-10T15:30:00',  # 中间时间
        },
        {
            'book_id': 1,  # 重复的 book_id，但时间更新
            'id': 1,
            'title': '人工智能基础（第二版）',
            'author': '张三',
            'rating': 8.6,
            'summary': '人工智能入门书籍（更新版）',
            'call_no': 'TP18',
            'similarity_score': 0.85,  # 相似度更低，但时间更新
            'embedding_id': 'emb_1_alt',
            'source_query_text': '人工智能',
            'embedding_date': '2025-12-15T09:20:00',  # 更新的时间
        },
        {
            'book_id': 3,
            'id': 3,
            'title': '深度学习',
            'author': '王五',
            'rating': 8.8,
            'summary': '深度学习理论与实践',
            'call_no': 'TP181',  # 与 book_id=2 的 call_no 相同，模拟数据库脏数据
            'similarity_score': 0.92,
            'embedding_id': 'emb_3',
            'source_query_text': '人工智能',
            'embedding_date': '2025-12-12T11:45:00',  # 比 book_id=2 的时间更新
        },
        {
            'book_id': 4,
            'id': 4,
            'title': '神经网络',
            'author': '赵六',
            'rating': 8.7,
            'summary': '神经网络原理与应用',
            'call_no': '',  # 空的索书号
            'similarity_score': 0.87,
            'embedding_id': 'emb_4',
            'source_query_text': '人工智能',
            'embedding_date': '',  # 没有时间字段
        },
        {
            'book_id': 5,
            'id': 5,
            'title': '数据挖掘',
            'author': '钱七',
            'rating': 8.9,
            'summary': '数据挖掘技术与实践',
            'call_no': 'TP311',  # 唯一的索书号
            'similarity_score': 0.90,
            'embedding_id': 'emb_5',
            'source_query_text': '人工智能',
            'embedding_date': '',  # 没有时间字段
        },
        {
            'book_id': 6,
            'id': 6,
            'title': 'Python编程',
            'author': '孙八',
            'rating': 8.4,
            'summary': 'Python编程从入门到精通',
            'call_no': 'TP312',  # 唯一的索书号
            'similarity_score': 0.82,
            'embedding_id': 'emb_6',
            'source_query_text': '人工智能',
            'embedding_date': '',  # 没有时间字段，但ID更大
        },
    ]
    
    print(f"原始结果数量: {len(mock_results)}")
    print("原始结果中的 book_id:", [r['book_id'] for r in mock_results])
    print("原始结果中的 call_no:", [r['call_no'] for r in mock_results])
    print("原始结果中的 embedding_date:", [r.get('embedding_date', 'None') for r in mock_results])
    
    # 创建检索器实例（仅用于测试去重方法）
    retriever = object.__new__(BookRetriever)
    
    # 测试去重函数
    deduplicated_results = retriever._deduplicate_by_book_id(mock_results)
    
    print(f"\n去重后结果数量: {len(deduplicated_results)}")
    print("去重后结果中的 book_id:", [r['book_id'] for r in deduplicated_results])
    print("去重后结果中的 call_no:", [r['call_no'] for r in deduplicated_results])
    print("去重后结果中的 embedding_date:", [r.get('embedding_date', 'None') for r in deduplicated_results])
    
    # 验证去重是否正确
    book_ids = [r['book_id'] for r in deduplicated_results]
    unique_book_ids = set(book_ids)
    
    if len(book_ids) == len(unique_book_ids):
        print("\n✅ book_id 去重功能正常工作 - 没有重复的 book_id")
    else:
        print("\n❌ book_id 去重功能存在问题 - 发现重复的 book_id")
        return False
    
    # 验证 call_no 去重是否正确
    call_nos = [str(r['call_no']).strip() for r in deduplicated_results]
    # 过滤掉空的 call_no，因为它们会被特殊处理
    non_empty_call_nos = [call_no for call_no in call_nos if call_no]
    unique_call_nos = set(non_empty_call_nos)
    
    if len(non_empty_call_nos) == len(unique_call_nos):
        print("✅ call_no 去重功能正常工作 - 没有重复的非空 call_no")
    else:
        print("❌ call_no 去重功能存在问题 - 发现重复的非空 call_no")
        from collections import Counter
        duplicates = [call_no for call_no, count in Counter(non_empty_call_nos).items() if count > 1]
        print(f"重复的 call_no: {duplicates}")
        return False
    
    # 验证是否保留了最新的记录
    # 对于 book_id=1，应该保留时间 '2025-12-15T09:20:00' 的记录（虽然相似度更低）
    # 对于 call_no='TP181'，应该在 book_id=2 和 book_id=3 中保留时间更新的 book_id=3
    expected_results = {
        1: '2025-12-15T09:20:00',  # book_id=1 的最新时间
        3: '2025-12-12T11:45:00',  # call_no='TP181' 的最新时间（book_id=3）
        4: '',  # 空 call_no，无时间
        5: '',  # call_no='TP311'，无时间
        6: '',  # call_no='TP312'，无时间但ID更大
    }
    
    print("\n验证保留的记录是否为最新的:")
    for result in deduplicated_results:
        book_id = result['book_id']
        actual_date = result.get('embedding_date', '')
        expected_date = expected_results.get(book_id)
        
        if expected_date is not None and actual_date == expected_date:
            print(f"  ✅ book_id={book_id}, call_no='{result['call_no']}': 时间 {actual_date or 'None'} (最新)")
        else:
            print(f"  ❌ book_id={book_id}, call_no='{result['call_no']}': 时间 {actual_date or 'None'} (期望 {expected_date or 'None'})")
            return False
    
    print("\n🎉 所有测试通过！基于时间的双重去重功能正常工作。")
    return True

if __name__ == "__main__":
    success = test_deduplication_logic()
    sys.exit(0 if success else 1)