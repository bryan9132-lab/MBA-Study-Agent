import os
from watcher import classify_file, extract_pdf_text, extract_text_file, save_document, log_action, CATEGORY_FOLDERS, COURSE_FOLDERS, WATCH_FOLDER
import shutil
from datetime import datetime

def process_existing_files():
    """處理已經在 Haas Course 根目錄，但還沒被分類的檔案"""
    files_in_root = [
        f for f in os.listdir(WATCH_FOLDER)
        if os.path.isfile(os.path.join(WATCH_FOLDER, f))
    ]

    if not files_in_root:
        print("根目錄沒有待處理的檔案。")
        return

    print(f"找到 {len(files_in_root)} 個待處理的檔案\n")

    for filename in files_in_root:
        filepath = os.path.join(WATCH_FOLDER, filename)
        print(f"處理中：{filename}")

        course, category = classify_file(filename, filepath)
        print(f"  AI判斷：課程={course}, 類型={category}")

        if filename.lower().endswith(".pdf"):
            full_content = extract_pdf_text(filepath, max_pages=20, max_chars=20000)
        elif filename.lower().endswith((".txt", ".md")):
            full_content = extract_text_file(filepath, max_chars=20000)
        else:
            full_content = ""

        save_document(filename, course, category, full_content, datetime.now().isoformat())
        print("  已存入 knowledge_base.db")

        course_folder_name = COURSE_FOLDERS.get(course, "Unsorted")
        category_folder_name = CATEGORY_FOLDERS.get(category, "Other")
        target_folder = os.path.join(WATCH_FOLDER, course_folder_name, category_folder_name)
        os.makedirs(target_folder, exist_ok=True)
        target_path = os.path.join(target_folder, filename)

        shutil.move(filepath, target_path)
        print(f"  已搬移到：{target_path}\n")

        log_action(filename, course, category)

if __name__ == "__main__":
    process_existing_files()