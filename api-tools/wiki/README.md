# Wiki 工具代码说明文档

本文档旨在说明 `wikidata_tool.py`、`wikipedia_tool.py` 和 `wikidata_vector_tool.py` 的功能、用法和实现细节。

## 1. Wikidata 工具 (`wikidata_tool.py`)

该工具用于从 Wikidata 知识库中检索实体信息。

### 主要功能: `search_wikidata()`

```python
search_wikidata(entity_label: str, lang: str = "zh", type_hint: Optional[str] = None) -> List[Dict[str, Any]]
```

- **功能**: 根据实体标签（如 "欧阳予倩"）进行搜索。
- **参数**:
    - `entity_label`: 需要搜索的实体名称。
    - `lang`: 搜索语言，默认为中文 (`"zh"`)。
- **返回值**: 一个包含搜索结果的列表，最多返回 2 个结果。每个结果是一个字典，包含：
    - `id`: Wikidata 实体 ID (如 "Q463335")。
    - `url`: 该实体在 Wikidata 上的完整 URL。
    - `raw`: 包含实体标签和描述的原始文本。

### 实现方式

该工具支持两种实现方式，可通过环境变量 `WD_USE_LC` 进行切换：

1.  **官方 API (默认)**:
    - **触发条件**: `WD_USE_LC` 环境变量未设置或值为 `"0"`。
    - **实现**: 直接调用 Wikidata 官方的 `wbsearchentities` API (`https://www.wikidata.org/w/api.php`)。
    - **依赖**: `httpx` 库。

2.  **LangChain (备选)**:
    - **触发条件**: `WD_USE_LC` 环境变量设置为 `"1"`。
    - **实现**: 使用 `langchain_community.tools.wikidata.tool.WikidataQueryRun` 模块进行查询，并解析其返回的文本结果。
    - **依赖**: `langchain-community` 库。

### 使用示例

```python
# 示例：搜索"欧阳予倩"
results = search_wikidata("欧阳予倩", lang="zh")
for item in results:
    print(f"ID: {item['id']}, URL: {item['url']}, 描述: {item['raw']}")
```

---

## 2. Wikipedia 工具 (`wikipedia_tool.py`)

该工具用于从 Wikipedia（维基百科）搜索并获取条目摘要。

### 主要功能: `search_wikipedia()`

```python
search_wikipedia(entity_label: str, lang: str = "zh", type_hint: Optional[str] = None) -> List[Dict[str, Any]]
```

- **功能**: 根据关键词搜索维基百科条目。
- **参数**:
    - `entity_label`: 需要搜索的条目名称。
    - `lang`: 搜索语言，默认为中文 (`"zh"`)。
- **返回值**: 如果找到匹配的条目，返回一个包含单个结果的列表。该结果是一个字典，包含：
    - `title`: 条目标题。
    - `canonicalurl`: 条目的标准 URL。
    - `summary`: 条目摘要（最多 1000 个字符）。
    - `_page`: `wikipediaapi` 库的内部页面对象，可供上层调用者进行更复杂的操作。

### 实现方式

- **实现**: 依赖 `wikipedia-api` 这个 Python 库来与维基百科进行交互。
- **User-Agent**: 为了遵循维基百科的 API 使用规范，工具在请求时会设置 `User-Agent` 为 `'HPD (wzjlxy@gmail.com)'`。

### 使用示例

```python
# 示例：搜索"欧阳予倩"
results = search_wikipedia("欧阳予倩", lang="zh")
if results:
    item = results[0]
    print(f"标题: {item['title']}\nURL: {item['canonicalurl']}\n摘要: {item['summary']}")
```

---

## 3. Wikidata 向量语义搜索工具 (`wikidata_vector_tool.py`)

该工具用于通过向量语义化在 Wikidata 知识库中进行相似性搜索。

### 主要功能: `query_wikidata_vector_db()`

```python
query_wikidata_vector_db(query_text, lang="en", k=10, rerank=False, return_vectors=False, api_secret=None)
```

- **功能**: 根据输入的文本，在 Wikidata 向量数据库中进行语义相似度查询。
- **参数**:
    - `query_text`: 查询的文本字符串。
    - `lang`: 查询语言，默认为 `"en"`。
    - `k`: 返回结果的数量，默认为 10。
    - `rerank`: 是否对结果进行重新排序，默认为 `False`。
    - `return_vectors`: 是否在结果中包含向量嵌入，默认为 `False`。
    - `api_secret`: 用于访问 API 的密钥（可选）。
- **返回值**: 一个包含 API 响应的 JSON 对象的字典。

### 实现方式

- **实现**: 通过向 `https://wd-vectordb.wmcloud.org/item/query/` 发送 GET 请求来查询外部向量数据库。
- **依赖**: `requests` 库。
- **User-Agent**: 为了表明客户端身份，工具在请求时会设置 `User-Agent`。

### 使用示例

```python
# 示例：搜索"人工智能"
results = query_wikidata_vector_db("人工智能")
if results:
    print(json.dumps(results, indent=2, ensure_ascii=False))
```

