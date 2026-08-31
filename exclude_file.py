import sys
import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_base.db")

def exclude_file(filename):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM documents WHERE filename = ?", (filename,))
    conn.commit()
    deleted = cursor.rowcount
    conn.close()
    if deleted:
        print(f"已從資料庫移除：{filename}")
    else:
        print(f"找不到這個檔名，請確認拼字是否正確：{filename}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python exclude_file.py \"檔名.pdf\"")
    else:
        exclude_file(sys.argv[1])