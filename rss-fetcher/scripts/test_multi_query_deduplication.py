#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试多子查询检索双重去重功能的简单脚本 - 基于 book_id 和 call_no，保留最新记录
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.book_vectorization.fusion import fuse_query_results, merge_exact_matches, FusionConfig, _prefer_higher_similarity, _is_record_newer

def test_fuse_query_results():
    """测试 fuse_query_results 的去重逻辑"""
    print("测试 fuse_query_results 的去重逻辑...")
    
    # 创建模拟的多子查询结果，包含重复的 book_id
    query_results = [
        ("primary", [
            {
                'book_id': 1,
                'id': 1,
                'title': '人工智能基础',
                'author': '张三',
                'rating': 8.5,
                'summary': '人工智能入门书籍',
                'call_no': 'TP18',
                'similarity_score': 0.95,
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
                'embedding_date': '2025-12-10T15:30:00',  # 中间时间
            },
        ]),
        ("tags", [
            {
                'book_id': 1,  # 重复的 book_id，但时间更新
                'id': 1,
                'title': '人工智能基础（第二版）',
                'author': '张三',
                'rating': 8.6,
                'summary': '人工智能入门书籍（更新版）',
                'call_no': 'TP18',
                'similarity_score': 0.85,  # 相似度更低，但时间更新
                'embedding_date': '2025-12-15T09:20:00',  # 更新的时间
            },
            {
                'book_id': 3,
                'id': 3,
                'title': '深度学习',
                'author': '王五',
                'rating': 8.8,
                'summary': '深度学习理论与实践',
                'call_no': 'TP181',  # 与 book_id=2 的 call_no 相同
                'similarity_score': 0.92,
                'embedding_date': '2025-12-12T11:45:00',  # 比 book_id=2 的时间更新
            },
        ]),
    ]
    
    print(f"原始查询结果数量: {sum(len(results) for _, results in query_results)}")
    for group_name, results in query_results:
        print(f"  {group_name}: {len(results)} 条结果")
        for result in results:
            print(f"    book_id={result['book_id']}, call_no={result['call_no']}, time={result.get('embedding_date', 'None')}")
    
    # 测试融合函数
    fusion_config = FusionConfig()
    fused_results = fuse_query_results(query_results, fusion_config)
    
    print(f"\n融合后结果数量: {len(fused_results)}")
    for result in fused_results:
        print(f"  book_id={result['book_id']}, call_no={result['call_no']}, time={result.get('embedding_date', 'None')}, fused_score={result.get('fused_score', 0):.3f}")
    
    # 验证去重是否正确
    book_ids = [r['book_id'] for r in fused_results]
    unique_book_ids = set(book_ids)
    
    if len(book_ids) == len(unique_book_ids):
        print("\n✅ fuse_query_results 的 book_id 去重功能正常工作")
    else:
        print("\n❌ fuse_query_results 的 book_id 去重功能存在问题")
        return False
    
    # 验证是否保留了最新的记录
    # 对于 book_id=1，应该保留时间 '2025-12-15T09:20:00' 的记录
    expected_book_1_time = '2025-12-15T09:20:00'
    actual_book_1 = next((r for r in fused_results if r['book_id'] == 1), None)
    
    if actual_book_1 and actual_book_1.get('embedding_date') == expected_book_1_time:
        print("✅ fuse_query_results 正确保留了 book_id=1 的最新记录")
    else:
        print(f"❌ fuse_query_results 未正确保留 book_id=1 的最新记录，期望时间: {expected_book_1_time}")
        return False
    
    return True

def test_merge_exact_matches():
    """测试 merge_exact_matches 的去重逻辑"""
    print("\n测试 merge_exact_matches 的去重逻辑...")
    
    # 创建模拟的向量检索结果和精确匹配结果
    vector_results = [
        {
            'book_id': 1,
            'id': 1,
            'title': '人工智能基础',
            'author': '张三',
            'rating': 8.5,
            'summary': '人工智能入门书籍',
            'call_no': 'TP18',
            'similarity_score': 0.95,
            'fused_score': 0.9,
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
            'fused_score': 0.85,
            'embedding_date': '2025-12-10T15:30:00',  # 中间时间
        },
    ]
    
    exact_matches = [
        {
            'book_id': 3,  # 添加 book_id 字段
            'douban_title': '深度学习',
            'douban_author': '王五',
            'douban_rating': 8.8,
            'douban_summary': '深度学习理论与实践',
            'call_no': 'TP181',  # 与 book_id=2 的 call_no 相同
            'exact_match_score': 1.0,
            'embedding_date': '2025-12-12T11:45:00',  # 比 book_id=2 的时间更新
        },
        {
            'book_id': 4,  # 添加 book_id 字段
            'douban_title': '神经网络',
            'douban_author': '赵六',
            'douban_rating': 8.7,
            'douban_summary': '神经网络原理与应用',
            'call_no': '',  # 空的索书号
            'exact_match_score': 0.9,
            'embedding_date': '',  # 没有时间字段
        },
    ]
    
    print(f"向量检索结果数量: {len(vector_results)}")
    print(f"精确匹配结果数量: {len(exact_matches)}")
    
    # 测试合并函数
    merged_results = merge_exact_matches(vector_results, exact_matches)
    
    print(f"\n合并后结果数量: {len(merged_results)}")
    for result in merged_results:
        print(f"  book_id={result['book_id']}, call_no={result['call_no']}, time={result.get('embedding_date', 'None')}, final_score={result.get('final_score', 0):.3f}")
    
    # 验证去重是否正确
    book_ids = [r['book_id'] for r in merged_results]
    unique_book_ids = set(book_ids)
    
    if len(book_ids) == len(unique_book_ids):
        print("\n✅ merge_exact_matches 的 book_id 去重功能正常工作")
    else:
        print("\n❌ merge_exact_matches 的 book_id 去重功能存在问题")
        return False
    
    # 验证 call_no 去重是否正确
    call_nos = [str(r['call_no']).strip() for r in merged_results]
    non_empty_call_nos = [call_no for call_no in call_nos if call_no]
    unique_call_nos = set(non_empty_call_nos)
    
    if len(non_empty_call_nos) == len(unique_call_nos):
        print("✅ merge_exact_matches 的 call_no 去重功能正常工作")
    else:
        print("❌ merge_exact_matches 的 call_no 去重功能存在问题")
        return False
    
    # 验证是否保留了最新的记录
    # 对于 call_no='TP181'，应该在 book_id=2 和 book_id=3 中保留时间更新的 book_id=3
    expected_tp181_book_id = 3
    actual_tp181 = next((r for r in merged_results if r.get('call_no') == 'TP181'), None)
    
    if actual_tp181 and actual_tp181['book_id'] == expected_tp181_book_id:
        print("✅ merge_exact_matches 正确保留了 call_no='TP181' 的最新记录")
    else:
        print(f"❌ merge_exact_matches 未正确保留 call_no='TP181' 的最新记录，期望 book_id: {expected_tp181_book_id}")
        return False
    
    return True

def test_prefer_higher_similarity():
    """测试 _prefer_higher_similarity 函数的时间优先级逻辑"""
    print("\n测试 _prefer_higher_similarity 函数...")
    
    current = {
        'book_id': 1,
        'id': 1,
        'title': '人工智能基础',
        'similarity_score': 0.95,
        'embedding_date': '2025-12-01T10:00:00',  # 较早的时间
    }
    
    candidate = {
        'book_id': 1,
        'id': 1,
        'title': '人工智能基础（第二版）',
        'similarity_score': 0.85,  # 相似度更低，但时间更新
        'embedding_date': '2025-12-15T09:20:00',  # 更新的时间
    }
    
    # 测试基于时间的优先级
    result = _prefer_higher_similarity(current, candidate)
    
    if result.get('embedding_date') == candidate.get('embedding_date'):
        print("✅ _prefer_higher_similarity 正确保留了时间更新的记录")
        return True
    else:
        print("❌ _prefer_higher_similarity 未正确保留时间更新的记录")
        return False

def test_is_record_newer():
    """测试 _is_record_newer 函数"""
    print("\n测试 _is_record_newer 函数...")
    
    # 测试基于时间的比较
    current_with_date = {
        'id': 1,
        'embedding_date': '2025-12-15T09:20:00',
    }
    
    existing_with_date = {
        'id': 1,
        'embedding_date': '2025-12-01T10:00:00',
    }
    
    if not _is_record_newer(current_with_date, existing_with_date):
        print("❌ _is_record_newer 时间比较失败")
        return False
    
    # 测试基于ID的比较（无时间字段）
    current_no_date = {
        'id': 5,
    }
    
    existing_no_date = {
        'id': 3,
    }
    
    if not _is_record_newer(current_no_date, existing_no_date):
        print("❌ _is_record_newer ID比较失败")
        return False
    
    print("✅ _is_record_newer 函数正常工作")
    return True

def main():
    """运行所有测试"""
    print("开始测试多子查询检索的双重去重逻辑...\n")
    
    tests = [
        test_fuse_query_results,
        test_merge_exact_matches,
        test_prefer_higher_similarity,
        test_is_record_newer,
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"❌ {test.__name__} 失败")
        except Exception as e:
            print(f"❌ {test.__name__} 异常: {e}")
    
    print(f"\n测试结果: {passed}/{len(tests)} 通过")
    
    if passed == len(tests):
        print("🎉 所有测试通过！多子查询检索的双重去重功能正常工作。")
        return True
    else:
        print("❌ 部分测试失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)