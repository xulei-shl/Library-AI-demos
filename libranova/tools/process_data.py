import pandas as pd
import json
from datetime import datetime
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def process_library_data(excel_path):
    # 读取Excel文件
    df = pd.read_excel(excel_path)
    
    # 检查必要的列是否存在
    required_columns = ['一级主题', '索书号']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Excel文件中缺少以下列：{', '.join(missing_columns)}")
    
    # 创建层级数据结构
    def create_hierarchy():
        hierarchy = {}
        
        # 处理一级主题
        level1_groups = df.groupby('一级主题')
        hierarchy['level1'] = []
        
        for topic, group in level1_groups:
            # 获取该主题下所有索书号的第一个字母
            call_numbers = group['索书号'].dropna()
            initial = call_numbers.iloc[0][0].upper() if not call_numbers.empty else ''
            
            hierarchy['level1'].append({
                'name': topic,
                'value': len(group),
                'initial': initial,
                'children': []
            })
        
        # 如果存在二级主题，则处理二级主题
        if '二级主题' in df.columns:
            for level1_node in hierarchy['level1']:
                level1_df = df[df['一级主题'] == level1_node['name']]
                
                # 处理二级主题
                level2_groups = level1_df.groupby('二级主题')
                level1_node['children'] = []
                
                for topic, group in level2_groups:
                    # 获取该主题下所有索书号的第一个字母
                    call_numbers = group['索书号'].dropna()
                    initial = call_numbers.iloc[0][0].upper() if not call_numbers.empty else ''
                    
                    level1_node['children'].append({
                        'name': topic,
                        'value': len(group),
                        'initial': initial,
                        'children': []
                    })
                
                # 如果存在三级主题，则处理三级主题
                if '三级主题' in df.columns:
                    for level2_node in level1_node['children']:
                        level2_df = level1_df[level1_df['二级主题'] == level2_node['name']]
                        
                        # 处理三级主题
                        level3_groups = level2_df.groupby('三级主题')
                        level2_node['children'] = []
                        
                        for topic, group in level3_groups:
                            # 获取该主题下所有索书号的第一个字母
                            call_numbers = group['索书号'].dropna()
                            initial = call_numbers.iloc[0][0].upper() if not call_numbers.empty else ''
                            
                            level2_node['children'].append({
                                'name': topic,
                                'value': len(group),
                                'initial': initial
                            })
        
        return hierarchy
    
    # 创建层级结构
    hierarchy = create_hierarchy()
    
    # 生成当前时间戳
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 构建最终的JSON数据
    result = {
        "timestamp": timestamp,
        "data": hierarchy
    }
    
    # 保存到JSON文件
    output_path = os.path.join(os.path.dirname(SCRIPT_DIR), 'data', 'library_data.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    return "数据处理成功！数据已保存到 " + output_path

if __name__ == "__main__":
    # 指定Excel文件路径
    excel_path = os.path.join(os.path.dirname(SCRIPT_DIR), 'data', 'library_data.xlsx')
    result = process_library_data(excel_path)
    print(result)
