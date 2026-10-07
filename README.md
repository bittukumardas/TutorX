# TutorX

A local Streamlit app that turns your notes, textbook chapters, or PDFs into
summaries, Q&A sessions, quizzes, and flashcards — powered by Google's free
Gemini API.

![screenshot](assets)

## Features

- **Summarize** — condense notes or textbook chapters into a study-ready summary, with adjustable detail level (very short → detailed).
- **Ask Questions** — chat with your material; the assistant answers strictly from your text, and tells you when it's falling back to general knowledge.
- **Quiz Me** — auto-generates multiple-choice quizzes with instant scoring and explanations.
- **Flashcards** — auto-generates flip-through flashcards for active recall.
- Works with **pasted text** or **uploaded PDF/TXT files**.

## Tech stack

- [Streamlit](https://streamlit.io/) — UI
- [Google Gemini API](https://ai.google.dev/) (`google-genai`) — summarization, Q&A, quiz/flashcard generation
- [pypdf](https://pypi.org/project/pypdf/) — PDF text extraction
- [python-dotenv](https://pypi.org/project/python-dotenv/) — local API key management

## Getting started

### 1. Clone the repo

```bash
git clone https://github.com/<your-username>/ai-study-assistant.git
cd ai-study-assistant
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv venv
source venv/bin/activate   # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Add your API key

Get a free key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) (no credit card required).

```bash
cp .env.example .env
# then edit .env and paste your key
```

Alternatively, you can paste your key directly into the app's sidebar at runtime.

### 4. Run the app

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`.

## Project structure

```
ai-study-assistant/
├── app.py              # main Streamlit app
├── requirements.txt
├── .env.example
└── assets/
    └── screenshot.png
```

## Why I built this

I wanted a lightweight, private study tool that runs entirely on my own
machine using a free-tier LLM — no subscriptions, no data leaving my control
beyond the API call itself. It's also a small exercise in building a
multi-tab, stateful Streamlit UI backed by structured LLM output (JSON quiz
and flashcard generation with parsing/error handling).

