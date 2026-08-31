import sqlite3
import os
from datetime import datetime, timedelta

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_base.db")

def init_db():
    """建立資料庫和表格（如果還不存在）"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            course TEXT NOT NULL,
            category TEXT NOT NULL,
            content TEXT,
            added_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            last_synced_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_document(filename, course, category, content, timestamp):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO documents (filename, course, category, content, added_at)
        VALUES (?, ?, ?, ?, ?)
    """, (filename, course, category, content, timestamp))
    conn.commit()
    conn.close()

def get_documents_by_course(course, days=None, exclude_categories=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    query = "SELECT filename, category, content, added_at FROM documents WHERE course = ?"
    params = [course]

    if days and days > 0:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        query += " AND added_at >= ?"
        params.append(cutoff)

    if exclude_categories:
        placeholders = ",".join("?" for _ in exclude_categories)
        query += f" AND category NOT IN ({placeholders})"
        params.extend(exclude_categories)

    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    return results

def get_all_filenames():
    """取得資料庫裡所有已存在的檔名，用來避免重複下載"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT filename FROM documents")
    results = cursor.fetchall()
    conn.close()
    return set(row[0] for row in results)

def get_last_sync_time():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            last_synced_at TEXT
        )
    """)
    cursor.execute("SELECT last_synced_at FROM sync_log ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def update_last_sync_time():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            last_synced_at TEXT
        )
    """)
    cursor.execute("INSERT INTO sync_log (last_synced_at) VALUES (?)", (datetime.now().isoformat(),))
    conn.commit()
    conn.close()