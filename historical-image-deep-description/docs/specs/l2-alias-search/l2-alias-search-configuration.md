# 别名检索配置说明

## 概述

本文档描述了内部API中别名检索备份机制的配置要求，包括需要在settings.yaml中添加的配置项。

## 配置项

### 1. 别名检索全局配置

在settings.yaml中添加以下配置：

```yaml
# 别名检索配置
alias_search:
  # 是否启用别名检索备份机制
  enabled: true
  # 最大别名尝试次数，默认3
  max_alias_attempts: 3
  # 别名检索的最小置信度阈值，低于此值的别名不会被使用
  min_confidence_threshold: 0.6
  # 别名检索的速率限制（毫秒）
  rate_limit_ms: 1000
```

### 2. 别名提取大模型配置

在tasks部分添加别名提取的配置：

```yaml
tasks:
  # 现有配置...
  
  # L2：别名提取
  l2_alias_extraction:
    provider_type: "text"
    model: "DeepSeek-V3.2-Exp"
    temperature: 0.2
    top_p: 0.9
    endpoint: "/chat/completions"
    system_prompt_file: "l2_alias_extraction.md"
```

### 3. 内部API配置更新

每个内部API配置中添加别名检索支持：

```yaml
tools:
  person_api:
    # 现有配置...
    # 是否启用别名检索备份机制
    enable_alias_search: true
    
  place_api:
    # 现有配置...
    enable_alias_search: true
    
  organization_api:
    # 现有配置...
    enable_alias_search: true
    
  event_api:
    # 现有配置...
    enable_alias_search: true
    
  work_api:
    # 现有配置...
    enable_alias_search: true
    
  architecture_api:
    # 现有配置...
    enable_alias_search: true
```

## 配置说明

### alias_search.enabled
- 类型：布尔值
- 默认值：true
- 说明：是否启用别名检索备份机制。当设置为false时，系统将不会尝试使用别名进行检索。

### alias_search.max_alias_attempts
- 类型：整数
- 默认值：3
- 说明：最大别名尝试次数。当从Wikipedia描述中提取到多个别名时，系统最多会尝试使用这个数量的别名进行检索。

### alias_search.min_confidence_threshold
- 类型：浮点数
- 默认值：0.6
- 说明：别名检索的最小置信度阈值。只有当大模型给出的别名置信度高于此值时，该别名才会被用于检索。

### alias_search.rate_limit_ms
- 类型：整数
- 默认值：1000
- 说明：别名检索的速率限制（毫秒）。每次别名检索之间的间隔时间，用于避免过于频繁的API调用。

### tools.{api_name}.enable_alias_search
- 类型：布尔值
- 默认值：true
- 说明：针对特定API是否启用别名检索。可以针对不同类型的实体单独控制是否启用别名检索。

## 使用场景

1. **人物检索**：当使用人物本名检索不到结果时，系统会从Wikipedia描述中提取笔名、字号、英文名等别名进行尝试检索。

2. **地点检索**：当地点的正式名称检索不到时，系统会尝试使用简称、旧称、译名等别名。

3. **机构检索**：当机构的完整名称检索不到时，系统会尝试使用缩写、简称等别名。

4. **事件检索**：当事件的标准名称检索不到时，系统会尝试使用俗称、别名等。

5. **作品检索**：当作品的标准名称检索不到时，系统会尝试使用译名、别名等。

6. **影剧院检索**：当影剧院的正式名称检索不到时，系统会尝试使用简称、旧称等。

## 实施流程

1. 系统首先使用原始实体标签进行内部API检索
2. 如果检索不到结果或大模型判断不匹配，检查是否有Wikipedia节点且description有值
3. 如果有，调用大模型从description中提取别名列表
4. 按照置信度排序，依次使用别名进行检索，直到找到匹配或达到最大尝试次数
5. 将最终结果写入JSON文件