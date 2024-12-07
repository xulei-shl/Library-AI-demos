import pandas as pd
import os

# Get the script directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))

# 读取Excel文件
def read_excel_sheets(file_path, sheet_names):
    # First check available sheets
    xl = pd.ExcelFile(file_path)
    available_sheets = xl.sheet_names
    print(f"Available sheets in the Excel file: {available_sheets}")
    
    # Verify all requested sheets exist
    for sheet in sheet_names:
        if sheet not in available_sheets:
            raise ValueError(f"Sheet '{sheet}' not found. Available sheets are: {available_sheets}")
    
    return {sheet_name: pd.read_excel(file_path, sheet_name=sheet_name) for sheet_name in sheet_names}

# 处理范围代码
def expand_range_codes(df_mapping):
    expanded_codes = []
    for code in df_mapping['代码']:
        if '/' in code:
            start, end = code.split('/')
            for i in range(int(start[1:]), int(end[1:]) + 1):
                expanded_codes.append(f"{start[0]}{i}")
        else:
            expanded_codes.append(code)
    df_mapping['代码'] = expanded_codes
    return df_mapping

# 创建映射字典
def create_mapping_dict(df_mapping):
    mapping_dict = {}
    for code, subject in zip(df_mapping['代码'], df_mapping['主题']):
        # 添加完整代码
        mapping_dict[code] = subject
        # 添加前缀（如果前缀不存在）
        for i in range(1, len(code)):
            prefix = code[:i]
            if prefix not in mapping_dict:
                mapping_dict[prefix] = subject
    return mapping_dict

# 分类函数
def classify_book(book_id, mapping_dict):
    # 只取前三个字符进行匹配
    prefix = book_id[:3]
    
    # 依次尝试前三位、前两位、第一位
    for length in range(len(prefix), 0, -1):
        current_prefix = prefix[:length]
        if current_prefix in mapping_dict:
            return mapping_dict[current_prefix]
    
    return '其他'

# 批量保存数据到Excel
def save_batch_to_excel(df, start_idx, end_idx, file_path, sheet_name='Sheet1'):
    try:
        # 如果文件不存在，先保存整个DataFrame
        if not os.path.exists(file_path):
            df.to_excel(file_path, sheet_name=sheet_name, index=False)
            return True
        
        # 读取现有的Excel文件
        with pd.ExcelWriter(file_path, mode='a', if_sheet_exists='overlay') as writer:
            # 获取要更新的批次数据
            batch_data = df.iloc[start_idx:end_idx]
            # 更新指定行的数据
            start_row = start_idx + 1  # 加1是因为Excel有标题行
            batch_data.to_excel(writer, sheet_name=sheet_name, startrow=start_row, 
                            header=False, index=False)
        return True
    except Exception as e:
        print(f"保存批次数据时出错: {str(e)}")
        return False

# 保存单行数据到Excel
def save_row_to_excel(df, index, file_path, sheet_name='Sheet1'):
    try:
        # 如果文件不存在，先保存整个DataFrame
        if not os.path.exists(file_path):
            df.to_excel(file_path, sheet_name=sheet_name, index=False)
            return True
        
        # 读取现有的Excel文件
        book = pd.read_excel(file_path, sheet_name=None)
        with pd.ExcelWriter(file_path, mode='a', if_sheet_exists='overlay') as writer:
            # 获取要更新的行
            row_data = df.iloc[[index]]
            # 更新指定行的数据
            start_row = index + 1  # 加1是因为Excel有标题行
            row_data.to_excel(writer, sheet_name=sheet_name, startrow=start_row, 
                            header=False, index=False)
        return True
    except Exception as e:
        print(f"保存行数据时出错: {str(e)}")
        return False

# 应用分类函数
def apply_classification(df_books, mapping_dicts, column_names, output_file=None):
    total_records = len(df_books)
    batch_size = 1000  # 设置批处理大小
    
    for column_name, mapping_dict in zip(column_names, mapping_dicts):
        # 预分配结果列
        df_books[column_name] = '其他'
        
        for batch_start in range(0, total_records, batch_size):
            batch_end = min(batch_start + batch_size, total_records)
            
            # 批量处理数据
            batch_ids = df_books.iloc[batch_start:batch_end]['索书号']
            classifications = [classify_book(book_id, mapping_dict) for book_id in batch_ids]
            df_books.loc[batch_start:batch_end-1, column_name] = classifications
            
            # 每1000条数据打印一次进度
            print(f"正在处理: {batch_end}/{total_records} 条数据 ({(batch_end/total_records*100):.1f}%)")
            
            # 如果提供了输出文件路径，则批量保存数据
            if output_file:
                save_batch_to_excel(df_books, batch_start, batch_end, output_file)
    
    return df_books

def main():
    file_path = os.path.join(os.path.dirname(SCRIPT_DIR), 'data', 'library_data.xlsx')
    sheet_names = ['sheet1', '一级']
    
    # 读取数据
    sheets = read_excel_sheets(file_path, sheet_names)
    df_books = sheets['sheet1']
    df_mapping = sheets['一级']
    
    # 处理范围代码
    df_mapping = expand_range_codes(df_mapping)
    
    # 创建映射字典
    mapping_dict = create_mapping_dict(df_mapping)
    
    # 应用分类函数
    output_file = os.path.join(os.path.dirname(SCRIPT_DIR), 'data', 'output.xlsx')
    df_books = apply_classification(df_books, [mapping_dict], ['一级主题'], output_file)

if __name__ == "__main__":
    main()