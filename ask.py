import sys
from datetime import datetime
from dotenv import load_dotenv
import anthropic
from database import get_documents_by_course

load_dotenv()
client = anthropic.Anthropic()

def summarize_course(course_name, days=None):
    documents = get_documents_by_course(course_name, days)

    if not documents:
        time_desc = f"最近{days}天" if days else "全部"
        print(f"目前資料庫裡沒有「{course_name}」{time_desc}的任何資料。")
        return

    combined_content = ""
    for filename, category, content, added_at in documents:
        combined_content += f"\n\n=== 檔案：{filename}（類型：{category}）===\n{content}"

    time_desc = f"最近{days}天" if days else "全部累積"
    print(f"找到 {len(documents)} 份「{course_name}」{time_desc}相關文件，正在請AI整理...\n")

    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=3000,
        messages=[
            {"role": "user", "content": f"""以下是MBA課程「{course_name}」的相關教材內容（包含講義、閱讀資料等）：

{combined_content}

請幫我做一份複習摘要，包含：
1. 這些內容涵蓋的主要概念（條列式）
2. 每個概念的簡短解釋
3. 最後附上3道練習題，每題附上詳解答案

用繁體中文回答。"""}
        ]
    )

    print(message.content[0].text)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python ask.py \"課程名稱\" [天數]")
        print("範例：")
        print("  python ask.py \"Microeconomics\"          → 全部累積內容")
        print("  python ask.py \"Microeconomics\" 7        → 最近7天（本週複習）")
        print("  python ask.py \"Microeconomics\" 28       → 最近28天（考前複習4週份）")
    else:
        course_name = sys.argv[1]
        days = int(sys.argv[2]) if len(sys.argv) > 2 else None
        summarize_course(course_name, days)