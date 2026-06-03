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

app = FastAPI(title="First National Bank Chatbot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SYSTEM_PROMPT = (
    "You are a helpful banking assistant for First National Bank. "
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

UNSAFE_PATTERN = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|TRUNCATE|REPLACE|MERGE|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)


class LoginRequest(BaseModel):
    username: str
    password: str


class ChatRequest(BaseModel):
    message: str


# ── helpers ──────────────────────────────────────────────────────────────────

def decode_token(authorization: Optional[str]) -> Optional[dict]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


def ask_claude(user_message: str, system: str = SYSTEM_PROMPT) -> str:
    try:
        resp = claude.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        return resp.content[0].text.strip()
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=503, detail="AI service authentication failed. Check your ANTHROPIC_API_KEY.")
    except anthropic.BadRequestError as e:
        msg = str(e)
        if "credit balance" in msg.lower():
            raise HTTPException(status_code=503, detail="AI service unavailable: insufficient API credits. Please add credits at console.anthropic.com.")
        raise HTTPException(status_code=503, detail=f"AI service error: {e}")
    except anthropic.APIError as e:
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {e}")


def get_faqs() -> str:
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT question, answer FROM faqs")).fetchall()
    return "\n\n".join(f"Q: {r[0]}\nA: {r[1]}" for r in rows)


def answer_from_faqs(user_message: str) -> str:
    faqs = get_faqs()
    prompt = (
        f"Here are our banking FAQs:\n\n{faqs}\n\n"
        f"Using only the information above, answer this question: {user_message}\n"
        "If the answer is not covered, say so politely."
    )
    return ask_claude(prompt)


def is_faq_question(message: str) -> bool:
    answer = ask_claude(
        f'Is this a general banking FAQ question? Reply only YES or NO.\n\nQuestion: "{message}"'
    )
    return answer.upper().startswith("YES")


def classify_question(message: str) -> str:
    """Returns 'A' for FAQ, 'B' for account-specific."""
    answer = ask_claude(
        f'Classify this banking question — is it '
        f'(A) a general FAQ or '
        f'(B) an account-specific question requiring personal data? '
        f'Reply only A or B.\n\nQuestion: "{message}"'
    )
    return "B" if answer.strip().upper().startswith("B") else "A"


def generate_query(message: str, user_id: Optional[int], is_admin: bool) -> str:
    restriction = (
        "No user_id restriction is needed (admin access)."
        if is_admin
        else (
            f"ALWAYS include WHERE user_id = {user_id} or "
            f"WHERE account_id IN (SELECT id FROM accounts WHERE user_id = {user_id}) "
            "to restrict data to this user only."
        )
    )
    prompt = (
        f"Database schema:\n{DB_SCHEMA}\n\n"
        f"Generate a safe SQLite SELECT query to answer: \"{message}\"\n"
        f"{restriction}\n"
        "Rules:\n"
        "- Return ONLY the raw SQL query, no explanation, no markdown, no code fences.\n"
        "- Never use DROP, DELETE, UPDATE, INSERT, ALTER, CREATE, TRUNCATE.\n"
        "- Only use SELECT statements."
    )
    raw = ask_claude(prompt)
    # Strip markdown fences if Claude adds them
    raw = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE).replace("```", "").strip()
    return raw


def execute_query(query: str) -> list[dict]:
    if UNSAFE_PATTERN.search(query):
        raise ValueError("Query contains disallowed SQL keywords.")
    with engine.connect() as conn:
        result = conn.execute(text(query))
        cols = list(result.keys())
        return [dict(zip(cols, row)) for row in result.fetchall()]


def answer_from_data(user_message: str, data: list[dict]) -> str:
    data_str = str(data) if data else "No records found."
    prompt = (
        f"A user asked: \"{user_message}\"\n\n"
        f"Here is the relevant data from our banking database:\n{data_str}\n\n"
        "Please answer the user's question in plain conversational English using this data."
    )
    return ask_claude(prompt)


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

    # ── Guest (not logged in) ─────────────────────────────────────────────
    if user is None:
        if is_faq_question(req.message):
            return {"response": answer_from_faqs(req.message)}
        return {
            "response": (
                "I can only answer general banking FAQs. "
                "Please log in to ask about your account."
            )
        }

    role = user.get("role", "customer")
    user_id = user.get("user_id")

    # ── Customer or Admin ─────────────────────────────────────────────────
    classification = classify_question(req.message)

    if classification == "A":
        return {"response": answer_from_faqs(req.message)}

    # Account-specific query
    is_admin = role == "admin"
    try:
        query = generate_query(req.message, user_id, is_admin)
        data = execute_query(query)
        return {"response": answer_from_data(req.message, data)}
    except ValueError as e:
        return {"response": f"Sorry, I couldn't process that request safely: {e}"}
    except Exception:
        return {
            "response": (
                "I encountered an error retrieving your account data. "
                "Please try rephrasing your question or contact support."
            )
        }
