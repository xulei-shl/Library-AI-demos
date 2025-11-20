# ISBN查重逻辑优化

## 修改时间
2025-11-20

## 问题描述

在FOLIO ISBN爬取流程中,数据库查重逻辑使用了豆瓣爬取的查重方法,导致以下问题:

1. **查重字段错误**: 检查的是`douban_url`字段,而不是`isbn`字段
2. **误判过期数据**: 即使`isbn`字段有值,但因为`douban_url`为空,仍被标记为"需要重新爬取"
3. **不必要的爬取**: 导致已有ISBN数据的记录被重复爬取

### 问题日志示例

```
时间=2025-11-20 15:48:06 | 信息=检测到 1744 条记录的ISBN列已存在合法值,将跳过后续处理
时间=2025-11-20 15:48:06 | 信息=执行数据库查重...
时间=2025-11-20 15:48:06 | 信息=查重完成: 0条有效, 54条需爬取, 0条新数据
时间=2025-11-20 15:48:06 | 信息=需要重新爬取的记录数: 54 条
```

**问题**: 这54条记录的`isbn`字段明明有值,但因为`douban_url`为空,被错误标记为需要重新爬取。

## 解决方案

### 核心思路

为ISBN爬取和豆瓣爬取创建**独立的查重逻辑**:

- **ISBN爬取**: 只检查`isbn`字段是否有值
- **豆瓣爬取**: 检查`douban_url`字段和过期时间(保持原逻辑)

### 代码修改

#### 1. `database_manager.py` - 新增ISBN查重方法

新增 `batch_check_isbn_duplicates()` 方法:

```python
def batch_check_isbn_duplicates(self, barcodes: List[str]) -> Dict:
    """
    批量查重ISBN数据 (专用于ISBN爬取阶段)
    
    分类逻辑:
    - existing_valid: 数据库中存在且isbn字段有值
    - existing_stale: 空列表(ISBN查重不需要此分类)
    - new: 数据库中不存在或isbn字段为空
    """
```

**关键逻辑**:
```python
for barcode in barcodes:
    if barcode in existing_dict:
        book_data = existing_dict[barcode]
        isbn = book_data.get('isbn', '')
        
        # 只检查isbn字段是否有值
        if isbn and str(isbn).strip() not in ['', 'nan', 'None']:
            result['existing_valid'].append({
                'barcode': barcode,
                'data': book_data
            })
        else:
            result['new'].append(barcode)
    else:
        result['new'].append(barcode)
```

#### 2. `data_checker.py` - 新增ISBN查重分类方法

新增 `check_and_categorize_isbn_books()` 方法:

```python
def check_and_categorize_isbn_books(self, excel_data: List[Dict]) -> Dict:
    """
    检查并分类书籍 (专用于ISBN爬取阶段)
    
    返回:
    {
        'existing_valid': [...],  # ISBN已存在,从DB直接获取
        'existing_stale': [],     # ISBN查重不使用此分类
        'new': [...]              # ISBN不存在,需要爬取
    }
    """
```

#### 3. `folio_isbn_async_processor.py` - 使用新的查重方法

修改查重调用:

```python
# 修改前
categories = self.data_checker.check_and_categorize_books(excel_data)

# 修改后
categories = self.data_checker.check_and_categorize_isbn_books(excel_data)
```

修改数据处理逻辑:

```python
# 修改前: 处理 existing_stale + new
all_books_to_process = categories['existing_stale'] + categories['new']

# 修改后: 只处理 new
all_books_to_process = categories['new']
```

## 修改影响

### 正面影响

1. **准确的查重**: 只检查`isbn`字段,不受豆瓣字段影响
2. **避免重复爬取**: 已有ISBN的记录不会被重复爬取
3. **提高效率**: 减少不必要的网络请求
4. **逻辑清晰**: ISBN和豆瓣查重逻辑分离,职责明确

### 兼容性

- ✅ **豆瓣爬取逻辑**: 保持不变,仍使用 `batch_check_duplicates()` 和 `check_and_categorize_books()`
- ✅ **向后兼容**: 新增方法,不影响现有代码
- ✅ **数据库结构**: 无需修改数据库表结构

## 验证方法

运行ISBN爬取流程,观察日志:

```
时间=2025-11-20 XX:XX:XX | 信息=执行ISBN数据库查重...
时间=2025-11-20 XX:XX:XX | 信息=ISBN查重完成: 已有ISBN=1744, 需爬取ISBN=54
时间=2025-11-20 XX:XX:XX | 信息=需要爬取ISBN的记录数: 54 条
```

**预期结果**:
- 已有ISBN的记录数量应该与Excel中ISBN列有值的记录数量一致
- 只有ISBN为空的记录才会被标记为需要爬取

## 相关文件

- `src/core/douban/database/database_manager.py`
- `src/core/douban/database/data_checker.py`
- `src/core/douban/folio_isbn_async_processor.py`
