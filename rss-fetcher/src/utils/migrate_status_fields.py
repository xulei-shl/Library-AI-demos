#!/usr/bin/env python3
"""状态字段迁移脚本

将现有的llm_status值迁移到filter_status，实现状态字段优化。
"""

import os
import sys
import pandas as pd
from typing import List, Dict
from src.utils.logger import get_logger

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = get_logger(__name__)


def migrate_status_fields(filepath: str) -> bool:
    """
    迁移Excel文件中的状态字段
    
    Args:
        filepath: Excel文件路径
        
    Returns:
        是否成功迁移
    """
    try:
        # 读取Excel文件
        df = pd.read_excel(filepath)
        articles = df.to_dict("records")
        
        logger.info(f"开始迁移文件: {filepath} (共 {len(articles)} 条记录)")
        
        # 统计迁移情况
        migrated_count = 0
        already_migrated_count = 0
        
        for article in articles:
            llm_status = str(article.get("llm_status", "") or "").strip()
            filter_status = str(article.get("filter_status", "") or "").strip()
            
            # 如果filter_status已存在且有值，跳过
            if filter_status and filter_status.lower() not in ('nan', 'none', ''):
                already_migrated_count += 1
                continue
            
            # 如果llm_status有值，迁移到filter_status
            if llm_status and llm_status.lower() not in ('nan', 'none', ''):
                article["filter_status"] = llm_status
                migrated_count += 1
                logger.debug(f"迁移: llm_status='{llm_status}' -> filter_status='{llm_status}'")
        
        # 保存迁移后的数据
        if migrated_count > 0:
            df = pd.DataFrame(articles)
            df.to_excel(filepath, index=False)
            logger.info(f"迁移完成: {filepath} (迁移 {migrated_count} 条，已存在 {already_migrated_count} 条)")
            return True
        else:
            logger.info(f"无需迁移: {filepath} (已存在 {already_migrated_count} 条)")
            return True
            
    except Exception as e:
        logger.error(f"迁移失败: {filepath}, 错误: {e}")
        return False


def migrate_all_files(output_dir: str = "runtime/outputs") -> None:
    """
    迁移输出目录中所有Excel文件的状态字段
    
    Args:
        output_dir: 输出目录路径
    """
    if not os.path.exists(output_dir):
        logger.error(f"输出目录不存在: {output_dir}")
        return
    
    # 查找所有Excel文件
    excel_files = []
    for filename in os.listdir(output_dir):
        if filename.endswith(".xlsx"):
            filepath = os.path.join(output_dir, filename)
            excel_files.append(filepath)
    
    if not excel_files:
        logger.info(f"目录中没有Excel文件: {output_dir}")
        return
    
    logger.info(f"找到 {len(excel_files)} 个Excel文件")
    
    success_count = 0
    for filepath in excel_files:
        if migrate_status_fields(filepath):
            success_count += 1
    
    logger.info(f"迁移完成: 成功 {success_count}/{len(excel_files)} 个文件")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="迁移状态字段: llm_status -> filter_status")
    parser.add_argument(
        "--file",
        type=str,
        help="指定要迁移的Excel文件路径"
    )
    parser.add_argument(
        "--dir",
        type=str,
        default="runtime/outputs",
        help="指定要迁移的目录路径 (默认: runtime/outputs)"
    )
    
    args = parser.parse_args()
    
    if args.file:
        # 迁移单个文件
        if not os.path.exists(args.file):
            logger.error(f"文件不存在: {args.file}")
            return 1
        
        success = migrate_status_fields(args.file)
        return 0 if success else 1
    else:
        # 迁移整个目录
        migrate_all_files(args.dir)
        return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)