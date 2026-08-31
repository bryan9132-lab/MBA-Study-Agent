import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_base.db")

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()
cursor.execute("SELECT id, filename, course, category FROM documents")
rows = cursor.fetchall()
conn.close()

for row in rows:
    print(row)