import os
import uuid
from typing import Dict, List, Literal, Optional
from groq import Groq
 codex/design-programming-qa-ai-assistant-application-31mmih
import httpx

 main
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


client = Groq(api_key=os.environ["k_aIXFJXkRJpW07Nn81pyxWGdyb3FYC56X3r8QajIaPk8OvDNBohOl"])

load_dotenv()

# Groq supplies an OpenAI-compatible chat-completions API. Keep this value in
# the environment only; it must never be sent to the browser or committed.
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL_NAME = "llama-3.3-70b-versatile"

# ✅ NEW Gemini SDK
from google import genai

# Load env variables
load_dotenv()

# Get Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing. Add it to your environment variables.")

# Initialize Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)
for m in client.models.list():
    print(m.name)
 main

app = FastAPI(title="Programming Q&A AI Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
 codex/design-programming-qa-ai-assistant-application-31mmih
    # Use an explicit origin list in production, for example:
    # FRONTEND_ORIGINS=https://your-app.example
    allow_origins=[
        origin.strip()
        for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:5500").split(",")
        if origin.strip()
    ],
    allow_credentials=False,

    allow_origins=["*"],
    allow_credentials=True,
 main
    allow_methods=["*"],
    allow_headers=["*"],
)

 codex/design-programming-qa-ai-assistant-application-31mmih
# In-memory session store. Replace with Redis/Postgres for production.

# In-memory session store
 main
chat_sessions: Dict[str, List[dict]] = {}

SYSTEM_PROMPT = (
    "You are an expert programming mentor. Help users with Python, Java, C++, "
 codex/design-programming-qa-ai-assistant-application-31mmih
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

    "JavaScript, and SQL. Always provide:\n"
    "1) Clear explanation\n"
    "2) Code example\n"
    "3) Optional improvements\n"
)

# =======================
# Models
# =======================

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=2, max_length=4000)
    session_id: Optional[str] = None
 main


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

 codex/design-programming-qa-ai-assistant-application-31mmih
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

# =======================
# Helper functions
# =======================

def detect_language(question: str) -> str:
    text = question.lower()
    rules = {
        "python": ["python", "pandas", "numpy", "def "],
        "java": ["java", "spring", "public static"],
        "cpp": ["c++", "std::", "#include"],
        "javascript": ["js", "node", "react"],
        "sql": ["select", "join", "sql"],
    }

    for lang, keywords in rules.items():
        if any(k in text for k in keywords):
main
            return lang
    return "unknown"


 codex/design-programming-qa-ai-assistant-application-31mmih
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

def get_or_create_session_id(session_id: Optional[str]) -> str:
    if session_id and session_id in chat_sessions:
        return session_id

    new_id = session_id or str(uuid.uuid4())
    chat_sessions[new_id] = []
    return new_id


def generate_ai_response(message: str) -> str:
    try:
        response = client.models.generate_content(
            model="models/gemini-2.0-flash-lite",
            contents=message,
        )
        return response.text or "No response from AI."
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini error: {e}")


# =======================
# Routes
# =======================

@app.get("/health")
def health_check():
    return {"status": "ok", "model": "gemini-1.5-flash"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
main
    user_message = request.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

 codex/design-programming-qa-ai-assistant-application-31mmih
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

    session_id = get_or_create_session_id(request.session_id)
    detected_language = detect_language(user_message)

    # Add system prompt
    final_prompt = f"{SYSTEM_PROMPT}\n\nUser: {user_message}"

    ai_answer = generate_ai_response(final_prompt)

    return ChatResponse(
        session_id=session_id,
        answer=ai_answer,
        detected_language=detected_language,
    )


@app.delete("/chat/{session_id}")
def clear_session(session_id: str):
main
    chat_sessions.pop(session_id, None)
    return {"cleared": True, "session_id": session_id}
