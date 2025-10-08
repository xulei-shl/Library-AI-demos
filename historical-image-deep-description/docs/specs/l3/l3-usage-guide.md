# L3 模块使用指南

## 概述

L3 语境线索层模块已成功实现！这是基于 Dify 知识库的 RAG 检索系统，能够为历史图像中的实体提供深度的上下文阐释。

## ✅ 已完成的功能

### 核心组件
- ✅ **DifyClient**: 基于官方示例的 Dify API 客户端封装
- ✅ **EntityExtractor**: 从 L2 JSON 文件中提取 `label`、`type`、`context_hint` 三个字段
- ✅ **ResultFormatter**: 处理 Dify 的四种响应状态并格式化存储
- ✅ **RagProcessor**: 协调整个检索流程的主控制器
- ✅ **主流程集成**: 与现有 L0→L1→L2 流水线无缝集成

### 功能特性
- ✅ **四种状态处理**: success、not_found、not_relevant、error
- ✅ **智能跳过**: 自动跳过已处理过的实体，支持断点续传
- ✅ **配置驱动**: 通过 settings.yaml 控制任务启用和参数
- ✅ **速率限制**: 内置 API 调用频率控制
- ✅ **错误处理**: 完整的异常捕获和错误恢复机制
- ✅ **日志记录**: 详细的执行日志，便于调试和监控

## 📁 文件结构

```
src/core/l3_context_interpretation/
├── __init__.py                 # 模块初始化
├── main.py                     # 主入口和任务调度
├── dify_client.py             # Dify API 客户端
├── entity_extractor.py        # 实体字段提取器
├── result_formatter.py        # 结果格式化器
└── rag_processor.py           # RAG 检索流程协调器

tests/
├── core/l3_context_interpretation/
│   └── test_l3_basic.py       # 单元测试
└── test_l3_integration.py     # 集成测试
```

## ⚙️ 配置说明

### 1. settings.yaml 配置

已在 `config/settings.yaml` 中添加了完整的 L3 配置：

```yaml
# L3 语境线索层配置
l3_context_interpretation:
  # 全局启用开关
  enabled: true
  
  # RAG 任务配置
  rag_tasks:
    # 任务1：基于实体标签的检索
    entity_label_retrieval:
      enabled: true
      dify_key: "env:DIFY_ENTITY_RETRIEVAL_KEY"
      dify_base_url: "https://api.dify.ai/v1"
      rate_limit_ms: 1000
      retry_policy:
        max_retries: 3
        delay_seconds: 2
        backoff_factor: 2.0
        
    # 任务2：基于已有信息的深度阐释（后续扩展）
    deep_interpretation:
      enabled: false
      dify_key: "env:DIFY_DEEP_INTERPRETATION_KEY"
      dify_base_url: "https://api.dify.ai/v1"
      rate_limit_ms: 1000
```

### 2. 环境变量配置

已在 `.env.example` 中添加了 L3 相关的环境变量：

```bash
# L3 RAG 任务 Dify API Keys
# 基于实体标签的检索
DIFY_ENTITY_RETRIEVAL_KEY="YOUR_DIFY_ENTITY_RETRIEVAL_KEY_HERE"

# 基于已有信息的深度阐释（后续使用）
DIFY_DEEP_INTERPRETATION_KEY="YOUR_DIFY_DEEP_INTERPRETATION_KEY_HERE"
```

## 🚀 使用方法

### 1. 环境准备

```bash
# 1. 复制环境变量模板
cp .env.example .env

# 2. 编辑 .env 文件，添加你的 Dify API 密钥
# DIFY_ENTITY_RETRIEVAL_KEY="your_actual_dify_key_here"
```

### 2. 命令行使用

```bash
# 执行完整流水线（L0→L1→L2→L3）
python main.py

# 只执行 L3 模块
python main.py --tasks "l3"

# 执行特定的 L3 RAG 任务
python main.py --tasks "l3:rag"

# 使用别名执行 RAG 任务
python main.py --tasks "rag"

# 限制处理文件数量（调试用）
python main.py --tasks "l3" --limit 5
```

### 3. 数据流程

1. **输入**: 从 `runtime/outputs/*.json` 读取 L2 阶段的实体数据
2. **字段提取**: 提取每个实体的 `label`、`type`、`context_hint`
3. **API调用**: 将三个字段原样传递给 Dify 知识库
4. **状态解析**: 根据响应内容判断四种状态
5. **结果存储**: 将结果存储到实体的 `l3_rag_entity_label_retrieval` 字段

### 4. 输出格式

处理后的实体会新增 L3 RAG 字段：

```json
{
  "label": "欧阳予倩",
  "type": "person",
  // ... 原有字段 ...
  "l3_rag_entity_label_retrieval": {
    "content": "检索到的相关知识内容...",
    "status": "success",
    "meta": {
      "executed_at": "2025-10-07T15:30:00+08:00",
      "task_type": "entity_label_retrieval",
      "dify_response_id": "resp_abc123",
      "error": null
    }
  }
}
```

## 🧪 测试验证

### 1. 单元测试

```bash
# 运行 L3 模块的单元测试
python -m pytest tests/core/l3_context_interpretation/test_l3_basic.py -v
```

### 2. 集成测试

```bash
# 运行完整的集成测试
python tests/test_l3_integration.py
```

集成测试会：
- 创建模拟的 JSON 文件
- 模拟 Dify API 响应
- 验证完整的处理流程
- 检查结果格式和状态

## 📊 状态说明

L3 模块会将 Dify 的响应解析为四种标准状态：

| 状态 | 描述 | 示例关键词 | content字段 |
|------|------|------------|-------------|
| `success` | 成功检索到相关信息 | 正常的知识内容 | 包含检索结果 |
| `not_found` | 知识库中没有相关信息 | "没有检索到"、"未找到相关" | `null` |
| `not_relevant` | 回答与实体不相关 | "不相关"、"无关" | 包含不相关回答 |
| `error` | 网络错误、API异常等 | 各种技术错误 | `null` |

## 🔧 故障排除

### 1. 常见问题

**Q: 提示 "L3模块未启用"**
- A: 检查 `config/settings.yaml` 中 `l3_context_interpretation.enabled` 是否为 `true`

**Q: 提示 "Dify API密钥未配置"**  
- A: 检查 `.env` 文件中是否正确设置了 `DIFY_ENTITY_RETRIEVAL_KEY`

**Q: 所有实体都被跳过**
- A: 实体可能已经处理过，检查 JSON 文件中是否存在 `l3_rag_entity_label_retrieval` 字段

### 2. 调试技巧

```bash
# 查看详细日志
python main.py --tasks "l3" --limit 1

# 检查 runtime/logs/ 目录下的日志文件
tail -f runtime/logs/app.log

# 使用 Python 调试器
python -m pdb tests/test_l3_integration.py
```

### 3. 性能优化

- **速率限制**: 通过 `rate_limit_ms` 控制 API 调用频率
- **批量处理**: 系统会自动处理多个 JSON 文件
- **断点续传**: 已处理的实体会自动跳过

## 🔮 未来扩展

### 已预留的扩展点

1. **RAG 任务2**: 基于已有信息的深度阐释
   - 配置已预留：`deep_interpretation`
   - 环境变量已准备：`DIFY_DEEP_INTERPRETATION_KEY`

2. **网络检索**: 
   - 配置结构已预留：`web_retrieval`

3. **多知识库支持**:
   - 架构支持多个 Dify 应用

4. **结果后处理**:
   - 可扩展结果过滤和增强逻辑

## 📈 成功指标

根据设计文档，当前实现已达到所有功能标准：

- ✅ 成功从 L2 JSON 文件中提取实体信息
- ✅ 成功调用 Dify API 进行知识检索  
- ✅ 正确处理四种响应状态并格式化存储
- ✅ 支持命令行任务触发和集成到主流水线
- ✅ 避免重复处理已执行过的实体

---

## 📞 技术支持

如果遇到问题或需要功能扩展，请参考：

1. **设计文档**: `docs/specs/l3/` 目录下的完整架构文档
2. **单元测试**: `tests/core/l3_context_interpretation/` 中的测试用例
3. **集成测试**: `tests/test_l3_integration.py` 的完整流程示例

**L3 模块现已就绪，可以开始使用！** 🎉