# 开发变更记录
- **日期**: 2025-12-14
- **对应设计文档**: [图书向量化预处理功能设计_20251213.md](../书目数据向量化/图书向量化预处理功能设计_20251213.md)

## 1. 变更摘要
- 新增 `scripts/retrieve_books.py`，提供可在命令行执行的图书向量检索工具，支持文本检索与分类检索两种模式。
- 支持从标准输入参数或文本文件加载查询语句，并提供评分过滤、结果格式化输出与错误校验。
- 为检索脚本补充 `tests/test_book_vectorization/test_retrieve_books_cli.py`，覆盖文本检索与分类检索两条核心路径。

## 2. 文件清单
- `scripts/retrieve_books.py`: **新增**，实现 CLI 检索逻辑及输出格式化。
- `tests/test_book_vectorization/test_retrieve_books_cli.py`: **新增**，包含 2 个测试用例覆盖文本与分类模式。
- `docs/changelog/20251214_vector_retrieval_cli.md`: **新增**，记录本次变更。

## 3. 测试结果
- [x] `pytest tests/test_book_vectorization/test_retrieve_books_cli.py -q`
