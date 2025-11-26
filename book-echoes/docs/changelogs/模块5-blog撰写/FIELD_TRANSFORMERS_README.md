# 字段转换器使用说明

## 概述

字段转换器(Field Transformers)提供了一种灵活的方式来配置不同HTML模板使用不同的字段处理规则,无需修改代码即可适配新模板的需求。

## 核心概念

### 问题背景

不同的HTML模板可能需要不同的字段显示方式:
- **模板A**: 显示所有作者,完整标题(含副标题)
- **模板B**: 只显示第一作者+"等",只显示主标题(不含副标题)

传统方式需要修改代码来适配不同模板,维护成本高。

### 解决方案

通过配置文件定义字段转换规则,实现:
1. **配置化**: 在`config/setting.yaml`中配置字段转换规则
2. **灵活性**: 支持多种转换类型(直接使用、提取第一作者、主标题/完整标题等)
3. **可扩展**: 可以轻松添加自定义转换器
4. **向后兼容**: 如果不配置转换器,使用默认逻辑

## 使用方法

### 1. 基本配置

在`config/setting.yaml`的`card_generator`部分添加`field_transformers`配置:

```yaml
card_generator:
  template_path: "config/card_template.html"
  
  field_transformers:
    # 配置AUTHOR字段
    AUTHOR:
      type: "first_author"        # 转换器类型
      source_field: "豆瓣作者"     # 源字段名
      separator: "/"              # 作者分隔符
      suffix: " 等"               # 多作者时的后缀
      default: ""                 # 默认值
```

### 2. 支持的转换器类型

#### 2.1 `direct` - 直接转换器

直接使用字段值,不做任何处理。

```yaml
PUBLISHER:
  type: "direct"
  source_field: "豆瓣出版社"
  default: ""
```

#### 2.2 `first_author` - 第一作者转换器

提取第一个作者,如果有多个作者则添加后缀。

**示例输入**: `"张三 / 李四 / 王五"`
**示例输出**: `"张三 等"`

```yaml
AUTHOR:
  type: "first_author"
  source_field: "豆瓣作者"
  separator: "/"              # 作者分隔符
  suffix: " 等"               # 多作者时的后缀
  default: ""
```

**配置参数**:
- `separator`: 作者分隔符,默认为`"/"`
- `suffix`: 多作者时的后缀,默认为`" 等"`
- `default`: 字段为空时的默认值

#### 2.3 `main_title_only` - 主标题转换器

只返回主标题,不包含副标题。

```yaml
TITLE:
  type: "main_title_only"
  source_field: "豆瓣书名"
  default: ""
```

#### 2.4 `full_title` - 完整标题转换器

返回主标题+副标题的完整标题。

**示例输入**: 
- 主标题: `"人类简史"`
- 副标题: `"从动物到上帝"`

**示例输出**: `"人类简史 : 从动物到上帝"`

```yaml
TITLE:
  type: "full_title"
  source_field: "豆瓣书名"
  subtitle_field: "豆瓣副标题"
  separator: " : "            # 主副标题分隔符
  default: ""
```

**配置参数**:
- `subtitle_field`: 副标题字段名
- `separator`: 主副标题分隔符,默认为`" : "`

### 3. 支持的字段名

可以为以下占位符配置转换器:

| 占位符 | 说明 | 默认行为 |
|--------|------|----------|
| `AUTHOR` | 作者 | 显示所有作者 |
| `TITLE` | 标题 | 显示主标题+副标题 |
| `PUBLISHER` | 出版社 | 直接显示 |
| `PUB_YEAR` | 出版年份 | 直接显示 |
| `CALL_NUMBER` | 索书号 | 直接显示 |
| `DOUBAN_RATING` | 豆瓣评分 | 直接显示 |
| `RECOMMENDATION` | 推荐语 | 智能截取 |

### 4. 支持的源字段名

可以从以下Excel列/数据库字段获取数据:

- `豆瓣作者`
- `豆瓣书名`
- `豆瓣副标题`
- `豆瓣出版社`
- `豆瓣出版年`
- `索书号`
- `豆瓣评分`
- `初评理由`

## 使用场景示例

### 场景1: 默认模板(显示完整信息)

**需求**: 显示所有作者,完整标题(含副标题)

**配置**: 不需要配置`field_transformers`,使用默认逻辑即可。

```yaml
card_generator:
  template_path: "config/card_template.html"
  field_transformers: {}  # 空配置,使用默认逻辑
```

### 场景2: 简化模板(只显示第一作者和主标题)

**需求**: 
- 作者: 只显示第一作者,多作者时加"等"
- 标题: 只显示主标题,不显示副标题

**配置**:

```yaml
card_generator:
  template_path: "config/simple_card_template.html"
  
  field_transformers:
    AUTHOR:
      type: "first_author"
      source_field: "豆瓣作者"
      separator: "/"
      suffix: " 等"
      default: ""
    
    TITLE:
      type: "main_title_only"
      source_field: "豆瓣书名"
      default: ""
```

### 场景3: 混合配置

**需求**:
- 作者: 只显示第一作者
- 标题: 显示完整标题(含副标题)
- 其他字段: 使用默认逻辑

**配置**:

```yaml
card_generator:
  template_path: "config/mixed_card_template.html"
  
  field_transformers:
    AUTHOR:
      type: "first_author"
      source_field: "豆瓣作者"
      separator: "/"
      suffix: " 等"
    
    TITLE:
      type: "full_title"
      source_field: "豆瓣书名"
      subtitle_field: "豆瓣副标题"
      separator: " : "
```

## 扩展开发

### 添加自定义转换器

如果内置转换器不满足需求,可以自定义转换器:

#### 1. 创建转换器类

在`field_transformers.py`中添加新的转换器类:

```python
class UpperCaseTransformer(FieldTransformer):
    """大写转换器 - 将文本转换为大写"""
    
    def transform(self, value: Any, **kwargs) -> str:
        if value is None:
            return kwargs.get('default', '')
        return str(value).upper()
```

#### 2. 注册转换器

在`FieldTransformerFactory`中注册:

```python
class FieldTransformerFactory:
    _transformers = {
        'direct': DirectTransformer,
        'first_author': FirstAuthorTransformer,
        'main_title_only': MainTitleOnlyTransformer,
        'full_title': FullTitleTransformer,
        'upper_case': UpperCaseTransformer,  # 新增
    }
```

#### 3. 在配置中使用

```yaml
TITLE:
  type: "upper_case"
  source_field: "豆瓣书名"
```

## 注意事项

1. **向后兼容**: 如果不配置`field_transformers`,系统会使用默认逻辑,保证现有模板正常工作
2. **配置优先级**: 如果配置了转换器,会优先使用转换器;否则使用默认逻辑
3. **错误处理**: 如果转换器执行失败,会使用配置的`default`值,并记录错误日志
4. **性能影响**: 字段转换器在初始化时创建,运行时性能影响很小

## 常见问题

### Q1: 如何知道当前使用的是哪个转换器?

查看日志,初始化时会输出:
```
字段转换器初始化成功: AUTHOR -> first_author
```

### Q2: 转换器配置错误会怎样?

系统会记录警告日志并使用默认逻辑:
```
字段转换器初始化失败: AUTHOR, 错误: 不支持的转换器类型: xxx
```

### Q3: 可以为同一个字段配置多个转换器吗?

不可以。每个字段只能配置一个转换器。如果需要复杂的转换逻辑,请自定义转换器。

### Q4: 如何调试转换器?

1. 设置日志级别为`DEBUG`
2. 查看日志输出,包含字段转换的详细信息
3. 检查生成的HTML文件,确认字段值是否符合预期

## 总结

字段转换器提供了一种优雅的方式来适配不同模板的需求:

- ✅ **配置化**: 无需修改代码
- ✅ **灵活性**: 支持多种转换类型
- ✅ **可扩展**: 可以添加自定义转换器
- ✅ **向后兼容**: 不影响现有模板
- ✅ **易维护**: 配置集中管理

通过合理使用字段转换器,可以轻松实现"一套代码,多套模板"的需求。
