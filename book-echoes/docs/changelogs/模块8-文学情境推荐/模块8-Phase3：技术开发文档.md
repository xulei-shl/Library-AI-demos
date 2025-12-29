# 模块8-文学情境推荐：技术开发文档

**Status**: Ready for Implementation \
**Date**: 2025-12-29 \
**Reference**: 主题卡模块向量与检索逻辑 \
**Vector Storage**: ChromaDB (not SQLite)

---

## 1. 整体架构设计

### 1.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         文学情境推荐系统架构                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      API Layer                                   │   │
│  │  generate_theme_shelf(theme_text, **options) → Excel            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Core Pipeline                                 │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │   │
│  │  │ThemeParser│→│VectorSearch│→│TagSearch │→│ThemeMerger│         │   │
│  │  │主题解析  │  │向量检索  │  │标签检索  │  │结果融合  │         │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘         │   │
│  │                            │                                      │   │
│  │                            ▼                                      │   │
│  │                    ┌──────────────┐                               │   │
│  │                    │Deduplicator  │                               │   │
│  │                    │去重 & 历史   │                               │   │
│  │                    └──────────────┘                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│            ┌───────────────────────┼───────────────────────┐           │
│            ▼                       ▼                       ▼           │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐       │
│  │   ChromaDB      │   │   SQLite        │   │   Embedding     │       │
│  │  runtime/       │   │  literary_tags  │   │   API           │       │
│  │  vector_db/     │   │  + history      │   │  Qwen3-Embed    │       │
│  │  literature_fm  │   │                 │   │                 │       │
│  └─────────────────┘   └─────────────────┘   └─────────────────┘       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 数据流

```
用户输入: "冬日暖阳，窝在沙发里阅读"
       │
       ▼
┌─────────────────┐
│  ThemeParser    │ ← LLM 解析 → tags_json
│  主题解析器     │    {reading_context: ["冬日"], ...}
└────────┬────────┘
         │
         ├────────────────────────────────────────┐
         ▼                                        ▼
┌─────────────────┐                    ┌─────────────────┐
│ VectorSearcher  │                    │  TagSearcher    │
│  向量检索       │                    │  标签检索       │
│                 │                    │  (带随机性)     │
│ query → embed   │                    │  SQL + random   │
│ → ChromaDB      │                    │  → results      │
└────────┬────────┘                    └────────┬────────┘
         │                                     │
         └─────────────────┬───────────────────┘
                           ▼
                 ┌─────────────────┐
                 │  ThemeMerger    │
                 │  结果融合器     │
                 │  fusion.py      │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Deduplicator    │
                 │ 去重器          │
                 │ - book_id       │
                 │ - call_no       │
                 │ - history       │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ ThemeExporter   │
                 │ 导出 Excel      │
                 └─────────────────┘
```

---

## 2. 核心模块详细设计

### 2.1 ThemeParser（主题解析器）

**文件**: `src/core/literature_fm/theme_parser.py`

```python
from typing import Dict, List, Tuple
import json
from src.core.literature_fm.llm_tagger import LLMTagger

class ThemeParser:
    """将自然语言主题解析为检索条件"""

    # 标签词表（5维 x 各维度标签）
    VOCABULARY = {
        "reading_context": [
            "冬日暖阳", "春日迟迟", "夏日午后", "秋日黄昏",
            "雨天窗前", "深夜独处", "午后慵懒", "旅途之中"
        ],
        "reading_load": [
            "酣畅易读", "需正襟危坐", "随时可停", "细水长流"
        ],
        "text_texture": [
            "诗意流动", "冷峻克制", "史诗宏大", "絮语呢喃",
            "细腻工笔", "粗粝有力", "意识流转", "幽默轻盈"
        ],
        "spatial_atmosphere": [
            "都市孤独", "乡土温情", "历史回响", "异域漂泊",
            "虚构奇境", "日常诗意", "自然书写", "家庭羁绊"
        ],
        "emotional_tone": [
            "温暖治愈", "忧郁沉思", "平静淡然", "浪漫柔情",
            "激昂振奋", "残酷真实", "幽默轻盈", "哲思深邃"
        ]
    }

    def __init__(self, llm_config: dict):
        self.llm = LLMTagger(llm_config)

    def parse(self, theme_text: str) -> Dict:
        """
        解析主题文本为检索条件

        Args:
            theme_text: 用户输入的情境主题描述

        Returns:
            {
                "conditions": {
                    "reading_context": [...],
                    "reading_load": [...],
                    ...
                },
                "min_confidence": 0.65,
                "reason": "解析理由..."
            }
        """
        prompt = self._build_prompt(theme_text)
        response = self.llm.call(prompt)
        return self._parse_response(response)

    def _build_prompt(self, theme_text: str) -> str:
        return f"""
        你是一位资深的文学编辑。请分析以下阅读主题，从标签词表中选择最匹配的标签。

        ## 标签词表
        {json.dumps(self.VOCABULARY, ensure_ascii=False, indent=2)}

        ## 用户输入
        {theme_text}

        ## 输出要求
        JSON格式：
        {{
            "conditions": {{"维度": ["标签1", "标签2"]}},
            "min_confidence": 0.65,
            "reason": "解析理由"
        }}
        """

    def _parse_response(self, response: str) -> Dict:
        # 提取 JSON 内容并解析
        ...
```

### 2.2 VectorSearcher（向量检索器）

**文件**: `src/core/literature_fm/vector_searcher.py`

```python
from typing import Dict, List, Optional
import yaml
import httpx
from openai import OpenAI
import chromadb
import time
from src.utils.logger import get_logger

logger = get_logger(__name__)


class VectorSearcher:
    """向量语义检索器（基于 ChromaDB）"""

    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.embedding_client = _EmbeddingClient(self.config['embedding'])
        self.vector_store = _VectorStore(self.config['vector_db'])
        self.db_reader = _DatabaseReader(self.config['database'])

    def search(
        self,
        query_text: str,
        top_k: int = 50,
        min_confidence: float = 0.65
    ) -> List[Dict]:
        """
        向量语义检索

        Args:
            query_text: 查询文本（情境主题）
            top_k: 返回结果数量
            min_confidence: 最小置信度

        Returns:
            检索结果列表
        """
        # 1. 查询文本向量化
        query_vector = self.embedding_client.get_embedding(query_text)

        # 2. ChromaDB 检索
        results = self.vector_store.search(
            query_embedding=query_vector,
            top_k=top_k
        )

        # 3. 补充书籍完整信息
        enriched = []
        for result in results:
            book_id = result['metadata']['id']
            book_info = self.db_reader.get_book_by_id(book_id)

            if book_info:
                similarity = 1 - result['distance']
                if similarity >= min_confidence:
                    enriched.append({
                        'book_id': book_id,
                        'title': book_info['title'],
                        'author': book_info['author'],
                        'call_no': book_info.get('call_no', ''),
                        'rating': book_info.get('rating', 0),
                        'tags_json': book_info.get('tags_json', ''),
                        'vector_score': round(similarity, 4),
                        'embedding_id': result['embedding_id'],
                        'source': 'vector'
                    })

        return enriched

    def build_index(
        self,
        books: List[Dict],
        batch_size: int = 32
    ) -> int:
        """
        为书籍列表构建向量索引

        Args:
            books: 书籍列表（包含 tags_json）
            batch_size: 批处理大小

        Returns:
            索引构建的书籍数量
        """
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
                'title': book['title'],
                'author': book.get('author', ''),
                'call_no': book.get('call_no', '')
            })
            documents.append(doc)

        # 4. 批量添加到 ChromaDB
        self.vector_store.add_batch(embeddings, metadatas, documents)

        # 5. 更新数据库状态
        for book in books:
            self.db_reader.update_embedding_status(
                book['id'],
                status='completed'
            )

        return len(books)

    def _build_context_text(self, tags_json: str) -> str:
        """基于标签构建情境描述文本"""
        try:
            tags = json.loads(tags_json)
        except:
            return "这是一本文学作品，适合一般阅读。"

        parts = []
        for dim, label_list in tags.items():
            if label_list:
                parts.append(f"{dim}: {'、'.join(label_list)}")

        return "适合阅读的场景和感受：" + "；".join(parts)

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r', encoding='utf-8') as f:
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
        api_key = self._resolve_env(config['api_key'])
        http_client = httpx.Client(timeout=config['timeout'], trust_env=False)
        return OpenAI(api_key=api_key, base_url=config['base_url'], http_client=http_client)

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
        import sqlite3
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
        self.conn.execute(
            f"UPDATE {self.table} SET embedding_status = ?, embedding_date = ? WHERE id = ?",
            (status, datetime.now().isoformat(), book_id)
        )
        self.conn.commit()

    def close(self):
        self.conn.close()
```

### 2.3 TagSearcher（标签检索器）

**文件**: `src/core/literature_fm/theme_searcher.py`

```python
import random
from typing import Dict, List
import sqlite3
import json
from dataclasses import dataclass


@dataclass
class TagSearchResult:
    book_id: int
    title: str
    author: str
    call_no: str
    tags_json: str
    tag_score: float
    confidence: float
    source: str = 'tag'


class TagSearcher:
    """标签检索器（带随机性策略）"""

    def __init__(self, db_path: str, table: str = 'literary_tags'):
        self.db_path = db_path
        self.table = table

    def search(
        self,
        conditions: Dict[str, List[str]],
        min_confidence: float = 0.65,
        limit: int = 50,
        randomness: float = 0.2
    ) -> List[TagSearchResult]:
        """
        带随机性的标签检索

        Args:
            conditions: 检索条件（各维度的标签列表）
            min_confidence: 最小置信度
            limit: 返回结果数量
            randomness: 随机性因子（0-1）

        Returns:
            检索结果列表
        """
        # 1. 高置信度基础查询
        base_results = self._query_by_conditions(
            conditions,
            min_confidence=min_confidence,
            limit=limit
        )

        # 2. 随机性扩展查询
        if randomness > 0:
            expanded_results = self._query_by_conditions(
                conditions,
                min_confidence=min_confidence * (1 - randomness),
                limit=limit
            )
            # 随机选取部分扩展结果
            expand_count = int(limit * randomness)
            if len(expanded_results) > expand_count:
                expanded_results = random.sample(expanded_results, expand_count)
            base_results.extend(expanded_results)

        # 3. 按分数排序
        base_results.sort(key=lambda x: x.tag_score, reverse=True)

        return base_results[:limit]

    def _query_by_conditions(
        self,
        conditions: Dict[str, List[str]],
        min_confidence: float,
        limit: int
    ) -> List[TagSearchResult]:
        """根据条件查询数据库"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        # 构建查询
        where_clauses = []
        params = []

        for dimension, tags in conditions.items():
            if tags:
                placeholders = ','.join(['?' for _ in tags])
                where_clauses.append(
                    f"json_extract(tags_json, '$.{dimension}') LIKE ?"
                )
                # 构建 JSON 数组查询条件
                tags_pattern = '%"' + '"%'.join(tags) + '"%'
                params.append(tags_pattern)

        if not where_clauses:
            return []

        where_sql = ' AND '.join(where_clauses)

        # 计算置信度分数
        confidence_formula = """
        (
            SELECT COUNT(*) FROM (
                SELECT value FROM json_each(tags_json)
                WHERE value IN ({tags_placeholders})
            )
        ) / {total_count}
        """.format(
            tags_placeholders=','.join(['?' for _ in tags if tags]),
            total_count=len([t for t in conditions.values() if t])
        )

        query = f"""
        SELECT id, title, author, call_no, tags_json,
               CAST({confidence_formula} AS REAL) as confidence
        FROM {self.table}
        WHERE {where_sql} AND confidence >= ?
        ORDER BY confidence DESC
        LIMIT ?
        """

        cursor = conn.execute(query, params + [min_confidence, limit])
        results = []

        for row in cursor.fetchall():
            results.append(TagSearchResult(
                book_id=row['id'],
                title=row['title'],
                author=row['author'],
                call_no=row['call_no'] or '',
                tags_json=row['tags_json'],
                tag_score=row['confidence'],
                confidence=row['confidence'],
                source='tag'
            ))

        conn.close()
        return results
```

### 2.4 ThemeMerger（结果融合器）

**文件**: `src/core/literature_fm/theme_merger.py`

```python
from typing import Dict, List, Tuple
from dataclasses import dataclass, field
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MergedResult:
    book_id: int
    title: str
    author: str
    call_no: str
    tags_json: str
    vector_score: float = 0
    tag_score: float = 0
    final_score: float = 0
    sources: List[str] = field(default_factory=list)


class ThemeMerger:
    """融合双路召回结果"""

    def __init__(self, vector_weight: float = 0.5):
        """
        Args:
            vector_weight: 向量检索结果权重（标签权重 = 1 - vector_weight）
        """
        self.vector_weight = vector_weight
        self.tag_weight = 1 - vector_weight

    def merge(
        self,
        vector_results: List[Dict],
        tag_results: List[Dict]
    ) -> List[MergedResult]:
        """
        融合向量检索和标签检索的结果

        Args:
            vector_results: 向量检索结果
            tag_results: 标签检索结果

        Returns:
            融合后的排序结果
        """
        # 1. 聚合结果
        aggregated: Dict[int, MergedResult] = {}

        for item in vector_results:
            book_id = item['book_id']
            aggregated[book_id] = MergedResult(
                book_id=book_id,
                title=item['title'],
                author=item['author'],
                call_no=item.get('call_no', ''),
                tags_json=item.get('tags_json', ''),
                vector_score=item.get('vector_score', 0),
                sources=['vector']
            )

        for item in tag_results:
            book_id = item['book_id']
            if book_id in aggregated:
                # 已存在，合并分数和来源
                aggregated[book_id].tag_score = item.get('tag_score', 0)
                if 'tag' not in aggregated[book_id].sources:
                    aggregated[book_id].sources.append('tag')
            else:
                # 新条目
                aggregated[book_id] = MergedResult(
                    book_id=book_id,
                    title=item['title'],
                    author=item['author'],
                    call_no=item.get('call_no', ''),
                    tags_json=item.get('tags_json', ''),
                    tag_score=item.get('tag_score', 0),
                    sources=['tag']
                )

        # 2. 计算综合分数
        for result in aggregated.values():
            result.final_score = (
                self.vector_weight * result.vector_score +
                self.tag_weight * result.tag_score
            )

        # 3. 按分数排序
        sorted_results = sorted(
            aggregated.values(),
            key=lambda x: x.final_score,
            reverse=True
        )

        logger.info(
            f"结果融合完成: 向量={len(vector_results)}, 标签={len(tag_results)}, "
            f"融合后={len(sorted_results)}"
        )

        return sorted_results
```

### 2.5 ThemeDeduplicator（去重器）

**文件**: `src/core/literature_fm/theme_deduplicator.py`

```python
import sqlite3
import json
from typing import Dict, List, Set, Optional


class ThemeDeduplicator:
    """推荐去重器"""

    def __init__(self, db_path: str, history_table: str = 'literature_recommendation_history'):
        self.db_path = db_path
        self.history_table = history_table

    def get_excluded_book_ids(
        self,
        user_input: str,
        conditions: Dict,
        similarity_threshold: float = 0.8
    ) -> Set[int]:
        """
        获取应排除的已推荐书目ID

        Args:
            user_input: 用户原始输入
            conditions: 检索条件
            similarity_threshold: 相似度阈值

        Returns:
            应排除的书目ID集合
        """
        excluded = set()

        # 1. 检查相似输入的历史推荐
        similar_history = self._find_similar_inputs(user_input, similarity_threshold)

        # 2. 检查相似条件的历史推荐
        condition_history = self._find_similar_conditions(conditions, similarity_threshold)

        for row in similar_history + condition_history:
            passed_ids = self._parse_book_ids(row['passed_book_ids'])
            excluded.update(passed_ids)

        return excluded

    def save_recommendation(
        self,
        user_input: str,
        conditions: Dict,
        book_ids: List[int],
        final_theme: Optional[str] = None,
        vector_weight: float = 0.5,
        randomness: float = 0.2
    ):
        """保存推荐记录"""
        conn = sqlite3.connect(self.db_path)
        conn.execute(f"""
            INSERT INTO {self.history_table}
            (user_input, llm_conditions, final_theme, book_ids,
             use_vector, vector_weight, randomness)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_input,
            json.dumps(conditions, ensure_ascii=False),
            final_theme,
            json.dumps(book_ids, ensure_ascii=False),
            1,
            vector_weight,
            randomness
        ))
        conn.commit()
        conn.close()

    def _find_similar_inputs(
        self,
        user_input: str,
        threshold: float
    ) -> List[Dict]:
        """查找相似输入的历史记录"""
        # 简单实现：完全匹配 + 关键词匹配
        # 实际可使用编辑距离或语义相似度
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(f"""
            SELECT * FROM {self.history_table}
            WHERE user_input = ?
        """, (user_input,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(zip([c[0] for c in cursor.description], row)) for row in rows]

    def _find_similar_conditions(
        self,
        conditions: Dict,
        threshold: float
    ) -> List[Dict]:
        """查找相似条件的历史记录"""
        # 简：检查是否有共同的标签维度
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(f"""
            SELECT * FROM {self.history_table}
        """)
        rows = cursor.fetchall()

        similar = []
        for row in rows:
            old_conditions = json.loads(row['llm_conditions'])
            similarity = self._calculate_condition_similarity(conditions, old_conditions)
            if similarity >= threshold:
                similar.append(dict(zip([c[0] for c in cursor.description], row)))

        conn.close()
        return similar

    def _calculate_condition_similarity(self, c1: Dict, c2: Dict) -> float:
        """计算两个条件的相似度"""
        all_keys = set(c1.keys()) | set(c2.keys())
        if not all_keys:
            return 0.0

        matches = sum(
            1 for key in all_keys
            if set(c1.get(key, [])) & set(c2.get(key, []))
        )
        return matches / len(all_keys)

    def _parse_book_ids(self, book_ids_json: Optional[str]) -> Set[int]:
        """解析 JSON 格式的书目ID列表"""
        if not book_ids_json:
            return set()
        try:
            return set(json.loads(book_ids_json))
        except:
            return set()
```

### 2.6 ThemeExporter（结果导出器）

**文件**: `src/core/literature_fm/theme_exporter.py`

```python
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional


class ThemeExporter:
    """导出主题书架结果"""

    def export_excel(
        self,
        results: List[Dict],
        theme_text: str,
        conditions: Dict,
        output_path: str
    ) -> str:
        """
        导出 Excel 格式的主题书架

        Args:
            results: 融合后的结果列表
            theme_text: 用户输入的主题
            conditions: 解析后的检索条件
            output_path: 输出文件路径

        Returns:
            实际输出的文件路径
        """
        # 1. 构建 DataFrame
        data = []

        for i, item in enumerate(results, 1):
            tags = self._parse_tags(item.get('tags_json', ''))
            match_tags = self._get_match_tags(conditions, tags)

            data.append({
                '序号': i,
                '书名': item['title'],
                '作者': item['author'],
                '索书号': item.get('call_no', ''),
                '综合评分': round(item.get('final_score', 0), 3),
                '向量得分': round(item.get('vector_score', 0), 3),
                '标签得分': round(item.get('tag_score', 0), 3),
                '匹配标签': '、'.join(match_tags),
                '来源': self._get_source_label(item)
            })

        df = pd.DataFrame(data)

        # 2. 添加元信息
        output_file = self._generate_filename(output_path, theme_text)

        # 3. 导出 Excel（使用 openpyxl）
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # 主结果表
            df.to_excel(writer, sheet_name='推荐结果', index=False)

            # 元信息表
            meta_data = [
                ['主题', theme_text],
                ['检索条件', str(conditions)],
                ['推荐时间', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                ['推荐数量', len(results)]
            ]
            meta_df = pd.DataFrame(meta_data, columns=['项目', '内容'])
            meta_df.to_excel(writer, sheet_name='元信息', index=False)

        return output_file

    def _parse_tags(self, tags_json: str) -> Dict:
        """解析标签 JSON"""
        import json
        try:
            return json.loads(tags_json)
        except:
            return {}

    def _get_match_tags(self, conditions: Dict, tags: Dict) -> List[str]:
        """获取匹配的标签"""
        matched = []
        for dim, dim_tags in conditions.items():
            for tag in dim_tags:
                if tag in tags.get(dim, []):
                    matched.append(f"{tag}")
        return matched

    def _get_source_label(self, item: Dict) -> str:
        """获取来源标签"""
        sources = item.get('sources', [])
        if 'vector' in sources and 'tag' in sources:
            return '混合'
        elif 'vector' in sources:
            return '向量'
        elif 'tag' in sources:
            return '标签'
        return '未知'

    def _generate_filename(self, base_path: str, theme_text: str) -> str:
        """生成输出文件名"""
        import re
        safe_name = re.sub(r'[^\w\s-]', '', theme_text)[:20]
        safe_name = re.sub(r'[\s-]+', '_', safe_name).strip('_')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{base_path}/主题书架_{safe_name}_{timestamp}.xlsx"
```

---

## 3. 数据库 Schema 设计

### 3.1 SQLite 表结构

#### literary_tags 表扩展

```sql
-- 向量化状态字段（新增）
ALTER TABLE literary_tags
ADD COLUMN embedding_status TEXT DEFAULT 'pending';
-- pending: 待向量化, vectorizing: 向量化中, completed: 已完成, failed: 失败

ALTER TABLE literary_tags
ADD COLUMN embedding_id TEXT;

ALTER TABLE literary_tags
ADD COLUMN embedding_date TEXT;
```

#### literature_recommendation_history 表

```sql
CREATE TABLE literature_recommendation_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 主题信息
    user_input      TEXT NOT NULL,           -- 用户原始输入
    llm_conditions  TEXT NOT NULL,           -- LLM解析后的检索条件(JSON)
    final_theme     TEXT,                    -- 最终主题名称(可人工设定)

    -- 推荐结果
    book_ids        TEXT NOT NULL,           -- 推荐的书目ID列表(JSON)
    passed_book_ids TEXT,                    -- 人工筛选通过的书目ID(JSON)

    -- 检索策略标记
    use_vector      INTEGER DEFAULT 1,       -- 是否使用向量检索
    vector_weight   REAL DEFAULT 0.5,        -- 向量检索权重
    randomness      REAL DEFAULT 0.2,        -- 随机性因子

    -- 元数据
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_history_input ON literature_recommendation_history(user_input);
CREATE INDEX idx_history_conditions ON literature_recommendation_history(llm_conditions);
CREATE INDEX idx_history_books ON literature_recommendation_history(book_ids);
```

### 3.2 ChromaDB Collection

**Collection 名称**: `literature_fm_contexts`

**存储内容**:
| 字段 | 类型 | 说明 |
|-----|------|------|
| embeddings | List[float] | 4096维向量 |
| metadatas | Dict | `{id, title, author, call_no}` |
| documents | str | 情境描述文本 |
| ids | str | `book_{id}_{timestamp}` |

---

## 4. 配置文件

### config/literature_fm_vector.yaml（参考主题卡模块）

```yaml
# ============================================================================
# 文学情境推荐向量检索配置
# 参考：主题卡模块 book_vectorization.yaml
# ============================================================================

# 数据库配置（SQLite - 读取 literary_tags 表）
database:
  path: "runtime/database/books_history.db"
  table: "literary_tags"

# 向量数据库配置
vector_db:
  type: "chromadb"
  persist_directory: "runtime/vector_db/literature_fm"
  collection_name: "literature_fm_contexts"
  distance_metric: "cosine"  # cosine / l2 / ip

# Embedding 模型配置（与主题卡模块一致）
embedding:
  provider: "SiliconFlow"
  model: "Qwen/Qwen3-Embedding-8B"
  api_key: "env:SiliconFlow_API_KEY"
  base_url: "https://api.siliconflow.cn/v1"
  dimensions: 4096
  batch_size: 50
  max_retries: 3
  timeout: 30
  retry_delay: 2

# Reranker 配置（与主题卡模块一致）
reranker:
  enabled: true
  provider: "siliconflow"
  model: "Qwen/Qwen3-Reranker-8B"
  api_key: "env:SiliconFlow_API_KEY"
  base_url: "https://api.siliconflow.cn/v1"
  top_n: 20
  timeout: 15

# 结果融合规则（与主题卡模块一致）
fusion:
  weights:
    max_similarity: 0.6
    avg_similarity: 0.2
    match_count: 0.2
  final_top_k: 15

# 检索策略默认值
default:
  use_vector: true
  vector_weight: 0.5
  randomness: 0.2
  min_confidence: 0.65
  top_k: 50
  final_top_k: 30
  similarity_threshold: 0.8
```

---

## 5. 模块结构

```
src/core/literature_fm/
├── __init__.py              # 导出主要类和函数
├── pipeline.py              # 主流程（已有）
├── llm_tagger.py            # LLM打标器（已有）
├── tag_manager.py           # 标签管理器（已有）
├── theme_parser.py          # 【新增】主题解析器
├── vector_searcher.py       # 【新增】向量检索器（基于ChromaDB）
├── theme_searcher.py        # 【新增】标签检索器
├── theme_merger.py          # 【新增】结果融合器
├── theme_deduplicator.py    # 【新增】去重器
├── theme_exporter.py        # 【新增】结果导出器
└── db_init.py               # 数据库初始化（已有）

config/
├── literature_fm.yaml       # 主配置（已有）
├── literary_tags_vocabulary.yaml  # 标签词表（已有）
├── llm.yaml                 # LLM配置（已有）
└── literature_fm_vector.yaml      # 【新增】向量检索配置

prompts/
├── literary_tagging.md      # 打标Prompt（已有）
└── literary_theme_parse.md  # 【新增】主题解析Prompt

migrations/
├── 003_create_theme_history.sql  # 【新增】推荐历史表
└── db_init.py                    # 数据库初始化（已有）
```

---

## 6. 实施步骤

### Step 1: 数据库迁移
- [ ] 新建 `migrations/003_create_theme_history.sql`
- [ ] 更新 `literary_tags` 表结构（添加向量化状态字段）

### Step 2: 配置与 Prompt
- [ ] 新建 `config/literature_fm_vector.yaml`
- [ ] 新建 `prompts/literary_theme_parse.md`

### Step 3: 核心模块实现
- [ ] 新建 `src/core/literature_fm/theme_parser.py`
- [ ] 新建 `src/core/literature_fm/vector_searcher.py`
- [ ] 新建 `src/core/literature_fm/theme_searcher.py`
- [ ] 新建 `src/core/literature_fm/theme_merger.py`
- [ ] 新建 `src/core/literature_fm/theme_deduplicator.py`
- [ ] 新建 `src/core/literature_fm/theme_exporter.py`

### Step 4: 主流程集成
- [ ] 更新 `pipeline.py` - 添加 `generate_theme_shelf()` 方法
- [ ] 更新 `__init__.py`

### Step 5: 测试验证
- [ ] 测试主题解析准确性
- [ ] 测试向量检索效果
- [ ] 测试标签检索随机性
- [ ] 测试结果融合排序
- [ ] 测试去重功能
- [ ] 测试导出功能

---

## 7. API 接口设计

### 主入口函数

```python
from src.core.literature_fm import generate_theme_shelf

def generate_theme_shelf(
    theme_text: str,
    use_vector: bool = True,
    vector_weight: float = 0.5,
    randomness: float = 0.2,
    min_confidence: float = 0.65,
    final_top_k: int = 30,
    output_dir: str = "output",
    config_path: str = "config/literature_fm_vector.yaml"
) -> Dict:
    """
    生成情境主题书架

    Args:
        theme_text: 用户输入的情境主题（如 "冬日暖阳，窝在沙发里阅读"）
        use_vector: 是否使用向量检索
        vector_weight: 向量检索权重
        randomness: 随机性因子（0-1）
        min_confidence: 最小置信度
        final_top_k: 最终输出数量
        output_dir: 输出目录
        config_path: 配置文件路径

    Returns:
        {
            "success": True,
            "theme": "冬日暖阳，窝在沙发里阅读",
            "conditions": {...},
            "books": [...],
            "output_file": "output/主题书架_xxx.xlsx",
            "stats": {...}
        }
    """
    pass
```

---

## 8. 依赖说明

### Python 依赖

```yaml
# requirements.txt 新增
chromadb>=0.4.0
openai>=1.0.0
httpx>=0.25.0
pandas>=2.0.0
openpyxl>=3.1.0
```

### 外部服务

| 服务 | 用途 | 配置键 |
|-----|------|-------|
| Embedding API | 文本向量化 | `embedding.model`, `embedding.api_key` |
| LLM API | 主题解析 | `llm.*`（复用现有配置） |

---

## 9. 参考资料

- **主题卡模块配置**: `docs/changelogs/模块8-文学情境推荐/主题卡模块向量与检索逻辑参考/book_vectorization.yaml`
- **主题卡模块向量代码**: `docs/changelogs/模块8-文学情境推荐/主题卡模块向量与检索逻辑参考/book_vectorization/`
- **ChromaDB 文档**: https://docs.trychroma.com/
- **SiliconFlow API**: https://docs.siliconflow.cn/
