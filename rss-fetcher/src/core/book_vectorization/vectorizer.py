#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图书向量化主控制器

负责协调整个向量化流程：读取数据 -> 过滤 -> 向量化 -> 存储
"""

import os
import json
import yaml
from typing import Dict, List
from datetime import datetime
from src.utils.logger import get_logger
from .database_reader import DatabaseReader
from .filter import BookFilter
from .embedding_client import EmbeddingClient
from .vector_store import VectorStore

logger = get_logger(__name__)


class BookVectorizer:
    """图书向量化主控制器"""
    
    def __init__(self, config_path: str):
        """
        初始化向量化器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.db_reader = DatabaseReader(self.config['database'])
        self.embedding_client = EmbeddingClient(self.config['embedding'])
        self.vector_store = VectorStore(self.config['vector_db'])
        
        logger.info("图书向量化器初始化完成")
    
    def _load_config(self, config_path: str) -> Dict:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置字典
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        logger.info(f"配置文件加载成功: {config_path}")
        return config
    
    def run(self, mode: str = "incremental") -> Dict:
        """
        执行向量化流程
        
        Args:
            mode: 运行模式
                - "full": 全量处理（重置所有状态）
                - "incremental": 增量处理（只处理 pending/failed/failed_final）
                - "retry": 只重试失败的书籍
                - "rebuild": 重建向量库（删除后重新处理）
        
        Returns:
            执行结果统计
        """
        logger.info(f"开始向量化流程: mode={mode}")
        
        # 1. 读取符合条件的书籍
        books = self._load_books(mode)
        
        if not books:
            logger.warning("没有需要处理的书籍")
            return {'total': 0, 'completed': 0, 'failed': 0, 'failed_final': 0}
        
        # 2. 批量向量化
        results = self._vectorize_batch(books)
        
        # 3. 兜底重试
        if self.config['mode']['final_retry']:
            failed_books = [b for b, r in zip(books, results) if r['status'] == 'failed']
            if failed_books:
                logger.info(f"开始兜底重试: 失败书籍数={len(failed_books)}")
                retry_results = self._final_retry(failed_books)
                # 更新结果
                for i, (book, result) in enumerate(zip(books, results)):
                    if result['status'] == 'failed':
                        # 找到对应的重试结果
                        for retry_result in retry_results:
                            if retry_result['book_id'] == book['id']:
                                results[i] = retry_result
                                break
        
        # 4. 生成报告
        report = self._generate_report(results)
        
        # 5. 关闭数据库连接
        self.db_reader.close()
        
        logger.info(f"向量化流程完成: {report}")
        return report
    
    def dry_run(self, mode: str = "incremental") -> Dict:
        """
        试运行模式（只统计，不实际执行）
        
        Args:
            mode: 运行模式
            
        Returns:
            统计信息
        """
        logger.info(f"试运行模式: mode={mode}")
        
        books = self._load_books(mode)
        
        stats = {
            'mode': mode,
            'total_to_process': len(books),
            'current_stats': self.db_reader.get_statistics()
        }
        
        self.db_reader.close()
        
        return stats
    
    def _load_books(self, mode: str) -> List[Dict]:
        """
        加载待处理书籍
        
        Args:
            mode: 运行模式
            
        Returns:
            待处理书籍列表
        """
        # 1. 从数据库读取
        all_books = self.db_reader.load_books()
        
        # 2. 根据模式过滤
        if mode == "incremental":
            # 增量模式：包含 pending + failed + failed_final（自动重试）
            # 但排除超过最大重试次数的书籍
            max_retry = self.config['mode']['max_retry_count']
            books = [
                b for b in all_books 
                if b.get('embedding_status') in ['pending', 'failed', 'failed_final', None]
                and b.get('retry_count', 0) < max_retry
            ]
            logger.info(f"增量模式: 加载 {len(books)} 本书 (pending/failed/failed_final, retry_count < {max_retry})")
        elif mode == "retry":
            # 仅重试失败的书籍
            books = [b for b in all_books if b.get('embedding_status') in ['failed', 'failed_final']]
            logger.info(f"重试模式: 加载 {len(books)} 本失败书籍")
        elif mode == "full":
            books = all_books
            logger.info(f"全量模式: 加载 {len(books)} 本书")
        elif mode == "rebuild":
            # 重建模式：删除向量库，重置状态
            self.vector_store.reset()
            self.db_reader.reset_embedding_status()
            books = all_books
            logger.info(f"重建模式: 重置向量库，加载 {len(books)} 本书")
        else:
            logger.error(f"未知的运行模式: {mode}")
            return []
        
        # 3. 应用过滤规则
        filter_engine = BookFilter(self.config['filters'], self.db_reader)
        filtered_books = filter_engine.apply(books)
        
        return filtered_books
    
    def _vectorize_batch(self, books: List[Dict]) -> List[Dict]:
        """
        批量向量化
        
        Args:
            books: 待处理书籍列表
            
        Returns:
            处理结果列表
        """
        results = []
        total = len(books)
        batch_size = self.config['embedding']['batch_size']
        
        logger.info(f"开始批量向量化: 总数={total}, 批大小={batch_size}")
        
        for i in range(0, total, batch_size):
            batch = books[i:i + batch_size]
            
            for book in batch:
                try:
                    # 1. 构建文本
                    text = self._build_text(book)
                    
                    # 2. 调用 Embedding API
                    embedding = self.embedding_client.get_embedding(text)
                    
                    # 3. 存储到 ChromaDB
                    metadata = self._build_metadata(book)
                    embedding_id = self.vector_store.add(
                        embedding=embedding,
                        metadata=metadata,
                        document=text
                    )
                    
                    # 4. 更新数据库状态为成功
                    self.db_reader.update_embedding_status(
                        book_id=book['id'],
                        status='completed',
                        embedding_id=embedding_id,
                        clear_error=True  # 清除之前的错误信息
                    )
                    
                    results.append({'book_id': book['id'], 'status': 'completed'})
                    
                except Exception as e:
                    logger.error(f"向量化失败: book_id={book['id']}, title={book.get('douban_title')}, error={str(e)}")
                    
                    # 增加重试计数
                    current_retry = book.get('retry_count', 0) + 1
                    
                    # 根据重试次数决定状态
                    if current_retry >= 3:
                        new_status = 'failed_final'
                    else:
                        new_status = 'failed'
                    
                    # 更新失败状态
                    self.db_reader.update_embedding_status(
                        book_id=book['id'],
                        status=new_status,
                        retry_count=current_retry,
                        error=str(e)
                    )
                    
                    results.append({'book_id': book['id'], 'status': 'failed', 'error': str(e)})
            
            # 定期输出进度
            processed = min(i + batch_size, total)
            if (i // batch_size) % self.config['logging']['progress_interval'] == 0:
                logger.info(f"进度: {processed}/{total} ({processed/total*100:.1f}%)")
        
        logger.info(f"批量向量化完成: 总数={total}")
        return results
    
    def _final_retry(self, failed_books: List[Dict]) -> List[Dict]:
        """
        兜底重试逻辑
        
        Args:
            failed_books: 失败的书籍列表
            
        Returns:
            重试结果列表
        """
        logger.info(f"开始兜底重试，共 {len(failed_books)} 本书")
        
        retry_results = []
        for book in failed_books:
            try:
                # 重新尝试向量化
                text = self._build_text(book)
                embedding = self.embedding_client.get_embedding(text)
                metadata = self._build_metadata(book)
                embedding_id = self.vector_store.add(
                    embedding=embedding,
                    metadata=metadata,
                    document=text
                )
                
                self.db_reader.update_embedding_status(
                    book_id=book['id'],
                    status='completed',
                    embedding_id=embedding_id,
                    clear_error=True
                )
                
                retry_results.append({'book_id': book['id'], 'status': 'completed'})
                logger.info(f"兜底重试成功: book_id={book['id']}")
                
            except Exception as e:
                logger.error(f"兜底重试仍失败: book_id={book['id']}, error={str(e)}")
                
                # 增加重试计数
                current_retry = book.get('retry_count', 0) + 1
                
                # 更新为 failed_final
                self.db_reader.update_embedding_status(
                    book_id=book['id'],
                    status='failed_final',
                    retry_count=current_retry,
                    error=str(e)
                )
                
                retry_results.append({'book_id': book['id'], 'status': 'failed_final', 'error': str(e)})
        
        return retry_results
    
    def _build_text(self, book: Dict) -> str:
        """
        构建向量化文本
        
        Args:
            book: 书籍信息字典
            
        Returns:
            构建好的文本
        """
        # 处理目录长度
        catalog = book.get('douban_catalog', '')
        if len(catalog) > self.config['text_construction']['max_catalog_length']:
            catalog = catalog[:self.config['text_construction']['max_catalog_length']] + "..."
        
        # 简介加权（重复）
        summary = book.get('douban_summary', '')
        summary_repeated = '\n'.join([summary] * self.config['text_construction']['summary_weight'])
        
        # 填充模板
        text = self.config['text_construction']['template'].format(
            douban_title=book.get('douban_title', self.config['text_construction']['empty_placeholder']),
            douban_author=book.get('douban_author', self.config['text_construction']['empty_placeholder']),
            douban_summary=summary_repeated,
            douban_catalog=catalog
        )
        
        return text
    
    def _build_metadata(self, book: Dict) -> Dict:
        """
        构建 ChromaDB Metadata
        
        Args:
            book: 书籍信息字典
            
        Returns:
            元数据字典
        """
        metadata = {}
        for field in self.config['metadata']['fields']:
            value = book.get(field)
            if value is not None:
                # ChromaDB 要求值为字符串、数字或布尔值
                if isinstance(value, (int, float, bool)):
                    metadata[field] = value
                else:
                    metadata[field] = str(value)
        
        return metadata
    
    def _generate_report(self, results: List[Dict]) -> Dict:
        """
        生成执行报告
        
        Args:
            results: 处理结果列表
            
        Returns:
            报告字典
        """
        total = len(results)
        completed = len([r for r in results if r['status'] == 'completed'])
        failed = len([r for r in results if r['status'] == 'failed'])
        failed_final = len([r for r in results if r['status'] == 'failed_final'])
        
        report = {
            'total': total,
            'completed': completed,
            'failed': failed,
            'failed_final': failed_final,
            'success_rate': f"{completed/total*100:.2f}%" if total > 0 else "0%"
        }
        
        # 保存失败报告
        if self.config['logging']['save_failed_report'] and (failed + failed_final) > 0:
            failed_books = [r for r in results if r['status'] in ['failed', 'failed_final']]
            self._save_failed_report(failed_books)
        
        return report
    
    def _save_failed_report(self, failed_books: List[Dict]):
        """
        保存失败报告
        
        Args:
            failed_books: 失败的书籍列表
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.config['logging']['failed_report_path'].format(timestamp=timestamp)
        
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(failed_books, f, ensure_ascii=False, indent=2)
        
        logger.info(f"失败报告已保存: {report_path}")
