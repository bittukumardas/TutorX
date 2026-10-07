"""
AI Study Assistant
------------------
A local Streamlit app that uses Google's free Gemini API to help to study:
- Summarize notes / textbook chapters / PDFs
- Ask questions about  material (Q&A)
- Auto-generate a multiple-choice quiz
- Auto-generate flashcards

Run locally with:
    streamlit run app.py
"""

import os
import re
import json

import streamlit as st
from dotenv import load_dotenv
from pypdf import PdfReader
from google import genai

# --------------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------------

load_dotenv()  # reads GEMINI_API_KEY from a local .env file, if present

st.set_page_config(page_title="AI Study Assistant", page_icon="📚", layout="wide")

MODEL_OPTIONS = {
    "Gemini 3 Flash (recommended, balanced)": "gemini-3-flash",
    "Gemini 3.1 Flash-Lite (fastest / lightest on quota)": "gemini-3.1-flash-lite",
}


def get_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def extract_text_from_pdf(uploaded_file) -> str:
    reader = PdfReader(uploaded_file)
    text = []
    for page in reader.pages:
        text.append(page.extract_text() or "")
    return "\n".join(text)


def call_gemini(client: genai.Client, model: str, prompt: str) -> str:
    response = client.models.generate_content(model=model, contents=prompt)
    return response.text or ""


def extract_json(text: str):
    """Pull a JSON array/object out of a model response that may include
    stray markdown fences or commentary."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(json)?", "", cleaned.strip())
    cleaned = re.sub(r"```$", "", cleaned.strip())
    cleaned = cleaned.strip()
    return json.loads(cleaned)


# --------------------------------------------------------------------------
# Sidebar: API key + model + study material input
# --------------------------------------------------------------------------

st.sidebar.title("⚙️ Settings")

api_key = st.sidebar.text_input(
    "Gemini API key",
    value=os.getenv("GEMINI_API_KEY", ""),
    type="password",
    key="api_key_input",
    help="Get a free key at https://aistudio.google.com/app/apikey. "
    "You can also put it in a .env file as GEMINI_API_KEY=... to avoid retyping it.",
)
# Fall back to whatever was last committed to session state, in case this
# rerun was triggered before the text_input's on-change fired (e.g. by the
# file uploader immediately after pasting the key).
api_key = api_key or st.session_state.get("api_key_input", "")

model_label = st.sidebar.selectbox("Model", list(MODEL_OPTIONS.keys()))
model_name = MODEL_OPTIONS[model_label]

st.sidebar.markdown("---")
st.sidebar.subheader("📖 Study material")

input_mode = st.sidebar.radio("Provide your material via:", ["Paste text", "Upload PDF/TXT"])

study_text = ""
if input_mode == "Paste text":
    study_text = st.sidebar.text_area(
        "Paste your notes / chapter text here", height=250, key="pasted_text"
    )
else:
    uploaded = st.sidebar.file_uploader("Upload a .pdf or .txt file", type=["pdf", "txt"])
    if uploaded is not None:
        if uploaded.name.lower().endswith(".pdf"):
            with st.spinner("Extracting text from PDF..."):
                study_text = extract_text_from_pdf(uploaded)
        else:
            study_text = uploaded.read().decode("utf-8", errors="ignore")
        with st.sidebar.expander("Preview extracted text"):
            st.write(study_text[:2000] + ("..." if len(study_text) > 2000 else ""))

if study_text:
    st.session_state["study_text"] = study_text

st.sidebar.caption(
    f"Loaded material: {len(st.session_state.get('study_text', ''))} characters"
)

# --------------------------------------------------------------------------
# Main area
# --------------------------------------------------------------------------

st.title("📚 AI Study Assistant")
st.caption("Summarize, ask questions, and generate quizzes/flashcards from your own study material — powered by the free Gemini API.")

if not api_key:
    st.info("👈 Enter your free Gemini API key in the sidebar to get started. "
            "Get one at https://aistudio.google.com/app/apikey (no credit card needed).")
    st.stop()

text = st.session_state.get("study_text", "")
if not text:
    st.info("👈 Paste your notes or upload a PDF/TXT file in the sidebar to begin.")
    st.stop()

client = get_client(api_key)

tab_summary, tab_qa, tab_quiz, tab_flash = st.tabs(
    ["📝 Summarize", "❓ Ask Questions", "🧠 Quiz Me", "🗂️ Flashcards"]
)

MAX_CHARS = 30000  # keep prompts reasonably sized for the free tier
material = text[:MAX_CHARS]

# ---- Summarize ----
with tab_summary:
    st.subheader("Summarize your material")
    detail = st.select_slider(
        "Summary length", options=["Very short", "Short", "Medium", "Detailed"], value="Medium"
    )
    if st.button("Generate summary", key="summarize_btn"):
        prompt = (
            "You are a helpful study assistant. Summarize the following study material "
            f"at a '{detail}' level of detail. Use clear headings and bullet points where "
            "useful, and highlight key terms in bold.\n\n"
            f"MATERIAL:\n{material}"
        )
        with st.spinner("Summarizing..."):
            try:
                summary = call_gemini(client, model_name, prompt)
                st.markdown(summary)
            except Exception as e:
                st.error(f"Something went wrong: {e}")

# ---- Q&A ----
with tab_qa:
    st.subheader("Ask a question about your material")
    if "qa_history" not in st.session_state:
        st.session_state.qa_history = []

    for q, a in st.session_state.qa_history:
        st.markdown(f"**You:** {q}")
        st.markdown(f"**Assistant:** {a}")
        st.markdown("---")

    question = st.text_input("Your question", key="qa_input")
    if st.button("Ask", key="qa_btn") and question:
        prompt = (
            "You are a study assistant. Answer the question using ONLY the study "
            "material below. If the answer isn't in the material, say so clearly and "
            "then answer from general knowledge, noting that it's not from the material.\n\n"
            f"MATERIAL:\n{material}\n\n"
            f"QUESTION: {question}"
        )
        with st.spinner("Thinking..."):
            try:
                answer = call_gemini(client, model_name, prompt)
                st.session_state.qa_history.append((question, answer))
                st.rerun()
            except Exception as e:
                st.error(f"Something went wrong: {e}")

# ---- Quiz ----
with tab_quiz:
    st.subheader("Generate a multiple-choice quiz")
    num_questions = st.slider("Number of questions", 3, 15, 5)
    if st.button("Generate quiz", key="quiz_btn"):
        prompt = (
            f"Create {num_questions} multiple-choice quiz questions based ONLY on the "
            "study material below. Return ONLY valid JSON (no markdown fences, no "
            "commentary) as a list of objects with keys: 'question' (string), "
            "'options' (list of 4 strings), 'correct_index' (integer 0-3), and "
            "'explanation' (short string explaining the right answer).\n\n"
            f"MATERIAL:\n{material}"
        )
        with st.spinner("Building your quiz..."):
            try:
                raw = call_gemini(client, model_name, prompt)
                quiz = extract_json(raw)
                st.session_state["quiz"] = quiz
                st.session_state["quiz_answers"] = {}
            except Exception as e:
                st.error(f"Couldn't parse the quiz, try again. ({e})")

    quiz = st.session_state.get("quiz")
    if quiz:
        with st.form("quiz_form"):
            for i, q in enumerate(quiz):
                st.markdown(f"**Q{i+1}. {q['question']}**")
                choice = st.radio(
                    "Choose one:", q["options"], key=f"quiz_q_{i}", label_visibility="collapsed"
                )
                st.session_state["quiz_answers"][i] = q["options"].index(choice)
                st.markdown("")
            submitted = st.form_submit_button("Submit answers")

        if submitted:
            score = 0
            for i, q in enumerate(quiz):
                chosen = st.session_state["quiz_answers"].get(i)
                correct = q["correct_index"]
                if chosen == correct:
                    score += 1
                    st.success(f"Q{i+1}: Correct! {q.get('explanation', '')}")
                else:
                    st.error(
                        f"Q{i+1}: Incorrect. Correct answer: {q['options'][correct]}. "
                        f"{q.get('explanation', '')}"
                    )
            st.info(f"Score: {score} / {len(quiz)}")

# ---- Flashcards ----
with tab_flash:
    st.subheader("Generate flashcards")
    num_cards = st.slider("Number of flashcards", 5, 30, 10)
    if st.button("Generate flashcards", key="flash_btn"):
        prompt = (
            f"Create {num_cards} flashcards based ONLY on the study material below. "
            "Return ONLY valid JSON (no markdown fences, no commentary) as a list of "
            "objects with keys 'front' (a term or question) and 'back' (the answer or "
            "definition).\n\n"
            f"MATERIAL:\n{material}"
        )
        with st.spinner("Building flashcards..."):
            try:
                raw = call_gemini(client, model_name, prompt)
                cards = extract_json(raw)
                st.session_state["cards"] = cards
                st.session_state["card_index"] = 0
                st.session_state["show_back"] = False
            except Exception as e:
                st.error(f"Couldn't parse the flashcards, try again. ({e})")

    cards = st.session_state.get("cards")
    if cards:
        idx = st.session_state.get("card_index", 0)
        card = cards[idx]

        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            st.markdown(
                f"""
                <div style="border:2px solid #ccc;border-radius:12px;padding:40px;
                text-align:center;min-height:150px;font-size:20px;">
                {card['back'] if st.session_state.get('show_back') else card['front']}
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.caption(f"Card {idx + 1} of {len(cards)}")

            b1, b2, b3 = st.columns(3)
            if b1.button("⬅️ Prev"):
                st.session_state["card_index"] = (idx - 1) % len(cards)
                st.session_state["show_back"] = False
                st.rerun()
            if b2.button("🔄 Flip"):
                st.session_state["show_back"] = not st.session_state.get("show_back", False)
                st.rerun()
            if b3.button("Next ➡️"):
                st.session_state["card_index"] = (idx + 1) % len(cards)
                st.session_state["show_back"] = False
                st.rerun()