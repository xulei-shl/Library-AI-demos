# 使用指南

## 快速开始

### 1. 准备工作

确保您的系统已安装：
- Python 3.8+
- pip

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 准备Excel文件

创建包含以下列的Excel文件：
- `ISBN`: ISBN列（支持各种格式）
- `题名`: 图书题名

### 4. 运行程序

```bash
python main.py data/2023年发行大码洋图书统计-馆藏部分.xlsx

python main.py data/2022年发行大码洋图书统计-馆藏部分20250107.xlsx
```

## 详细使用说明

### 命令行参数

```bash
python main.py [Excel文件路径] [选项]
```

**必需参数:**
- `excel_path`: Excel文件路径

**可选参数:**
- `--isbn-col`: 指定ISBN列名（默认: ISBN）
- `--title-col`: 指定题名列名（默认: 题名）
- `--sheet-name`: 指定工作表（默认: 0）
- `--log-level`: 日志级别 DEBUG/INFO/WARNING/ERROR（默认: INFO）
- `--log-dir`: 日志目录（默认: logs）
- `--no-real-time-save`: 禁用实时保存

### 示例命令

```bash
# 基本使用
python main.py data/books.xlsx

# 自定义列名
python main.py data/books.xlsx --isbn-col "图书编号" --title-col "书名"

# 指定工作表
python main.py data/books.xlsx --sheet-name "2024年图书"

# 调试模式
python main.py data/books.xlsx --log-level DEBUG

# 所有处理完成后统一保存
python main.py data/books.xlsx --no-real-time-save
```

## Excel文件要求

### 必需列

| 列名 | 说明 | 示例 |
|------|------|------|
| ISBN | ISBN编号 | 9787559850140, 978-7-02-015595-0, 7544258655 |
| 题名 | 图书名称 | 红楼梦, 三国演义 |

### ISBN格式支持

- ISBN-13: `9787559850140`, `978-7-02-015595-0`
- ISBN-10: `7544258655`
- 程序会自动清理连字符和空格

### 关键词提取逻辑

1. 如果ISBN列包含有效ISBN → 使用ISBN作为检索关键词
2. 如果ISBN无效 → 使用题名作为检索关键词
3. 如果都无效 → 跳过该行

## 输出结果说明

程序会在原Excel文件中添加以下列：

| 列名 | 说明 |
|------|------|
| keyword_type | 关键词类型（isbn/title） |
| keyword_value | 使用的关键词值 |
| success | 是否成功获取结果 |
| error_message | 错误信息（如果失败） |
| libraries_count | 图书馆数量 |
| 图书馆_1, 图书馆_2, ... | 图书馆名称 |

## 配置文件

您可以通过修改 `config.py` 文件来调整程序行为：

```python
DEFAULT_CONFIG = {
    # 爬虫配置
    'cinii': {
        'timeout': 30,        # 请求超时时间
        'delay': 2,           # 请求间隔
        'max_retries': 3      # 最大重试次数
    },

    # Excel配置
    'excel': {
        'real_time_save': True,      # 实时保存
        'backup_enabled': True,      # 启用备份
        'library_columns_prefix': '图书馆_'  # 图书馆列前缀
    }
}
```

## 扩展新网站

要添加新的网站爬虫：

### 1. 创建爬虫文件

在 `src/scrapers/` 目录下创建新文件，继承 `BaseScraper`：

```python
from src.core.base_scraper import BaseScraper

class NewSiteScraper(BaseScraper):
    def build_search_url(self, keyword: str) -> str:
        # 构建搜索URL
        pass

    def search_books(self, keyword: str) -> Optional[str]:
        # 搜索图书
        pass

    def get_libraries(self, detail_url: str) -> List[str]:
        # 获取图书馆信息
        pass
```

### 2. 修改主程序

在 `main.py` 中集成新爬虫：

```python
# 导入新爬虫
from src.scrapers.new_site_scraper import NewSiteScraper

# 修改BookScraperApp类
def setup_scraper(self):
    # 选择使用的爬虫
    self.scraper = NewSiteScraper(self.config.get('new_site', {}))
```

## 故障排除

### 常见问题

1. **网络连接失败**
   - 检查网络连接
   - 查看防火墙设置
   - 确认目标网站可访问

2. **Excel文件无法打开**
   - 检查文件路径是否正确
   - 确认文件格式为.xlsx或.xls
   - 确保文件没有被其他程序占用

3. **没有搜索结果**
   - 检查ISBN是否有效
   - 确认题名是否准确
   - 查看目标网站是否有相关数据

4. **程序运行缓慢**
   - 增加请求间隔时间
   - 减少同时处理的行数
   - 检查网络速度

### 日志分析

查看 `logs/` 目录下的日志文件：

```bash
# 查看主程序日志
tail -f logs/BookScraperApp_YYYYMMDD.log

# 查看爬虫日志
tail -f logs/CiNiiScraper_YYYYMMDD.log
```

### 调试模式

使用DEBUG级别日志获取详细信息：

```bash
python main.py your_file.xlsx --log-level DEBUG
```

## 性能优化建议

1. **批量处理**: 对于大量数据，考虑分批处理
2. **并发控制**: 适当调整请求间隔
3. **网络优化**: 使用稳定的网络连接
4. **存储优化**: 定期清理日志文件

## 注意事项

1. **合规使用**: 遵守目标网站的使用条款
2. **请求频率**: 不要对目标网站造成过大压力
3. **数据备份**: 重要数据建议提前备份
4. **法律合规**: 确保爬取行为符合相关法律法规