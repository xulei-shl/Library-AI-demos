# 模块8-Phase3：情境主题书架生成功能

**Status**: Planning  \
**Date**: 2025-12-29  \
**Author**: AI Architect  \
**Phase**: Phase 3 - 情境主题书架

---

## 1. 需求理解

### 1.1 核心问题
> **如何让"纯文学"通过情境化主题进入读者视野？**

### 1.2 用户使用流程
```
┌─────────────────────────────────────────────────────────────────────┐
│  1. 人工输入情境主题                                                │
│     例如："冬日暖阳"、"春日迟迟"、"深夜独处的孤独"                  │
├─────────────────────────────────────────────────────────────────────┤
│  2. LLM主题解析                                                     │
│     将自然语言主题 → 转换为检索条件（标签组合）                      │
├─────────────────────────────────────────────────────────────────────┤
│  3. 向量检索 + 标签检索                                             │
│     双路召回：语义相似度 + 标签匹配                                 │
├─────────────────────────────────────────────────────────────────────┤
│  4. 结果融合与排序                                                  │
│     综合评分 + 随机性策略，避免推荐趋同                             │
├─────────────────────────────────────────────────────────────────────┤
│  5. 导出Excel列表                                                   │
│     输出20-30本图书，供人工筛选                                     │
├─────────────────────────────────────────────────────────────────────┤
│  6. 记录推荐历史                                                    │
│     避免重复推荐，支持去重和迭代优化                                │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.3 设计定位
| 维度 | 描述 |
|------|------|
| 检索方式 | **双路召回**：向量检索(语义) + 标签检索(结构化) |
| 结果排序 | 综合评分 + 随机多样性策略 |
| 输出形式 | Excel列表（20-30本） |
| 去重机制 | 记录推荐历史，避免重复推荐 |

---

## 2. 现有数据结构

### 2.1 literary_tags 表（已存在）
```sql
CREATE TABLE literary_tags (
    id, book_id, call_no, title,
    tags_json TEXT,          -- JSON: 5维标签 + 置信度
    llm_status, retry_count, ...
)
```

### 2.2 标签维度（5个）
| 维度 | 标签数 | 示例 |
|------|-------|------|
| reading_context | 8 | 暮色四合时、深夜独处、雨天窗前 |
| reading_load | 4 | 酣畅易读、需正襟危坐、细水长流 |
| text_texture | 8 | 诗意流动、冷峻克制、史诗宏大 |
| spatial_atmosphere | 8 | 都市孤独、乡土温情、历史回响 |
| emotional_tone | 8 | 忧郁沉思、温暖治愈、平静淡然 |

---

## 3. 检索策略

### 3.1 双路召回架构

```
                        ┌─────────────────────────────────────┐
                        │         用户输入：情境主题           │
                        └─────────────────────────────────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
                    ▼                      ▼                      ▼
          ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
          │   LLM主题解析   │    │   向量检索      │    │   标签检索      │
          │  (动态解析条件) │    │  (语义相似度)   │    │  (结构化匹配)   │
          └─────────────────┘    └─────────────────┘    └─────────────────┘
                   │                      │                      │
                   └──────────────────────┼──────────────────────┘
                                          │
                                          ▼
                               ┌─────────────────────┐
                               │    结果融合与排序    │
                               │  - 综合评分计算      │
                               │  - 随机性策略        │
                               │  - 去重过滤          │
                               └─────────────────────┘
                                          │
                                          ▼
                               ┌─────────────────────┐
                               │    输出20-30本书    │
                               └─────────────────────┘
```

### 3.2 向量检索（方案A）

> **重要说明**：向量数据存储在 **ChromaDB** 中，不是 SQLite！
>
> - SQLite (`literary_tags` 表)：存储向量化状态标记（`embedding_status`, `embedding_id`, `embedding_date`）
> - ChromaDB (`runtime/vector_db/literature_fm`)：存储实际的 4096 维向量

#### 3.2.1 向量存储设计

```sql
-- literary_tags 表新增字段（存储向量化状态）
ALTER TABLE literary_tags ADD COLUMN embedding_status TEXT DEFAULT 'pending';
-- pending: 待向量化, vectorizing: 向量化中, completed: 已完成, failed: 失败

ALTER TABLE literary_tags ADD COLUMN embedding_id TEXT;
-- 对应 ChromaDB 中的 document ID

ALTER TABLE literary_tags ADD COLUMN embedding_date TEXT;
-- 向量化完成时间
```

#### 3.2.2 向量库配置（ChromaDB）

```yaml
# config/literature_fm_vector.yaml（新增）

vector_db:
  # ChromaDB 持久化存储路径
  persist_directory: "runtime/vector_db/literature_fm"
  # Collection 名称
  collection_name: "literature_fm_contexts"
  # 距离度量方式
  distance_metric: "cosine"  # cosine, l2, ip
```

#### 3.2.3 向量生成策略

基于 5 维标签构建情境描述文本，然后调用 Embedding API 生成向量：

```python
# 参考：主题卡模块 embedding_client.py
class LiteratureEmbeddingClient:
    """文学情境 Embedding 客户端"""

    def __init__(self, config: dict):
        self.config = config
        self.client = self._init_client()

    def _init_client(self):
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
        """获取文本向量（带重试）"""
        for attempt in range(self.config['max_retries']):
            try:
                response = self.client.embeddings.create(
                    model=self.config['model'],  # BAAI/bge-m3
                    input=text,
                    dimensions=self.config.get('dimensions', 4096)
                )
                return response.data[0].embedding
            except Exception as e:
                if attempt < self.config['max_retries'] - 1:
                    time.sleep(self.config['retry_delay'])
                else:
                    raise

def build_context_text(tags_json: str) -> str:
    """基于标签构建情境描述文本"""
    tags = json.loads(tags_json)

    # 解析各维度标签
    contexts = tags.get('reading_context', [])
    loads = tags.get('reading_load', [])
    textures = tags.get('text_texture', [])
    spaces = tags.get('spatial_atmosphere', [])
    emotions = tags.get('emotional_tone', [])

    # 构建描述文本
    description = f"""
    阅读场景：{'、'.join(contexts) if contexts else '无特定场景'}
    阅读负担：{'、'.join(loads) if loads else '适中'}
    文字风格：{'、'.join(textures) if textures else '平实自然'}
    空间氛围：{'、'.join(spaces) if spaces else '无特定氛围'}
    情感基调：{'、'.join(emotions) if emotions else '平和淡然'}
    """.strip()

    return description
```

#### 3.2.4 向量检索实现（参考主题卡模块）
```python
# 参考：主题卡模块 retriever.py + vector_store.py
class VectorSearcher:
    """向量检索器（复用 ChromaDB）"""

    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.embedding_client = LiteratureEmbeddingClient(self.config['embedding'])
        self.vector_store = VectorStore(self.config['vector_db'])
        self.db_reader = DatabaseReader(self.config['database'])

    def search(
        self,
        query_text: str,
        top_k: int = 50,
        min_confidence: float = 0.65
    ) -> list[dict]:
        """向量语义检索"""
        # 1. 查询文本向量化
        query_vector = self.embedding_client.get_embedding(query_text)

        # 2. ChromaDB 检索
        results = self.vector_store.search(
            query_embedding=query_vector,
            top_k=top_k,
            filter_metadata=None
        )

        # 3. 补充书籍完整信息
        enriched = []
        for result in results:
            book_id = result['metadata']['id']
            book_info = self.db_reader.get_book_by_id(book_id)

            if book_info:
                # 计算相似度（distance 转相似度）
                similarity = 1 - result['distance']
                if similarity >= min_confidence:
                    enriched.append({
                        'book_id': book_id,
                        'title': book_info['title'],
                        'author': book_info['author'],
                        'call_no': book_info.get('call_no', ''),
                        'vector_score': similarity,
                        'embedding_id': result['embedding_id'],
                        'tags_json': book_info.get('tags_json', ''),
                        'source': 'vector'
                    })

        return enriched
```

#### 3.2.5 向量存储实现（ChromaDB）

```python
# 参考：主题卡模块 vector_store.py
class VectorStore:
    """ChromaDB 向量存储"""

    def __init__(self, config: dict):
        self.config = config
        self.client = chromadb.PersistentClient(
            path=config['persist_directory']
        )
        self.collection = self.client.get_or_create_collection(
            name=config['collection_name'],
            metadata={"hnsw:space": config['distance_metric']}
        )

    def add(
        self,
        embedding: List[float],
        metadata: dict,
        document: str
    ) -> str:
        """添加向量到数据库"""
        embedding_id = f"book_{metadata['id']}_{int(time.time())}"
        self.collection.add(
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[document],
            ids=[embedding_id]
        )
        return embedding_id

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter_metadata: dict = None
    ) -> List[dict]:
        """向量检索"""
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
```

### 3.3 标签检索（方案C - 带随机性）

```python
class TagSearcher:
    """标签检索器（带随机性策略）"""

    def search(
        self,
        conditions: dict,
        min_confidence: float = 0.65,
        limit: int = 50,
        randomness: float = 0.2  # 随机性因子
    ) -> list[dict]:
        """带随机性的标签检索"""
        # 1. 基础查询（高置信度优先）
        base_query = self._build_query(conditions, min_confidence)
        base_results = self._execute_query(base_query, limit=limit)

        # 2. 随机性策略：引入低置信度候选
        if randomness > 0:
            expanded_query = self._build_query(
                conditions,
                min_confidence * (1 - randomness)
            )
            expanded_results = self._execute_query(expanded_query, limit=limit)

            expanded_count = int(limit * randomness)
            base_results.extend(
                random.sample(expanded_results, min(expanded_count, len(expanded_results)))
            )

        # 3. 计算分数并排序
        scored_results = self._calculate_scores(base_results, conditions)
        return scored_results[:limit]
```

### 3.4 推荐历史表（方案D）

```sql
-- 新增：主题推荐历史表
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
    use_vector      INTEGER DEFAULT 0,       -- 是否使用向量检索
    vector_weight   REAL DEFAULT 0.5,        -- 向量检索权重
    randomness      REAL DEFAULT 0.2,        -- 随机性因子

    -- 元数据
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_history_input ON literature_recommendation_history(user_input);
CREATE INDEX idx_history_conditions ON literature_recommendation_history(llm_conditions);
CREATE INDEX idx_history_books ON literature_recommendation_history(book_ids);
CREATE INDEX idx_history_passed ON literature_recommendation_history(passed_book_ids);
```

### 3.5 去重查询实现

```python
class ThemeDeduplicator:
    """推荐去重器"""

    def get_excluded_book_ids(
        self,
        user_input: str,
        conditions: dict,
        similarity_threshold: float = 0.8
    ) -> set:
        """获取应排除的已推荐书目ID"""
        # 1. 检查相似输入的历史推荐
        similar_history = self._find_similar_inputs(user_input, similarity_threshold)

        # 2. 检查相似条件的历史推荐
        condition_history = self._find_similar_conditions(conditions, similarity_threshold)

        excluded_ids = set()
        for row in similar_history + condition_history:
            book_ids = json.loads(row['book_ids'])
            passed_ids = json.loads(row['passed_book_ids']) if row['passed_book_ids'] else []

            excluded_ids.update(passed_ids)  # 优先排除已通过的书目
            excluded_ids.update(book_ids)

        return excluded_ids

    def _calculate_condition_similarity(self, c1: dict, c2: dict) -> float:
        """计算两个条件的相似度"""
        all_keys = set(c1.keys()) | set(c2.keys())
        if not all_keys:
            return 0.0

        matches = sum(
            1 for key in all_keys
            if set(c1.get(key, [])) & set(c2.get(key, []))
        )
        return matches / len(all_keys)

    def save_recommendation(self, **kwargs):
        """保存推荐记录"""
        self.db.execute("""
            INSERT INTO literature_recommendation_history
            (user_input, llm_conditions, final_theme, book_ids,
             use_vector, vector_weight, randomness)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (...))
        self.db.commit()
```

### 3.6 综合检索流程

```python
def search_theme_books(
    theme_text: str,
    use_vector: bool = True,
    vector_weight: float = 0.5,
    randomness: float = 0.2,
    min_confidence: float = 0.65,
    limit: int = 30,
    deduplicator: ThemeDeduplicator = None
) -> dict:
    """主题图书综合检索"""
    # 1. LLM主题解析
    parser = ThemeParser(vocabulary)
    parsed = parser.parse(theme_text)

    # 2. 获取需要排除的已推荐书目
    excluded_ids = set()
    if deduplicator:
        excluded_ids = deduplicator.get_excluded_book_ids(theme_text, parsed['conditions'])

    # 3. 双路召回
    vector_results = []
    tag_results = []

    if use_vector:
        vector_results = vector_searcher.search(theme_text, top_k=50)
        vector_results = [r for r in vector_results if r['book_id'] not in excluded_ids]

    tag_results = tag_searcher.search(
        parsed['conditions'], min_confidence=min_confidence,
        randomness=randomness, limit=50
    )
    tag_results = [r for r in tag_results if r['book_id'] not in excluded_ids]

    # 4. 结果融合
    merged = merge_results(vector_results, tag_results, vector_weight=vector_weight)

    # 5. 去重并返回
    final_books = deduplicate_by_book_id(merged)[:limit]

    return {
        "books": final_books,
        "conditions": parsed['conditions'],
        "reason": parsed['reason'],
        "excluded_count": len(excluded_ids),
        "vector_results": len(vector_results),
        "tag_results": len(tag_results)
    }
```

---

## 4. 主题模板设计

### 4.1 主题分类

#### A. 季节主题（按月份自动编排）
```yaml
seasonal_themes:
  spring:
    title: "春日书单｜万物复苏时"
    rules:
      emotional_tone: ["温暖治愈", "浪漫柔情"]
      reading_context: ["午后慵懒", "精力充沛"]

  summer:
    title: "夏夜书单｜星空与蝉鸣"
    rules:
      emotional_tone: ["浪漫柔情", "激昂振奋"]
      spatial_atmosphere: ["虚构奇境", "乡土温情"]

  autumn:
    title: "秋思书单｜落叶与怀旧"
    rules:
      emotional_tone: ["忧郁沉思", "平静淡然"]
      reading_context: ["暮色四合时", "午后慵懒"]

  winter:
    title: "冬日书单｜围炉与内省"
    rules:
      emotional_tone: ["温暖治愈", "平静淡然"]
      reading_load: ["需正襟危坐", "细水长流"]
```

#### B. 情境主题（固定主题）
```yaml
situational_themes:
  rainy_window:
    title: "雨天窗前｜听雨读书时"
    rules:
      reading_context: ["雨天窗前", "暮色四合时"]
      emotional_tone: ["忧郁沉思", "细腻工笔"]

  late_night:
    title: "深夜独处｜与灵魂对话"
    rules:
      reading_context: ["深夜独处"]
      text_texture: ["诗意流动", "絮语呢喃"]
      emotional_tone: ["忧郁沉思", "平静淡然"]

  weekend_afternoon:
    title: "周末午后｜慵懒的时光"
    rules:
      reading_context: ["午后慵懒"]
      reading_load: ["酣畅易读", "随时可停"]

  on_the_road:
    title: "旅途之中｜在路上的阅读"
    rules:
      reading_context: ["旅途之中"]
      spatial_atmosphere: ["异域漂泊", "都市孤独"]
```

#### C. 心情主题（按情绪需求）
```yaml
emotional_themes:
  need_comfort:
    title: "需要治愈｜抱抱自己"
    rules:
      emotional_tone: ["温暖治愈"]

  need_reflection:
    title: "需要沉思｜与自己对话"
    rules:
      emotional_tone: ["忧郁沉思", "平静淡然"]
      reading_load: ["需正襟危坐"]

  need_energy:
    title: "需要热血｜重新出发"
    rules:
      emotional_tone: ["激昂振奋"]
```

---

## 5. 技术架构

### 5.1 模块结构
```
src/core/literature_fm/
├── pipeline.py              # 主流程（已有）
├── llm_tagger.py            # LLM打标器（已有）
├── tag_manager.py           # 标签管理器（已有）
├── theme_parser.py          # 【新增】主题解析器
├── theme_searcher.py        # 【新增】标签检索器
├── vector_searcher.py       # 【新增】向量检索器
├── theme_merger.py          # 【新增】结果融合器
├── theme_deduplicator.py    # 【新增】去重器
├── theme_exporter.py        # 【新增】结果导出器
├── db_init.py               # 数据库初始化（已有）
└── __init__.py

config/
├── literature_fm.yaml       # 主配置（已有）
├── literary_tags_vocabulary.yaml  # 标签词表（已有）
├── llm.yaml                 # LLM配置（已有）
└── embedding.yaml           # 【新增】向量检索配置

prompts/
├── literary_tagging.md      # 打标Prompt（已有）
└── literary_theme_parse.md  # 【新增】主题解析Prompt
```

### 5.2 类设计

#### ThemeParser（主题解析器）
```python
class ThemeParser:
    """将自然语言主题解析为检索条件"""
    def parse(self, theme_text: str) -> dict:
        pass
```

#### VectorSearcher（向量检索器）
```python
class VectorSearcher:
    """向量语义检索器"""
    def __init__(self, embedding_model=None, index_path=None):
        self.model = embedding_model or load_embedding_model()
        self.index = load_faiss_index(index_path)

    def search(self, query: str, top_k: int = 50, score_threshold: float = 0.5) -> list[dict]:
        pass

    def build_index(self, books: list):
        pass
```

#### TagSearcher（标签检索器）
```python
class TagSearcher:
    """标签检索器（带随机性）"""
    def search(self, conditions: dict, min_confidence: float = 0.65,
               limit: int = 30, randomness: float = 0.2) -> list[dict]:
        pass
```

#### ThemeMerger（结果融合器）
```python
class ThemeMerger:
    """融合双路召回结果"""
    def merge(self, vector_results: list, tag_results: list,
              vector_weight: float = 0.5) -> list:
        pass
```

#### ThemeDeduplicator（去重器）
```python
class ThemeDeduplicator:
    """推荐去重器"""
    def get_excluded_book_ids(self, user_input: str, conditions: dict,
                              similarity_threshold: float = 0.8) -> set:
        pass

    def save_recommendation(self, user_input: str, conditions: dict,
                            book_ids: list, **kwargs):
        pass
```

#### ThemeExporter（结果导出器）
```python
class ThemeExporter:
    """导出主题书架结果"""
    def export_excel(self, df: pd.DataFrame, theme_text: str,
                     conditions: dict, output_path: str) -> str:
        pass
```

---

## 6. LLM Prompt设计

### prompts/literary_theme_parse.md

```markdown
# 文学情境主题解析任务

你是一位资深的文学编辑和阅读推广专家。请分析给定的阅读主题，
从标签词表中选择最匹配的标签组合。

## 标签词表

{tag_dimensions_yaml}

## 任务要求

1. 仔细阅读用户给出的阅读主题
2. 从5个维度中选择最匹配的标签（每维度可选1-3个）
3. 设置最小置信度阈值
4. 给出解析理由

## 输出格式

```json
{
  "conditions": {
    "reading_context": ["标签1", "标签2"],
    "reading_load": ["标签1"],
    "text_texture": ["标签1", "标签2"],
    "spatial_atmosphere": ["标签1"],
    "emotional_tone": ["标签1", "标签2"]
  },
  "min_confidence": 0.7,
  "reason": "解析理由：用户想要..."
}
```

## 注意事项

- 每维度最多选择3个标签
- 优先选择与主题最相关的标签
- 如果无法判断某维度，该维度可为空数组
- 置信度阈值建议设置为0.65-0.75
```

---

## 7. 输出格式示例

### Excel格式
| 序号 | 书名 | 作者 | 出版社 | 索书号 | 豆瓣评分 | 匹配标签 | 匹配度 | 来源 |
|------|------|------|--------|--------|---------|---------|-------|------|
| 1 | 《边城》 | 沈从春 | 江苏凤凰文艺 | I247.5/4023 | 9.0 | 乡土温情 | 0.85 | V |
| 2 | 《活着》 | 余华 | 作家出版社 | I247.5/8964 | 9.4 | 细水长流 | 0.82 | T |

> 来源列：V=向量检索，T=标签检索

---

## 8. 实施步骤

### Step 1: 创建主题解析Prompt
- [ ] 新建 `prompts/literary_theme_parse.md`

### Step 2: 实现主题解析器
- [ ] 新建 `src/core/literature_fm/theme_parser.py`

### Step 3: 实现向量检索器
- [ ] 新建 `src/core/literature_fm/vector_searcher.py`
- [ ] 新建 `config/embedding.yaml`

### Step 4: 实现标签检索器（带随机性）
- [ ] 新建 `src/core/literature_fm/theme_searcher.py`

### Step 5: 实现结果融合器
- [ ] 新建 `src/core/literature_fm/theme_merger.py`

### Step 6: 实现去重器
- [ ] 新建 `src/core/literature_fm/theme_deduplicator.py`

### Step 7: 实现导出功能
- [ ] 新建 `src/core/literature_fm/theme_exporter.py`

### Step 8: 数据库迁移
- [ ] 新增 `migrations/003_create_theme_history.sql`
- [ ] 新增 `migrations/004_create_book_embeddings.sql`
- [ ] 更新 `db_init.py`

### Step 9: 更新主流程
- [ ] 更新 `pipeline.py` - 添加 `generate_theme_shelf()` 方法
- [ ] 更新 `__init__.py`

### Step 10: 测试验证
- [ ] 测试主题解析准确性
- [ ] 测试向量检索效果
- [ ] 测试标签检索随机性
- [ ] 测试结果融合排序
- [ ] 测试去重功能

---

## 9. 关键文件清单

| 操作 | 文件路径 |
|------|---------|
| 新建 | `prompts/literary_theme_parse.md` |
| 新建 | `src/core/literature_fm/theme_parser.py` |
| 新建 | `src/core/literature_fm/vector_searcher.py` |
| 新建 | `src/core/literature_fm/theme_searcher.py` |
| 新建 | `src/core/literature_fm/theme_merger.py` |
| 新建 | `src/core/literature_fm/theme_deduplicator.py` |
| 新建 | `src/core/literature_fm/theme_exporter.py` |
| 新建 | `config/literature_fm_vector.yaml` |
| 新建 | `migrations/003_create_theme_history.sql` |
| 修改 | `src/core/literature_fm/pipeline.py` |
| 修改 | `src/core/literature_fm/__init__.py` |
| 修改 | `src/core/literature_fm/db_init.py` |

---

## 10. 配置参数

### literature_fm_vector.yaml（基于 ChromaDB）
```yaml
# 向量数据库配置
vector_db:
  persist_directory: "runtime/vector_db/literature_fm"
  collection_name: "literature_fm_contexts"
  distance_metric: "cosine"  # cosine, l2, ip

# Embedding API 配置
embedding:
  model: "BAAI/bge-m3"
  dimensions: 4096
  api_key: "env:OPENAI_API_KEY"
  base_url: "https://api.openai.com/v1"
  timeout: 60
  max_retries: 3
  retry_delay: 1

# 数据库配置（SQLite - 读取 literary_tags 表）
database:
  path: "data/books_history.db"
  table: "literary_tags"

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
