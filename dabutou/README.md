# 图书馆藏信息爬虫

一个模块化的Python爬虫系统，用于从Excel文件中提取ISBN/题名信息，并在指定网站检索图书馆藏信息。

## 功能特性

- **模块化设计**: 高内聚低耦合的模块结构
- **多网站支持**: 易于扩展支持多个检索网站
- **实时保存**: 每处理一行立即保存结果
- **错误处理**: 完善的错误处理和日志记录
- **智能关键词**: 自动识别ISBN或题名作为检索关键词
- **结果去重**: 自动去重图书馆名称

## 项目结构

```
dabutou/
├── src/                    # 源代码目录
│   ├── core/              # 核心模块
│   │   ├── base_scraper.py    # 爬虫基类
│   │   └── keyword_processor.py  # 关键词处理器
│   ├── scrapers/          # 网站爬虫模块
│   │   └── cinii_scraper.py     # CiNii网站爬虫
│   └── utils/             # 工具模块
│       ├── excel_reader.py      # Excel读取器
│       ├── excel_writer.py      # Excel写入器
│       └── logger_config.py     # 日志配置
├── data/                  # 数据目录
├── logs/                  # 日志目录
├── main.py               # 主程序入口
├── config.py             # 配置文件
├── requirements.txt      # 依赖包
└── README.md            # 说明文档
```

## 安装说明

### 1. 安装Python依赖

```bash
pip install -r requirements.txt
```

### 2. 准备Excel文件

确保Excel文件包含以下列：
- `ISBN`: ISBN列（支持ISBN-10和ISBN-13格式）
- `题名`: 图书题名列

## 使用方法

### 命令行使用

```bash
# 基本用法
python main.py data/your_file.xlsx

# 指定列名
python main.py data/your_file.xlsx --isbn-col "ISBN编号" --title-col "书名"

# 指定工作表
python main.py data/your_file.xlsx --sheet-name "Sheet1"

# 设置日志级别
python main.py data/your_file.xlsx --log-level DEBUG

# 禁用实时保存（所有处理完成后统一保存）
python main.py data/your_file.xlsx --no-real-time-save
```

### 参数说明

- `excel_path`: Excel文件路径（必需）
- `--isbn-col`: ISBN列名（默认: ISBN）
- `--title-col`: 题名列名（默认: 题名）
- `--sheet-name`: 工作表名称或索引（默认: 0）
- `--log-level`: 日志级别 DEBUG/INFO/WARNING/ERROR（默认: INFO）
- `--log-dir`: 日志目录（默认: logs）
- `--no-real-time-save`: 禁用实时保存

### 编程方式使用

```python
from main import BookScraperApp

# 创建应用实例
config = {
    'log_dir': 'logs',
    'cinii': {
        'timeout': 30,
        'delay': 2,
        'max_retries': 3
    }
}

app = BookScraperApp(config)

# 运行爬虫
success = app.run(
    excel_path='data/your_file.xlsx',
    isbn_col='ISBN',
    title_col='题名',
    sheet_name=0,
    real_time_save=True
)
```

## 输出结果

程序会在原Excel文件中添加以下列：

- `keyword_type`: 关键词类型（isbn/title）
- `keyword_value`: 使用的关键词值
- `success`: 是否成功获取结果
- `error_message`: 错误信息（如果失败）
- `libraries_count`: 图书馆数量
- `图书馆_1`, `图书馆_2`, ...: 图书馆名称

## 扩展新网站

要添加新的网站爬虫，只需要：

1. 在 `src/scrapers/` 目录下创建新的爬虫类
2. 继承 `BaseScraper` 基类
3. 实现必需的抽象方法：

```python
from src.core.base_scraper import BaseScraper

class NewSiteScraper(BaseScraper):
    def build_search_url(self, keyword: str) -> str:
        # 构建搜索URL
        pass

    def search_books(self, keyword: str) -> Optional[str]:
        # 搜索图书，获取详情页URL
        pass

    def get_libraries(self, detail_url: str) -> List[str]:
        # 获取图书馆信息
        pass
```

4. 在主程序中注册新爬虫

## 注意事项

1. **请求频率**: 程序已内置延迟机制，避免对目标网站造成过大压力
2. **网络问题**: 网络连接问题时会自动重试
3. **文件备份**: 程序会自动备份原Excel文件
4. **编码问题**: 确保Excel文件使用UTF-8编码

## 错误处理

- 网络连接失败会自动重试
- 每行处理错误不会影响其他行的处理
- 详细的错误日志记录
- 自动创建文件备份

## 日志记录

程序会在 `logs/` 目录下生成日志文件：
- `BookScraperApp_YYYYMMDD.log`: 主程序日志
- `CiNiiScraper_YYYYMMDD.log`: 爬虫日志

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。