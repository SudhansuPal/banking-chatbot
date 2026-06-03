# First National Bank — AI Customer Service Chatbot

An AI-powered banking customer service application built with FastAPI, React, and Anthropic Claude. The system implements role-based access control so that unauthenticated users can ask general banking FAQs, authenticated customers can query their own account data, and admins have unrestricted access across all accounts.

---

## Features

- **Conversational AI** powered by Anthropic Claude (`claude-haiku-4-5`)
- **Three-tier access model** — guest, customer, and admin roles with server-side enforcement
- **Dynamic SQL generation** — Claude writes contextual database queries at runtime, scoped to the authenticated user
- **JWT authentication** — HS256 tokens stored in React state (never `localStorage`)
- **SQL injection protection** — blocklist validation on all Claude-generated queries before execution
- **Responsive UI** — clean, bank-styled chat interface with no external CSS libraries

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLAlchemy, SQLite |
| AI | Anthropic Claude API (`claude-haiku-4-5`) |
| Auth | PyJWT (HS256), bcrypt |
| Frontend | React 18, Vite, plain CSS |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     React Frontend                       │
│          Chat UI · Login Modal · JWT in state            │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP (REST)
┌────────────────────────▼────────────────────────────────┐
│                    FastAPI Backend                        │
│                                                          │
│   /login   →   validate credentials, issue JWT           │
│   /logout  →   stateless (client discards token)         │
│   /chat    →   role-based Claude routing pipeline        │
│                                                          │
│   ┌──────────────────────────────────────────────┐       │
│   │              Claude Routing Logic             │       │
│   │                                              │       │
│   │  Guest  →  FAQ check → answer or gate        │       │
│   │  Customer → classify → FAQ or scoped query   │       │
│   │  Admin    → classify → FAQ or open query     │       │
│   └──────────────────────────────────────────────┘       │
│                         │                                │
│              SQLAlchemy + SQLite                         │
└─────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
banking-chatbot/
├── backend/
│   ├── main.py             # FastAPI application — /login, /logout, /chat
│   ├── generate_db.py      # Database seeding script (run once)
│   ├── bank.db             # SQLite database (generated)
│   ├── requirements.txt
│   └── .env                # API keys and secrets (not committed)
├── frontend/
│   ├── src/
│   │   ├── App.jsx         # Main application component
│   │   ├── App.css         # Styles
│   │   └── main.jsx        # React entry point
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
git clone <your-repo-url>
cd banking-chatbot
```

### 2. Backend setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env   # or edit .env directly
# Set ANTHROPIC_API_KEY and JWT_SECRET in .env

# Seed the database (run once)
python generate_db.py

# Start the API server
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.  
Interactive API docs are available at `http://localhost:8000/docs`.

### 3. Frontend setup

```bash
cd frontend

npm install
npm run dev
```

The app will be available at `http://localhost:5173`.

### Environment Variables

Create a `backend/.env` file with the following:

```env
ANTHROPIC_API_KEY=sk-ant-...
JWT_SECRET=your-random-secret-string
```

Generate a secure `JWT_SECRET` with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Demo Credentials

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | Admin |
| `jsmith` | `password123` | Customer |
| `mjones` | `password123` | Customer |
| `bwilliams` | `password123` | Customer |
| `sdavis` | `password123` | Customer |

> **Note:** These credentials are for local development only. The seeded database contains synthetic data.

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

Stateless logout — the client is responsible for discarding the token.

```json
// Response
{ "message": "Logged out successfully" }
```

### `POST /chat`

Accepts a natural language message and returns an AI-generated response. Include the `Authorization` header to access account-specific data.

```
Authorization: Bearer <token>   (optional)
```

```json
// Request
{ "message": "What is my current balance?" }

// Response
{ "response": "Your checking account (FNB4821903741) has a current balance of $3,421.50." }
```

---

## Security Model

### Authentication

Login issues a signed HS256 JWT containing `user_id`, `username`, and `role` with a 2-hour expiry. The frontend stores the token exclusively in React component state — it is never written to `localStorage`, `sessionStorage`, or cookies, so it cannot be accessed cross-tab and is automatically cleared on page close.

### Role-Based Access Control

Access is enforced server-side on every `/chat` request based on the decoded JWT:

| Role | Behavior |
|---|---|
| **Guest** (no token) | Claude determines if the question is a general FAQ. If yes, answers from the FAQ table. If no, prompts the user to log in. |
| **Customer** | Claude classifies the question as FAQ or account-specific. Account queries always include `WHERE user_id = {user_id}`, enforced in the prompt and validated server-side. |
| **Admin** | Same classification flow, but queries are unrestricted — all accounts and transactions are accessible. |

### SQL Safety

All SQL generated by Claude passes through a server-side validation layer before execution:

- A regex blocklist rejects any query containing `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE`, or `TRUNCATE`
- Only `SELECT` statements are permitted
- Raw query strings are never included in API responses
- All queries execute through SQLAlchemy with read-only intent

---

## License

MIT
