# 图书馆借书卡生成功能

## 概述

图书馆借书卡生成功能是一个与图书卡片生成并行运行的独立模块，用于生成复古风格的图书馆借书卡。

## 功能特性

- **并行执行**：与图书卡片生成和推荐结果写入同时运行，不影响主流程性能
- **随机数据生成**：
  - 随机生成3-4条借阅记录
  - 借阅者姓名：80%中文名（使用Faker zh_CN），20%英文名（使用Faker en_US）
  - 借阅日期：从当年1月1日到当前日期的随机日期（YYYY-MM-DD格式）
- **卡片编号提取**：自动从索书号中提取卡片编号（如 "B512.59/5024-3" → "5024"）
- **文件命名**：输出文件自动添加 `-S` 后缀（如 `123456-S.html`, `123456-S.png`）

## 配置说明

在 `config/setting.yaml` 中配置：

```yaml
library_card_generator:
  # 是否启用借书卡生成功能
  enabled: true
  
  # HTML模板文件路径
  template_path: "config/library_card_template.html"
  
  # 借阅记录生成配置
  borrower_records_count: 3  # 每张卡片生成的随机借阅记录数量
  
  # 借阅者姓名配置
  chinese_name_ratio: 0.8  # 中文名占比（0.8表示80%中文名，20%英文名）
  
  # 日期范围配置
  date_range:
    start: "auto"  # "auto"表示当前年份1月1日，或指定"YYYY-MM-DD"格式
    end: "auto"    # "auto"表示当前日期，或指定"YYYY-MM-DD"格式
  
  # 输出文件后缀
  output_suffix: "-S"  # 借书卡文件名后缀
```

## 使用方法

1. **安装依赖**：
   ```bash
   pip install radar Faker
   ```

2. **启用功能**：
   在 `config/setting.yaml` 中设置 `library_card_generator.enabled: true`

3. **运行**：
   ```bash
   python src/core/card_generator/card_main.py --excel-file "path/to/excel.xlsx"
   ```

4. **查看输出**：
   - HTML文件：`runtime/outputs/[书目条码]/[书目条码-S].html`
   - 图片文件：`runtime/outputs/[书目条码]/[书目条码-S].png`

## 输出示例

生成的借书卡包含以下信息：

- **卡片编号**：从索书号中自动提取
- **图书信息**：作者、书名、索书号、出版年份
- **借阅记录**：3-4条随机生成的借阅记录，包括：
  - 借阅日期（格式：MAY 15 '23）
  - 借阅者姓名（中文或英文）

## 技术实现

### 核心模块

1. **library_card_models.py**：数据模型
   - `BorrowerRecord`：借阅记录
   - `LibraryCardData`：借书卡数据

2. **library_card_html_generator.py**：HTML生成器
   - 模板加载和缓存
   - 随机数据生成
   - HTML填充和保存

3. **card_main.py**：主流程集成
   - 并行任务调度
   - 统计信息收集
   - 错误处理

### 并行执行架构

```
主流程
├── 任务1: 图书卡片生成
├── 任务2: 推荐结果数据库写入
└── 任务3: 图书馆借书卡生成（新增）
```

所有任务使用 `ThreadPoolExecutor` 并行执行，互不阻塞。

## 注意事项

1. **依赖要求**：需要安装 `radar` 和 `Faker` 库
2. **模板文件**：确保 `config/library_card_template.html` 存在
3. **浏览器实例**：与图书卡片生成共用浏览器实例，节省资源
4. **错误处理**：借书卡生成失败不影响图书卡片生成和数据库写入

## 禁用功能

如需禁用借书卡生成，在 `config/setting.yaml` 中设置：

```yaml
library_card_generator:
  enabled: false
```

## 故障排查

### 问题：借书卡未生成

**可能原因**：
1. 功能未启用：检查 `library_card_generator.enabled` 配置
2. 依赖未安装：运行 `pip install radar Faker`
3. 模板文件缺失：确认 `config/library_card_template.html` 存在

### 问题：卡片编号显示为 "0000"

**可能原因**：
索书号格式不符合预期（应包含 `/` 符号）

**解决方法**：
检查Excel中的索书号格式，确保包含类似 "B512.59/5024-3" 的格式

## 更新日志

### v1.0.0 (2025-11-21)
- 初始版本发布
- 支持并行生成借书卡
- 支持随机借阅记录生成
- 支持中英文混合姓名
