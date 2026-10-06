import streamlit as st
import json
from database import get_documents_by_course, init_db, count_documents
from config import get_secret, DEMO_MODE
import anthropic

init_db()
if DEMO_MODE and count_documents() == 0:
    from seed_demo import seed
    seed()
client = anthropic.Anthropic(api_key=get_secret("ANTHROPIC_API_KEY"))

COURSES = ["Microeconomics", "Accounting", "Leading People", "Data and Decisions"]

st.set_page_config(page_title="Haas Study Agent", page_icon="📚")

st.title("📚 Haas Study Agent")
st.caption("Automatically organizes course materials and generates review summaries with practice questions")

def esc(text):
    """避免 $ 符號被誤判成LaTeX公式"""
    return text.replace("$", "\\$")

if DEMO_MODE:
    st.info("Public demo with sample course material. Pick a course, choose **Ask a Specific Question**, and try: *What's due in the next two weeks, and how long will each take?*")

with st.sidebar:
    if not DEMO_MODE:
        st.header("Sync from Canvas")

        from database import get_last_sync_time, update_last_sync_time
        last_sync = get_last_sync_time()
        if last_sync:
            st.caption(f"Last synced: {last_sync[:16].replace('T', ' ')}")
        else:
            st.caption("Never synced yet")

        if st.button("🔄 Sync & Organize", use_container_width=True):
            with st.spinner("Downloading from Canvas..."):
                from canvas_sync import COURSE_IDS, get_excluded_folder_ids, list_course_files, download_file
                from database import get_all_filenames

                existing_filenames = get_all_filenames()
                sync_log = []

                for course_name, course_id in COURSE_IDS.items():
                    excluded_folder_ids = get_excluded_folder_ids(course_id)
                    files = list_course_files(course_id)
                    filtered_files = [f for f in files if f.get("folder_id") not in excluded_folder_ids]

                    for file_info in filtered_files:
                        filename = file_info["display_name"]
                        if filename not in existing_filenames:
                            download_file(file_info, existing_filenames)
                            sync_log.append(filename)

            update_last_sync_time()

            if sync_log:
                st.success(f"Downloaded {len(sync_log)} new file(s)")
                with st.spinner("Organizing new files..."):
                    from batch_process import process_existing_files
                    process_existing_files()
                st.success("Files organized and added to knowledge base!")
            else:
                st.info("No new files found on Canvas.")
            st.rerun()

        st.divider()

    st.header("Query Settings")
    course = st.selectbox("Select Course", COURSES)

    time_option = st.radio(
        "Time Range",
        ["Past 7 days (this week)", "Past 21 days (~3 weeks)", "Past 28 days (~4 weeks)", "All accumulated content"]
    )

    time_map = {
        "Past 7 days (this week)": 7,
        "Past 21 days (~3 weeks)": 21,
        "Past 28 days (~4 weeks)": 28,
        "All accumulated content": None
    }
    days = time_map[time_option]

    mode = st.radio(
        "What do you want?",
        ["Summary + Practice Questions", "Practice Questions Only", "Ask a Specific Question", "Interactive Practice"]
    )

    custom_question = ""
    if mode == "Ask a Specific Question":
        custom_question = st.text_area(
            "Your question",
            placeholder="e.g. What are the homework and exam dates for this course?"
        )

    num_questions = 4
    if mode == "Interactive Practice":
        num_questions = st.slider("Number of questions", min_value=2, max_value=8, value=4)

    include_readings = st.checkbox("Include Readings", value=False)

    generate_button = st.button("Generate", type="primary", use_container_width=True)

def get_combined_content(course, days, include_readings):
    exclude = [] if include_readings else ["Reading"]
    documents = get_documents_by_course(course, days, exclude_categories=exclude)

    combined_content = ""
    for filename, category, content, added_at in documents:
        combined_content += f"\n\n=== File: {filename} (Type: {category}) ===\n{content}"

    return documents, combined_content

def generate_interactive_questions(course, combined_content, num_questions):
    prompt = f"""Below is course material for the MBA course "{course}":

{combined_content}

Generate {num_questions} practice questions based on this material. Mix question types appropriately for the subject:
- multiple_choice: for conceptual/theoretical questions (include 4 options)
- fill_in_blank: for short, specific answers (e.g. accounting entries, definitions, numbers)
- open_ended: for questions requiring explanation or calculation

Respond ONLY with valid JSON in this exact format, no other text:
{{
  "questions": [
    {{
      "id": 1,
      "type": "multiple_choice",
      "question": "question text here",
      "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
      "correct_answer": "A) option1"
    }},
    {{
      "id": 2,
      "type": "fill_in_blank",
      "question": "question text here",
      "correct_answer": "expected answer"
    }},
    {{
      "id": 3,
      "type": "open_ended",
      "question": "question text here",
      "correct_answer": "key points the answer should cover"
    }}
  ]
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}]
    )

    raw_text = message.content[0].text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`").replace("json", "", 1).strip()

    return json.loads(raw_text)

def grade_answer(question_text, correct_answer, user_answer):
    prompt = f"""Question: {question_text}
Reference answer / key points: {correct_answer}
Student's answer: {user_answer}

Evaluate if the student's answer is correct. Respond in this format:
Verdict: [Correct/Partially Correct/Incorrect]
Feedback: [1-2 sentences of feedback, explain what's right or missing]"""

    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = None

if generate_button:
    if mode == "Ask a Specific Question" and not custom_question.strip():
        st.error("Please enter your question first.")
    else:
        documents, combined_content = get_combined_content(course, days, include_readings)

        if not documents:
            st.warning(f"No matching documents found for **{course}** in the selected time range.")
            st.session_state.quiz_data = None
        else:
            st.success(f"Found {len(documents)} relevant document(s)")

            with st.expander("📄 Documents included"):
                for filename, category, content, added_at in documents:
                    st.write(f"- **{filename}** ({category}) — {added_at[:10]}")

            if mode == "Interactive Practice":
                with st.spinner("Generating interactive questions..."):
                    st.session_state.quiz_data = generate_interactive_questions(course, combined_content, num_questions)
            else:
                st.session_state.quiz_data = None

                if mode == "Summary + Practice Questions":
                    prompt = f"""Below is course material for the MBA course "{course}":

{combined_content}

Please create a review summary that includes:
1. Key concepts covered (bullet points)
2. A brief explanation of each concept
3. 3 practice questions at the end, each with a detailed answer

Respond in English, formatted in Markdown."""

                elif mode == "Practice Questions Only":
                    prompt = f"""Below is course material for the MBA course "{course}":

{combined_content}

Please generate 3 practice questions based on this material, each with a detailed answer. Do not include a summary — just the questions and answers.

Respond in English, formatted in Markdown."""

                else:
                    prompt = f"""Below is course material for the MBA course "{course}":

{combined_content}

Please answer this question: {custom_question}

If there are specific dates or deadlines relevant to the question, list them clearly. Respond in English."""

                with st.spinner("AI is generating your content..."):
                    message = client.messages.create(
                        model="claude-sonnet-4-5-20250929",
                        max_tokens=3000,
                        messages=[{"role": "user", "content": prompt}]
                    )

                response_text = esc(message.content[0].text)
                st.markdown("---")
                st.markdown(response_text)

if st.session_state.quiz_data:
    st.markdown("---")
    st.subheader("📝 Interactive Practice")

    with st.form("quiz_form"):
        user_answers = {}

        for q in st.session_state.quiz_data["questions"]:
            st.markdown(f"**Q{q['id']}. {esc(q['question'])}**")

            if q["type"] == "multiple_choice":
                user_answers[q["id"]] = st.radio(
                    "Select an answer:", q["options"], key=f"q{q['id']}", label_visibility="collapsed"
                )
            elif q["type"] == "fill_in_blank":
                user_answers[q["id"]] = st.text_area(
                    "Your answer:", key=f"q{q['id']}", label_visibility="collapsed", height=68
                )
            else:
                user_answers[q["id"]] = st.text_area(
                    "Your answer:", key=f"q{q['id']}", label_visibility="collapsed"
                )

            st.markdown("")

        submitted = st.form_submit_button("Submit Answers", type="primary")

    if submitted:
        st.markdown("---")
        st.subheader("✅ Results")

        for q in st.session_state.quiz_data["questions"]:
            user_answer = user_answers.get(q["id"], "")
            st.markdown(f"**Q{q['id']}. {esc(q['question'])}**")
            st.write(f"Your answer: {user_answer if user_answer.strip() else '(no answer provided)'}")

            with st.spinner(f"Grading Q{q['id']}..."):
                feedback = grade_answer(q["question"], q["correct_answer"], user_answer)

            st.info(esc(feedback))
            st.markdown("---")

if not generate_button and not st.session_state.quiz_data:
    st.info("👈 Select a course and time range on the left, then click \"Generate\"")