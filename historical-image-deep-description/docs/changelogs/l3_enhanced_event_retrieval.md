# L3 增强事件检索功能

## 功能概述

L3阶段的增强事件检索功能为事件类型实体提供了扩展的RAG检索能力。该功能通过大模型智能提取关键词，优化搜索效果，提升检索准确性。

## 核心特性

### 1. 智能关键词提取
- 使用大模型从原始事件label中提取核心关键词
- 复用L2阶段的关键词提取提示词(`l2_event_keyword_extraction.md`)
- 支持配置化启用/禁用

### 2. 替换式检索
- 使用提取的关键词替换原始label进行RAG检索
- 保留原始label信息用于追溯
- 与现有RAG流程完全兼容

### 3. 独立结果存储
- 结果写入专门的JSON节点：`l3_rag_enhanced_event_retrieval`
- 不影响原有的`l3_rag_entity_label_retrieval`结果
- metadata中保留搜索关键词信息

### 4. 配置驱动
- 支持全局、任务级、实体类型级的细粒度控制
- 与现有L3配置体系保持一致
- 支持独立的Dify API配置

## 配置说明

在`config/settings.yaml`中新增以下配置：

```yaml
l3_context_interpretation:
  # 增强事件检索配置
  enhanced_event_retrieval:
    # 全局启用开关
    enabled: true
    # Dify API配置
    dify_key: "env:DIFY_ENHANCED_EVENT_KEY"
    dify_base_url: "https://api.dify.ai/v1"
    # 速率限制（毫秒）
    rate_limit_ms: 1000
    # 请求超时时间（秒）
    timeout_seconds: 90
    # 超时恢复配置
    timeout_recovery:
      enabled: true
      max_attempts: 3
      delay_seconds: 10
      match_time_window: 120
    # 按实体类型的启用配置
    entity_types:
      event:
        enabled: true   # 仅对事件类型启用增强检索
      person:
        enabled: false  # 其他类型默认禁用
      organization:
        enabled: false
      architecture:
        enabled: false
      location:
        enabled: false
      work:
        enabled: false
```

## 环境变量

需要在`.env`文件中配置：

```bash
# 增强事件检索专用的Dify API密钥
DIFY_ENHANCED_EVENT_KEY=your_enhanced_event_api_key_here
```

## 使用方法

### 1. 通过主流程执行

```bash
# 执行所有启用的L3任务（包括增强事件检索）
python main.py --tasks "l3"

python main.py --tasks "l3:enhanced"
# 或者
python main.py --tasks "l3:enhanced_event"

# 仅执行增强事件检索
python -c "
from src.core.l3_context_interpretation.main import run_l3
run_l3(tasks=['enhanced_event_retrieval'])
"
```

### 2. 单独使用增强事件检索

```python
from src.core.l3_context_interpretation.enhanced_event_retrieval import EnhancedEventRetrieval
from src.utils.llm_api import load_settings

# 加载配置
settings = load_settings()

# 创建处理器
retrieval = EnhancedEventRetrieval(settings)

# 处理单个实体
entity = {
    "type": "event",
    "label": "话剧《日出》首演",
    "confidence": 0.9
}

metadata = {
    "row_id": "2202_001",
    "title": "话剧《日出》首演海报",
    "desc": "曹禺话剧《日出》首演纪念海报"
}

success = retrieval.process_entity(entity, "2202_001", metadata)
```

## 结果格式

### 成功情况

```json
{
  "l3_rag_enhanced_event_retrieval": {
    "status": "success",
    "content": "曹禺的话剧《日出》是现代戏剧史上的重要作品...",
    "metadata": {
      "original_label": "话剧《日出》首演",
      "search_keyword": "话剧 日出",
      "keyword_extracted": "true",
      "task_type": "enhanced_event_retrieval",
      "executed_at": "2025-10-07T21:00:00Z",
      "model": "gpt-4"
    }
  }
}
```

### 失败情况

```json
{
  "l3_rag_enhanced_event_retrieval": null,
  "metadata.l3_rag_enhanced_event_retrieval": {
    "error": "关键词提取失败",
    "original_label": "话剧《日出》首演",
    "keyword_extracted": "false",
    "task_type": "enhanced_event_retrieval",
    "executed_at": "2025-10-07T21:00:00Z"
  }
}
```

## 关键词提取示例

输入：
```
实体标签：话剧《日出》首演
实体类型：event
```

输出：
```
话剧 日出
```

## 集成点

### 1. 主流程集成
- 在`src/core/l3_context_interpretation/main.py`中集成
- 支持任务列表中的`enhanced_event_retrieval`任务
- 支持简化任务名：`enhanced`、`enhanced_event`

### 2. 配置验证
- 三层启用检查：全局→任务→实体类型
- 与现有RAG任务配置保持一致
- 支持运行时配置修改

### 3. 异常处理
- 统一的异常处理模式
- 兼容L2阶段的异常存储格式
- 完整的错误日志记录

## 性能考虑

### 1. 速率限制
- 可配置的API调用间隔
- 避免频繁调用导致的限流

### 2. 跳过机制
- 自动跳过已处理的实体
- 支持中断续跑
- 避免重复处理

### 3. 资源优化
- 仅对事件类型实体启用
- 支持按需关闭功能
- 内存友好的批量处理

## 测试覆盖

### 1. 单元测试
- 配置加载和验证
- 关键词提取逻辑
- 结果格式化和写入
- 跳过机制和异常处理

### 2. 集成测试
- 完整流程测试
- 失败场景测试
- 配置驱动行为测试

### 3. 测试运行
```bash
# 运行单元测试
python -m pytest tests/core/l3_context_interpretation/test_enhanced_event_retrieval.py -v

# 运行集成测试
python -m pytest tests/core/l3_context_interpretation/test_enhanced_event_retrieval_integration.py -v
```

## 故障排查

### 1. 常见问题

**问题：增强事件检索未执行**
- 检查配置是否正确启用
- 确认实体类型为`event`
- 查看日志确认跳过原因

**问题：关键词提取失败**
- 检查L2阶段的提示词文件是否存在
- 确认大模型API配置正确
- 查看错误日志定位具体问题

**问题：Dify API调用失败**
- 确认API密钥配置正确
- 检查网络连接和API地址
- 查看超时配置是否合理

### 2. 日志查看

增强事件检索的日志会包含以下关键信息：
- 关键词提取成功/失败
- Dify API调用状态
- 结果写入情况
- 跳过原因

```bash
# 查看最新日志
tail -f runtime/logs/app.log | grep enhanced_event
```

## 扩展说明

### 1. 支持新的实体类型
在配置文件中的`entity_types`部分添加新类型：

```yaml
entity_types:
  event:
    enabled: true
  custom_type:  # 新增的实体类型
    enabled: true
```

### 2. 自定义关键词提取逻辑
可以修改`_extract_keyword_with_llm`方法来实现特定的关键词提取策略。

### 3. 结果后处理
可以通过修改`_format_enhanced_result`方法来添加额外的结果处理逻辑。