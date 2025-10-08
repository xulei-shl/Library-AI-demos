# L3 语境线索层架构设计文档

## 状态：Proposal

## 目标摘要

设计并实现 L3 语境线索层模块，通过 RAG 知识库检索和网络检索两大功能，为历史图像提供深度上下文阐释。该模块以 L2 阶段锚定的实体为"钥匙"，启动检索流程，结合本地语料库的相关片段，生成高质量的历史与艺术价值阐释。

## 核心需求分析

### 任务触发机制
- 支持命令行参数触发：`python main.py --tasks "l3:rag"` 或 `python main.py --tasks "l3:retrieval"`
- 默认顺序执行：`python main.py` 从 L0→L1→L2→L3 完整流水线
- 与现有 L0、L1、L2 模块保持一致的任务调度机制

### RAG 任务分类
1. **基于实体标签的知识检索**（当前第一阶段开发目标）
   - 基于实体的 `label`、`type`、`context_hint` 字段
   - 调用 Dify 知识库检索接口
   - 处理四种响应状态：无相关信息、回答不相关、正确返回、异常错误

2. **基于已有信息的深度阐释**（后续扩展）
   - 整合所有已知信息进行综合分析
   - 生成深度历史文化阐释

### 核心架构原则
- **高内聚低耦合**：单个 Python 文件保持简洁，职责明确
- **可配置性**：通过 `settings.yaml` 控制任务启用状态和参数
- **可扩展性**：为后续 RAG 任务2和网络检索预留架构空间
- **共享复用**：最大化利用 `/src/utils` 中的现有工具

## 详细架构设计

### 目录结构
```
src/core/l3_context_interpretation/
├── __init__.py
├── main.py                      # 主入口，任务调度
├── rag_processor.py            # RAG 检索处理器
├── dify_client.py              # Dify API 客户端
├── entity_extractor.py         # 实体信息提取器
├── result_formatter.py         # 结果格式化器
└── config_manager.py           # 配置管理器
```

### 核心组件设计

#### 1. DifyClient（dify_client.py）
```python
class DifyClient:
    """Dify API 客户端，负责与 Dify 知识库交互"""
    
    def __init__(self, api_key: str, base_url: str)
    def query_knowledge_base(self, query: str, conversation_id: str = "") -> DifyResponse
    def _handle_response(self, response: dict) -> DifyResponse
    def _parse_error_status(self, response: dict) -> ResponseStatus
```

**职责：**
- 封装 Dify API 调用逻辑
- 处理 HTTP 请求/响应
- 解析响应状态（成功/失败/无相关/异常）
- 提供统一的错误处理机制

#### 2. EntityExtractor（entity_extractor.py）
```python
class EntityExtractor:
    """实体信息提取器，从 JSON 文件中提取目标字段"""
    
    def extract_entity_fields(self, entity: dict) -> EntityFields
    def _build_context_hint(self, row_id: str, metadata: dict) -> str
    def _validate_entity_eligibility(self, entity: dict) -> bool
```

**职责：**
- 从 L2 阶段的 JSON 输出中提取实体信息
- 组装 `label`、`type`、`context_hint` 三个关键字段
- 验证实体是否已执行过当前任务（避免重复处理）

#### 3. RagProcessor（rag_processor.py）
```python
class RagProcessor:
    """RAG 检索处理器，协调整个检索流程"""
    
    def __init__(self, settings: dict, dify_client: DifyClient)
    def process_entity_retrieval(self, entity: dict, row_id: str) -> RagResult
    def _should_skip_entity(self, entity: dict) -> bool
    def _update_entity_with_result(self, entity: dict, result: RagResult) -> None
```

**职责：**
- 协调实体提取、Dify 查询、结果格式化的完整流程
- 控制任务执行状态和跳过逻辑
- 将检索结果写入实体节点的元数据

#### 4. ResultFormatter（result_formatter.py）
```python
class ResultFormatter:
    """结果格式化器，将 Dify 响应转换为标准存储格式"""
    
    def format_rag_result(self, dify_response: DifyResponse, task_type: str) -> dict
    def _generate_metadata(self, status: str, error: str = None) -> dict
    def _extract_content_from_response(self, response: DifyResponse) -> str
```

**职责：**
- 将 Dify 响应格式化为与 L2 一致的存储结构
- 生成执行元数据（时间戳、状态、错误信息等）
- 确保存储格式的一致性

#### 5. ConfigManager（config_manager.py）
```python
class ConfigManager:
    """配置管理器，处理 L3 相关配置"""
    
    def __init__(self, settings: dict)
    def get_dify_config(self, task_type: str) -> DifyConfig
    def is_task_enabled(self, task_type: str) -> bool
    def get_output_settings(self) -> OutputConfig
```

**职责：**
- 从全局配置中提取 L3 相关设置
- 管理不同 RAG 任务的 Dify 密钥配置
- 提供配置验证和默认值处理

### 配置设计（settings.yaml 扩展）

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
      
    # 任务2：基于已有信息的深度阐释（后续扩展）
    deep_interpretation:
      enabled: false
      dify_key: "env:DIFY_DEEP_INTERPRETATION_KEY"
      dify_base_url: "https://api.dify.ai/v1"
  
  # 网络检索配置（后续扩展）
  web_retrieval:
    enabled: false
    
  # 输出配置
  output:
    # 是否启用结果缓存
    enable_caching: true
    # 结果保存到实体节点的字段前缀
    result_field_prefix: "l3_rag"
```

### 数据流设计

#### 输入数据格式
从 `runtime/outputs/*.json` 读取的实体节点：
```json
{
  "label": "欧阳予倩",
  "type": "person", 
  "context_hint": "[元数据]\n- 编号: 2202_001\n- 题名: 话剧《日出》...",
  "metadata": {},
  "wikidata": {...},
  "shl_data": {...}
}
```

#### 输出数据格式
处理后的实体节点增加 L3 相关字段：
```json
{
  "label": "欧阳予倩",
  "type": "person",
  // ... 原有字段 ...
  "l3_rag_entity_retrieval": {
    "content": "检索到的相关知识内容",
    "status": "success", // success|not_found|not_relevant|error
    "meta": {
      "executed_at": "2025-10-07T10:30:00+08:00",
      "task_type": "entity_label_retrieval",
      "dify_response_id": "resp_abc123",
      "error": null
    }
  }
}
```

### 错误处理与状态管理

#### 响应状态定义
- **success**: 成功检索到相关信息
- **not_found**: 知识库中没有检索到相关信息
- **not_relevant**: 大模型判断回答与实体不相关
- **error**: 网络错误、API 错误等异常情况

#### 重试与容错机制
- 网络错误：自动重试 3 次，间隔递增
- API 限流：指数退避重试策略
- 无效响应：记录错误详情，继续处理下一个实体
- 任务中断：支持断点续传，跳过已处理的实体

### 与现有模块的集成

#### main.py 集成
扩展现有的任务解析机制：
```python
# 新增L3任务别名映射
_ALIAS_TO_TARGET = {
    # ... 现有映射 ...
    "context_interpretation": ("l3", "context_interpretation"),
    "l3": ("l3", "context_interpretation"),
    "rag": ("l3", "rag"),
    "l3_rag": ("l3", "rag"),
}
```

#### 共享工具复用
- `src/utils/llm_api.py`: 复用配置加载和环境变量解析
- `src/utils/logger.py`: 复用日志记录机制
- `src/utils/json_repair.py`: 处理可能的 JSON 解析问题
- `src/utils/excel_io.py`: 复用文件 I/O 功能

### 性能与扩展性考虑

#### 性能优化
- 批量处理：支持批量提交 Dify 查询（如 API 支持）
- 并发控制：限制同时发起的 API 请求数量
- 缓存机制：避免重复查询相同实体
- 速率限制：遵守 Dify API 调用频率限制

#### 扩展性设计
- **插件化架构**: RAG 任务可独立开发和配置
- **多检索源支持**: 预留接口支持其他知识库或搜索引擎
- **结果后处理**: 支持自定义结果过滤和增强逻辑
- **配置热更新**: 支持运行时修改部分配置参数

## 实施计划

### 第一阶段（当前）
1. ✅ 分析现有代码结构和共享工具
2. 🔄 创建 L3 模块基础架构
3. 🔄 实现 DifyClient 和基础 API 调用
4. 🔄 实现实体标签检索任务
5. 🔄 集成到主流水线并进行测试

### 第二阶段（后续）
1. 实现基于已有信息的深度阐释任务
2. 添加网络检索功能
3. 性能优化和错误处理完善
4. 批量处理和并发控制

### 第三阶段（未来）
1. 支持更多检索源
2. 结果质量评估和过滤机制
3. 可视化界面和结果展示
4. 高级配置和调优功能

## 技术风险与缓解

### 主要风险
1. **Dify API 稳定性**: API 服务不稳定或限流
2. **知识库质量**: 检索结果质量不符合预期
3. **配置复杂性**: 多个密钥和配置项管理复杂
4. **性能瓶颈**: 大量实体处理时的速度问题

### 缓解措施
1. **健壮的重试机制**: 多层次的容错和重试策略
2. **结果质量控制**: 增加结果验证和过滤逻辑
3. **配置模板化**: 提供标准配置模板和验证工具
4. **分批处理**: 支持分批和并发处理优化性能

## 成功标准

### 功能标准
- ✅ 成功从 L2 JSON 文件中提取实体信息
- ✅ 成功调用 Dify API 进行知识检索
- ✅ 正确处理四种响应状态并格式化存储
- ✅ 支持命令行任务触发和集成到主流水线
- ✅ 避免重复处理已执行过的实体

### 质量标准  
- 📊 单个实体处理成功率 > 95%
- 📊 API 调用平均响应时间 < 5秒
- 📊 错误恢复和重试机制有效性 > 90%
- 📊 与现有模块集成无冲突
- 📊 代码测试覆盖率 > 80%

---

**文档版本**: v1.0  
**创建时间**: 2025-10-07  
**作者**: Qoder AI Assistant  
**状态**: Proposal（等待用户审批）