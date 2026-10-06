import os
import shutil
import csv
import time
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import anthropic
import pdfplumber
from database import init_db, save_document
from config import get_secret, WATCH_FOLDER, DATA_DIR

client = anthropic.Anthropic(api_key=get_secret("ANTHROPIC_API_KEY"))

LOG_FILE = os.path.join(DATA_DIR, "log.csv")

CATEGORY_FOLDERS = {
    "Lecture Slides": "Lecture_Slides",
    "Reading": "Readings",
    "Assignment": "Assignments",
    "Syllabus": "Other",
    "Class Notes": "Class_Notes",
    "Other": "Other"
}

COURSE_FOLDERS = {
    "Microeconomics": "Microeconomics",
    "Accounting": "Accounting",
    "Leading People": "Leading_People",
    "Data and Decisions": "Data_and_Decisions",
    "Unknown": "Unsorted"
}

def extract_pdf_text(filepath, max_pages=3, max_chars=3000):
    try:
        text = ""
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages[:max_pages]:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                if len(text) >= max_chars:
                    break
        return text[:max_chars]
    except Exception as e:
        print(f"[警告] PDF讀取失敗：{e}")
        return ""

def extract_text_file(filepath, max_chars=3000):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()[:max_chars]
    except Exception as e:
        print(f"[警告] 文字檔讀取失敗：{e}")
        return ""

def classify_file(filename, filepath):
    is_pdf = filename.lower().endswith(".pdf")
    is_text = filename.lower().endswith((".txt", ".md"))
    content_snippet = ""

    if is_pdf:
        content_snippet = extract_pdf_text(filepath)
    elif is_text:
        content_snippet = extract_text_file(filepath)

    if content_snippet:
        content_info = f"檔案內容前幾段：\n{content_snippet}"
    else:
        content_info = "（無法讀取內容，僅能依檔名判斷）"

    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=30,
        messages=[
            {"role": "user", "content": f"""這是一個MBA課程資料夾裡新出現的檔案。

檔名：{filename}

{content_info}

請判斷這個檔案屬於哪門課，以及是什麼類型的資料。

課程選項（一字不改）：
Microeconomics
Accounting
Leading People
Data and Decisions
Unknown

類型選項（一字不改）：
Lecture Slides
Reading
Assignment
Syllabus
Class Notes
Other

請用這個格式回答，不要加任何其他文字：
課程|類型"""}
        ]
    )
    result = message.content[0].text.strip()
    try:
        course, category = result.split("|")
        return course.strip(), category.strip()
    except ValueError:
        print(f"[警告] AI回覆格式異常：{repr(result)}")
        return "Unknown", "Other"

def log_action(filename, course, category):
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "filename", "course", "category"])
        writer.writerow([datetime.now().isoformat(), filename, course, category])

class MyHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return

        filename = os.path.basename(event.src_path)

        if os.path.dirname(event.src_path) != WATCH_FOLDER:
            return

        print(f"偵測到新檔案：{filename}")

        time.sleep(0.5)

        course, category = classify_file(filename, event.src_path)
        print(f"AI判斷：課程={course}, 類型={category}")

        if filename.lower().endswith(".pdf"):
            full_content = extract_pdf_text(event.src_path, max_pages=20, max_chars=20000)
        elif filename.lower().endswith((".txt", ".md")):
            full_content = extract_text_file(event.src_path, max_chars=20000)
        else:
            full_content = ""

        save_document(filename, course, category, full_content, datetime.now().isoformat())
        print("已存入 knowledge_base.db")

        course_folder_name = COURSE_FOLDERS.get(course, "Unsorted")
        category_folder_name = CATEGORY_FOLDERS.get(category, "Other")

        target_folder = os.path.join(WATCH_FOLDER, course_folder_name, category_folder_name)
        os.makedirs(target_folder, exist_ok=True)

        target_path = os.path.join(target_folder, filename)

        shutil.move(event.src_path, target_path)
        print(f"已搬移到：{target_path}")

        log_action(filename, course, category)

if __name__ == "__main__":
    init_db()
    event_handler = MyHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_FOLDER, recursive=True)
    observer.start()
    print(f"開始監控資料夾：{WATCH_FOLDER}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()