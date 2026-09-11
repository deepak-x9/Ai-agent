import os
import uuid
from typing import Dict, List, Literal, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


load_dotenv()

# Groq supplies an OpenAI-compatible chat-completions API. Keep this value in
# the environment only; it must never be sent to the browser or committed.
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL_NAME = "llama-3.3-70b-versatile"

app = FastAPI(title="Programming Q&A AI Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    # Use an explicit origin list in production, for example:
    # FRONTEND_ORIGINS=https://your-app.example
    allow_origins=[
        origin.strip()
        for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:5500").split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store. Replace with Redis/Postgres for production.
chat_sessions: Dict[str, List[dict]] = {}

SYSTEM_PROMPT = (
    "You are an expert programming mentor. Help users with Python, Java, C++, "
    "JavaScript, and SQL, but also provide guidance for other languages when asked. "
    "Your replies must be clear, practical, and beginner-friendly. "
    "Always include: 1) a short explanation, 2) at least one code example in fenced "
    "markdown blocks, and 3) optional optimization ideas if relevant. "
    "If the question is ambiguous, ask a concise clarifying question first. "
    "Use safe coding practices and mention edge cases when useful."
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=2, max_length=4000)
    session_id: Optional[str] = Field(default=None, min_length=1, max_length=128)


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    detected_language: Literal[
        "python",
        "java",
        "cpp",
        "javascript",
        "sql",
        "unknown",
    ]


def detect_language(question: str) -> str:
    text = question.lower()
    rules = {
        "python": ["python", "pandas", "numpy", "django", "flask", "def ", "pip"],
        "java": ["java", "spring", "jdk", "jvm", "public static void main"],
        "cpp": ["c++", "cpp", "std::", "#include", "g++", "template<"],
        "javascript": ["javascript", "js", "node", "react", "npm", "async/await"],
        "sql": ["sql", "select", "join", "group by", "postgres", "mysql", "sqlite"],
    }

    for lang, keywords in rules.items():
        if any(keyword in text for keyword in keywords):
            return lang
    return "unknown"


def get_ai_settings() -> tuple[str, str]:
    """Read model settings when a request arrives, keeping credentials server-side."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY is not configured. Add it to backend/.env and restart the server.",
        )
    return api_key, os.getenv("GROQ_MODEL", DEFAULT_MODEL_NAME)


def request_completion(messages: List[dict]) -> str:
    """Call Groq's OpenAI-compatible endpoint and return the first text answer."""
    api_key, model_name = get_ai_settings()
    try:
        response = httpx.post(
            f"{GROQ_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model_name, "messages": messages, "temperature": 0.3},
            timeout=30.0,
        )
        response.raise_for_status()
        answer = response.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
        # Do not expose provider responses or internal exceptions to API clients.
        raise HTTPException(status_code=502, detail="The AI provider could not complete the request.") from exc

    if not isinstance(answer, str) or not answer.strip():
        raise HTTPException(status_code=502, detail="The AI provider returned an empty response.")
    return answer.strip()


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "model": os.getenv("GROQ_MODEL", DEFAULT_MODEL_NAME)}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    user_message = request.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    session_id = request.session_id or str(uuid.uuid4())
    detected_language = detect_language(user_message)

    conversation = chat_sessions.get(session_id, [])
    try:
        # Keep last 12 turns to control token usage, plus this new message.
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *conversation[-12:],
            {"role": "user", "content": user_message},
            {
                "role": "system",
                "content": (
                    f"Detected language hint: {detected_language}. "
                    "Prefer examples in that language unless user asks otherwise."
                ),
            },
        ]
        ai_answer = request_completion(messages)
        chat_sessions.setdefault(session_id, conversation)
        conversation.append({"role": "user", "content": user_message})
        conversation.append({"role": "assistant", "content": ai_answer})

        return ChatResponse(
            session_id=session_id,
            answer=ai_answer,
            detected_language=detected_language,
        )
    except HTTPException:
        raise


@app.delete("/chat/{session_id}")
def clear_session(session_id: str) -> dict:
    chat_sessions.pop(session_id, None)
    return {"cleared": True, "session_id": session_id}
