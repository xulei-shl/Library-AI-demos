# 书籍封面生成器

## 概述
该项目旨在基于从 PostgreSQL 数据库中检索到的书籍信息生成书籍封面 SVG。该过程包括使用条形码提取书籍详细信息，将提取的信息转换为 Markdown 表格格式，然后使用书籍的详细信息生成 SVG 卡片。

## 组件

### 1. `main.py`
该脚本是应用程序的入口点。它使用条形码检索书籍信息，生成 SVG 卡片，并将其保存到指定目录。

#### 主要功能：
- **`item_folio_sql_search(barcode)`**：根据提供的条形码查询数据库以获取书籍信息。
- **`book_card(book_info)`**：使用书籍信息生成 SVG 卡片。

### 2. `folio_books_info.py`
该模块处理数据库交互并将 SQL 查询结果转换为 Markdown 表格格式。

#### 主要功能：
- **`sql_results_to_markdown(results)`**：将 SQL 查询结果转换为 Markdown 表格格式。
- **`item_folio_sql_search(barcode)`**：根据提供的条形码查询数据库以获取书籍信息。
- **`instance_folio_sql_search(id)`**：使用实例 ID 获取详细的书籍信息。

### 3. `text_cards.py`
该模块负责使用书籍信息生成 SVG 卡片。

#### 主要功能：
- **`book_card(content)`**：使用书籍信息生成 SVG 卡片。
- **`book_depiction(content)`**：使用 SVG 创建书籍的视觉描述。
- **`extract_json_content(result)`**：从结果中提取 SVG 内容。

## 设置

### 环境变量
请确保在 `.env` 文件中设置以下环境变量：
- `DB_NAME`: 数据库名称
- `DB_USER`: 数据库用户
- `DB_PASSWORD`: 数据库密码
- `DB_HOST`: 数据库主机
- `DB_PORT`: 数据库端口
- `API_KEY`: 语言模型的 API 密钥
- `BASE_URL`: 语言模型的基本 URL

### 安装
1. 克隆代码库。
2. 安装所需的依赖项：
   ```bash
   pip install -r requirements.txt
   ```
3. 使用必要的环境变量设置 `.env` 文件。

### 运行应用程序
执行 `main.py` 脚本生成书籍封面 SVG: