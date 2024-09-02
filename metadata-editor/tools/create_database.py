import sqlite3

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建主表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS main_table (
        id TEXT PRIMARY KEY,
        json_data TEXT,
        ocr_data TEXT,
        md_data TEXT,
        createdat TEXT,
        updatedat TEXT,
        current_version INTEGER
    )
    ''')
    
    # 创建版本历史表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS version_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_id TEXT,
        version INTEGER,
        json_data TEXT,
        createdat TEXT,
        updatedat TEXT
    )
    ''')

    # Create MATERIAL_TYPES table
    cursor.execute('''CREATE TABLE IF NOT EXISTS MATERIAL_TYPES
                 (id INTEGER PRIMARY KEY, json_data TEXT, created_at TEXT, updated_at TEXT)''')

    # Create EVENT_TYPES table
    cursor.execute('''CREATE TABLE IF NOT EXISTS EVENT_TYPES
                 (id INTEGER PRIMARY KEY, json_data TEXT, created_at TEXT, updated_at TEXT)''')


    # Create persons_relationship table
    cursor.execute('''CREATE TABLE IF NOT EXISTS persons_relationship
                 (id INTEGER PRIMARY KEY, json_data TEXT, created_at TEXT, updated_at TEXT)''')

    # Create events_relationship table
    cursor.execute('''CREATE TABLE IF NOT EXISTS events_relationship
                 (id INTEGER PRIMARY KEY, json_data TEXT, created_at TEXT, updated_at TEXT)''')

    # Create groups_relationship table
    cursor.execute('''CREATE TABLE IF NOT EXISTS groups_relationship
                 (id INTEGER PRIMARY KEY, json_data TEXT, created_at TEXT, updated_at TEXT)''')

    # Create works_relationship table
    cursor.execute('''CREATE TABLE IF NOT EXISTS works_relationship
                 (id INTEGER PRIMARY KEY, json_data TEXT, created_at TEXT, updated_at TEXT)''')

    # Create architectures_relationship table
    cursor.execute('''CREATE TABLE IF NOT EXISTS architectures_relationship
                 (id INTEGER PRIMARY KEY, json_data TEXT, created_at TEXT, updated_at TEXT)''')

    # Create materrials_relationship table
    cursor.execute('''CREATE TABLE IF NOT EXISTS materials_relationship
                 (id INTEGER PRIMARY KEY, json_data TEXT, created_at TEXT, updated_at TEXT)''')
    
    conn.commit()
    conn.close()