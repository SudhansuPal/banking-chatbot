import { useState, useRef, useEffect } from 'react'

const API = 'http://localhost:8000'

function formatTime() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default function App() {
  const [messages, setMessages] = useState([
    {
      id: 0,
      role: 'bot',
      text: 'Hello! I\'m the First National Bank virtual assistant. How can I help you today?',
      time: formatTime(),
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [token, setToken] = useState(null)
  const [user, setUser] = useState(null) // { full_name, role }
  const [showLogin, setShowLogin] = useState(false)
  const [loginForm, setLoginForm] = useState({ username: '', password: '' })
  const [loginError, setLoginError] = useState('')
  const [loginLoading, setLoginLoading] = useState(false)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function sendMessage(e) {
    e.preventDefault()
    const text = input.trim()
    if (!text || loading) return

    const userMsg = { id: Date.now(), role: 'user', text, time: formatTime() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const headers = { 'Content-Type': 'application/json' }
      if (token) headers['Authorization'] = `Bearer ${token}`

      const res = await fetch(`${API}/chat`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ message: text }),
      })

      const data = await res.json()
      setMessages(prev => [
        ...prev,
        { id: Date.now() + 1, role: 'bot', text: data.response, time: formatTime() },
      ])
    } catch {
      setMessages(prev => [
        ...prev,
        { id: Date.now() + 1, role: 'bot', text: 'Connection error. Please try again.', time: formatTime() },
      ])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  async function handleLogin(e) {
    e.preventDefault()
    setLoginError('')
    setLoginLoading(true)

    try {
      const res = await fetch(`${API}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(loginForm),
      })
      const data = await res.json()

      if (!res.ok) {
        setLoginError(data.detail || 'Login failed')
        return
      }

      setToken(data.access_token)
      setUser({ full_name: data.full_name, role: data.role })
      setShowLogin(false)
      setLoginForm({ username: '', password: '' })
      setMessages(prev => [
        ...prev,
        {
          id: Date.now(),
          role: 'bot',
          text: `Welcome, ${data.full_name}! You're now logged in as ${data.role}. You can now ask about your account details.`,
          time: formatTime(),
        },
      ])
    } catch {
      setLoginError('Connection error. Please try again.')
    } finally {
      setLoginLoading(false)
    }
  }

  async function handleLogout() {
    try {
      await fetch(`${API}/logout`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
    } catch { /* ignore */ }

    const name = user?.full_name
    setToken(null)
    setUser(null)
    setMessages(prev => [
      ...prev,
      {
        id: Date.now(),
        role: 'bot',
        text: `Goodbye, ${name}! You've been logged out. You can still ask general banking questions.`,
        time: formatTime(),
      },
    ])
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-left">
          <div className="bank-logo">FNB</div>
          <div>
            <div className="header-title">First National Bank</div>
            <div className="header-subtitle">Virtual Assistant</div>
          </div>
        </div>
        <div className="header-right">
          {user && (
            <div className="user-badge">
              <span className="user-name">{user.full_name}</span>
              <span className={`role-tag role-${user.role}`}>{user.role}</span>
            </div>
          )}
          {user ? (
            <button className="btn btn-outline" onClick={handleLogout}>
              Log out
            </button>
          ) : (
            <button className="btn btn-primary" onClick={() => setShowLogin(true)}>
              Log in
            </button>
          )}
        </div>
      </header>

      {/* Guest banner */}
      {!user && (
        <div className="guest-banner">
          You're chatting as a guest.{' '}
          <button className="banner-link" onClick={() => setShowLogin(true)}>
            Log in
          </button>{' '}
          to access your account information.
        </div>
      )}

      {/* Chat area */}
      <main className="chat-area">
        <div className="messages">
          {messages.map(msg => (
            <div key={msg.id} className={`message-row ${msg.role}`}>
              {msg.role === 'bot' && <div className="avatar bot-avatar">FNB</div>}
              <div className="bubble-wrap">
                <div className={`bubble ${msg.role}`}>{msg.text}</div>
                <div className="msg-time">{msg.time}</div>
              </div>
              {msg.role === 'user' && <div className="avatar user-avatar">You</div>}
            </div>
          ))}

          {loading && (
            <div className="message-row bot">
              <div className="avatar bot-avatar">FNB</div>
              <div className="bubble-wrap">
                <div className="bubble bot typing">
                  <span className="dot" />
                  <span className="dot" />
                  <span className="dot" />
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </main>

      {/* Input */}
      <form className="input-area" onSubmit={sendMessage}>
        <input
          ref={inputRef}
          className="chat-input"
          type="text"
          placeholder={user ? 'Ask about your account or general banking questions…' : 'Ask a general banking question…'}
          value={input}
          onChange={e => setInput(e.target.value)}
          disabled={loading}
        />
        <button className="send-btn" type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>

      {/* Login modal */}
      {showLogin && (
        <div className="modal-overlay" onClick={() => setShowLogin(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Log in to First National Bank</h2>
              <button className="modal-close" onClick={() => setShowLogin(false)}>✕</button>
            </div>

            <form onSubmit={handleLogin}>
              <div className="form-group">
                <label>Username</label>
                <input
                  type="text"
                  value={loginForm.username}
                  onChange={e => setLoginForm(f => ({ ...f, username: e.target.value }))}
                  placeholder="Enter your username"
                  autoFocus
                  required
                />
              </div>
              <div className="form-group">
                <label>Password</label>
                <input
                  type="password"
                  value={loginForm.password}
                  onChange={e => setLoginForm(f => ({ ...f, password: e.target.value }))}
                  placeholder="Enter your password"
                  required
                />
              </div>

              {loginError && <div className="login-error">{loginError}</div>}

              <button className="btn btn-primary btn-full" type="submit" disabled={loginLoading}>
                {loginLoading ? 'Logging in…' : 'Log in'}
              </button>
            </form>

            <div className="modal-hint">
              <strong>Demo credentials:</strong><br />
              admin / admin123 &nbsp;|&nbsp; jsmith / password123
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
