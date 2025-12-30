"""
数据库向量化脚本
将 literary_tags 表中的已打标书籍向量化并存入 ChromaDB
"""

import sys
from pathlib import Path

# 添加项目根目录
root_dir = Path(__file__).absolute().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(root_dir / "config" / ".env")

import sqlite3
import time
from typing import List, Dict

from src.utils.logger import get_logger
from .vector_searcher import VectorSearcher
from .tag_manager import TagManager
from .db_init import init_literary_tags_table

logger = get_logger(__name__)


def get_books_to_vectorize(
    db_path: str = "runtime/database/books_history.db",
    batch_size: int = 100
) -> List[Dict]:
    """
    获取待向量化的书籍列表

    Args:
        db_path: 数据库路径
        batch_size: 每批数量

    Returns:
        书籍列表
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    cursor = conn.execute("""
        SELECT
            lt.id as id,
            lt.book_id,
            lt.call_no,
            lt.title,
            lt.tags_json,
            b.douban_title,
            b.douban_summary,
            b.douban_catalog,
            lt.embedding_status
        FROM literary_tags lt
        LEFT JOIN books b ON lt.book_id = b.id
        WHERE lt.llm_status = 'success'
          AND (lt.embedding_status IS NULL OR lt.embedding_status != 'completed')
        ORDER BY lt.id ASC
        LIMIT ?
    """, (batch_size,))

    books = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return books


def update_embedding_status(
    db_path: str,
    book_id: int,
    embedding_id: str,
    status: str = 'completed'
) -> bool:
    """更新向量化状态"""
    try:
        from datetime import datetime
        conn = sqlite3.connect(db_path)
        conn.execute("""
            UPDATE literary_tags
            SET embedding_status = ?, embedding_id = ?, embedding_date = ?
            WHERE book_id = ?
        """, (status, embedding_id, datetime.now().isoformat(), book_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"更新向量化状态失败: {e}")
        return False


def vectorize_database(
    db_path: str = "runtime/database/books_history.db",
    config_path: str = "config/literature_fm_vector.yaml",
    batch_size: int = 50,
    max_books: int = 0
) -> Dict:
    """
    将数据库中的书籍向量化

    Args:
        db_path: 数据库路径
        config_path: 配置文件路径
        batch_size: 每批处理数量
        max_books: 最大处理数量（0表示全部）

    Returns:
        统计信息
    """
    logger.info("\n" + "="*80)
    logger.info("数据库向量化")
    logger.info("="*80 + "\n")

    # 初始化
    init_literary_tags_table(db_path)
    vector_searcher = VectorSearcher(config_path)

    stats = {
        'total': 0,
        'success': 0,
        'failed': 0,
        'skipped': 0
    }

    offset = 0
    while True:
        # 获取一批待向量化的书籍
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        if max_books > 0:
            limit_clause = f"LIMIT {batch_size} OFFSET {offset}"
        else:
            limit_clause = f"LIMIT {batch_size}"

        cursor = conn.execute(f"""
            SELECT
                lt.id as id,
                lt.book_id,
                lt.call_no,
                lt.title,
                lt.tags_json,
                b.douban_title,
                b.douban_subtitle,
                b.douban_author,
                b.douban_summary,
                b.douban_author_intro,
                b.douban_catalog,
                lt.embedding_status
            FROM literary_tags lt
            LEFT JOIN books b ON lt.book_id = b.id
            WHERE lt.llm_status = 'success'
              AND (lt.embedding_status IS NULL OR lt.embedding_status != 'completed')
            ORDER BY lt.id ASC
            {limit_clause}
        """, () if max_books > 0 else ())

        books = [dict(row) for row in cursor.fetchall()]
        conn.close()

        if not books:
            break

        if max_books > 0 and offset >= max_books:
            break

        logger.info(f"处理批次: {len(books)} 本 (累计处理 {offset + len(books)} 本)")

        # 批量向量化
        for book in books:
            try:
                if not book.get('tags_json'):
                    stats['skipped'] += 1
                    continue

                # 生成向量并添加到 ChromaDB
                doc, metadata = vector_searcher._build_context_text(
                    book_id=book['book_id'],
                    call_no=book.get('call_no', ''),
                    tags_json=book.get('tags_json', ''),
                    douban_title=book.get('douban_title', ''),
                    douban_subtitle=book.get('douban_subtitle', ''),
                    douban_author=book.get('douban_author', ''),
                    douban_summary=book.get('douban_summary', ''),
                    douban_author_intro=book.get('douban_author_intro', ''),
                    douban_catalog=book.get('douban_catalog', '')
                )
                embedding = vector_searcher.embedding_client.get_embedding(doc)

                embedding_id = vector_searcher.vector_store.add(
                    embedding=embedding,
                    metadata=metadata,
                    document=doc
                )

                # 更新状态
                update_embedding_status(db_path, book['book_id'], embedding_id, 'completed')
                stats['success'] += 1

            except Exception as e:
                logger.error(f"向量化失败 (book_id={book['book_id']}): {e}")
                update_embedding_status(db_path, book['book_id'], '', 'failed')
                stats['failed'] += 1

        offset += len(books)
        stats['total'] = offset

        # 批次间延迟
        time.sleep(1)

    # 统计完成
    logger.info("\n" + "="*80)
    logger.info("向量化完成！")
    logger.info(f"  - 总处理: {stats['total']} 本")
    logger.info(f"  - 成功: {stats['success']} 本")
    logger.info(f"  - 失败: {stats['failed']} 本")
    logger.info(f"  - 跳过: {stats['skipped']} 本")
    logger.info("="*80 + "\n")

    return stats


def clear_vector_collection(
    db_path: str = "runtime/database/books_history.db",
    config_path: str = "config/literature_fm_vector.yaml"
) -> bool:
    """
    清空向量集合（破坏性操作）
    用于数据结构重大变更时的重建

    Args:
        db_path: 数据库路径
        config_path: 向量配置文件路径

    Returns:
        bool: 是否成功
    """
    import shutil
    from pathlib import Path
    import yaml

    try:
        # 加载配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        persist_dir = Path(config['vector_db']['persist_directory'])

        # 删除向量数据库目录
        if persist_dir.exists():
            shutil.rmtree(persist_dir)
            logger.info(f"已删除向量数据库目录: {persist_dir}")

        # 重置数据库状态
        conn = sqlite3.connect(db_path)
        conn.execute("""
            UPDATE literary_tags
            SET embedding_status = NULL,
                embedding_id = NULL,
                embedding_date = NULL
            WHERE embedding_status = 'completed'
        """)
        conn.commit()
        conn.close()

        logger.info("已重置向量化状态")
        return True

    except Exception as e:
        logger.error(f"清空向量集合失败: {e}")
        return False


def get_vectorize_status(
    db_path: str = "runtime/database/books_history.db"
) -> Dict:
    """获取向量化状态"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 统计总数
    cursor.execute("""
        SELECT COUNT(*) FROM literary_tags
        WHERE llm_status = 'success'
    """)
    total_tagged = cursor.fetchone()[0]

    # 统计已向量化
    cursor.execute("""
        SELECT COUNT(*) FROM literary_tags
        WHERE llm_status = 'success' AND embedding_status = 'completed'
    """)
    vectorized = cursor.fetchone()[0]

    # 统计失败
    cursor.execute("""
        SELECT COUNT(*) FROM literary_tags
        WHERE embedding_status = 'failed'
    """)
    failed = cursor.fetchone()[0]

    conn.close()

    return {
        'total_tagged': total_tagged,
        'vectorized': vectorized,
        'pending': total_tagged - vectorized - failed,
        'failed': failed,
        'progress': round(vectorized / total_tagged * 100, 2) if total_tagged > 0 else 0
    }


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='数据库向量化工具')
    parser.add_argument('--batch-size', type=int, default=50, help='每批处理数量')
    parser.add_argument('--max', type=int, default=0, help='最大处理数量（0表示全部）')
    parser.add_argument('--status', action='store_true', help='查看向量化状态')
    parser.add_argument('--clear', action='store_true', help='清空向量数据库（破坏性操作）')
    parser.add_argument('--confirm-clear', type=str, default='',
                       help='确认清空操作（需输入 "YES_I_CONFIRM"）')

    args = parser.parse_args()

    if args.clear:
        if args.confirm_clear == "YES_I_CONFIRM":
            clear_vector_collection()
        else:
            logger.error("清空操作需要确认: --confirm-clear YES_I_CONFIRM")
    elif args.status:
        status = get_vectorize_status()
        logger.info("="*60)
        logger.info("向量化状态")
        logger.info("="*60)
        logger.info(f"  已打标总数: {status['total_tagged']}")
        logger.info(f"  已向量化: {status['vectorized']}")
        logger.info(f"  待向量化: {status['pending']}")
        logger.info(f"  失败: {status['failed']}")
        logger.info(f"  进度: {status['progress']}%")
        logger.info("="*60)
    else:
        vectorize_database(
            batch_size=args.batch_size,
            max_books=args.max
        )


if __name__ == "__main__":
    main()
