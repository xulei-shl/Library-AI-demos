# 豆瓣图书信息爬虫

这是一个使用 Playwright 和 Python 的豆瓣图书信息爬虫项目。

## 功能特点

- 自动登录豆瓣账号
- 搜索图书信息
- 提取图书详情
- 数据保存为 Excel 格式
- 支持配置文件管理登录凭据

## 安装依赖

```bash
pip install playwright pandas openpyxl beautifulsoup4
playwright install
```

## 配置说明

项目使用 `config.json` 配置文件来管理登录凭据和其他设置。

### 配置文件结构

创建项目根目录下的 `config.json` 文件：

```json
{
  "douban": {
    "username": "your_username@163.com",
    "password": "your_password"
  },
  "scraping": {
    "headless": false,
    "timeout": 30000,
    "retry_times": 3
  }
}
```

### 重要说明

**安全提醒**: 
- 请妥善保管 `config.json` 文件，不要将其提交到版本控制系统
- 建议在 `.gitignore` 中添加 `config.json`
- 可以在环境变量中设置敏感信息，然后通过程序读取环境变量来覆盖配置文件中的默认值

## 使用方法

### 1. 准备配置文件

编辑 `config.json` 文件，填入您的豆瓣登录凭据：

```json
{
  "douban": {
    "username": "your_username@163.com",
    "password": "your_password"
  }
}
```

**⚠️ 安全提醒**: 请使用您自己的真实用户名和密码，不要使用示例中的占位符。

### 2. 运行爬虫

```python
from src.douban_spider import DoubanBookSpider

# 创建爬虫实例
spider = DoubanBookSpider(headless=False)

# 要爬取的ISBN列表
isbns = [
    "9787576022520",
    "9787301302071", 
    "9787567532694"
]

# 开始爬取
spider.crawl_books(isbns, "豆瓣图书信息.xlsx")
```

### 3. 程序会自动：

- 从 `config.json` 读取登录凭据
- 自动登录豆瓣账号
- 搜索图书信息
- 提取图书详情
- 保存到 Excel 文件

## 登录流程

程序会按以下顺序处理登录：

1. **检查配置**: 首先从 `config.json` 读取用户名和密码
2. **自动登录**: 如果 `headless=False`，程序会自动填写登录表单
3. **手动登录**: 如果自动登录失败或需要验证码，用户可以手动登录
4. **状态保持**: 登录成功后保持会话状态，后续操作无需重复登录

## 安全性改进

- ✅ **移除硬编码**: 用户名和密码不再硬编码在源代码中
- ✅ **配置分离**: 登录凭据从独立的配置文件中读取
- ✅ **灵活配置**: 可以轻松更换登录凭据而无需修改代码
- ✅ **环境适配**: 支持不同环境的配置文件

## 项目结构

```
├── config.json           # 配置文件（需要手动创建）
├── src/
│   ├── base_spider.py    # 基础浏览器管理
│   ├── login_handler.py  # 登录处理（已修改）
│   ├── search_handler.py # 搜索功能
│   ├── detail_extractor.py # 详情页提取
│   ├── data_manager.py   # 数据管理
│   └── douban_spider.py  # 主程序入口
├── README.md            # 项目说明
└── 豆瓣图书信息.xlsx     # 生成的Excel文件
```

## 注意事项

1. **首次使用**: 需要手动创建 `config.json` 文件并填入正确的登录凭据
2. **验证码处理**: 如果遇到验证码，程序会提示用户手动处理
3. **网络问题**: 如果网络较慢，可以适当增加 `timeout` 设置
4. **反爬虫**: 程序内置了延迟机制，避免被豆瓣的反爬虫机制检测

## 更新历史

- **v2.0**: 移除硬编码登录凭据，改为从配置文件读取
  - 新增 `config.json` 配置文件支持
  - 增强安全性，登录凭据不再暴露在代码中
  - 改进了登录流程的错误处理

- **v1.0**: 初始版本，包含基本的爬虫功能