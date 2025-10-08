# L3 模块快速开始指南

## 目标概述

实现 L3 语境线索层的第一个 RAG 任务：**基于实体标签的知识库检索**。

## 核心需求要点

### 输入数据
- 从 `runtime/outputs/*.json` 读取 L2 阶段的实体数据
- 提取每个实体的三个关键字段：
  - `label`: 实体标签（如"欧阳予倩"）
  - `type`: 实体类型（如"person"）  
  - `context_hint`: 上下文提示（包含元数据信息）

### 处理逻辑
1. **跳过检查**: 判断实体是否已执行过当前任务
2. **API调用**: 将三个字段作为参数调用 Dify 知识库接口
3. **状态解析**: 解析响应为四种状态之一
4. **结果存储**: 按照 L2 格式存储到实体节点

### 响应状态处理
| 状态 | 描述 | 存储字段 |
|------|------|----------|
| `success` | 成功检索到相关信息 | `content` + `meta` |
| `not_found` | 知识库中没有相关信息 | `content: null` + `meta` |
| `not_relevant` | 回答与实体不相关 | `content` + `meta` |
| `error` | 网络错误/API异常 | `content: null` + `meta` |

### 存储格式示例
```json
{
  "l3_rag_entity_label_retrieval": {
    "content": "检索到的知识内容...", 
    "status": "success",
    "meta": {
      "executed_at": "2025-10-07T10:30:00+08:00",
      "task_type": "entity_label_retrieval",
      "dify_response_id": "resp_123",
      "error": null
    }
  }
}
```

## 文件结构设计

```
src/core/l3_context_interpretation/
├── __init__.py
├── main.py              # 主入口，任务调度
├── dify_client.py       # Dify API 客户端封装  
├── rag_processor.py     # RAG 检索流程协调器
├── entity_extractor.py  # 实体字段提取器
└── result_formatter.py  # 结果格式化器
```

## 配置需求

### settings.yaml 新增配置
```yaml
l3_context_interpretation:
  enabled: true
  rag_tasks:
    entity_label_retrieval:
      enabled: true
      dify_key: "env:DIFY_ENTITY_RETRIEVAL_KEY"
      dify_base_url: "https://api.dify.ai/v1"
      rate_limit_ms: 1000
```

### 环境变量
```bash
# .env 文件中添加
DIFY_ENTITY_RETRIEVAL_KEY=app-your-dify-key-here
```

## 核心接口设计

### 1. DifyClient 
```python
class DifyClient:
    def query_knowledge_base(self, label: str, entity_type: str, context_hint: str) -> DifyResponse
```

### 2. EntityExtractor
```python  
class EntityExtractor:
    def extract_entity_fields(self, entity: dict, row_id: str, metadata: dict) -> EntityFields
    def should_skip_entity(self, entity: dict, task_name: str) -> bool
```

### 3. RagProcessor  
```python
class RagProcessor:
    def process_entity_retrieval(self, entity: dict, row_id: str) -> RagResult
```

### 4. ResultFormatter
```python
class ResultFormatter:
    def format_rag_result(self, dify_response: DifyResponse, task_name: str) -> dict
```

## 集成点

### main.py 任务解析扩展
```python
# 新增 L3 任务别名
_ALIAS_TO_TARGET = {
    # ... 现有映射 ...
    "l3": ("l3", "context_interpretation"),
    "rag": ("l3", "rag"),
}

# 新增 L3 执行逻辑
if l3_enabled:
    from src.core.l3_context_interpretation.main import run_l3
    run_l3(excel_path=None, images_dir=None, limit=args.limit, tasks=l3_phases)
```

### 共享工具复用
- `src/utils/llm_api.py`: 配置加载、环境变量解析
- `src/utils/logger.py`: 日志记录
- `src/utils/json_repair.py`: JSON 解析容错
- `src/utils/excel_io.py`: 文件路径管理

## 关键实现要点

### 1. 实体字段提取
```python
# context_hint 构建格式要与现有样例完全一致
context_hint = f"""[元数据]
- 编号: {row_id}
- 题名: {metadata.get('title', '')}
- 说明: {metadata.get('desc', '')}
- 相关人物: {metadata.get('persons', '')}
- 所属专题: {metadata.get('topic', '')}"""
```

### 2. 跳过逻辑
```python
# 检查实体是否已有 l3_rag_entity_label_retrieval 字段且包含 executed_at
def should_skip_entity(entity: dict, task_name: str) -> bool:
    field_name = f"l3_rag_{task_name}"
    if field_name in entity:
        meta = entity[field_name].get("meta", {})
        return bool(meta.get("executed_at"))
    return False
```

### 3. Dify API 调用
```python
# 参数组装：三个字段原样传递
query_text = f"label: {label}\ntype: {entity_type}\ncontext_hint: {context_hint}"

payload = {
    "inputs": {},
    "query": query_text,
    "response_mode": "blocking", 
    "conversation_id": "",
    "user": "l3_rag_user"
}
```

### 4. 状态解析关键词
```python
# 根据响应内容判断状态
no_info_keywords = ["没有检索到", "未找到相关", "知识库中没有", "无法找到"]
irrelevant_keywords = ["不相关", "无关", "不匹配", "无法确定相关性"] 
```

## 测试策略

### Mock 测试
- 模拟 Dify API 的四种响应状态
- 测试实体字段提取的各种边界情况
- 验证跳过逻辑的正确性

### 集成测试  
- 使用真实的 JSON 文件进行端到端测试
- 验证与现有流水线的集成
- 测试配置加载和环境变量解析

## 命令行使用

```bash
# 执行 L3 RAG 任务
python main.py --tasks "l3:rag"

# 执行完整流水线（L0→L1→L2→L3）
python main.py

# 只执行 L3 模块
python main.py --tasks "l3"
```

## 下一步行动

1. ✅ **架构设计完成** - 已完成设计文档
2. 🔄 **创建基础文件结构** - 创建模块目录和初始文件
3. 🔄 **实现 DifyClient** - 基于 dify.py 样例完善 API 客户端
4. 🔄 **实现实体处理逻辑** - 字段提取、跳过检查、结果存储
5. 🔄 **集成到主流水线** - 修改 main.py 支持 L3 任务
6. 🔄 **测试验证** - 单元测试和集成测试

---

**创建时间**: 2025-10-07  
**文档类型**: 快速开始指南  
**状态**: Ready for Implementation