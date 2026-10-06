import streamlit as st
import json
from datetime import datetime
from database import get_documents_by_course, init_db, count_documents
from config import get_secret, DEMO_MODE
import anthropic

init_db()
if DEMO_MODE:
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

def log_event(text):
    """Record what the agent did, shown in the Under the hood tab."""
    st.session_state.setdefault("activity", []).insert(0, (datetime.now().strftime("%H:%M:%S"), text))

def detect_course(text):
    """Ask the AI which course a pasted note belongs to."""
    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=10,
        messages=[{"role": "user", "content": f"""Which MBA course are these lecture notes from?
Options (reply with one, exactly as written): {", ".join(COURSES)}, Unknown

Notes:
{text[:4000]}"""}]
    )
    answer = message.content[0].text.strip()
    return answer if answer in COURSES else None

def save_granola_notes(text, course_choice, title, lecture_date=None):
    """Save pasted Granola notes into the knowledge base as Class Notes."""
    from database import save_document
    status = st.status("Agent processing your notes...", expanded=True)
    status.write(f"📄 Read {len(text.split()):,} words of notes")
    if course_choice in COURSES:
        course_name = course_choice
        status.write(f"🏷️ Course: **{course_name}** (chosen by you)")
    else:
        status.write("🤖 Asking Claude which course this belongs to...")
        course_name = detect_course(text)
        if not course_name:
            status.update(label="Couldn't tell the course", state="error")
            log_event("Granola notes: course could not be detected")
            return None
        status.write(f"🏷️ Course: **{course_name}** (detected by AI)")
    now = datetime.now()
    # Date the notes by when the lecture happened, so time-range filters stay accurate
    when = datetime.combine(lecture_date, now.time()) if lecture_date else now
    label = title.strip() or f"Lecture notes {when:%Y-%m-%d}"
    filename = f"Granola - {label} ({when:%Y-%m-%d} saved {now:%H%M%S}).txt"
    if DEMO_MODE:
        st.session_state.setdefault("demo_notes", []).append((filename, "Class Notes", text.strip(), when.isoformat(), course_name))
    else:
        save_document(filename, course_name, "Class Notes", text.strip(), when.isoformat())
    status.write(f"🗂️ Filed as **Class Notes**, dated {when:%b %d}")
    status.write("🧠 Added to the course brain")
    status.update(label=f"Notes saved to {course_name}", state="complete", expanded=False)
    log_event(f"Granola notes saved: {course_name}, Class Notes, dated {when:%b %d}")
    return course_name

def course_label(course):
    return "my MBA courses" if course == "All courses" else f'the MBA course "{course}"'

# Rough size budget for one AI request (~4 characters per token)
MAX_CONTEXT_CHARS = 400_000

def pick_documents(documents, question=""):
    """Keep every syllabus, then the most relevant (or most recent) material until the budget is used.
    Returns (kept_documents, number_left_out)."""
    total = sum(len(d[2] or "") for d in documents)
    if total <= MAX_CONTEXT_CHARS:
        return documents, 0

    words = {w for w in question.lower().split() if len(w) > 3}

    def score(doc):
        filename, category, content, added_at = doc[:4]
        text = (content or "").lower()
        relevance = sum(text.count(w) for w in words) if words else 0
        return (relevance, added_at)

    syllabi = [d for d in documents if d[1] == "Syllabus"]
    others = sorted([d for d in documents if d[1] != "Syllabus"], key=score, reverse=True)

    kept, used = [], 0
    for d in syllabi + others:
        size = len(d[2] or "")
        if used + size > MAX_CONTEXT_CHARS and d[1] != "Syllabus":
            continue
        kept.append(d)
        used += size
    return kept, len(documents) - len(kept)

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

    with st.expander("📝 Add Granola notes"):
        granola_course = st.selectbox("Course", ["Auto-detect"] + COURSES, key="granola_course")
        granola_title = st.text_input("Lecture title (optional)", key="granola_title", placeholder="e.g. Week 6: price discrimination")
        granola_date = st.date_input("Lecture date", key="granola_date")
        granola_text = st.text_area("Paste the transcript or summary", key="granola_text", height=180)
        if st.button("Save notes", use_container_width=True):
            if not granola_text.strip():
                st.error("Paste the notes first.")
            else:
                with st.spinner("Saving notes..."):
                    saved_course = save_granola_notes(granola_text, granola_course, granola_title, granola_date)
                if saved_course:
                    st.success(f"Saved to {saved_course}." + (" In this demo, your notes stay in your session only." if DEMO_MODE else ""))
                else:
                    st.error("Couldn't tell which course this belongs to. Pick the course and save again.")

    st.divider()

    st.header("Query Settings")
    course = st.selectbox("Select Course", ["All courses"] + COURSES)

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

def get_combined_content(course, days, include_readings, question=""):
    exclude = [] if include_readings else ["Reading"]
    courses = COURSES if course == "All courses" else [course]
    documents = []
    for c in courses:
        for doc in get_documents_by_course(c, days, exclude_categories=exclude):
            documents.append((*doc, c))
    for note in st.session_state.get("demo_notes", []):
        if note[4] in courses:
            documents.append(note)

    documents, left_out = pick_documents(documents, question)
    st.session_state["last_left_out"] = left_out

    combined_content = ""
    for filename, category, content, added_at, c in documents:
        combined_content += f"\n\n=== Course: {c} | File: {filename} (Type: {category}) ===\n{content}"

    return documents, combined_content

def generate_interactive_questions(course, combined_content, num_questions):
    prompt = f"""Below is course material for {course_label(course)}:

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

study_tab, hood_tab = st.tabs(["📚 Study", "🔍 Under the hood"])

with study_tab:
    if "quiz_data" not in st.session_state:
        st.session_state.quiz_data = None

    if generate_button:
        if mode == "Ask a Specific Question" and not custom_question.strip():
            st.error("Please enter your question first.")
        else:
            started = datetime.now()
            status = st.status("Agent working...", expanded=True)
            status.write(f"🔎 Searching the course brain: **{course}**, {time_option.lower()}")
            documents, combined_content = get_combined_content(course, days, include_readings, custom_question)

            if not documents:
                status.update(label="Nothing found", state="error")
                st.warning(f"No matching documents found for **{course}** in the selected time range.")
                st.session_state.quiz_data = None
            else:
                from collections import Counter
                by_type = Counter(d[1] for d in documents)
                status.write(f"📚 Found **{len(documents)} documents**: " + ", ".join(f"{n} {t}" for t, n in by_type.most_common()))
                if st.session_state.get("last_left_out"):
                    status.write(f"✂️ Too much to send at once, so kept the most relevant ({st.session_state['last_left_out']} left out; syllabi always kept)")
                status.write(f"📤 Sending about {len(combined_content.split()):,} words to Claude")
                with status.expander("📄 Documents used"):
                    for filename, category, content, added_at, c in documents:
                        st.write(f"- **{filename}** ({c}, {category}), {added_at[:10]}")

                if mode == "Interactive Practice":
                    status.write("✍️ Writing practice questions...")
                    st.session_state.quiz_data = generate_interactive_questions(course, combined_content, num_questions)
                    secs = (datetime.now() - started).seconds
                    status.update(label=f"Done: {num_questions} questions from {len(documents)} documents in {secs}s", state="complete", expanded=False)
                    log_event(f"Practice quiz: {course}, {len(documents)} documents, {secs}s")
                else:
                    st.session_state.quiz_data = None

                    if mode == "Summary + Practice Questions":
                        prompt = f"""Below is course material for {course_label(course)}:

    {combined_content}

    Please create a review summary that includes:
    1. Key concepts covered (bullet points)
    2. A brief explanation of each concept
    3. 3 practice questions at the end, each with a detailed answer

    Respond in English, formatted in Markdown."""

                    elif mode == "Practice Questions Only":
                        prompt = f"""Below is course material for {course_label(course)}:

    {combined_content}

    Please generate 3 practice questions based on this material, each with a detailed answer. Do not include a summary — just the questions and answers.

    Respond in English, formatted in Markdown."""

                    else:
                        prompt = f"""Below is course material for {course_label(course)}:

    {combined_content}

    Today's date is {datetime.now():%A, %B %d, %Y}.

    Please answer this question: {custom_question}

    If there are specific dates or deadlines relevant to the question, list them clearly in date order, with the course for each. If asked how long something will take, give a realistic time estimate and briefly say what it's based on. Respond in English."""

                    status.write("🤖 Claude is reading and writing the answer...")
                    message = client.messages.create(
                        model="claude-sonnet-4-5-20250929",
                        max_tokens=3000,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    secs = (datetime.now() - started).seconds
                    status.update(label=f"Done: answered from {len(documents)} documents in {secs}s", state="complete", expanded=False)
                    log_event(f"{mode}: {course}, {len(documents)} documents, {secs}s")

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
        st.info("👈 Pick a course (or All courses) on the left, then click \"Generate\"")


# ---------------- Under the hood ----------------
with hood_tab:
    from database import get_brain_summary
    import pandas as pd

    st.markdown("**How the agent works:** Collect (Canvas, Granola, your files) → Read (PDF and text) → Understand (Claude tags course, type, dates) → Course brain (one library) → Answer (summaries, deadlines, quizzes)")

    counts, recent = get_brain_summary()
    demo_notes = st.session_state.get("demo_notes", [])
    rows = [(c, t, n) for c, t, n in counts] + [(n[4], n[1], 1) for n in demo_notes]
    total = sum(r[2] for r in rows)
    syllabi = sum(r[2] for r in rows if r[1] == "Syllabus")
    notes = sum(r[2] for r in rows if r[1] == "Class Notes")
    asked = len([a for a in st.session_state.get("activity", []) if not a[1].startswith("Granola")])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Documents in brain", total)
    m2.metric("Syllabi tracked", syllabi)
    m3.metric("Lecture notes", notes)
    m4.metric("Questions this session", asked)

    st.subheader("What's in the course brain")
    if rows:
        df = pd.DataFrame(rows, columns=["Course", "Type", "Count"]).groupby(["Course", "Type"])["Count"].sum().unstack(fill_value=0)
        st.dataframe(df, use_container_width=True)
    else:
        st.caption("Empty so far. Sync from Canvas or add Granola notes to fill it.")

    st.subheader("Recently added")
    recent_rows = [(n[0], n[4], n[1], n[3][:10]) for n in reversed(demo_notes)] + [(f, c, t, a[:10]) for f, c, t, a in recent]
    if recent_rows:
        st.dataframe(pd.DataFrame(recent_rows[:12], columns=["File", "Course", "Type", "Dated"]), use_container_width=True, hide_index=True)

    st.subheader("Agent activity")
    activity = st.session_state.get("activity", [])
    if activity:
        for t, text in activity[:20]:
            st.write(f"`{t}` {text}")
    else:
        st.caption("Nothing yet this session. Ask a question or add notes, then come back here.")

    if not DEMO_MODE:
        from watcher import LOG_FILE
        import os
        if os.path.isfile(LOG_FILE):
            st.subheader("File classification history")
            log = pd.read_csv(LOG_FILE).tail(15).iloc[::-1]
            st.dataframe(log, use_container_width=True, hide_index=True)
