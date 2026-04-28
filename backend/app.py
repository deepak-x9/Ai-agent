import os
import uuid
from typing import Dict, List, Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from openai import OpenAI
import google.generativeai as genai
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("models/gemini-1.5-flash")

response = model.generate_content("Hello")

print(response.text)

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing. Add it to your .env file.")

MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

app = FastAPI(title="Programming Q&A AI Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=OPENAI_API_KEY)

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
    session_id: Optional[str] = Field(default=None, description="Client session identifier")


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


def get_or_create_session_id(session_id: Optional[str]) -> str:
    if session_id and session_id in chat_sessions:
        return session_id

    new_id = session_id or str(uuid.uuid4())
    if new_id not in chat_sessions:
        chat_sessions[new_id] = []
    return new_id


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "model": MODEL_NAME}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    user_message = request.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    session_id = get_or_create_session_id(request.session_id)
    detected_language = detect_language(user_message)

    conversation = chat_sessions[session_id]
    conversation.append({"role": "user", "content": user_message})

    # Keep last 12 turns to control token usage.
    recent_conversation = conversation[-12:]

    try:
        response = client.responses.create(
            model=MODEL_NAME,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *recent_conversation,
                {
                    "role": "system",
                    "content": (
                        f"Detected language hint: {detected_language}. "
                        "Prefer examples in that language unless user asks otherwise."
                    ),
                },
            ],
            temperature=0.3,
        )

        ai_answer = response.output_text.strip()
        if not ai_answer:
            raise HTTPException(status_code=500, detail="Empty response from model.")

        conversation.append({"role": "assistant", "content": ai_answer})

        return ChatResponse(
            session_id=session_id,
            answer=ai_answer,
            detected_language=detected_language,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"AI request failed: {exc}") from exc


@app.delete("/chat/{session_id}")
def clear_session(session_id: str) -> dict:
    chat_sessions.pop(session_id, None)
    return {"cleared": True, "session_id": session_id}
