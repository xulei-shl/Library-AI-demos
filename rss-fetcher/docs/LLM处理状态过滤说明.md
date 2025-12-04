# LLM处理状态过滤功能说明

## 概述

为了避免重复调用LLM（节省成本和时间），新增了LLM处理状态跟踪和过滤功能。系统现在可以识别哪些文章已经处理过，避免重复处理。

## 新增功能

### 1. LLM状态跟踪 (`llm_status`)

在Excel文件中新增 `llm_status` 列，用于跟踪LLM处理状态：

- **"成功"**: LLM调用成功且JSON解析成功
- **"JSON解析错误"**: LLM返回非JSON格式响应
- **"LLM调用错误"**: LLM调用过程中出现异常
- **"跳过"**: 缺少full_text和content字段，无需LLM处理

### 2. 错误信息处理

- **成功状态**: `llm_raw_response` 字段包含LLM返回的有效JSON响应
- **错误状态**: `llm_raw_response` 字段包含错误信息原文（原样填入）

### 3. 重复处理过滤

在保存分析结果时，系统会：
1. 检查每篇文章的 `llm_raw_response` 字段是否有值
2. 检查 `llm_status` 字段是否有值
3. 如果任一字段有值，认为该文章已处理，跳过LLM分析
4. 只处理那些没有LLM响应记录的新文章

## 实现细节

### 修改的文件

1. **`src/core/article_analyzer.py`**
   - 修改 `analyze_article()` 方法，新增状态跟踪
   - 根据处理结果设置不同的 `llm_status` 值
   - 错误信息原样填入 `llm_raw_response` 字段

2. **`src/core/storage.py`**
   - 修改 `save_analyze_results()` 方法，新增 `skip_processed` 参数
   - 实现过滤逻辑，检查已处理文章
   - 更新Excel列定义，包含 `llm_status` 字段

### 使用方法

#### 自动启用（推荐）

默认情况下，过滤功能已启用，无需修改代码：

```python
# 过滤已处理数据（默认行为）
output_file = self.storage.save_analyze_results(articles, input_file)
```

#### 禁用过滤

如果需要重新处理所有文章（不推荐，仅用于特殊情况）：

```python
# 跳过过滤，处理所有文章
output_file = self.storage.save_analyze_results(articles, input_file, skip_processed=False)
```

## Excel文件结构

### 阶段3 Excel列顺序

| 列名 | 描述 |
|------|------|
| source | 文章来源 |
| title | 文章标题 |
| article_date | 文章日期 |
| published_date | 发布日期 |
| link | 文章链接 |
| fetch_date | 抓取日期 |
| summary | 摘要 |
| extract_status | 提取状态 |
| extract_error | 提取错误信息 |
| content | 内容 |
| full_text | 全文 |
| **llm_status** | **LLM处理状态** |
| llm_decision | LLM决策 |
| llm_score | LLM评分 |
| llm_reason | LLM理由 |
| llm_summary | LLM摘要 |
| llm_tags | LLM标签 |
| llm_keywords | LLM关键词 |
| llm_primary_dimension | LLM主要维度 |
| llm_mentioned_books | LLM提及的书籍 |
| llm_book_clues | LLM书籍线索 |
| llm_raw_response | LLM原始响应 |

## 状态示例

### 成功处理
```
llm_status: "成功"
llm_raw_response: {"decision": true, "score": 85, "reason": "...", ...}
```

### JSON解析错误
```
llm_status: "JSON解析错误"  
llm_raw_response: "Invalid JSON response from LLM"
```

### LLM调用错误
```
llm_status: "LLM调用错误"
llm_raw_response: "Connection timeout: The request took too long"
```

### 跳过处理
```
llm_status: "跳过"
llm_raw_response: "缺少 full_text 和 content 字段"
```

## 优势

1. **节省成本**: 避免重复调用LLM API
2. **节省时间**: 跳过已处理文章，提高处理效率
3. **状态透明**: 清晰标识每篇文章的处理状态
4. **错误追踪**: 详细记录错误信息，便于问题排查
5. **向后兼容**: 不影响现有功能，自动检测已处理数据

## 修复的问题

### 1. 过滤逻辑优化
- **问题**: 原有过滤逻辑在storage层面，过滤时已经执行了LLM调用
- **解决**: 在pipeline层面添加预过滤，只对未处理文章执行LLM调用
- **效果**: 真正避免重复调用LLM

### 2. 结果保存完善
- **问题**: 已处理文章的结果没有正确保存到Excel
- **解决**: 优化存储逻辑，确保处理结果正确更新到现有数据
- **效果**: Excel文件包含完整的处理状态和结果

## 注意事项

1. **数据完整性**: 确保 `llm_raw_response` 字段不为空才认为已处理
2. **手动干预**: 如需强制重新处理某篇文章，可清空其 `llm_raw_response` 字段
3. **状态一致性**: `llm_status` 和 `llm_raw_response` 应同时存在和更新
4. **版本兼容**: 旧版Excel文件会自动添加 `llm_status` 列，值为空

## 监控建议

建议定期检查以下指标：
- 已成功处理文章数量
- JSON解析错误比例
- LLM调用错误比例  
- 跳过处理文章比例

通过 `llm_status` 字段可以方便地进行数据统计和分析。