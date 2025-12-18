# 图书检索API接口文档

## 概述

图书检索API提供了基于向量语义检索的能力，支持单文本检索和多子查询融合检索两种模式。API基于FastAPI框架实现，可被本地应用或其他项目调用。

**API基础信息：**
- **服务地址**: `http://localhost:8000`（默认本地端口）
- **协议**: HTTP POST
- **数据格式**: JSON
- **编码**: UTF-8

## 接口列表

### 1. 文本相似度检索

#### 接口地址
```
POST /api/books/text-search
```

#### 请求参数

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `query` | string | ✅ | - | 检索关键词或文本 |
| `top_k` | integer | ❌ | 5 | 返回结果数量 |
| `min_rating` | float | ❌ | - | 最低豆瓣评分过滤（可选） |
| `response_format` | string | ❌ | "json" | 响应格式："json" 或 "plain_text" |
| `plain_text_template` | string | ❌ | - | 纯文本模式下的格式模板 |
| `llm_hint` | object | ❌ | - | LLM提示信息（透传用） |
| `save_to_file` | boolean | ❌ | false | 是否保存结果到文件 |

#### 请求示例

```json
{
  "query": "人工智能伦理与社会影响",
  "top_k": 5,
  "min_rating": 7.5,
  "response_format": "json"
}
```

#### 返回字段说明

**成功响应 (HTTP 200):**
```json
{
  "results": [
    {
      "title": "书名",
      "author": "作者",
      "rating": 8.5,
      "summary": "完整的书籍简介内容",
      "call_no": "索书号",
      "similarity_score": 0.9245,
      "fused_score": 2.1234,
      "embedding_id": "book_xxx",
      "book_id": "12345"
    }
  ],
  "metadata": {
    "mode": "text_search",
    "query": "人工智能伦理与社会影响",
    "top_k": 5,
    "min_rating": 7.5,
    "response_format": "json"
  }
}
```

**字段详细说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `results` | array | 检索结果列表 |
| `title` | string | 书籍标题 |
| `author` | string | 作者信息 |
| `rating` | float | 豆瓣评分 |
| `summary` | string | 完整书籍简介（不截断） |
| `call_no` | string | 图书馆索书号 |
| `similarity_score` | float | 文本相似度分数 |
| `fused_score` | float | 融合分数（多查询时） |
| `reranker_score` | float | 重排序分数（启用rerank时） |
| `final_score` | float | 最终分数（重排序后） |
| `embedding_id` | string | 向量存储ID |
| `book_id` | string | 书籍数据库ID |
| `source_query_type` | string | 源查询类型（多查询时） |
| `match_source` | string | 匹配来源（精确匹配时） |
| `metadata` | object | 元数据信息 |
| `metadata.mode` | string | 检索模式："text_search" |

### 2. 多子查询检索

#### 接口地址
```
POST /api/books/multi-query
```

#### 请求参数

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `markdown_text` | string | ✅ | - | Markdown格式的交叉分析文本 |
| `per_query_top_k` | integer | ❌ | 15 | 每个子查询的候选数量 |
| `final_top_k` | integer | ❌ | 15 | 融合后最终返回数量 |
| `min_rating` | float | ❌ | - | 最低豆瓣评分过滤（可选） |
| `enable_rerank` | boolean | ❌ | false | 是否启用重排序功能 |
| `disable_exact_match` | boolean | ❌ | false | 是否禁用精确匹配 |
| `response_format` | string | ❌ | "json" | 响应格式："json" 或 "plain_text" |
| `plain_text_template` | string | ❌ | - | 纯文本模式下的格式模板 |
| `llm_hint` | object | ❌ | - | LLM提示信息（透传用） |
| `save_to_file` | boolean | ❌ | false | 是否保存结果到文件 |

#### Markdown文本格式要求

多查询检索需要特定格式的Markdown文本：

```markdown
# 交叉主题分析报告 - 主题名称

## 共同母题

- 名称: 主题名称
- 关键词: 关键词1, 关键词2, 关键词3
- 摘要: 主题摘要描述

## 文章列表

### 文章 1: 文章标题

| 字段 | 内容 |
| --- | --- |
| 主题聚焦 | 主题聚焦描述 |
| 标签 | 标签1, 标签2, 标签3 |
| 提及书籍 | [{'title': '书名', 'author': '作者'}] |

## 深度洞察

- 洞察要点1
- 洞察要点2
```

#### 请求示例

```json
{
  "markdown_text": "# 交叉主题分析报告 - AI技术对现代民主选举的双刃剑作用\n\n## 共同母题\n\n- 名称: AI技术对现代民主选举的双刃剑作用\n- 关键词: AI选举, 民主合法性, 政治传播\n- 摘要: 本文聚焦于AI技术在选举中的深度介入...",
  "per_query_top_k": 10,
  "final_top_k": 15,
  "enable_rerank": true,
  "response_format": "json"
}
```

#### 返回字段说明

**成功响应 (HTTP 200):**
```json
{
  "results": [
    {
      "title": "书名",
      "author": "作者", 
      "rating": 8.5,
      "summary": "完整的书籍简介内容",
      "call_no": "索书号",
      "similarity_score": 0.9245,
      "fused_score": 2.1234,
      "reranker_score": 0.8567,
      "final_score": 0.9123,
      "embedding_id": "book_xxx",
      "book_id": "12345",
      "source_query_type": "primary",
      "match_source": "title"
    }
  ],
  "metadata": {
    "mode": "multi_query",
    "query_package_origin": "parsed",
    "enable_rerank": true,
    "disable_exact_match": false,
    "per_query_top_k": 10,
    "final_top_k": 15,
    "min_rating": null,
    "response_format": "json"
  },
  "query_package": {
    "primary": ["主题名称"],
    "tags": ["标签1", "标签2"],
    "insight": ["洞察1", "洞察2"],
    "books": ["书名1", "书名2"]
  },
  "query_package_metadata": {
    "parse_method": "structured"
  }
}
```

**额外字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `source_query_type` | string | 源查询类型：primary/tags/insight/books |
| `match_source` | string | 精确匹配来源：title/author/custom_keywords |
| `query_package` | object | 解析的查询包信息 |
| `query_package_metadata` | object | 查询包元数据 |

## 错误处理

### HTTP状态码说明

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 422 | 请求数据验证失败 |
| 500 | 服务器内部错误 |

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

### 常见错误

| 错误类型 | 触发条件 | 解决方案 |
|----------|----------|----------|
| 参数验证失败 | 必填字段缺失或格式错误 | 检查请求参数 |
| 查询为空 | query或markdown_text为空 | 提供有效的查询文本 |
| top_k无效 | top_k <= 0 | 使用正整数 |
| 响应格式错误 | response_format不在支持范围内 | 使用"json"或"plain_text" |

## 纯文本模式

当 `response_format` 设置为 `"plain_text"` 时，API返回格式化的纯文本结果：

```json
{
  "results": [...],
  "metadata": {...},
  "context_plain_text": "1. 书名 by 作者\n2. 书名 by 作者\n..."
}
```

**默认模板**: `*- {title} by {author}`

**自定义模板变量**:
- `{index}` - 序号
- `{title}` - 书名
- `{author}` - 作者  
- `{rating}` - 评分
- `{summary}` - 简介
- `{call_no}` - 索书号

## 性能优化建议

1. **合理设置top_k**: 避免返回过多结果影响性能
2. **使用评分过滤**: 通过min_rating减少不相关结果
3. **启用重排序**: enable_rerank=true可提升结果相关性
4. **批量查询**: 对多文本查询可考虑合并处理

## 使用示例

### Python requests调用

```python
import requests

# 文本检索
response = requests.post('http://localhost:8000/api/books/text-search', json={
    "query": "人工智能伦理",
    "top_k": 5,
    "response_format": "json"
})

data = response.json()
for book in data['results']:
    print(f"{book['title']} - {book['author']} (评分: {book['rating']})")

# 多查询检索
with open('analysis_report.md', 'r', encoding='utf-8') as f:
    markdown_text = f.read()

response = requests.post('http://localhost:8000/api/books/multi-query', json={
    "markdown_text": markdown_text,
    "per_query_top_k": 10,
    "final_top_k": 15,
    "enable_rerank": True
})

data = response.json()
print(f"找到 {len(data['results'])} 本相关书籍")
```

### JavaScript fetch调用

```javascript
// 文本检索
const response = await fetch('http://localhost:8000/api/books/text-search', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        query: "人工智能伦理",
        top_k: 5,
        response_format: "json"
    })
});

const data = await response.json();
data.results.forEach(book => {
    console.log(`${book.title} - ${book.author} (评分: ${book.rating})`);
});
```

## 启动服务

### 开发环境启动
```bash
cd f:/Github/Library-AI-demos/rss-fetcher
uvicorn scripts.api.book_retrieval_api:app --reload --port 8000
```

### 生产环境启动
```bash
uvicorn scripts.api.book_retrieval_api:app --host 0.0.0.0 --port 8000
```

### 测试API
```bash
python tests/test_book_vectorization/manual_test_api.py
```

## 依赖要求

```txt
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0
requests>=2.31.0
```

## 注意事项

1. **服务端口**: 默认使用8000端口，确保端口未被占用
2. **临时文件**: 多查询模式会创建临时Markdown文件，服务会自动清理
3. **内存使用**: 大量查询时注意内存使用情况
4. **并发限制**: 当前版本未实现并发控制，高并发时需自行处理
5. **数据完整性**: API返回的summary字段为完整内容，不进行截断

## 版本历史

- **v1.0.0** (2025-12-17): 初始版本，支持文本检索和多查询检索
- 修复摘要字段完整显示问题
- 完善API文档和使用示例