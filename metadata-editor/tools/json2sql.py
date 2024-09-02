import json
import sqlite3
import os
from datetime import datetime
import create_database


# def create_database(db_path):
#     conn = sqlite3.connect(db_path)
#     cursor = conn.cursor()
    
#     # 创建主表
#     cursor.execute('''
#     CREATE TABLE IF NOT EXISTS main_table (
#         id TEXT PRIMARY KEY,
#         json_data TEXT,
#         ocr_data TEXT,
#         md_data TEXT,
#         createdat TEXT,
#         updatedat TEXT,
#         current_version INTEGER
#     )
#     ''')
    
#     # 创建版本历史表
#     cursor.execute('''
#     CREATE TABLE IF NOT EXISTS version_history (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         data_id TEXT,
#         version INTEGER,
#         json_data TEXT,
#         createdat TEXT,
#         updatedat TEXT
#     )
#     ''')
    
#     conn.commit()
#     conn.close()

def insert_data(db_path, json_data, excel_file):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for item in json_data:
        performing_event = item['performingEvent']
        data_id = performing_event['id']
        data_json = json.dumps(item, ensure_ascii=False)
        createdat = datetime.now().isoformat()
        updatedat = createdat
        
        # Extract base_id by removing any suffix after the last underscore
        base_id = '-'.join(data_id.split('-')[:-1]) if '-' in data_id else data_id   
             
        # Construct file paths for md_data and ocr_data
        md_file_path = os.path.join(excel_file, f"{base_id}_md_final_result.md")
        ocr_file_path = os.path.join(excel_file, f"{base_id}_ocr_1_final_result.md")
        
        # Read md_data and ocr_data from the files
        with open(md_file_path, 'r', encoding='utf-8') as md_file:  # Specify UTF-8 encoding
            md_data = md_file.read()
        
        with open(ocr_file_path, 'r', encoding='utf-8') as ocr_file:
            ocr_data = ocr_file.read()
        
        # Check if the record exists in the main table
        cursor.execute('SELECT * FROM main_table WHERE id = ?', (data_id,))
        existing_record = cursor.fetchone()
        
        if existing_record:
            print(f"Duplicate ID found: {data_id}. Skipping insertion.")
        else:
            current_version = 1
            
            # Insert into the main table
            cursor.execute('''
            INSERT INTO main_table (id, json_data, ocr_data, md_data, createdat, updatedat, current_version)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (data_id, data_json, ocr_data, md_data, createdat, updatedat, current_version))
            
            # Insert into the version history table
            cursor.execute('''
            INSERT INTO version_history (data_id, version, json_data, createdat, updatedat)
            VALUES (?, ?, ?, ?, ?)
            ''', (data_id, current_version, data_json, createdat, updatedat))
    
    conn.commit()
    conn.close()

def json_sqlite(excel_file, logger):
    db_folder = os.path.join(excel_file, 'database')
    if not os.path.exists(db_folder):
        os.makedirs(db_folder)
    
    db_path = os.path.join(db_folder, 'database.db')
    create_database.init_db(db_path)
    
    json_file = [f for f in os.listdir(excel_file) if f.startswith('results_') and f.endswith('.json')][0]
    json_path = os.path.join(excel_file, json_file)
    
    with open(json_path, 'r', encoding='utf-8') as f:  # Specify UTF-8 encoding
        json_data = json.load(f)
    
    insert_data(db_path, json_data, excel_file)