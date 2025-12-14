# 代码审查报告 (Code Review Report)
- **审查对象**: src/core/book_vectorization 模块
- **日期**: 2025-12-14
- **总体评分**: 7/10

## 1. 阻断性问题 (Blockers)
> 必须修复，否则不可合并。

- **位置**: `src/core/book_vectorization/database_reader.py:60`, `81`, `136-140`, `152-160`, `180-186`, `206-214`
  - **问题**: 多处 SQL 语句直接使用 f-string 拼接 `self.table`，一旦配置被篡改或被外部输入污染，就会触发 SQL 注入风险，违反 `@.rules/00_STANDARDS.md` 第 4 节关于安全与硬编码的要求。
  - **建议**: 限定允许访问的表名（白名单），并在构建 SQL 时通过参数化或 `sqlite3` 的 `execute` 接口安全地注入标识符；至少在初始化阶段对 `db_config['table']` 做严格校验。

- **位置**: `src/core/book_vectorization/vectorizer.py:225-233`（与配置 `config/book_vectorization.yaml:71-77` 不一致）
  - **问题**: 失败阈值被硬编码为 `3`，完全忽略了配置文件里的 `mode.max_retry_count=5`，导致达到 3 次失败就被标记为 `failed_final`，既违背了设计文档，也违反 `@.rules/00_STANDARDS.md` “拒绝硬编码” 的要求。
  - **建议**: 读取 `self.config['mode']['max_retry_count']`（并提供默认值），用它来判断是否进入 `failed_final`，同时将 `retry_count` 写回数据库，保证配置与行为一致。

## 2. 优化建议 (Nitpicks)
> 建议修改，提升质量。

1. **资源释放不安全** — `src/core/book_vectorization/vectorizer.py:70-104`
   - `self.db_reader.close()` 仅在成功路径执行，若 `_load_books` 或 `_vectorize_batch` 抛异常，SQLite 连接不会被关闭，数据库文件可能长期处于锁定状态。建议使用 `try/finally` 或实现上下文管理器确保连接总能释放。

2. **环境变量缺失时静默返回** — `src/core/book_vectorization/embedding_client.py:127-133`
   - `_resolve_env` 在环境变量未设置时仍返回 `None`，随后 OpenAI SDK 会在调用时抛出难以定位的异常。建议直接抛出 `ValueError` 并在日志中指明缺失的变量，满足 `00_STANDARDS` 3.2 对清晰错误提示的要求。

3. **向量 ID 生成不具备并发安全** — `src/core/book_vectorization/vector_store.py:72-101`
   - 依赖 `int(time.time())`（秒级）生成 ID，多本书同秒写入会产生重复 ID，Chroma 会拒绝插入。建议改用 `uuid.uuid4()` 或 `time.time_ns()`/自增序列来保证唯一性。

4. **SQLite 连接线程安全风险** — `src/core/book_vectorization/database_reader.py:38-41`
   - 连接在 `check_same_thread=False` 下复用，但类本身未加锁，若被多线程调用可能出现数据竞争。建议限制该类只在单线程场景使用或为连接/游标访问加锁。

5. **相似度换算忽略距离度量配置** — `src/core/book_vectorization/retriever.py:79-104` + `config/book_vectorization.yaml:11-16`
   - 结果统一用 `1 - distance` 转为“相似度”，但当 `distance_metric` 切到 `l2` 或 `ip` 时该公式不成立。建议根据 `vector_db.distance_metric` 选择正确换算或直接返回原始距离。

6. **测试覆盖缺口** — `tests/test_book_vectorization/` 仅包含 `test_filter.py` 和 `test_vectorizer.py`，缺少对 `database_reader.py`、`embedding_client.py`、`vector_store.py`、`retriever.py` 的单元测试，未满足 `00_STANDARDS` 3.3 对核心功能的覆盖要求。建议补齐这些模块的 mock 测试。

7. **评分解析缺乏容错** — `src/core/book_vectorization/filter.py:88-105`
   - `float(rating)` 没有捕获 `ValueError`，一旦评分字段为 `'N/A'` 或空字符串，整个过滤流程会异常中断。应增加 try/except 并把该书判定为未达标。

8. **配置漂移** — `config/book_vectorization.yaml:71-99`
   - `mode.incremental`、`performance.batch_commit_size`、`performance.enable_progress_bar` 等字段在代码中完全未使用，违背了“文档留痕”与“拒绝幻觉”的规范。建议实现相应功能或删除这些配置并更新文档。

9. 性能问题

1. **未使用批量嵌入API** - `embedding_client` 有 `get_embeddings_batch` 方法，但向量化器中未使用
2. **重复的数据库更新** - 每本书都单独调用 `update_embedding_status`，可考虑批量操作
3. **单线程向量化** - 完全可以并行化 Embedding API 调用
4. **ChromaDB 批量操作** - 有 `add_batch` 方法但未使用
5. **向量ID生成效率** - 每本书都单独生成ID，可考虑批量生成策略   

## 3. 安全与规范检查
- [x] 目录结构符合规范
- [x] 无敏感信息硬编码
- [x] 注释与日志为中文
