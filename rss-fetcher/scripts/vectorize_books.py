#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图书向量化命令行入口

用法示例:
    # 增量向量化（默认）
    python scripts/vectorize_books.py
    
    # 全量向量化
    python scripts/vectorize_books.py --mode full
    
    # 只重试失败的书籍
    python scripts/vectorize_books.py --mode retry
    
    # 重建向量库
    python scripts/vectorize_books.py --mode rebuild
    
    # 试运行（只统计，不实际执行）
    python scripts/vectorize_books.py --dry-run
"""

import argparse
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
try:
    from dotenv import load_dotenv
    from pathlib import Path
    
    env_file = Path(__file__).parent.parent / 'config' / '.env'
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass  # python-dotenv 未安装时忽略

from src.core.book_vectorization.vectorizer import BookVectorizer
from src.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='图书向量化预处理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  增量向量化（默认）:
    python scripts/vectorize_books.py
  
  全量向量化:
    python scripts/vectorize_books.py --mode full
  
  只重试失败的书籍:
    python scripts/vectorize_books.py --mode retry
  
  重建向量库:
    python scripts/vectorize_books.py --mode rebuild
  
  试运行（只统计）:
    python scripts/vectorize_books.py --dry-run
        """
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/book_vectorization.yaml',
        help='配置文件路径（默认: config/book_vectorization.yaml）'
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=['full', 'incremental', 'retry', 'rebuild'],
        default='incremental',
        help='运行模式（默认: incremental）'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='试运行模式（只统计，不实际执行）'
    )
    
    args = parser.parse_args()
    
    try:
        # 初始化向量化器
        logger.info("=" * 60)
        logger.info("图书向量化预处理工具")
        logger.info("=" * 60)
        
        vectorizer = BookVectorizer(config_path=args.config)
        
        if args.dry_run:
            # 试运行：只统计符合条件的书籍数量
            logger.info("试运行模式：只统计，不实际执行")
            stats = vectorizer.dry_run(mode=args.mode)
            
            logger.info("=" * 60)
            logger.info("试运行结果:")
            logger.info(f"  运行模式: {stats['mode']}")
            logger.info(f"  待处理书籍数: {stats['total_to_process']}")
            logger.info("  当前数据库统计:")
            for status, count in stats['current_stats'].items():
                logger.info(f"    {status}: {count}")
            logger.info("=" * 60)
        else:
            # 正式运行
            logger.info(f"开始向量化，模式: {args.mode}")
            logger.info("=" * 60)
            
            report = vectorizer.run(mode=args.mode)
            
            logger.info("=" * 60)
            logger.info("向量化完成！")
            logger.info(f"  总处理数: {report['total']}")
            logger.info(f"  成功: {report['completed']}")
            logger.info(f"  失败: {report['failed']}")
            logger.info(f"  最终失败: {report['failed_final']}")
            logger.info(f"  成功率: {report['success_rate']}")
            logger.info("=" * 60)
    
    except Exception as e:
        logger.error(f"执行失败: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
