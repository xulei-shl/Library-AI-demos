import requests
import json
import re
import pandas as pd
import time
from tqdm import tqdm
import os
import shutil
from datetime import datetime

def extract_subject_id(douban_url):
    """从豆瓣链接中提取subject ID"""
    match = re.search(r'/subject/(\d+)/', douban_url)
    return match.group(1) if match else None

def get_douban_subject(subject_id: str):
    """根据豆瓣 subject ID 获取其详细信息"""
    url = f"https://m.douban.com/rexxar/api/v2/subject/{subject_id}"
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Connection': 'keep-alive',
        'Referer': 'https://m.douban.com/',
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"获取ID {subject_id} 失败: {str(e)}")
        return None

def process_douban_data(data):
    """处理豆瓣API返回的数据"""
    if not data:
        return {}
    
    # 安全获取列表第一个元素的辅助函数
    def get_first_item(field):
        if isinstance(field, list) and field:
            return field[0]
        return ''  # 空列表或None都返回空字符串
    
    # 安全获取嵌套字典值的辅助函数
    def safe_get(obj, key, default=''):
        if obj is None:
            return default
        value = obj.get(key, default)
        # 如果值是空列表，返回空字符串
        if value == []:
            return ''
        return value
    
    # 处理作者和译者（多值用' / '连接）
    author_list = data.get('author', [])
    author = ' / '.join(author_list) if author_list else ''
    
    translator_list = data.get('translator', [])
    translator = ' / '.join(translator_list) if translator_list else ''
    
    # 处理副标题
    subtitle_list = data.get('subtitle', [])
    subtitle = ' '.join(subtitle_list) if subtitle_list else ''
    
    # 安全处理可能为非列表的字段
    press = get_first_item(data.get('press'))
    producer = get_first_item(data.get('producers'))
    pubdate = get_first_item(data.get('pubdate'))
    pages = get_first_item(data.get('pages'))
    price = get_first_item(data.get('price'))
    
    # 安全处理丛书信息
    book_series = data.get('book_series')
    series_title = safe_get(book_series, 'title')
    series_url = safe_get(book_series, 'url')
    
    # 安全处理评分信息
    rating = data.get('rating', {})
    rating_value = safe_get(rating, 'value', 0)
    rating_count = safe_get(rating, 'count', 0)
    
    # 安全处理所有字段，确保空列表转换为空字符串
    return {
        "豆瓣评分": rating_value if rating_value else 0,  # 评分保持数字
        "豆瓣书名": safe_get(data, 'title'),
        "豆瓣副标题": subtitle,
        "豆瓣原作名": safe_get(data, 'origin_title'),
        "豆瓣作者": author,
        "豆瓣译者": translator,
        "豆瓣出版社": press,
        "豆瓣出品方": producer,
        "豆瓣丛书": series_title,
        "豆瓣丛书链接": series_url,
        "豆瓣定价": price,
        "豆瓣ISBN": safe_get(data, 'isbn'),
        "豆瓣页数": pages,
        "豆瓣装帧": safe_get(data, 'binding'),
        "豆瓣出版年": pubdate,
        "豆瓣评价人数": rating_count if rating_count else 0,  # 评价人数保持数字
        "豆瓣封面图片链接": safe_get(data, 'cover_url'),
        "豆瓣内容简介": safe_get(data, 'intro'),
        "豆瓣作者简介": safe_get(data, 'author_intro'),
        "豆瓣目录": safe_get(data, 'catalog')
    }

def create_backup(file_path):
    """创建Excel文件的备份"""
    if not os.path.exists(file_path):
        return None
    
    # 创建备份文件名（添加时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name, ext = os.path.splitext(file_path)
    backup_path = f"{base_name}_backup_{timestamp}{ext}"
    
    try:
        shutil.copy2(file_path, backup_path)
        print(f"已创建备份文件: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"创建备份失败: {str(e)}")
        return None

def process_excel(file_path, create_backup_file=True):
    """处理Excel文件并直接保存"""
    # 检查文件是否存在
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    # 创建备份
    backup_path = None
    if create_backup_file:
        backup_path = create_backup(file_path)
    
    # 读取Excel文件
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        raise ValueError(f"读取Excel文件失败: {str(e)}")
    
    # 检查是否包含豆瓣链接列
    if '豆瓣链接' not in df.columns:
        raise ValueError("Excel文件中必须包含'豆瓣链接'列")
    
    # 创建所有需要添加的列（如果不存在）
    new_columns = [
        "豆瓣评分", "豆瓣书名", "豆瓣副标题", "豆瓣原作名", "豆瓣作者", 
        "豆瓣译者", "豆瓣出版社", "豆瓣出品方", "豆瓣丛书", "豆瓣丛书链接",
        "豆瓣定价", "豆瓣ISBN", "豆瓣页数", "豆瓣装帧", "豆瓣出版年",
        "豆瓣评价人数", "豆瓣封面图片链接", "豆瓣内容简介", 
        "豆瓣作者简介", "豆瓣目录"
    ]
    
    for col in new_columns:
        if col not in df.columns:
            df[col] = None
    
    # 统计信息
    total_rows = len(df)
    processed_count = 0
    success_count = 0
    
    print(f"开始处理文件: {file_path}")
    print(f"总行数: {total_rows}")
    
    # 使用tqdm显示进度条
    for index, row in tqdm(df.iterrows(), total=total_rows, desc="处理进度"):
        douban_url = row['豆瓣链接']
        if pd.isna(douban_url) or not douban_url:
            continue
            
        processed_count += 1
        
        # 提取subject ID
        subject_id = extract_subject_id(douban_url)
        if not subject_id:
            print(f"行 {index + 2}: 无法从链接中提取ID: {douban_url}")
            continue
        
        # 获取豆瓣数据
        data = get_douban_subject(subject_id)
        if not data:
            print(f"行 {index + 2}: 获取数据失败 (ID: {subject_id})")
            continue
        
        # 处理数据
        try:
            processed_data = process_douban_data(data)
            
            # 将数据写入DataFrame
            for key, value in processed_data.items():
                df.at[index, key] = value
            
            success_count += 1
            print(f"行 {index + 2}: 成功获取数据 (ID: {subject_id})")
        except Exception as e:
            print(f"行 {index + 2}: 处理数据时出错 (ID: {subject_id}): {str(e)}")
            # 打印API返回的数据以便调试
            print(f"API返回数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        # 避免请求过于频繁
        time.sleep(1)
    
    # 保存结果到原文件
    try:
        df.to_excel(file_path, index=False)
        print(f"\n处理完成！")
        print(f"处理行数: {processed_count}")
        print(f"成功获取: {success_count}")
        print(f"结果已保存到原文件: {file_path}")
        if create_backup_file and backup_path:
            print(f"备份文件: {backup_path}")
    except Exception as e:
        print(f"保存文件失败: {str(e)}")
        if create_backup_file and backup_path:
            print(f"可以从备份文件恢复: {backup_path}")
        raise

if __name__ == "__main__":
    # 使用说明
    print("=" * 50)
    print("豆瓣图书信息批量获取工具")
    print("=" * 50)
    print("功能：从Excel中的豆瓣链接获取图书信息并直接保存到原文件")
    print("注意：程序会自动创建备份文件")
    print("=" * 50)
    
    # 输入Excel文件路径
    excel_file = input("请输入Excel文件路径（或直接回车使用默认路径）: ").strip()
    if not excel_file:
        excel_file = r"F:\Github\Library-AI-demos\book-echoes\runtime\outputs\1.xlsx"
    
    # 确认处理
    confirm = input(f"\n确认处理文件 '{excel_file}' 吗？(y/n): ").strip().lower()
    if confirm != 'y':
        print("操作已取消")
        exit()
    
    try:
        process_excel(excel_file, create_backup_file=True)
    except Exception as e:
        print(f"\n处理过程中发生错误: {str(e)}")
        print("请检查文件路径和格式是否正确")