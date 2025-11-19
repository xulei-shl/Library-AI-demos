# Card Generator 文档

## 概述

`card_generator` 模块是图书推荐系统中的第5个核心模块，负责将经过智能评选的图书数据生成为精美的可视化卡片。该模块能够自动下载图书封面、生成索书号二维码、创建HTML模板并转换为高质量PNG图片。

## 核心功能

### 1. 图书卡片生成流程
- **数据验证**: 验证Excel输入数据的完整性和有效性
- **智能筛选**: 自动筛选终评结果为"通过"的图书
- **资源准备**: 复制Logo文件，下载封面图片，生成二维码
- **模板渲染**: 使用HTML模板填充图书数据
- **图片生成**: 将HTML转换为高质量PNG图片
- **报告生成**: 生成详细的执行汇总报告

### 2. 支持的图书信息字段
- **必填字段**: 书目条码、索书号、豆瓣评分、初评理由、豆瓣封面图片链接
- **可选字段**: 豆瓣书名、豆瓣作者、豆瓣出版社、豆瓣出版年、豆瓣副标题
- **智能推荐语**: 支持优先使用人工推荐语，智能截取推荐内容

### 3. 生成的文件结构
每个图书条码会生成独立目录，包含：
```
runtime/outputs/{barcode}/
├── pic/
│   ├── cover.jpg/png     # 下载的图书封面
│   ├── qrcode.png        # 索书号二维码
│   ├── logo_shl.png      # 图书馆Logo
│   ├── logozi_shl.jpg    # 图书馆子Logo
│   └── b.png             # 随机背景图
├── {barcode}.html        # HTML卡片模板
└── {barcode}.png         # 最终生成的卡片图片
```

## 文件结构

```
src/core/card_generator/
├── __init__.py                   # 模块初始化
├── card_main.py                  # 主程序入口（CardGeneratorModule类）
├── models.py                     # 数据模型定义（BookCardData, OutputPaths）
├── validator.py                  # 数据验证器（DataValidator类）
├── directory_manager.py          # 目录管理器（DirectoryManager类）
├── image_downloader.py           # 图片下载器（ImageDownloader类）
├── qrcode_generator.py           # 二维码生成器（QRCodeGenerator类）
├── html_generator.py             # HTML生成器（HTMLGenerator类）
├── html_to_image_converter.py    # HTML转图片转换器（HTMLToImageConverter类）
├── README.md                     # 本文档
└── __pycache__/                  # Python缓存目录
```

## 核心类说明

### 1. CardGeneratorModule（主控制器）
**位置**: `card_main.py`

负责统筹整个卡片生成流程：

- **主要方法**:
  - `run(excel_path)`: 主函数流程，依次执行验证、加载、筛选、生成等步骤
  - `process_single_book(row)`: 处理单本图书的完整流程
  - `extract_book_data(row)`: 从Excel行数据提取图书卡片数据
  - `check_existing_files(output_paths)`: 检查已有文件，避免重复生成
  - `generate_summary_report()`: 生成详细的执行汇总报告

- **统计数据**:
  - `total_count`: 总记录数
  - `passed_count`: 筛选通过的图书数
  - `success_count`: 成功生成的卡片数
  - `failed_count`: 失败的记录数
  - `warning_count`: 警告记录数

### 2. BookCardData（数据模型）
**位置**: `models.py`

图书卡片数据的数据容器：

- **主要属性**:
  - `barcode`: 书目条码（必填）
  - `call_number`: 索书号（必填）
  - `douban_rating`: 豆瓣评分（必填）
  - `final_review_reason`: 初评理由（必填，支持智能截取）
  - `cover_image_url`: 豆瓣封面图片链接（必填）
  - `title`: 书名
  - `author`: 作者
  - `publisher`: 出版社
  - `pub_year`: 出版年
  - `subtitle`: 副标题

- **主要方法**:
  - `full_title`: 获取完整书名（书名 + 副标题）
  - `truncated_reason`: 智能截取推荐语，避免在语句中间截断
  - `validate()`: 验证必填字段是否完整

### 3. DataValidator（数据验证器）
**位置**: `validator.py`

负责验证输入数据的完整性：

- **主要方法**:
  - `validate_excel_file()`: 验证Excel文件是否存在且可读
  - `validate_required_columns()`: 验证必填列是否存在
  - `filter_passed_books()`: 筛选终评结果为"通过"的图书
  - `validate_row_data()`: 验证单行数据的必填字段

- **筛选逻辑**:
  - 支持配置化的优先规则（priority_rule）
  - 默认按"终评结果"列为"通过"进行筛选
  - 支持动态列名和值配置

### 4. DirectoryManager（目录管理器）
**位置**: `directory_manager.py`

负责创建和管理输出目录结构：

- **主要方法**:
  - `create_book_directory(barcode)`: 创建图书输出目录结构
  - `copy_logo_files(pic_dir)`: 复制Logo文件到pic目录
  - `clean_barcode(barcode)`: 清理条码字符串（去除非法字符）

- **特色功能**:
  - 自动从多个b-*.png文件中随机选择一个作为背景图
  - 支持条码非法字符清理
  - 智能目录结构创建

### 5. HTMLGenerator（HTML生成器）
**位置**: `html_generator.py`

负责填充HTML模板并生成HTML文件：

- **主要方法**:
  - `generate_html(book_data, output_path)`: 生成HTML文件
  - `load_template()`: 加载HTML模板文件（支持缓存）
  - `fill_template(template, book_data)`: 填充HTML模板

- **模板变量**:
  - `{{AUTHOR}}`: 作者
  - `{{TITLE}}`: 完整书名
  - `{{PUBLISHER}}`: 出版社
  - `{{PUB_YEAR}}`: 出版年
  - `{{CALL_NUMBER}}`: 索书号
  - `{{DOUBAN_RATING}}`: 豆瓣评分
  - `{{RECOMMENDATION}}`: 截取后的推荐语

### 6. ImageDownloader（图片下载器）
**位置**: `image_downloader.py`

负责下载豆瓣封面图片：

- **主要方法**:
  - `download_cover_image(url, output_path)`: 下载封面图片
  - `process_douban_url(url)`: 处理豆瓣图片URL
  - `detect_image_format(content)`: 通过魔数检测图片格式

- **特性功能**:
  - 支持重试机制（可配置重试次数和间隔）
  - 自动检测图片格式（JPG/PNG）
  - 支持URL替换规则
  - 自定义User-Agent

### 7. QRCodeGenerator（二维码生成器）
**位置**: `qrcode_generator.py`

负责将索书号转换为二维码图片：

- **主要方法**:
  - `generate_qrcode(call_number, output_path)`: 生成二维码
  - `build_search_url(call_number)`: 构建检索URL
  - `create_transparent_qrcode(data)`: 创建透明背景二维码

- **特性功能**:
  - 生成透明背景的二维码
  - 支持多种错误纠正级别（L/M/Q/H）
  - 支持索书号URL编码规则
  - 生成图书馆OPAC检索链接

### 8. HTMLToImageConverter（HTML转图片转换器）
**位置**: `html_to_image_converter.py`

负责将HTML卡片转换为PNG图片：

- **主要方法**:
  - `convert_html_to_image(html_path, output_path)`: 转换HTML为图片
  - `load_html_page(page, html_path)`: 加载HTML页面
  - `take_screenshot(page, output_path)`: 截图并保存
  - `apply_border_radius(page)`: 应用圆角效果

- **特性功能**:
  - 使用Playwright浏览器引擎
  - 支持元素级截图
  - 自动应用圆角效果
  - 支持多种截图选择器
  - 支持网络空闲等待

## 业务流程

### 1. 整体流程
1. **验证输入文件**: 检查Excel文件是否存在且可读
2. **加载数据**: 读取Excel文件，统计总记录数
3. **验证必填列**: 检查必要的列是否存在
4. **筛选图书**: 选择终评结果为"通过"的图书
5. **逐本处理**: 对每本图书执行完整的卡片生成流程
6. **生成报告**: 创建执行汇总报告

### 2. 单本图书处理流程
1. **数据提取**: 从Excel行提取图书数据并验证
2. **目录创建**: 创建以条码命名的输出目录结构
3. **资源检查**: 检查已有文件，避免重复生成
4. **Logo复制**: 复制Logo文件到pic目录
5. **封面下载**: 下载图书封面图片（如果不存在）
6. **二维码生成**: 生成索书号二维码（如果不存在）
7. **HTML生成**: 填充HTML模板并保存
8. **图片转换**: 将HTML转换为PNG图片

## 配置说明

### 主要配置项
```yaml
card_generator:
  output:
    base_dir: "runtime/outputs"     # 输出基础目录
    html_extension: ".html"         # HTML文件扩展名
    image_extension: ".png"         # 图片文件扩展名
  
  fields:
    required: ["书名", "索书号"]     # 必填字段列表
    recommendation_column: "初评理由"  # 推荐语列名
    recommendation_priority_column: "人工推荐语"  # 优先推荐语列名
    truncate:                       # 截取长度配置
      "初评理由": 50
      "人工推荐语": 80
    
  filter:
    column: "终评结果"              # 筛选列名
    value: "通过"                   # 筛选值
    
  logo:
    source_dir: "data/logo"         # Logo源目录
    
  image_download:
    timeout: 30                     # 下载超时时间
    max_retries: 3                  # 最大重试次数
    retry_delay: 2                  # 重试间隔
    cover_filename: "cover"         # 封面文件名
    
  qrcode:
    filename: "qrcode.png"          # 二维码文件名
    url_template: "https://vufind.library.sh.cn/Search/Results?searchtype=vague&lookfor={call_number}&type=CallNumber"  # 检索URL模板
    
  html_to_image:
    headless: true                  # 无头模式
    viewport_width: 1200           # 视口宽度
    viewport_height: 800           # 视口高度
    device_scale_factor: 2         # 设备缩放因子
    image_format: "png"            # 图片格式
    border_radius: 8               # 圆角半径
```

## 使用方法

### 1. 命令行使用
```bash
# 从模块4生成的Excel文件生成图书卡片
python -m src.core.card_generator.card_main --excel-file "path/to/evaluation_result.xlsx"
```

### 2. 编程调用
```python
from src.core.card_generator.card_main import CardGeneratorModule
from src.utils.config_manager import get_config_manager

# 加载配置
config_manager = get_config_manager()
config = config_manager.get_config()
card_config = config.get('card_generator', {})

# 创建并运行模块
module = CardGeneratorModule(card_config)
exit_code = module.run("path/to/evaluation_result.xlsx")
```

## 输出报告

模块执行完成后会生成详细的汇总报告，包含：
- 输入文件信息
- 总记录数和通过筛选数量
- 成功、失败、警告统计
- 失败记录详情（前20条）
- 执行时间统计

报告文件保存路径：
`runtime/outputs/card_generation_report_{timestamp}.txt`

## 依赖关系

### 核心依赖
- `pandas`: Excel文件读取
- `requests`: 图片下载
- `qrcode`: 二维码生成
- `PIL (Pillow)`: 图片处理
- `playwright`: HTML转图片

### 项目依赖
- `src.utils.logger`: 日志记录
- `src.utils.config_manager`: 配置管理
- `config/card_template.html`: HTML模板文件
- `data/logo/`: Logo文件目录

## 错误处理

### 常见错误类型
1. **文件错误**: Excel文件不存在或无法读取
2. **列缺失**: Excel缺少必填列
3. **网络错误**: 图片下载失败（自动重试）
4. **文件错误**: 输出目录创建失败
5. **渲染错误**: HTML模板问题或数据格式错误
6. **浏览器错误**: Playwright截图失败

### 错误处理机制
- **重试机制**: 网络请求支持自动重试
- **优雅降级**: 部分资源失败不影响整体流程
- **详细日志**: 记录每步的执行状态和错误信息
- **错误统计**: 在最终报告中汇总所有错误
- **部分成功**: 即使某些图书失败，也会继续处理其他图书

## 扩展性

### 支持的扩展点
1. **数据源**: 可扩展支持其他数据格式（JSON、CSV等）
2. **模板系统**: 支持多模板切换和自定义模板
3. **图片格式**: 支持多种输出图片格式（PNG、JPG、SVG等）
4. **二维码**: 支持多种二维码内容和格式
5. **导出选项**: 支持不同的文件组织结构和命名规则

### 二次开发建议
- **新增数据字段**: 在`BookCardData`模型中添加字段，更新验证和模板
- **自定义筛选**: 扩展`DataValidator`的筛选逻辑
- **模板增强**: 在HTMLGenerator中添加新的模板变量
- **效果优化**: 在HTMLToImageConverter中添加新的渲染效果

---

*最后更新: 2025-11-19*
*模块版本: 1.0*
*维护者: Library AI Team*
