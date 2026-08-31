import sys
from dotenv import load_dotenv
import anthropic
from database import get_documents_by_course

load_dotenv()
client = anthropic.Anthropic()

def ask_question(course_name, question, days=None):
    documents = get_documents_by_course(course_name, days)

    if not documents:
        print(f"目前資料庫裡沒有「{course_name}」的任何資料。")
        return

    combined_content = ""
    for filename, category, content, added_at in documents:
        combined_content += f"\n\n=== 檔案：{filename}（類型：{category}）===\n{content}"

    print(f"找到 {len(documents)} 份文件，正在請AI回答...\n")

    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1000,
        messages=[
            {"role": "user", "content": f"""以下是MBA課程「{course_name}」的相關資料：

{combined_content}

請回答這個問題：{question}

如果資料裡有明確的日期或截止時間，請完整列出。用繁體中文回答。"""}
        ]
    )

    print(message.content[0].text)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法：python ask_question.py \"課程名稱\" \"你的問題\" [天數]")
        print("範例：python ask_question.py \"Accounting\" \"這門課有哪些作業和考試日期？\"")
    else:
        course_name = sys.argv[1]
        question = sys.argv[2]
        days = int(sys.argv[3]) if len(sys.argv) > 3 else None
        ask_question(course_name, question, days)