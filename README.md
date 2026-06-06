# PalBank — Banking Customer Service Demo

I built this project to show how a real full-stack application can layer AI on top of solid engineering — not replace it. PalBank is a fictional bank with a complete customer-facing site, authenticated account access, and a conversational assistant that can answer FAQs or query live account data in plain English.

The goal wasn't to wrap an API call in a chat box. I wanted to demonstrate **auth, role-based access control, a realistic data model, and safe dynamic querying** — with Claude as the natural-language interface on top.

---

## What I Built

### Backend (FastAPI + SQLite)

- **REST API** with `/login`, `/logout`, and `/chat` endpoints
- **JWT authentication** (HS256, 2-hour expiry) with bcrypt password hashing
- **Three-tier RBAC** enforced server-side on every request — guest, customer, and admin
- **Relational schema** — users, accounts, transactions, and FAQs across four tables
- **Database seeding script** — 10 users, ~15 accounts, hundreds of synthetic transactions, and 18 PalBank FAQs
- **SQL safety layer** — regex blocklist on all generated queries; SELECT-only execution via SQLAlchemy

### Frontend (React + Vite)

- **Bank landing page** — hero section, feature cards, stats, and footer (no UI libraries — plain CSS)
- **Floating chat widget** with open/close toggle and typing indicator
- **Login modal** with error handling and role-aware welcome messages
- **Conversation history** — last 10 turns sent with each request for multi-turn context
- **Token in React state only** — never persisted to `localStorage`, `sessionStorage`, or cookies

### Where AI Fits In

Claude (`claude-haiku-4-5`) handles the parts that need language understanding, not the security or data access logic:

| Step | Who does it |
|---|---|
| Classify FAQ vs. account question | Claude |
| Answer general banking questions | Claude (from FAQ context) |
| Generate a scoped SQL query | Claude |
| Validate and execute the query | Server (blocklist + SQLAlchemy) |
| Format results as natural language | Claude |

Guests get FAQ answers or a login prompt. Customers get scoped queries (`WHERE user_id = …`). Admins get unrestricted read access. The model never touches the database directly.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLAlchemy, SQLite |
| Frontend | React 18, Vite, plain CSS |
| Auth | PyJWT (HS256), bcrypt |
| AI | Anthropic Claude API (`claude-haiku-4-5`) |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      React Frontend                          │
│   Landing page · Chat widget · Login modal · JWT in state   │
└──────────────────────────┬──────────────────────────────────┘
                           │  REST
┌──────────────────────────▼──────────────────────────────────┐
│                     FastAPI Backend                          │
│                                                              │
│  /login  →  bcrypt verify → issue JWT                       │
│  /chat   →  decode JWT → route by role → AI pipeline        │
│                                                              │
│  ┌────────────┐   ┌─────────────────┐   ┌─────────────────┐  │
│  │  RBAC      │   │  Claude calls   │   │  SQL guardrails │  │
│  │  guest /   │ → │  classify ·     │ → │  blocklist ·    │  │
│  │  customer /│   │  answer · SQL · │   │  SELECT only    │  │
│  │  admin     │   │  format         │   │                 │  │
│  └────────────┘   └─────────────────┘   └─────────────────┘  │
│                           │                                  │
│                  SQLAlchemy + SQLite                         │
│         users · accounts · transactions · faqs               │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
banking-chatbot/
├── backend/
│   ├── main.py             # FastAPI app — auth, chat pipeline, SQL safety
│   ├── generate_db.py      # Schema creation + synthetic data seeding
│   ├── bank.db             # SQLite database (generated locally, gitignored)
│   ├── requirements.txt
│   ├── .env.example
│   └── .env                # API keys and secrets (not committed)
├── frontend/
│   ├── src/
│   │   ├── App.jsx         # Landing page, chat UI, login flow
│   │   ├── App.css         # All styles (no external CSS libraries)
│   │   └── main.jsx
│   ├── index.html
│   └── package.json
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- An [Anthropic API key](https://console.anthropic.com) with available credits

### 1. Clone the repository

```bash
git clone https://github.com/SudhansuPal/banking-chatbot.git
cd banking-chatbot
```

### 2. Backend setup

```bash
cd backend

pip install -r requirements.txt

cp .env.example .env
# Set ANTHROPIC_API_KEY and JWT_SECRET in .env

python generate_db.py

uvicorn main:app --reload --port 8000
```

The API runs at `http://localhost:8000`.  
Interactive docs at `http://localhost:8000/docs`.

### 3. Frontend setup

```bash
cd frontend

npm install
npm run dev
```

The app runs at `http://localhost:5173`.

### Environment Variables

Create `backend/.env`:

```env
ANTHROPIC_API_KEY=sk-ant-...
JWT_SECRET=your-random-secret-string
```

Generate a secure secret:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Try It

**As a guest** (no login):

- "What are PalBank's branch hours?"
- "How do I dispute a charge?"

**As a customer** (log in as `jsmith`):

- "What is my current balance?"
- "Show me my recent transactions"
- "How many accounts do I have?"

**As an admin** (log in as `admin`):

- "List all customer accounts"
- "Who has the highest balance?"

---

## Demo Credentials

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | Admin |
| `jsmith` | `password123` | Customer |
| `mjones` | `password123` | Customer |
| `bwilliams` | `password123` | Customer |
| `sdavis` | `password123` | Customer |

> These credentials are for local development only. All data is synthetic.

---

## API Reference

### `POST /login`

Authenticates a user and returns a signed JWT.

```json
// Request
{ "username": "jsmith", "password": "password123" }

// Response
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "role": "customer",
  "full_name": "John Smith"
}
```

### `POST /logout`

Stateless logout — the client discards the token.

```json
// Response
{ "message": "Logged out successfully" }
```

### `POST /chat`

Accepts a natural language message and returns a response. Send an `Authorization` header to unlock account-specific queries.

```
Authorization: Bearer <token>   (optional)
```

```json
// Request
{ "message": "What is my current balance?" }

// Response
{ "response": "Your checking account (FNB4821903741) has a current balance of $3,421.50." }
```

The request body also accepts an optional `history` array of prior `{ role, content }` turns for multi-turn conversations.

---

## Security Model

### Authentication

Login issues an HS256 JWT with `user_id`, `username`, and `role`. The frontend keeps the token in React component state — not in browser storage — so it clears on page close and isn't accessible across tabs.

### Role-Based Access Control

Every `/chat` request is routed based on the decoded JWT:

| Role | Behavior |
|---|---|
| **Guest** (no token) | FAQ questions answered from the database; everything else prompts login |
| **Customer** | FAQ or account-specific queries scoped to `user_id` via prompt constraints |
| **Admin** | Same flow, but queries can access all accounts and transactions |

Access rules are enforced server-side. The frontend never decides what data a user can see.

### SQL Safety

Because Claude generates SQL at runtime, every query passes through validation before execution:

- Regex blocklist rejects `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE`, `TRUNCATE`, and related keywords
- Only `SELECT` statements are permitted
- Raw query strings are never returned in API responses
- All execution goes through SQLAlchemy with read-only intent

---

## What I'd Improve Next

- Structured logging and request tracing for the chat pipeline
- Rate limiting on `/chat` to prevent API abuse [done]
- Integration tests for RBAC and SQL blocklist edge cases

---
