import os
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import anthropic
import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 2
MODEL = "claude-haiku-4-5"
DB_PATH = "bank.db"

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

app = FastAPI(title="PalBank Chatbot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SYSTEM_PROMPT = (
    "You are a helpful banking assistant for PalBank. "
    "Only answer questions related to banking, accounts, transactions, and financial services. "
    "Do not answer questions outside this domain. Be concise and professional."
)

DB_SCHEMA = """
Tables:
  users(id, username, full_name, email, role, created_at)
  accounts(id, user_id, account_number, account_type, balance, opened_at)
  transactions(id, account_id, date, description, amount, running_balance)
  faqs(id, question, answer)
"""

# Sentinel prefix Claude uses to signal a SQL query is needed
SQL_SENTINEL = "__SQL__:"

UNSAFE_PATTERN = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|TRUNCATE|REPLACE|MERGE|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)


class LoginRequest(BaseModel):
    username: str
    password: str


class HistoryMessage(BaseModel):
    role: str     # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[HistoryMessage] = []


# ── helpers ──────────────────────────────────────────────────────────────────

def decode_token(authorization: Optional[str]) -> Optional[dict]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


def build_messages(prompt: str, history: list[HistoryMessage]) -> list[dict]:
    """
    Prepend prior turns to the current prompt.
    Claude requires strictly alternating user/assistant roles starting with user,
    so we normalise the history before appending the new user message.
    """
    normalised = []
    expected = "user"
    for msg in history:
        if msg.role == expected:
            normalised.append({"role": msg.role, "content": msg.content})
            expected = "assistant" if expected == "user" else "user"
    normalised.append({"role": "user", "content": prompt})
    return normalised


def ask_claude(prompt: str, history: list[HistoryMessage] = None, system: str = SYSTEM_PROMPT) -> str:
    messages = build_messages(prompt, history or [])
    try:
        resp = claude.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system,
            messages=messages,
        )
        return resp.content[0].text.strip()
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=503, detail="AI service authentication failed. Check your ANTHROPIC_API_KEY.")
    except anthropic.BadRequestError as e:
        if "credit balance" in str(e).lower():
            raise HTTPException(status_code=503, detail="AI service unavailable: insufficient API credits. Please add credits at console.anthropic.com.")
        raise HTTPException(status_code=503, detail=f"AI service error: {e}")
    except anthropic.APIError as e:
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {e}")


def get_faqs() -> str:
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT question, answer FROM faqs")).fetchall()
    return "\n\n".join(f"Q: {r[0]}\nA: {r[1]}" for r in rows)


def execute_query(query: str) -> list[dict]:
    if UNSAFE_PATTERN.search(query):
        raise ValueError("Query contains disallowed SQL keywords.")
    with engine.connect() as conn:
        result = conn.execute(text(query))
        cols = list(result.keys())
        return [dict(zip(cols, row)) for row in result.fetchall()]


def chat_guest(message: str, history: list[HistoryMessage]) -> str:
    """1 Claude call: answer FAQ directly, or return gate message."""
    faqs = get_faqs()
    prompt = (
        f"Banking FAQs:\n\n{faqs}\n\n"
        f"User question: \"{message}\"\n\n"
        "If this is a general banking question covered by the FAQs above, answer it concisely.\n"
        "If it is NOT a general banking/FAQ question, respond with exactly: __NOT_FAQ__"
    )
    response = ask_claude(prompt, history)
    if response.strip().startswith("__NOT_FAQ__"):
        return "I can only answer general banking FAQs. Please log in to ask about your account."
    return response


def chat_authenticated(message: str, user_id: int, is_admin: bool, history: list[HistoryMessage]) -> str:
    """
    1 Claude call for FAQ questions.
    2 Claude calls for account-specific questions (generate SQL, then format results).
    """
    faqs = get_faqs()
    restriction = (
        "No user_id restriction needed — this is an admin query."
        if is_admin
        else (
            f"ALWAYS restrict to this user: include "
            f"WHERE user_id = {user_id} or "
            f"WHERE account_id IN (SELECT id FROM accounts WHERE user_id = {user_id})."
        )
    )
    prompt = (
        f"Database schema:\n{DB_SCHEMA}\n"
        f"Banking FAQs:\n\n{faqs}\n\n"
        f"User question: \"{message}\"\n\n"
        "Choose exactly one of the following responses:\n"
        "1. If this is a general FAQ question, answer it directly using the FAQ context above.\n"
        f"2. If this requires personal account data, respond with a single line in this exact format:\n"
        f"   {SQL_SENTINEL} <SQLite SELECT query>\n"
        f"   Query rules: {restriction} "
        "Never use DROP, DELETE, UPDATE, INSERT, ALTER, CREATE, or TRUNCATE. SELECT only."
    )
    response = ask_claude(prompt, history)

    if not response.startswith(SQL_SENTINEL):
        return response

    # Extract, sanitise, and execute the generated query
    raw_query = response[len(SQL_SENTINEL):].strip()
    raw_query = re.sub(r"```(?:sql)?", "", raw_query, flags=re.IGNORECASE).replace("```", "").strip()

    try:
        data = execute_query(raw_query)
    except ValueError as e:
        return f"Sorry, I couldn't process that request safely: {e}"
    except Exception:
        return "I encountered an error retrieving your account data. Please try rephrasing your question or contact support."

    # Second call: format the query results as natural language
    data_str = str(data) if data else "No records found."
    return ask_claude(
        f"A user asked: \"{message}\"\n\n"
        f"Here is the relevant data from our banking database:\n{data_str}\n\n"
        "Answer the user's question in plain conversational English using this data.",
        history,
    )


# ── endpoints ─────────────────────────────────────────────────────────────────

@app.post("/login")
def login(req: LoginRequest):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, username, password_hash, full_name, role FROM users WHERE username = :u"),
            {"u": req.username},
        ).fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id, username, pw_hash, full_name, role = row
    if not bcrypt.checkpw(req.password.encode(), pw_hash.encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"access_token": token, "token_type": "bearer", "role": role, "full_name": full_name}


@app.post("/logout")
def logout(authorization: Optional[str] = Header(default=None)):
    return {"message": "Logged out successfully"}


@app.post("/chat")
def chat(req: ChatRequest, authorization: Optional[str] = Header(default=None)):
    user = decode_token(authorization)

    if user is None:
        return {"response": chat_guest(req.message, req.history)}

    return {"response": chat_authenticated(
        req.message,
        user_id=user.get("user_id"),
        is_admin=user.get("role") == "admin",
        history=req.history,
    )}
