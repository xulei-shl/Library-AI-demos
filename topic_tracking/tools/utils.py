import pandas as pd

def read_csv(file_path):
    encodings = ['utf-8', 'gbk', 'gb2312', 'iso-8859-1']
    for encoding in encodings:
        try:
            return pd.read_csv(file_path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"无法使用常见编码读取文件 {file_path}。请检查文件编码。")

def search_data(df, conditions):
    query = ''
    for condition in conditions:
        column, keyword, logic = condition
        if keyword:
            if logic == '与':
                query += f"({column}.str.contains('{keyword}', case=False, na=False)) & "
            elif logic == '或':
                query += f"({column}.str.contains('{keyword}', case=False, na=False)) | "
            elif logic == '非':
                query += f"~({column}.str.contains('{keyword}', case=False, na=False)) & "
    query = query.rstrip(' & | ')
    if query:
        return df.query(query)
    return df