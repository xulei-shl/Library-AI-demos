# LLM Request with Langfuse

一个基于 Langfuse 的 LLM 请求封装工具，提供了重试机制、备用配置切换和监控能力。

## 功能特点

- 🔄 多级重试机制
  - 支持指数退避策略
  - 可配置最大重试次数和初始等待时间
  - 自动切换备用配置

- 🎯 灵活的提示词管理
  - 支持 Langfuse 远程提示词配置
  - 支持本地提示词配置
  - 支持直接传入系统提示词
  
- 📊 Langfuse 监控集成
  - 集成 Langfuse 监控

- ⚙️ 丰富的配置选项
  - 多级配置优先级管理
  - 支持多个备用 API 端点
  - 可自定义模型参数

## 环境要求

- Python 3.7+
- 相关依赖包：
  - langfuse
  - python-dotenv
  - tenacity

## 环境变量配置

创建 `.env` 文件并配置以下环境变量：

```plaintext
# Langfuse 配置
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_HOST=your_host_url

# 主要 API 配置
DEEPSEEK_API_KEY=your_api_key

# 备用配置 1
FALLBACK_API_BASE_1=your_fallback_base_url_1
FALLBACK_API_KEY_1=your_fallback_api_key_1

# 备用配置 2
FALLBACK_API_BASE_2=your_fallback_base_url_2
FALLBACK_API_KEY_2=your_fallback_api_key_2
```

## 使用示例

### 1. 使用 Langfuse 提示词配置

```python
response = get_llm_response(
    user_prompt="什么是图像多模态大语言模型？",
    prompt_name="翻译成英文",  # Langfuse中的提示词名称
)
```

### 2. 使用本地提示词配置

```python
response = get_llm_response(
    user_prompt="什么是图像多模态大语言模型？",
    prompt_name="翻译成英文",
    use_langfuse_prompt=False  # 使用本地提示词
)
```

### 3. 使用自定义系统提示词

```python
response = get_llm_response(
    user_prompt="什么是图像多模态大语言模型？",
    system_prompt="你是一个专业的Python教程助手",
    use_langfuse_prompt=False
)
```

### 4. 完全自定义配置

```python
response = get_llm_response(
    user_prompt="什么是图像多模态大语言模型？",
    base_url="your_api_base",
    api_key="your_api_key",
    model_name="your_model",
    temperature=0.7,
    name="测试",
    tags=["Literature Search"],
    metadata={"project": "test"},
    use_langfuse_prompt=False
)
```

## 参数优先级

从高到低：

1. 显式传入的参数值
2. 本地提示词配置
3. Langfuse 提示词配置（当 use_langfuse_prompt=True）
4. 函数默认值

## 重试机制说明

- 默认最大重试次数：3次
- 默认初始等待时间：1秒
- 使用指数退避策略进行重试
- 重试时自动切换到备用配置

## 注意事项

1. 重试时的参数覆盖规则：
   - 本地提示词或 Langfuse 提示词中的配置仅在首次调用时生效
   - 重试时会使用 fallback_configs 中的配置覆盖非显式参数
   - 系统提示词在重试过程中保持不变

2. Token 使用统计限制：
   - 使用非 Langfuse 提示词配置时，token 使用统计可能不准确
   - 部分大语言模型的 token 使用量统计存在异常。
   - 建议在需要精确 token 统计的场景下进行实际测试验证