import streamlit as st
import json
import sqlite3
from typing import Any, Dict
from datetime import datetime


RELATIONSHIP_TABLES = [
    'materials_relationship',
    'architectures_relationship',
    'works_relationship',
    'groups_relationship',
    'events_relationship',
    'persons_relationship'
]

def load_from_db(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT id, json_data FROM main_table")
    rows = cursor.fetchall()
    return [{'id': row[0], 'data': row[1]} for row in rows]

def load_settings(conn):
    cursor = conn.cursor()
    settings = {}
    
    tables = ['EVENT_TYPES', 'MATERIAL_TYPES'] + RELATIONSHIP_TABLES
    
    for table in tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if cursor.fetchone():
            # Fetch id and json_data for all tables
            cursor.execute(f"SELECT id, json_data FROM {table}")
            rows = cursor.fetchall()
            if rows:
                settings[table] = []
                for row in rows:
                    try:
                        json_data = json.loads(row[1])
                        if not json_data.get('deleted', False):  # Skip deleted items
                            settings[table].append(json_data)
                    except json.JSONDecodeError:
                        st.warning(f"Invalid JSON data in table {table}, id {row[0]}")
            else:
                settings[table] = []
        else:
            settings[table] = []
    
    return settings

def save_settings(settings, db_path):
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()

    tables = ['MATERIAL_TYPES', 'EVENT_TYPES'] + RELATIONSHIP_TABLES

    for table in tables:
        if table in settings:
            for item in settings[table]:
                json_data = json.dumps(item, ensure_ascii=False)
                now = datetime.now().isoformat()
                # 确保插入或更新操作正确执行
                c.execute(f'''INSERT OR REPLACE INTO {table} 
                              (id, json_data, created_at, updated_at) 
                              VALUES (?, ?, COALESCE((SELECT created_at FROM {table} WHERE id = ?), ?), ?)''', 
                          (item['id'], json_data, item['id'], now, now))

    conn.commit()
    conn.close()

def get_column_names(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]

def save_to_db(db_path: str, data: Dict[str, Any], data_id: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get current version
    cursor.execute("SELECT current_version FROM main_table WHERE id = ?", (data_id,))
    result = cursor.fetchone()
    if result:
        current_version = result[0] + 1
    else:
        current_version = 1

    # Update main_table
    json_data = json.dumps(data, ensure_ascii=False)
    updatedat = datetime.now().isoformat()
    cursor.execute("""
        UPDATE main_table 
        SET json_data = ?, updatedat = ?, current_version = ?
        WHERE id = ?
    """, (json_data, updatedat, current_version, data_id))
    
    # Insert into version_history
    cursor.execute("""
        INSERT INTO version_history (data_id, version, json_data, createdat, updatedat)
        VALUES (?, ?, ?, ?, ?)
    """, (data_id, current_version, json_data, updatedat, updatedat))
    
    # Clean up version history, keeping only the latest 3 versions
    cursor.execute("""
        DELETE FROM version_history
        WHERE data_id = ? AND version < ?
    """, (data_id, current_version - 2))
    
    conn.commit()
    conn.close()

def edit_settings(settings, table, item, new_values):
    # Edit item in settings
    for key, value in new_values.items():
        item[key] = value
    settings[table] = [i for i in settings[table] if not i.get('deleted', False)]
    return settings

def delete_item(settings, table, item_index):
    # Mark item as deleted
    settings[table][item_index]['deleted'] = True
    return settings

def add_item(settings, table, new_item):
    # Add new item to settings
    new_id = max([item['id'] for item in settings[table]], default=0) + 1
    new_item['id'] = new_id
    settings[table].append(new_item)
    return settings