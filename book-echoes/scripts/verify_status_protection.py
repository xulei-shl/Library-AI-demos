#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""状态管理优化验证脚本.

用于验证数据库查重阶段的终态保护逻辑是否正常工作。
"""

import pandas as pd
from pathlib import Path


def create_test_excel():
    """创建测试用的 Excel 文件,包含各种状态的记录."""
    
    data = {
        "书目条码": [
            "1000001",  # 待处理 + 数据库有完整数据
            "1000002",  # 完成 + 数据库有完整数据
            "1000003",  # 未找到 + 数据库没有
            "1000004",  # ISBN无效 + 数据库没有
            "1000005",  # 待处理 + 数据库没有
            "1000006",  # 完成 + 数据库没有
            "1000007",  # 待处理 + 数据库有不完整数据
            "1000008",  # 未找到 + 数据库有不完整数据
        ],
        "ISBN": [
            "9787544270878",
            "9787544270878",
            "9787111111111",
            "invalid-isbn",
            "9787222222222",
            "9787333333333",
            "9787544270878",
            "9787544270878",
        ],
        "处理状态": [
            "待处理",
            "完成",
            "未找到",
            "ISBN无效",
            "待处理",
            "完成",
            "待处理",
            "未找到",
        ],
        "豆瓣书名": ["", "测试书名", "", "", "", "测试书名2", "", ""],
        "豆瓣评分": ["", "8.5", "", "", "", "9.0", "", ""],
    }
    
    df = pd.DataFrame(data)
    output_file = Path("runtime/test_status_protection.xlsx")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output_file, index=False)
    
    print(f"✅ 测试文件已创建: {output_file}")
    print("\n初始状态分布:")
    print(df["处理状态"].value_counts())
    print("\n预期结果:")
    print("- 1000001: 待处理 → 数据库已有 (数据库有完整数据)")
    print("- 1000002: 完成 → 完成 (终态保护)")
    print("- 1000003: 未找到 → 未找到 (终态保护)")
    print("- 1000004: ISBN无效 → ISBN无效 (终态保护)")
    print("- 1000005: 待处理 → 待处理 (数据库没有)")
    print("- 1000006: 完成 → 完成 (终态保护)")
    print("- 1000007: 待处理 → 待处理 (数据库有不完整数据)")
    print("- 1000008: 未找到 → 未找到 (终态保护)")
    print("\n终态保护数量应该为: 4 (1000002, 1000003, 1000004, 1000006, 1000008)")
    
    return output_file


def verify_results(excel_file: Path):
    """验证处理结果."""
    
    if not excel_file.exists():
        print(f"❌ 文件不存在: {excel_file}")
        return
    
    df = pd.read_excel(excel_file)
    
    print(f"\n处理后状态分布:")
    print(df["处理状态"].value_counts())
    
    # 检查终态是否被保护
    protected_records = []
    for idx, row in df.iterrows():
        barcode = row["书目条码"]
        status = row["处理状态"]
        
        # 这些记录应该保持原状态
        if barcode in ["1000002", "1000003", "1000004", "1000006", "1000008"]:
            expected_status = {
                "1000002": "完成",
                "1000003": "未找到",
                "1000004": "ISBN无效",
                "1000006": "完成",
                "1000008": "未找到",
            }[barcode]
            
            if status == expected_status:
                protected_records.append(barcode)
                print(f"✅ {barcode}: 终态保护成功 ({status})")
            else:
                print(f"❌ {barcode}: 终态保护失败 (期望: {expected_status}, 实际: {status})")
    
    print(f"\n终态保护成功数量: {len(protected_records)}/5")


if __name__ == "__main__":
    print("=" * 60)
    print("状态管理优化验证脚本")
    print("=" * 60)
    
    # 创建测试文件
    test_file = create_test_excel()
    
    print("\n" + "=" * 60)
    print("请按以下步骤验证:")
    print("=" * 60)
    print(f"1. 运行模块3,使用测试文件: {test_file}")
    print("2. 观察日志中是否有 '终态保护: X 条记录保持原状态不变'")
    print("3. 运行验证脚本检查结果:")
    print(f"   python {__file__} --verify")
    print("=" * 60)
