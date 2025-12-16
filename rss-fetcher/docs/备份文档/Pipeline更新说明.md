# Pipeline 更新说明

## 更新内容

已更新 `src/core/pipeline.py` 以适配重构后的双 Agent 架构。

## 主要变更

### 1. ArticleProcessor 初始化 (第370-372行)

**修改前:**
```python
# 初始化 LLM 处理器
llm_task_name = self.config.get("llm_analysis", {}).get("task_name", "subject_bibliography_analysis")
processor = ArticleProcessor(task_name=llm_task_name)
```

**修改后:**
```python
# 初始化 LLM 处理器 (双 Agent 架构)
processor = ArticleProcessor()
```

**原因:** 重构后的 `ArticleProcessor` 不再接受 `task_name` 参数,因为它内部使用了两个独立的 Agent,每个 Agent 都有自己的任务配置。

## 工作流程

### 运行 `python main.py --stage analyze` 时的执行流程:

```
1. 加载最新的 extract 文件
   ↓
2. 筛选需要分析的文章 (extract_status == "success" 且未处理过的)
   ↓
3. 对每篇文章执行双 Agent 分析:
   
   3.1 Agent 1: Filter (初筛)
       - 使用标题 + 前1000字符
       - 判断是否值得深度分析
       - 输出: {pass, reason, status}
       ↓
   3.2 如果通过初筛 (pass == true):
       Agent 2: Analyst (深度分析)
       - 使用全文 (截断至8000字符)
       - 评分、分类、提取信息
       - 输出: {score, primary_dimension, summary, thematic_essence, tags, mentioned_books}
       ↓
   3.3 如果未通过初筛 (pass == false):
       直接返回,标记为 "已拒绝"
   ↓
4. 保存结果到同一个文件
```

## 输出字段变化

### 新增字段:
- `filter_pass`: 是否通过初筛 (boolean)
- `filter_reason`: 初筛理由 (string)
- `filter_status`: 初筛状态 ("成功"/"失败")
- `llm_thematic_essence`: 母题本质,用于向量检索 (string, ~300字)

### 移除字段:
- `llm_decision`: 已由 `filter_pass` 替代
- `llm_keywords`: 简化字段
- `llm_book_clues`: 简化字段
- `llm_raw_response`: 简化字段

### llm_status 的可能值:
- `"成功"`: 完整流程成功(通过初筛 + 深度分析成功)
- `"已拒绝"`: 未通过初筛
- `"初筛失败"`: Agent 1 调用失败
- `"分析失败"`: Agent 2 调用失败
- `"跳过"`: 缺少必要字段

## 配置说明

### config/llm.yaml

双 Agent 使用的任务配置:

```yaml
article_filter:
  provider_type: text-small  # 使用小模型进行初筛
  temperature: 0.3
  prompt:
    type: md
    source: "prompts/article_filter.md"

article_analysis:
  provider_type: text  # 使用大模型进行深度分析
  temperature: 0.5
  prompt:
    type: md
    source: "prompts/article_analysis.md"
```

### config/subject_bibliography.yaml

`llm_analysis.task_name` 字段已废弃,保留仅用于向后兼容。

## 使用方式

### 完全不变!

```bash
# 运行完整流程
python main.py

# 仅运行分析阶段
python main.py --stage analyze

# 指定输入文件
python main.py --stage analyze --input runtime/outputs/2025-12.xlsx
```

## 优势

1. **成本优化**: 初筛使用小模型 (gpt-4o-mini),深度分析使用大模型 (gemini-2.5-pro)
2. **效率提升**: 低价值文章在初筛阶段就被过滤,不会浪费大模型 token
3. **质量保证**: 通过初筛的文章才会进行深度分析,确保分析质量
4. **可观测性**: Langfuse 会分别记录两个 Agent 的调用,便于监控和调试

## 注意事项

1. **向后兼容**: 旧的 `network_article_initial_review` 任务配置保留,但不再使用
2. **自动升级**: 无需修改命令行参数,运行方式完全不变
3. **增量处理**: 已处理的文章不会重复分析,支持断点续传
