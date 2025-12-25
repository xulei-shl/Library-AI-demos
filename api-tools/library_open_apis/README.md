# 书目数据 API 示例代码集合

本目录包含从 [BookReconciler](https://github.com/your-repo/BookReconciler) 项目中提取的 7 个主流书目数据库 API 调用示例。

这些示例代码是从原始 `lib/strategies_*.py` 文件中提取并简化而来，可直接在其他项目中参考使用。

## 目录结构

```
library_open_apis/
├── 01_google_books.py      # Google Books API
├── 02_id_loc_gov.py        # Library of Congress (id.loc.gov) API
├── 03_oclc_worldcat.py     # OCLC WorldCat API
├── 04_viaf.py              # VIAF (Virtual International Authority File)
├── 05_wikidata.py          # Wikidata SPARQL API
├── 06_hathitrust.py        # HathiTrust (本地数据库)
├── 07_openlibrary.py       # Open Library API
└── README.md               # 本文档
```

## API 概览

| # | API | 类型 | 认证 | 主要功能 |
|---|-----|------|------|---------|
| 1 | [Google Books](#1-google-books) | 公共 | 无 | 书籍元数据、ISBN、描述 |
| 2 | [id.loc.gov](#2-library-of-congress) | 公共 | 无 | 作品搜索、主题词、LCCN |
| 3 | [OCLC WorldCat](#3-oclc-worldcat) | 需要密钥 | OAuth | 书目搜索、Work ID 聚类 |
| 4 | [VIAF](#4-viaf) | 公共 | 无 | 权威名称、跨库整合 |
| 5 | [Wikidata](#5-wikidata) | 公共 | 无 | SPARQL 查询、实体链接 |
| 6 | [HathiTrust](#6-hathitrust) | 本地 DB | 无 | 本地搜索、HDL 标识符 |
| 7 | [Open Library](#7-open-library) | 公共 | 无 | 作品搜索、版本信息 |

## 依赖安装

```bash
pip install requests thefuzz
```

对于 HathiTrust，还需要 SQLite3 支持（Python 标准库已包含）。

## 详细说明

### 1. Google Books

**文件**: `01_google_books.py`

**API 端点**: `https://www.googleapis.com/books/v1/volumes`

**功能**:
- 通过标题和作者搜索书籍
- 获取书籍元数据（标题、作者、描述、ISBN、出版信息等）
- 使用 fuzzy matching 进行相似度评分

**使用示例**:

```python
from 01_google_books import search_google_books, search_and_score

# 简单搜索
results = search_google_books("The Great Gatsby", "F. Scott Fitzgerald")

# 搜索并评分
scored = search_and_score("1984", "George Orwell", quality_threshold='medium')

# 获取单本书详情
details = get_book_details("volume_id")
```

---

### 2. Library of Congress (id.loc.gov)

**文件**: `02_id_loc_gov.py`

**API 端点**: `https://id.loc.gov/resources/works/suggest2`

**功能**:
- 搜索 Library of Congress 作品资源
- 获取完整的书目元数据（RDF/XML）
- 通过 CBD 端点获取丰富数据

**使用示例**:

```python
from 02_id_loc_gov import search_id_loc, enrich_with_cbd

# 搜索
results = search_id_loc("Moby Dick", "Herman Melville")

# 获取丰富数据
enriched = enrich_with_cbd(instance_uri)
```

---

### 3. OCLC WorldCat

**文件**: `03_oclc_worldcat.py`

**API 端点**: `https://americas.discovery.api.oclc.org/worldcat/search/v2/bibs`

**功能**:
- 搜索 WorldCat 书目数据库
- 需要 OAuth 认证
- 支持 Work ID 聚类

**使用示例**:

```python
from 03_oclc_worldcat import WorldCatClient, search_with_scoring

# 创建客户端（需要环境变量设置）
client = WorldCatClient(
    client_id=os.environ.get('OCLC_CLIENT_ID'),
    secret=os.environ.get('OCLC_SECRET')
)

# 搜索并评分
results = search_with_scoring(client, "Pride and Prejudice", "Jane Austen")
```

**环境变量**:
- `OCLC_CLIENT_ID`: OCLC Client ID
- `OCLC_SECRET`: OCLC Secret

---

### 4. VIAF

**文件**: `04_viaf.py`

**API 端点**: `https://viaf.org/api/search`

**功能**:
- 搜索权威名称记录
- 搜索作品记录
- 获取跨图书馆的权威数据

**使用示例**:

```python
from 04_viaf import search_names, search_works, parse_name_results

# 搜索个人名称
results = search_names("Shakespeare, William", name_type="VIAF_Personal")

# 解析结果
parsed = parse_name_results(results, "Shakespeare, William", birth_year="1564")
```

---

### 5. Wikidata

**文件**: `05_wikidata.py`

**API 端点**: `https://query.wikidata.org/sparql`

**功能**:
- 使用 SPARQL 查询 Wikidata
- EntitySearch 实体搜索
- 通过 ISBN 查找实体

**使用示例**:

```python
from 05_wikidata import entity_search, search_by_isbn, parse_search_results

# 实体搜索
results = entity_search("1984")

# 通过 ISBN 搜索
isbn_results = search_by_isbn("9780743273565")

# 解析并评分
parsed = parse_search_results(results, "1984", "George Orwell")
```

---

### 6. HathiTrust

**文件**: `06_hathitrust.py`

**说明**: HathiTrust 没有公共 API，需要使用本地数据库

**功能**:
- 使用 SQLite FTS5 进行全文搜索
- 获取 HDL、LCCN、OCLC 等标识符
- 生成封面缩略图 URL

**使用示例**:

```python
from 06_hathitrust import search_local_hathi_db, build_db_from_files

# 构建数据库（从数据文件）
build_db_from_files(data_dir="./hathitrust_data", db_path="./hathitrust.db")

# 搜索
results = search_local_hathi_db("Moby Dick", "Herman Melville",
                                db_path="./hathitrust.db")

# 搜索并评分
scored = search_and_score("Pride and Prejudice", "Jane Austen",
                          db_path="./hathitrust.db")
```

**注意**: 需要预先下载 HathiTrust 数据库转储文件（TSV 格式）。

---

### 7. Open Library

**文件**: `07_openlibrary.py`

**API 端点**: `https://openlibrary.org/search.json`

**功能**:
- 搜索作品和作者
- 获取作品详情和版本信息
- 获取封面图片

**使用示例**:

```python
from 07_openlibrary import search_works, get_work, get_work_editions

# 搜索作品
results = search_works("The Great Gatsby", "F. Scott Fitzgerald")

# 获取作品详情
work_data = get_work("OL45804W")

# 获取所有版本
editions = get_work_editions("OL45804W")

# 扩展作品数据
extended = extend_work_data("OL45804W", properties=['description', 'subjects', 'isbn_13'])
```

## 通用函数

每个文件都包含以下通用函数：

| 函数 | 说明 |
|-----|------|
| `search_*()` | 执行 API 搜索 |
| `calculate_fuzzy_score()` | 计算模糊匹配分数 |
| `parse_*_results()` | 解析并评分搜索结果 |
| `get_*()` | 获取单个实体的详细信息 |

## 评分系统

所有 API 都使用类似的评分系统（基于 thefuzz 库的 Levenshtein 距离）：

| 分数范围 | 质量等级 |
|---------|---------|
| 0.95+ | Very High |
| 0.90+ | High |
| 0.80+ | Medium |
| 0.60+ | Low |
| 0.30+ | Very Low |

## 注意事项

1. **速率限制**: 大多数 API 都有速率限制，建议适当添加延迟
2. **认证**: OCLC 需要 API 密钥，其他为公共 API
3. **数据完整性**: 不同的 API 返回的数据字段和完整性不同
4. **HathiTrust**: 需要本地数据库，不支持在线 API

## 许可证

本项目基于 BookReconciler 项目，遵循相同的许可证。
