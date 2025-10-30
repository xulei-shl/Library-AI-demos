# 统一LLM调用系统

一个功能完整、高度可配置的LLM调用系统，支持多种提供商、智能重试、中文日志、JSON智能修复等功能。

## ✨ 特性

### 🚀 核心特性

- **统一配置管理** - 集中管理所有API提供商和任务配置
- **智能重试机制** - 三层重试策略：Provider内重试、Provider切换、最终失败
- **多格式提示词** - 支持 `.md` 文件、Langfuse平台、Python dict三种格式
- **中文日志系统** - 完整的中文日志格式，按日期轮转和分级存储
- **JSON智能修复** - 自动检测和修复JSON格式错误，支持多种输出格式
- **流式调用支持** - 实时流式响应，提升用户体验
- **批量调用** - 高效处理批量请求，支持并发控制

### 🎯 高可用性

- **主备Provider切换** - 自动切换到备用提供商，提升系统可用性
- **指数退避重试** - 智能退避算法，减少系统压力
- **随机抖动** - 避免雪崩效应
- **错误分类处理** - 针对不同错误类型采用不同策略

### 🔧 高度可配置

- **任务级配置** - 每个任务可独立配置参数
- **Provider级配置** - 支持主备Provider独立配置
- **全局默认配置** - 减少重复配置
- **动态配置覆盖** - 调用时可临时覆盖配置

### 📊 监控与调试

- **Langfuse集成** - 完整的调用链路追踪（可选）
- **详细日志** - 中文日志格式，便于理解和调试
- **错误历史** - 完整的错误追踪和诊断信息

## 📦 安装

### 依赖

```bash
pip install openai PyYAML
```

### 可选依赖

```bash
# Langfuse监控（可选）
pip install langfuse

# YAML支持（可选）
pip install PyYAML
```

### 环境变量

在 `.env` 文件中配置API密钥：

```bash
# 主文本提供商
SophNet_API_KEY=your_api_key_here

# 备用文本提供商
ModelScope_API_KEY=your_api_key_here

# 主视觉提供商
OneAPI_API_KEY=your_api_key_here

# Langfuse（可选）
LANGFUSE_HOST=your_langfuse_host
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_PUBLIC_KEY=your_public_key
```

## 🚀 快速开始

### 基础使用

```python
import asyncio
from core.llm_client import UnifiedLLMClient

async def main():
    # 创建客户端
    client = UnifiedLLMClient()

    # 简单调用
    result = await client.call(
        task_name="fact_description",
        user_prompt="描述这张图片的内容"
    )
    print(f"结果: {result}")

    await client.close()

asyncio.run(main())
```

### 流式调用

```python
import asyncio
from core.llm_client import UnifiedLLMClient

async def streaming_example():
    client = UnifiedLLMClient()

    print("流式响应: ", end="", flush=True)
    async for chunk in client.stream_call(
        task_name="fact_description",
        user_prompt="写一篇关于AI的文章"
    ):
        print(chunk, end="", flush=True)
    print()

    await client.close()

asyncio.run(streaming_example())
```

### 批量调用

```python
import asyncio
from core.llm_client import UnifiedLLMClient

async def batch_example():
    client = UnifiedLLMClient()

    requests = [
        {"task_name": "fact_description", "user_prompt": "图片1"},
        {"task_name": "fact_description", "user_prompt": "图片2"},
        {"task_name": "fact_description", "user_prompt": "图片3"},
    ]

    results = await client.batch_call(requests, max_concurrent=3)

    for i, result in enumerate(results):
        print(f"请求 {i+1}: {result}")

    await client.close()

asyncio.run(batch_example())
```

## 📋 配置说明

### 完整配置示例

参见 [config/settings.yaml](config/settings.yaml)

### 主要配置项

```yaml
# API提供商配置
api_providers:
  text:
    primary:
      name: "主文本提供商"
      api_key: env:API_KEY_NAME
      base_url: "https://api.example.com/v1"
      model: "your-model-name"
      timeout_seconds: 120
    secondary:  # 可选
      # 备用提供商配置

  vision:
    # 视觉提供商配置
    # ...

# 任务配置
tasks:
  my_task:
    provider_type: "text"  # text 或 vision
    temperature: 0.7
    top_p: 0.9

    # 提示词配置
    prompt:
      type: "md"  # md | langfuse | dict
      source: "prompts/my_task.md"  # type=md时使用

    # 重试策略
    retry:
      max_retries: 3
      base_delay: 1
      max_delay: 60
      enable_provider_switch: true

    # Langfuse监控（可选）
    langfuse:
      enabled: false
      name: "my_task"
      tags: ["tag1", "tag2"]

    # JSON处理（可选）
    json_repair:
      enabled: true
      strict_mode: false
```

### 提示词格式

#### 1. .md 文件格式

```markdown
<!-- prompts/my_task.md -->
# 我的任务

你是一个专业的助手...

## 要求
1. 要求1
2. 要求2

## 输出格式
请按以下格式返回：
```
json
{
  "result": "..."
}
```
```

配置：
```yaml
prompt:
  type: "md"
  source: "prompts/my_task.md"
```

#### 2. Langfuse格式

配置：
```yaml
prompt:
  type: "langfuse"
  langfuse_name: "my_langfuse_prompt"
```

#### 3. Python dict格式

配置：
```yaml
prompt:
  type: "dict"
  content:
    role: "system"
    content: |
      你是一个专业的助手...
```

## 📚 API参考

### UnifiedLLMClient

#### 初始化

```python
client = UnifiedLLMClient(config_path="config/settings.yaml")
```

#### 核心方法

##### `call(task_name, user_prompt, **kwargs)`

执行LLM调用

**参数:**
- `task_name`: 任务名称（必须在配置中定义）
- `user_prompt`: 用户提示词（字符串或消息列表）
- `**kwargs`: 覆盖配置的参数

**返回:** LLM响应文本

##### `stream_call(task_name, user_prompt, **kwargs)`

流式调用（异步生成器）

**参数:**
- `task_name`: 任务名称
- `user_prompt`: 用户提示词
- `**kwargs`: 覆盖参数

**返回:** AsyncGenerator[str, None] - 流式响应片段

##### `batch_call(requests, max_concurrent=5)`

批量调用

**参数:**
- `requests`: 请求列表 [{'task_name': str, 'user_prompt': str}, ...]
- `max_concurrent`: 最大并发数

**返回:** 响应列表

#### 辅助方法

##### `get_task_config(task_name)`

获取任务配置

##### `list_tasks()`

列出所有任务名称

##### `reload_config()`

重新加载配置

##### `close()`

关闭客户端

## 🎯 使用场景

### 1. 图像描述

```python
result = await client.call(
    task_name="fact_description",
    user_prompt="请详细描述这张图片"
)
```

### 2. 文本校对

```python
result = await client.call(
    task_name="correction",
    user_prompt="请校对以下文本：这是一个测试文本..."
)
```

### 3. 自定义任务

在配置中添加新任务：

```yaml
tasks:
  my_custom_task:
    provider_type: "text"
    temperature: 0.5
    prompt:
      type: "md"
      source: "prompts/custom_task.md"
    retry:
      max_retries: 3
      enable_provider_switch: true
```

## 📊 错误处理

### 常见异常

```python
from core.exceptions import (
    LLMCallError,       # 调用失败
    ConfigurationError, # 配置错误
    ProviderError,      # Provider错误
    NetworkError,       # 网络错误
    RateLimitError,     # 速率限制
    AuthenticationError # 认证错误
)

try:
    result = await client.call(
        task_name="fact_description",
        user_prompt="测试"
    )
except LLMCallError as e:
    print(f"调用失败: {e}")
    print(f"错误历史: {e.error_history}")
except ConfigurationError as e:
    print(f"配置错误: {e}")
except Exception as e:
    print(f"其他错误: {e}")
```

### 错误类型

- `LLMCallError`: 所有重试都失败
- `ConfigurationError`: 配置文件错误
- `ProviderError`: API提供商返回错误
- `NetworkError`: 网络连接错误
- `RateLimitError`: 速率限制
- `AuthenticationError`: 认证失败
- `ModelError`: 模型错误
- `PromptError`: 提示词加载失败

## 🔧 高级功能

### JSON处理

系统集成JSON智能修复功能：

```python
# 配置任务启用JSON修复
tasks:
  my_task:
    json_repair:
      enabled: true
      strict_mode: false  # false: 修复失败返回原文, true: 返回None
```

自动处理：
- 移除代码块标记 ```json ```
- 修复常见JSON语法错误
- 提取JSON片段
- 格式化输出

### 日志系统

#### 基础使用

```python
from utils.logger import get_logger

logger = get_logger(__name__)
logger.info("这是一条中文日志")
```

#### 函数调用日志装饰器

```python
from utils.logger import log_function_call

@log_function_call
async def my_function(x, y):
    return x + y

# 自动记录：函数调用、参数、返回值、耗时、异常
```

#### 日志配置

```yaml
logging:
  level: "INFO"
  logs_dir: "runtime/logs"

  # 控制台级别
  levels:
    console: "INFO"
    file: "DEBUG"

  # 轮转配置
  rotation:
    when: "D"  # 按天轮转
    interval: 1
    backup_count: 7
```

日志文件：
- `llm.log` - 主要日志（按日期轮转）
- `error.log` - 错误日志（按大小轮转）
- `debug.log` - 调试日志（按大小轮转）

### 重试机制

#### 策略

1. **Provider内重试** - 指数退避 + 随机抖动
2. **Provider切换** - 主Provider失败后切换到备用
3. **最终失败** - 记录详细错误并抛出异常

#### 配置

```yaml
retry:
  max_retries: 3           # 最大重试次数
  base_delay: 1            # 基数延迟（秒）
  max_delay: 60            # 最大延迟（秒）
  enable_provider_switch: true  # 启用Provider切换
```

#### 错误分类

- **NETWORK** - 网络错误
- **TIMEOUT** - 超时错误
- **API_ERROR** - API返回错误
- **RATE_LIMIT** - 速率限制
- **PROVIDER_DOWN** - Provider不可用
- **AUTH_ERROR** - 认证错误
- **MODEL_ERROR** - 模型错误

## 📁 项目结构

```
llm-request-langfuse/
├── config/
│   ├── settings.yaml    # 统一配置文件
│   └── settings.yaml            # 旧配置文件（兼容）
├── core/
│   ├── config_loader.py         # 配置加载器
│   ├── retry_manager.py         # 重试管理器
│   ├── llm_client.py            # 统一LLM客户端
│   └── exceptions.py            # 自定义异常
├── utils/
│   ├── logger.py                # 中文日志系统
│   ├── json_handler.py          # JSON处理工具
│   └── json_repair.py           # JSON修复工具
├── prompts/
│   ├── fact_description.md      # 图像描述提示词
│   └── correction.md            # 文本校对提示词
├── examples/
│   ├── basic_usage.py           # 基础使用示例
│   ├── streaming_example.py     # 流式调用示例
│   ├── batch_call_example.py    # 批量调用示例
│   └── custom_config_example.py # 自定义配置示例
└── docs/
    └── 重构方案设计.md            # 重构方案文档
```

## 🎓 示例

完整示例请参考 [examples/](examples/) 目录：

- `basic_usage.py` - 基础使用
- `streaming_example.py` - 流式调用
- `batch_call_example.py` - 批量调用
- `custom_config_example.py` - 自定义配置

## ⚡ 性能优化

### 建议

1. **批量调用** - 尽可能使用批量调用减少网络开销
2. **并发控制** - 根据API限制调整并发数
3. **缓存配置** - 配置只加载一次，无需重复加载
4. **流式调用** - 对于长文本，使用流式调用提升用户体验

### 配置建议

```yaml
# 速率限制
rate_limit:
  global:
    requests_per_minute: 1000
    concurrent_requests: 10

# Provider超时
api_providers:
  text:
    primary:
      timeout_seconds: 120  # 合理设置超时时间
```

## 🐛 故障排除

### 常见问题

1. **配置文件不存在**
   ```
   FileNotFoundError: 配置文件不存在
   ```
   解决：确保 `config/settings.yaml` 存在

2. **API密钥缺失**
   ```
   警告: missing_env_key key=API_KEY_NAME
   ```
   解决：在 `.env` 文件中配置API密钥

3. **提示词文件不存在**
   ```
   PromptError: 文件不存在
   ```
   解决：确保 `prompts/` 目录下的文件存在

4. **Langfuse未安装**
   ```
   Langfuse未安装
   ```
   解决：`pip install langfuse` 或在配置中设置 `langfuse.enabled: false`

### 调试技巧

1. **启用详细日志**
   ```yaml
   logging:
     levels:
       file: "DEBUG"  # 文件日志使用DEBUG级别
   ```

2. **查看错误历史**
   ```python
   try:
       await client.call(...)
   except LLMCallError as e:
       print(e.error_history)  # 查看详细错误历史
   ```

3. **使用函数调用装饰器**
   ```python
   @log_function_call
   async def my_function():
       # 函数调用会自动记录日志
       pass
   ```

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者！

---

**版本**: v1.0
**更新时间**: 2025-10-30