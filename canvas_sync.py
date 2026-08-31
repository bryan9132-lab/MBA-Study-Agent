import os
import requests
from database import get_all_filenames
from config import get_secret, WATCH_FOLDER

CANVAS_TOKEN = get_secret("CANVAS_API_TOKEN")
CANVAS_BASE_URL_RAW = get_secret("CANVAS_BASE_URL")
CANVAS_BASE_URL = CANVAS_BASE_URL_RAW.rstrip("/") if CANVAS_BASE_URL_RAW else ""

HEADERS = {
    "Authorization": f"Bearer {CANVAS_TOKEN}"
}

COURSE_IDS = {
    "Data and Decisions": "1555528",
    "Microeconomics": "1555514",
    "Accounting": "1555594",
    "Leading People": "1555298"
}

EXCLUDED_FOLDER_KEYWORDS = ["additional resources"]

DOWNLOAD_FOLDER = WATCH_FOLDER

def get_excluded_folder_ids(course_id):
    url = f"{CANVAS_BASE_URL}/api/v1/courses/{course_id}/folders"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        print(f"[警告] 無法取得資料夾清單：{response.status_code}")
        return set()

    folders = response.json()
    excluded_ids = set()
    for folder in folders:
        folder_name = folder.get("name", "").lower()
        if any(keyword in folder_name for keyword in EXCLUDED_FOLDER_KEYWORDS):
            excluded_ids.add(folder["id"])
            print(f"  將排除資料夾：{folder['name']}")

    return excluded_ids

def list_course_files(course_id):
    url = f"{CANVAS_BASE_URL}/api/v1/courses/{course_id}/files"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        print(f"[錯誤] 無法取得課程 {course_id} 的檔案清單：{response.status_code}")
        print(response.text)
        return []

    return response.json()

def download_file(file_info, existing_filenames):
    filename = file_info["display_name"]
    download_url = file_info["url"]

    if filename in existing_filenames:
        print(f"資料庫已有紀錄，跳過：{filename}")
        return

    target_path = os.path.join(DOWNLOAD_FOLDER, filename)

    if os.path.exists(target_path):
        print(f"根目錄已存在，跳過：{filename}")
        return

    response = requests.get(download_url, headers=HEADERS)
    if response.status_code == 200:
        with open(target_path, "wb") as f:
            f.write(response.content)
        print(f"已下載：{filename}")
    else:
        print(f"[錯誤] 下載失敗：{filename}，狀態碼：{response.status_code}")

if __name__ == "__main__":
    existing_filenames = get_all_filenames()
    print(f"資料庫目前已有 {len(existing_filenames)} 筆檔案紀錄\n")

    for course_name, course_id in COURSE_IDS.items():
        print(f"=== 檢查課程：{course_name} ===")

        excluded_folder_ids = get_excluded_folder_ids(course_id)
        files = list_course_files(course_id)

        filtered_files = [f for f in files if f.get("folder_id") not in excluded_folder_ids]

        print(f"找到 {len(files)} 個檔案，排除後剩 {len(filtered_files)} 個\n")

        for file_info in filtered_files:
            download_file(file_info, existing_filenames)

        print()