## 背景与目标

图书向量检索 CLI 已通过 `scripts/retrieve_books.py` 支撑多种模式。当前需求是在 **不改动既有检索流程** 的前提下，新增可被 Next.js 等本地应用调用的 API 模块，获取“文本相似度检索”及“多子查询检索”结果。本方案承担接口设计与模块拆分职责，为后续开发提供约束。

## 模块结构

```
scripts/
  api/
    book_retrieval_api.py        # FastAPI 应用与路由
    services/
      __init__.py
      retriever_service.py       # 包装 BookRetriever 和输出策略
```

- `book_retrieval_api.py`：负责 HTTP 端点、请求体验证、统一响应模型。
- `retriever_service.py`：集中管理 `ConfigManager`、`BookRetriever`、`OutputFormatter`，对外暴露 `text_search()` 与 `multi_query_search()`，确保逻辑复用且便于注入。
- 其他依赖（`build_query_package_from_md` 等）直接引用现有实现，不触碰 `scripts/retrieve_books.py`。

## 接口定义

### 1. 文本相似度检索
- **URL**：`POST /api/books/text-search`
- **请求体**
  ```json
  {
    "query": "string (必填)",
    "top_k": 5,
    "min_rating": 7.5,
    "response_format": "json",
    "plain_text_template": "string"
  }
  ```
- **返回**：`results` 列表、`metadata`（模式、top_k、min_rating、response_format），以及当 `response_format=plain_text` 时的 `context_plain_text`。
- **流程**：直接调用 `BookRetriever.search_by_text`；当缺省 `top_k/min_rating` 时沿用配置默认值；异常统一转成 HTTP 4xx/5xx。

### 2. 多子查询检索
- **URL**：`POST /api/books/multi-query`
- **请求体**
  ```json
  {
    "markdown_text": "string (必填)",
    "per_query_top_k": 15,
    "final_top_k": 10,
    "min_rating": 8,
    "enable_rerank": true,
    "disable_exact_match": false,
    "response_format": "json",
    "plain_text_template": "string"
  }
  ```
- **返回**：包含融合结果、`query_package_origin`、`enable_rerank`、`disable_exact_match`、`metadata.response_format` 等字段，当 `response_format=plain_text` 时追加 `context_plain_text`，结构与 CLI 输出一致（去掉交互提示、Excel 导出逻辑）。

## LLM 对接约束

- **纯文本约定**：`response_format` 支持 `json`（默认）与 `plain_text`。当调用方传入 `plain_text` 时，API 直接返回 `Content-Type: text/plain` 的整段文本，或在 JSON 中附带 `context_plain_text` 字段（由 `plain_text_template` 描述格式，例如“序号. 书名 - 亮点”）。模板缺省时，服务端内置 `*- {title} by {author}` 的兜底模式。
- **OpenAI 兼容**：API 不直接调用 LLM，而是保证 `context_plain_text` 只包含可被 OpenAI 兼容接口（如 Vercel AI SDK、OpenAI SDK、自建兼容实现）直接拼接到 `messages[].content` 的纯文本；下游可使用自定义 `base_url`、`api_key`、`model` 等参数驱动 LLM。
- **配置透传**：请求体允许附带可选字段
  ```json
  {
    "llm_hint": {
      "provider": "openai-compatible",
      "base_url_env": "AIBOT_LLM_BASE_URL",
      "api_key_env": "AIBOT_LLM_API_KEY",
      "model_env": "AIBOT_LLM_MODEL",
      "suggested_temperature": 0.3
    }
  }
  ```
  `llm_hint` 不会在服务端使用，仅写入响应 `metadata.llm_hint`，帮助 Next.js 端根据 profile 选择正确的环境变量或 UI 预设，实现 baseURL/API Key/Model 名称的自定义。

## 多子查询文本处理策略

原流程 `build_query_package_from_md` 仅接受 Markdown **文件路径**。为在“不改动原代码”前提下支持 API 传入文本：

1. API 接到 `markdown_text` 后，在 `retriever_service.py` 内创建只读临时文件（`tempfile.NamedTemporaryFile`）。  
2. 将文本内容写入该文件并刷新到磁盘。  
3. 调用 `build_query_package_from_md(temp_path, ...)` 与 CLI 完全一致的参数。  
4. 完成后立即删除临时文件，避免磁盘残留。  

此方式保证核心逻辑透明复用，且圈复杂度受控。

## 输出与日志

- API 默认仅返回 JSON，不强制触发 `OutputFormatter` 落盘；若后续需要保存，可在请求中加入布尔开关（默认 `false`），由 `retriever_service` 决定是否调用 `_save_results_if_enabled`。
- 继续复用 `get_logger`，在服务启动时初始化单例记录器，统一记录请求参数概要与异常堆栈。

## 运行方式

1. 安装 FastAPI/uvicorn 依赖（若尚未安装），写入 `requirements`。
2. 本地启动 `uvicorn scripts.api.book_retrieval_api:app --reload`。
3. Next.js Demo 通过 `fetch`/`axios` 调用上述端点即可。

## 风险与约束

- 临时文件写入需捕获 IO 异常，并确保 `finally` 中删除。
- API 仅面向本地实验，无鉴权；若未来扩展，需要补充鉴权与速率限制。
- 多子查询请求体包含大段文本，应设置 `uvicorn` 与 FastAPI 的 `max_body_size`（或反向代理配置）以避免 413。
