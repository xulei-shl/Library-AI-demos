"""
向量检索器
基于 ChromaDB 实现语义检索
"""

import json
import os
import time
from typing import Dict, List, Optional
from pathlib import Path

import httpx
import chromadb
from openai import OpenAI
import sqlite3

from src.utils.logger import get_logger

logger = get_logger(__name__)


class VectorSearcher:
    """向量语义检索器（基于 ChromaDB）"""

    def __init__(self, config_path: str = "config/literature_fm_vector.yaml"):
        """
        初始化向量检索器

        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.embedding_client = _EmbeddingClient(self.config['embedding'])
        self.vector_store = _VectorStore(self.config['vector_db'])
        self.db_reader = _DatabaseReader(self.config['database'])

    def search(
        self,
        query_text: str,
        top_k: int = 50,
        min_confidence: float = 0.65,
        query_expansion: bool = True,
        dynamic_threshold: bool = True
    ) -> List[Dict]:
        """
        向量语义检索

        Args:
            query_text: 查询文本（情境主题）
            top_k: 返回结果数量
            min_confidence: 最小置信度（当 dynamic_threshold=False 时使用）
            query_expansion: 是否启用查询扩展（多路查询）
            dynamic_threshold: 是否启用动态阈值（根据 Top5 平均值自动调整）

        Returns:
            检索结果列表
        """
        try:
            # 1. 预处理查询文本
            processed_query = self._preprocess_query(query_text)

            # 2. 查询扩展（生成多个查询变体）
            queries = [processed_query]
            if query_expansion:
                queries = self._expand_query(processed_query)

            # 3. 多路查询与结果融合
            all_results = {}
            for i, query in enumerate(queries):
                query_vector = self.embedding_client.get_embedding(query)

                # ChromaDB 检索
                results = self.vector_store.search(
                    query_embedding=query_vector,
                    top_k=top_k
                )

                # 融合结果（取最高相似度）
                for result in results:
                    book_id = result['metadata'].get('id')
                    if not book_id:
                        continue

                    similarity = 1 - result['distance']
                    # 保留该书的最高相似度
                    if book_id not in all_results or similarity > all_results[book_id]['distance']:
                        all_results[book_id] = {
                            'metadata': result['metadata'],
                            'distance': result['distance'],
                            'embedding_id': result['embedding_id']
                        }

            # 4. 补充书籍完整信息
            enriched = []

            # 计算相似度并确定阈值
            raw_similarities = [(book_id, 1 - result['distance']) for book_id, result in all_results.items()]

            # 动态阈值计算
            if dynamic_threshold and raw_similarities:
                raw_similarities.sort(key=lambda x: x[1], reverse=True)
                top_similarities = raw_similarities[:5]

                # 取 Top5 平均值作为基准
                avg_similarity = sum(s for _, s in top_similarities) / len(top_similarities)
                # 阈值 = Top5 平均值 * 0.85（适当放宽）
                actual_threshold = max(avg_similarity * 0.85, min_confidence * 0.7)

                logger.info(f"原始相似度 Top5: {[(f'book_{bid}', f'{s:.4f}') for bid, s in top_similarities]}")
                logger.info(f"动态阈值: {actual_threshold:.4f} (Top5平均: {avg_similarity:.4f}, 固定阈值: {min_confidence})")
            else:
                actual_threshold = min_confidence
                if raw_similarities:
                    raw_similarities.sort(key=lambda x: x[1], reverse=True)
                    logger.info(f"原始相似度 Top5: {[(f'book_{bid}', f'{s:.4f}') for bid, s in raw_similarities[:5]]}")
                    logger.info(f"使用固定阈值: {actual_threshold:.4f}")

            for book_id, result in all_results.items():
                similarity = 1 - result['distance']
                if similarity >= actual_threshold:
                    book_info = self.db_reader.get_book_by_id(book_id)
                    if not book_info:
                        continue

                    enriched.append({
                        'book_id': book_id,
                        'title': book_info.get('title', ''),
                        'author': book_info.get('author', ''),
                        'call_no': book_info.get('call_no', ''),
                        'rating': book_info.get('rating', 0),
                        'tags_json': book_info.get('tags_json', ''),
                        'vector_score': round(similarity, 4),
                        'embedding_id': result['embedding_id'],
                        'source': 'vector'
                    })

            # 按相似度排序
            enriched.sort(key=lambda x: x['vector_score'], reverse=True)
            enriched = enriched[:top_k]

            logger.info(f"向量检索完成: 查询={query_text[:30]}..., 结果数={len(enriched)}")
            return enriched

        except Exception as e:
            logger.error(f"向量检索失败: {str(e)}")
            return []

    def _preprocess_query(self, query_text: str) -> str:
        """
        预处理查询文本

        Args:
            query_text: 原始查询文本

        Returns:
            处理后的查询文本
        """
        # 去除 '解析理由：' 等前缀
        prefixes_to_remove = [
            '解析理由：',
            '解析理由:',
            '理由：',
            '理由:',
        ]
        for prefix in prefixes_to_remove:
            if query_text.startswith(prefix):
                query_text = query_text[len(prefix):].strip()

        # 去除开头和结尾的引号
        query_text = query_text.strip('"\'""''')

        return query_text.strip()

    def _expand_query(self, query: str) -> List[str]:
        """
        查询扩展：生成多个查询变体

        Args:
            query: 预处理后的查询文本

        Returns:
            查询变体列表
        """
        queries = [query]

        # 尝试提取核心描述（去除"暗示"、"体现"等连接词后的内容）
        import re

        # 匹配 "暗示了...，适合..." 模式
        pattern1 = r'暗示了(.{2,50}?)[,，。]?适合(.{2,50})'
        match1 = re.search(pattern1, query)
        if match1:
            context = match1.group(1).strip()
            feeling = match1.group(2).strip()
            queries.append(f"{context}，{feeling}")
            queries.append(context)
            queries.append(feeling)

        # 匹配 "用户描述的'...'" 模式
        pattern2 = r"用户描述的['\"](.+?)['\"]"
        match2 = re.search(pattern2, query)
        if match2:
            user_desc = match2.group(1).strip()
            queries.append(user_desc)

        # 去重
        seen = set()
        unique_queries = []
        for q in queries:
            if q and q not in seen:
                seen.add(q)
                unique_queries.append(q)

        return unique_queries

    def build_index(
        self,
        books: List[Dict],
        batch_size: int = 32
    ) -> int:
        """
        为书籍列表构建向量索引

        Args:
            books: 书籍列表（包含 id 和 tags_json）
            batch_size: 批处理大小

        Returns:
            索引构建的书籍数量
        """
        try:
            embeddings = []
            metadatas = []
            documents = []

            for book in books:
                # 1. 构建情境描述文本
                doc = self._build_context_text(book.get('tags_json', ''))

                # 2. 生成向量
                embedding = self.embedding_client.get_embedding(doc)

                # 3. 收集数据
                embeddings.append(embedding)
                metadatas.append({
                    'id': book['id'],
                    'title': book.get('title', ''),
                    'author': book.get('author', ''),
                    'call_no': book.get('call_no', '')
                })
                documents.append(doc)

                # 批次处理
                if len(embeddings) >= batch_size:
                    self.vector_store.add_batch(embeddings, metadatas, documents)

                    # 更新数据库状态
                    for m in metadatas:
                        self.db_reader.update_embedding_status(
                            m['id'], status='completed'
                        )

                    embeddings = []
                    metadatas = []
                    documents = []

            # 处理剩余数据
            if embeddings:
                self.vector_store.add_batch(embeddings, metadatas, documents)
                for m in metadatas:
                    self.db_reader.update_embedding_status(m['id'], status='completed')

            logger.info(f"向量索引构建完成: 书籍数={len(books)}")
            return len(books)

        except Exception as e:
            logger.error(f"向量索引构建失败: {str(e)}")
            return 0

    def _build_context_text(
        self,
        tags_json: str = '',
        douban_title: str = '',
        douban_summary: str = '',
        douban_catalog: str = ''
    ) -> str:
        """
        基于标签和豆瓣信息构建情境描述文本

        Args:
            tags_json: 标签 JSON 字符串
            douban_title: 豆瓣书名
            douban_summary: 豆瓣内容简介
            douban_catalog: 豆瓣目录

        Returns:
            情境描述文本
        """
        parts = []

        # 1. 添加豆瓣书名（如果有）
        if douban_title:
            parts.append(f"书名：{douban_title.strip()}")

        # 2. 添加标签信息
        if tags_json:
            try:
                tags = json.loads(tags_json)
                tag_parts = []
                for dim, label_list in tags.items():
                    if label_list:
                        if isinstance(label_list, list):
                            tag_parts.append(f"{dim}：{'、'.join(label_list)}")
                        else:
                            tag_parts.append(f"{dim}：{label_list}")
                if tag_parts:
                    parts.append("阅读情境标签：" + "；".join(tag_parts))
            except (json.JSONDecodeError, TypeError):
                pass

        # 3. 添加豆瓣简介
        if douban_summary:
            summary = douban_summary.strip()
            parts.append(f"内容简介：{summary}")

        # 4. 添加豆瓣目录（限制长度）
        if douban_catalog:
            catalog = douban_catalog.strip()
            if len(catalog) > 300:
                catalog = catalog[:300] + "..."
            parts.append(f"目录：{catalog}")

        if parts:
            return "；".join(parts)
        return "这是一本文学作品，适合一般阅读。"

    def _load_config(self, config_path: str) -> Dict:
        """加载配置"""
        import yaml
        config_file = Path(config_path)
        if not config_file.exists():
            # 尝试从项目根目录查找
            root_dir = Path(__file__).parent.parent.parent.parent
            config_file = root_dir / config_path

        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def close(self):
        """关闭资源"""
        self.db_reader.close()


class _EmbeddingClient:
    """Embedding API 客户端（内部类）"""

    def __init__(self, config: Dict):
        self.config = config
        self.client = self._init_client()

    def _init_client(self) -> OpenAI:
        api_key = self._resolve_env(self.config['api_key'])
        http_client = httpx.Client(
            timeout=self.config['timeout'],
            trust_env=False
        )
        return OpenAI(
            api_key=api_key,
            base_url=self.config['base_url'],
            http_client=http_client
        )

    def get_embedding(self, text: str) -> List[float]:
        for attempt in range(self.config['max_retries']):
            try:
                response = self.client.embeddings.create(
                    model=self.config['model'],
                    input=text,
                    dimensions=self.config.get('dimensions', 4096)
                )
                return response.data[0].embedding
            except Exception as e:
                if attempt < self.config['max_retries'] - 1:
                    time.sleep(self.config['retry_delay'])
                else:
                    raise

    def _resolve_env(self, value: str) -> str:
        if value.startswith('env:'):
            return os.getenv(value[4:], '')
        return value


class _VectorStore:
    """ChromaDB 向量存储（内部类）"""

    def __init__(self, config: Dict):
        self.config = config
        self.client = chromadb.PersistentClient(path=config['persist_directory'])
        self.collection = self.client.get_or_create_collection(
            name=config['collection_name'],
            metadata={"hnsw:space": config['distance_metric']}
        )

    def add(self, embedding: List[float], metadata: Dict, document: str) -> str:
        embedding_id = f"book_{metadata['id']}_{int(time.time())}"
        self.collection.add(
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[document],
            ids=[embedding_id]
        )
        return embedding_id

    def add_batch(self, embeddings: List[List[float]], metadatas: List[Dict], documents: List[str]):
        embedding_ids = [
            f"book_{m['id']}_{int(time.time())}_{i}"
            for i, m in enumerate(metadatas)
        ]
        self.collection.add(
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
            ids=embedding_ids
        )

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_metadata
        )

        formatted = []
        if results and results.get('ids') and results['ids'][0]:
            for i in range(len(results['ids'][0])):
                formatted.append({
                    'embedding_id': results['ids'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i],
                    'document': results['documents'][0][i]
                })
        return formatted


class _DatabaseReader:
    """SQLite 数据库读取（内部类）"""

    def __init__(self, config: Dict):
        self.conn = sqlite3.connect(config['path'])
        self.table = config.get('table', 'literary_tags')

    def get_book_by_id(self, book_id: int) -> Optional[Dict]:
        cursor = self.conn.execute(
            f"SELECT * FROM {self.table} WHERE id = ?",
            (book_id,)
        )
        row = cursor.fetchone()
        if row:
            return dict(zip([c[0] for c in cursor.description], row))
        return None

    def update_embedding_status(self, book_id: int, status: str):
        from datetime import datetime
        self.conn.execute(
            f"UPDATE {self.table} SET embedding_status = ?, embedding_date = ? WHERE book_id = ?",
            (status, datetime.now().isoformat(), book_id)
        )
        self.conn.commit()

    def close(self):
        self.conn.close()
