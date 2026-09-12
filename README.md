# Programming Q&A AI Assistant (Full-Stack)

A beginner-friendly but scalable client-server application for answering programming questions using the Groq API.

## 1) Project Architecture

- **Backend**: FastAPI (`backend/app.py`)
  - Exposes REST API endpoint `/chat`
  - Maintains **session-based chat history** in memory
  - Uses Groq's Chat Completions REST API for AI responses
  - Detects likely language (Python/Java/C++/JavaScript/SQL)
- **Frontend**: Vanilla HTML/CSS/JavaScript (`frontend/`)
  - Chat-style UI
  - Renders Markdown responses + syntax highlighting
  - Supports copy-to-clipboard for code blocks
  - Persists chat in browser localStorage

## 2) Features Included

✅ User asks programming questions  
✅ AI responds with explanation + code example (+ optional optimization via system prompt)  
✅ Syntax-highlighted code blocks  
✅ Session-based chat history on backend  
✅ Local chat history persistence on frontend  
✅ Error handling for invalid input or API failures  
✅ Auto-scroll and loading state  
✅ "New Chat" reset flow

---

## 3) File Structure

```text
Ai-agent/
├── backend/
│   ├── __init__.py
│   ├── app.py
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── README.md
└── requirements.txt
```

---

## 4) Backend Setup (FastAPI)

### Step A: Create a virtual environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run these commands from the **repository root**. The root `requirements.txt`
installs the backend dependencies from `backend/requirements.txt`. The ASGI
module name belongs only in the `uvicorn` command below, not in a pip command.

### Step B: Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
FRONTEND_ORIGINS=http://localhost:5500
```

### Step C: Run backend server

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Backend available at: `http://localhost:8000`

Health check:

```bash
curl http://localhost:8000/health
```

---

## 5) Frontend Setup

In a new terminal:

```bash
cd frontend
python -m http.server 5500
```

Open: `http://localhost:5500`

> Note: `frontend/app.js` points to `http://localhost:8000` by default.
> For deployment, define `window.QA_API_BASE_URL` before loading `app.js` to use
> your hosted backend without editing the application source.

---

## 6) API Contract

### `POST /chat`

Request body:

```json
{
  "message": "How do I reverse a list in Python?",
  "session_id": "optional-session-id"
}
```

Response:

```json
{
  "session_id": "uuid-or-existing-id",
  "answer": "...markdown response with code blocks...",
  "detected_language": "python"
}
```

### `DELETE /chat/{session_id}`
Clears in-memory backend session history.

---

## 7) AI Behavior Design

The backend injects a **system prompt** that enforces:

1. Clear explanation
2. At least one fenced code example
3. Optional optimization notes
4. Clarifying question when prompt is ambiguous
5. Safer coding practices and edge-case awareness

---

## 8) Scalability Notes (Next Steps)

For production, replace in-memory session store with:

- Redis (fast, session-friendly)
- PostgreSQL (durable, queryable)

Also consider:

- Authentication (JWT/session cookies)
- Rate limiting
- Structured logging + observability
- Conversation summarization for long chats

---

## 9) Deployment Options

### Option A: Render (easy full-stack)

1. Push the repository to GitHub.
2. Create the service from the included `render.yaml`, or use these exact commands:
   - Build: `python -m pip install -r requirements.txt`
   - Start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
3. Set `GROQ_API_KEY` in Render's environment-variable dashboard.
4. Host `frontend/` as a static site (Render Static Site, Netlify, or Vercel).
5. Define `window.QA_API_BASE_URL` with the deployed backend URL before loading
   `frontend/app.js`.

### Option B: Railway

- Use the root build command `python -m pip install -r requirements.txt` and
  the start command `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
- Add `GROQ_API_KEY` in the Railway dashboard.
- Deploy frontend separately as static site

### Option C: Vercel + separate backend

- Vercel for frontend static hosting
- Render/Railway/Fly.io for backend API

---

## 10) Beginner Tips

- Start with local setup only
- Confirm `/health` works before opening frontend
- Ask simple prompts first (e.g., "Explain JavaScript promises")
- If responses fail, check backend logs and your API key

---

## 11) Security Notes

- Never commit real API keys. If a key is shared in chat, revoke/rotate it in the provider dashboard before using a replacement locally.
- Keep `.env` out of source control
- Add request validation and rate limits for public deployment
