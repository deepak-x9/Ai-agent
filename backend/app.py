import os
import uuid
from typing import Dict, List, Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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

app = FastAPI(title="Programming Q&A AI Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store
chat_sessions: Dict[str, List[dict]] = {}

SYSTEM_PROMPT = (
    "You are an expert programming mentor. Help users with Python, Java, C++, "
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
            return lang
    return "unknown"


def get_or_create_session_id(session_id: Optional[str]) -> str:
    if session_id and session_id in chat_sessions:
        return session_id

    new_id = session_id or str(uuid.uuid4())
    chat_sessions[new_id] = []
    return new_id


def generate_ai_response(message: str) -> str:
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
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
    user_message = request.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

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
    chat_sessions.pop(session_id, None)
    return {"cleared": True, "session_id": session_id}
