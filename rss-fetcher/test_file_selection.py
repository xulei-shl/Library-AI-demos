#!/usr/bin/env python3
"""测试文件选择功能的脚本"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import run_interactive_stage

def test_file_selection():
    """测试文件选择功能"""
    print("测试文件选择功能")
    print("="*60)

    # 测试用例1: summary阶段
    print("\n测试1: 执行summary阶段，选择MD处理后的文件")
    run_interactive_stage('summary')

    # 测试用例2: analysis阶段
    print("\n测试2: 执行analysis阶段，选择MD处理后的文件")
    run_interactive_stage('analysis')

    # 测试用例3: cross阶段
    print("\n测试3: 执行cross阶段，选择MD处理后的文件")
    run_interactive_stage('cross')

if __name__ == "__main__":
    test_file_selection()