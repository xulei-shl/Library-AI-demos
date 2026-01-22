# 文学图书检索 API

基于向量+BM25的混合检索服务，支持结构化过滤条件。

## 功能特性

- **混合检索**：向量语义检索 + BM25全文检索
- **结构化过滤**：支持MUST/SHOULD/MUST_NOT三种操作符
- **RRF融合**：自动合并多路检索结果并去重
- **BM25随机性**：增加推荐多样性
- **可选重排序**：支持CrossEncoder精细排序
- **多种响应模式**：basic/standard/rich三种详细程度

## 快速开始

### 安装依赖

```bash
cd f:\Github\Library-AI-demos\book-echoes
pip install -e .
```

### 启动服务

```bash
cd src/core/literature_fm/literaturefm-api
uvicorn main:app --reload --port 8001
```

### 访问文档

启动后访问 http://localhost:8001/docs 查看Swagger文档。

## API接口

### 1. 单主题检索

**端点**：`POST /api/literary/search`

**请求示例**：
```json
{
  "filter_conditions": [
    {"field": "spatial_atmosphere", "values": ["荒野自然"], "operator": "SHOULD"},
    {"field": "reading_load", "values": ["酣畅易读"], "operator": "MUST"}
  ],
  "search_keywords": ["荒野", "星空", "海洋"],
  "synthetic_query": "这本书非常适合那些被信息过载压垮的读者...",
  "top_k": 30,
  "response_detail": "standard",
  "enable_rerank": false,
  "bm25_randomness": 0.15
}
```

### 2. 批量主题检索

**端点**：`POST /api/literary/batch-search`

**请求示例**：
```json
{
  "queries": [
    {
      "filter_conditions": [...],
      "search_keywords": [...],
      "synthetic_query": "..."
    }
  ],
  "top_k": 30,
  "response_detail": "standard",
  "enable_rerank": false
}
```

## 参数说明

### 过滤条件字段

| 字段 | 说明 | 候选值 |
|------|------|--------|
| `reading_context` | 阅读情境 | 暮色四合时、深夜独处、午后慵懒... |
| `reading_load` | 阅读体感 | 酣畅易读、需正襟危坐、细水长流... |
| `text_texture` | 文本质感 | 诗意流动、冷峻克制、絮语呢喃... |
| `spatial_atmosphere` | 时空氛围 | 都市孤独、乡土温情、异域漂泊... |
| `emotional_tone` | 情绪基调 | 忧郁沉思、温暖治愈、激昂振奋... |

### 操作符说明

| 操作符 | 含义 | 实现方式 |
|--------|------|----------|
| `MUST` | 必须匹配 | Pre-filter（向量检索前） |
| `MUST_NOT` | 必须排除 | Post-filter（检索后过滤） |
| `SHOULD` | 优选匹配 | 多路检索合并 |

### 响应详细程度

| 模式 | 包含字段 |
|------|----------|
| `basic` | 书籍基础信息、分数 |
| `standard` | + tags_json、过滤条件 |
| `rich` | + 检索统计信息 |

## 测试

```bash
cd tests
python manual_test.py
```

## 配置

API复用 `config/literature_fm_vector.yaml` 配置文件。

## 目录结构

```
literaturefm-api/
├── main.py                 # FastAPI应用入口
├── config.py               # 配置加载
├── models/
│   ├── requests.py         # 请求模型
│   └── responses.py        # 响应模型
├── services/
│   └── search_service.py   # 检索服务
└── tests/
    └── manual_test.py      # 测试脚本
```

## 依赖组件

API复用文学检索模块的核心组件：

- `HybridVectorSearcher` - 增强向量检索器
- `BM25Searcher` - BM25全文检索器
- `RRFFusion` - RRF融合器
- `VectorSearcher` - 基础向量检索器
- `CrossEncoderReranker` - 重排序器

## 版本

1.0.0
