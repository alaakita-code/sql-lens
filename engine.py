import sqlite3
import random
import sys
import time
from itertools import islice
import sqlglot
from sqlglot import exp

def get_connection(db_path):
    """啟用極限效能參數的連線"""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA synchronous = OFF;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA cache_size = -64000;")
    return conn

def check_unsafe_sql(query):
    """AST 靜態語法防呆：阻斷無 WHERE 的危險操作"""
    try:
        parsed = sqlglot.parse_one(query)
        if isinstance(parsed, (exp.Delete, exp.Update)):
            if not parsed.args.get("where"):
                raise SystemExit("Unsafe SQL")
        return True
    except SystemExit as e:
        raise e
    except Exception as e:
        raise ValueError(f"語法解析失敗: {e}")

def batch_generator(total_rows):
    """Generator: 記憶體友善的資料產生器"""
    statuses = ['active', 'inactive', 'pending']
    for i in range(1, total_rows + 1):
        yield (i, f"User_{i}", random.randint(18, 65), random.choice(statuses))

def generate_mock_data(db_path, total_rows=50000, batch_size=10000):
    """百萬級分塊寫入優化"""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER, status TEXT)")
    cursor.execute("DROP INDEX IF EXISTS idx_status;")
    cursor.execute("DELETE FROM users;")
    
    gen = batch_generator(total_rows)
    for i in range(0, total_rows, batch_size):
        batch = list(islice(gen, batch_size))
        cursor.executemany("INSERT INTO users (id, name, age, status) VALUES (?, ?, ?, ?)", batch)
        conn.commit()
        
    conn.close()
