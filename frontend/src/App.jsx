import { useState, useRef, useEffect } from 'react'

const API = 'http://localhost:8000'

function formatTime() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const IconChat = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  </svg>
)

const IconX = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
  </svg>
)

const IconSend = () => (
  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
  </svg>
)

const IconShield = () => (
  <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
  </svg>
)

const IconZap = () => (
  <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
  </svg>
)

const IconTrend = () => (
  <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" /><polyline points="17 6 23 6 23 12" />
  </svg>
)

const IconSupport = () => (
  <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 18v-6a9 9 0 0 1 18 0v6" />
    <path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z" />
  </svg>
)

const IconUser = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
  </svg>
)

const FEATURES = [
  { icon: <IconShield />, title: 'Bank-grade security', desc: 'Every account is protected by 256-bit encryption, real-time fraud detection, and multi-factor authentication around the clock.' },
  { icon: <IconZap />, title: 'Instant transfers', desc: 'Move money between accounts in seconds. Send to anyone, pay bills, and set up direct deposit — all without visiting a branch.' },
  { icon: <IconTrend />, title: 'Grow your savings', desc: 'Competitive APYs on savings accounts and CDs. Transparent rates, no surprises, and tools to help your money work harder.' },
  { icon: <IconSupport />, title: 'AI-powered support', desc: 'Our virtual assistant answers questions instantly — from branch hours to your transaction history — any time of day.' },
]

const STATS = [
  { value: '50,000+', label: 'Customers' },
  { value: '$2B+', label: 'Assets managed' },
  { value: '99.9%', label: 'Uptime' },
  { value: '100+', label: 'Years in business' },
]

const FOOTER_COLS = [
  { heading: 'Products', links: ['Checking', 'Savings', 'Credit Cards', 'Mortgages', 'Investments'] },
  { heading: 'Company', links: ['About Us', 'Careers', 'Newsroom', 'Community'] },
  { heading: 'Support', links: ['Help Center', 'Contact Us', 'Security Center', 'Privacy Policy', 'Terms of Use'] },
]

export default function App() {
  const [messages, setMessages] = useState([{
    id: 0, role: 'bot', time: formatTime(),
    text: "Hello! I'm your PalBank virtual assistant. I can answer general banking questions. Sign in to get account-specific help.",
  }])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [isChatOpen, setIsChatOpen] = useState(false)

  const [token, setToken] = useState(null)
  const [user, setUser] = useState(null)
  const [showLogin, setShowLogin] = useState(false)
  const [loginForm, setLoginForm] = useState({ username: '', password: '' })
  const [loginError, setLoginError] = useState('')
  const [loginLoading, setLoginLoading] = useState(false)

  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    if (isChatOpen) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isChatOpen])

  async function sendMessage(e) {
    e.preventDefault()
    const text = input.trim()
    if (!text || loading) return

    // Build history from prior turns before adding the current message.
    // Cap at last 20 messages (10 turns) and skip the initial bot greeting (id=0).
    const history = messages
      .filter(m => m.id !== 0)
      .slice(-20)
      .map(m => ({ role: m.role === 'bot' ? 'assistant' : 'user', content: m.text }))

    setMessages(prev => [...prev, { id: Date.now(), role: 'user', text, time: formatTime() }])
    setInput('')
    setLoading(true)
    try {
      const headers = { 'Content-Type': 'application/json' }
      if (token) headers['Authorization'] = `Bearer ${token}`
      const res = await fetch(`${API}/chat`, { method: 'POST', headers, body: JSON.stringify({ message: text, history }) })
      const data = await res.json()
      const text2 = res.ok ? data.response : (data.detail || 'Something went wrong. Please try again.')
      setMessages(prev => [...prev, { id: Date.now() + 1, role: 'bot', text: text2, time: formatTime() }])
    } catch {
      setMessages(prev => [...prev, { id: Date.now() + 1, role: 'bot', text: 'Connection error. Please try again.', time: formatTime() }])
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
      const res = await fetch(`${API}/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(loginForm) })
      const data = await res.json()
      if (!res.ok) { setLoginError(data.detail || 'Login failed. Please check your credentials.'); return }
      setToken(data.access_token)
      setUser({ full_name: data.full_name, role: data.role })
      setShowLogin(false)
      setLoginForm({ username: '', password: '' })
      setMessages(prev => [...prev, {
        id: Date.now(), role: 'bot', time: formatTime(),
        text: `Welcome back, ${data.full_name}! You're signed in as ${data.role === 'admin' ? 'an administrator' : 'a customer'}. Ask me about your accounts, recent transactions, or anything else.`,
      }])
    } catch {
      setLoginError('Connection error. Please try again.')
    } finally {
      setLoginLoading(false)
    }
  }

  async function handleLogout() {
    try { await fetch(`${API}/logout`, { method: 'POST', headers: token ? { Authorization: `Bearer ${token}` } : {} }) } catch { }
    const name = user?.full_name
    setToken(null)
    setUser(null)
    setMessages(prev => [...prev, { id: Date.now(), role: 'bot', time: formatTime(), text: `You've been signed out, ${name}. You can still ask me general banking questions anytime.` }])
  }

  return (
    <div className="site">

      {/* ── Navbar ── */}
      <header className="navbar">
        <div className="container nav-inner">
          <a href="#" className="nav-brand">
            <span className="brand-mark">PB</span>
            <span className="brand-name">PalBank</span>
          </a>
          <nav className="nav-links">
            <a href="#features" className="nav-link">Products</a>
            <a href="#" className="nav-link">Services</a>
            <a href="#" className="nav-link">About</a>
            <a href="#" className="nav-link">Support</a>
          </nav>
          <div className="nav-actions">
            {user ? (
              <>
                <div className="nav-user-pill">
                  <IconUser />
                  <span>{user.full_name.split(' ')[0]}</span>
                  <span className={`role-badge ${user.role}`}>{user.role}</span>
                </div>
                <button className="btn-ghost" onClick={handleLogout}>Sign out</button>
              </>
            ) : (
              <>
                <button className="btn-ghost" onClick={() => setShowLogin(true)}>Sign in</button>
                <button className="btn-navy" onClick={() => setShowLogin(true)}>Open account</button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* ── Hero ── */}
      <section className="hero">
        <div className="container hero-inner">
          <div className="hero-copy">
            <p className="hero-eyebrow">Trusted since 1924 · FDIC Insured</p>
            <h1 className="hero-h1">
              Banking built<br />
              for your <span className="hero-gold">future</span>
            </h1>
            <p className="hero-body">
              Manage your money with confidence. Secure accounts, instant transfers,
              and AI-powered support — all in one place.
            </p>
            <div className="hero-btns">
              <button className="btn-gold" onClick={() => setShowLogin(true)}>Get started</button>
              <button className="btn-outline-light" onClick={() => setIsChatOpen(true)}>Talk to an assistant</button>
            </div>
            <div className="hero-badges">
              <span className="hero-badge">FDIC Insured</span>
              <span className="hero-badge">256-bit SSL</span>
              <span className="hero-badge">No hidden fees</span>
            </div>
          </div>

          <div className="hero-visual">
            <div className="card-3d">
              <div className="debit-card">
                <div className="dc-top">
                  <div className="dc-chip" />
                  <span className="dc-brand">PB</span>
                </div>
                <div className="dc-number">•••• •••• •••• 4821</div>
                <div className="dc-bottom">
                  <div>
                    <div className="dc-label">CARDHOLDER</div>
                    <div className="dc-value">{user ? user.full_name.toUpperCase() : 'JOHN SMITH'}</div>
                  </div>
                  <div>
                    <div className="dc-label">EXPIRES</div>
                    <div className="dc-value">12 / 28</div>
                  </div>
                </div>
              </div>
              <div className="balance-card">
                <div className="bc-label">Available balance</div>
                <div className="bc-amount">$24,831.50</div>
                <div className="bc-trend">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><polyline points="18 15 12 9 6 15" /></svg>
                  2.4% this month
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section className="features-section" id="features">
        <div className="container">
          <div className="section-head">
            <h2 className="section-h2">Everything you need, nothing you don't</h2>
            <p className="section-sub">Built around your everyday financial life with enterprise-grade security.</p>
          </div>
          <div className="features-grid">
            {FEATURES.map((f, i) => (
              <div className="feature-card" key={i}>
                <div className="feature-icon-wrap">{f.icon}</div>
                <h3 className="feature-h3">{f.title}</h3>
                <p className="feature-p">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Stats ── */}
      <section className="stats-section">
        <div className="container stats-grid">
          {STATS.map((s, i) => (
            <div className="stat-item" key={i}>
              <div className="stat-value">{s.value}</div>
              <div className="stat-label">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="cta-section">
        <div className="container cta-inner">
          <div className="cta-copy">
            <h2 className="cta-h2">Ready to take control of your finances?</h2>
            <p className="cta-sub">Open an account in under 5 minutes. No paperwork. No branch visit required.</p>
          </div>
          <button className="btn-gold" onClick={() => setShowLogin(true)}>Open an account</button>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="footer">
        <div className="container footer-inner">
          <div className="footer-brand">
            <div className="footer-logo">
              <span className="brand-mark sm">PB</span>
              <span>PalBank</span>
            </div>
            <p className="footer-tagline">Member FDIC · Equal Housing Lender</p>
          </div>
          <div className="footer-cols">
            {FOOTER_COLS.map(col => (
              <div className="footer-col" key={col.heading}>
                <div className="footer-col-heading">{col.heading}</div>
                {col.links.map(l => <a href="#" key={l} className="footer-link">{l}</a>)}
              </div>
            ))}
          </div>
        </div>
        <div className="footer-bar">
          <div className="container footer-bar-inner">
            <span>© 2026 PalBank. All rights reserved.</span>
            <span className="footer-edu">This website is built solely for educational purposes.</span>
          </div>
        </div>
      </footer>

      {/* ── Chat widget ── */}
      <div className="chat-widget">
        {isChatOpen && (
          <div className="chat-panel">
            <div className="cp-header">
              <div className="cp-identity">
                <div className="cp-avatar">PB</div>
                <div>
                  <div className="cp-name">PalBank Assistant</div>
                  <div className="cp-status"><span className="status-dot" />Online</div>
                </div>
              </div>
              <div className="cp-actions">
                {user ? (
                  <span className="cp-user-tag">
                    {user.full_name.split(' ')[0]}
                    <span className={`role-badge ${user.role} xs`}>{user.role}</span>
                  </span>
                ) : (
                  <button className="cp-signin-btn" onClick={() => setShowLogin(true)}>Sign in</button>
                )}
                <button className="icon-btn" onClick={() => setIsChatOpen(false)}>
                  <IconX />
                </button>
              </div>
            </div>

            {!user && (
              <div className="cp-guest-bar">
                Sign in to access your account details.
                <button className="cp-guest-cta" onClick={() => setShowLogin(true)}>Log in</button>
              </div>
            )}

            <div className="cp-messages">
              {messages.map(msg => (
                <div key={msg.id} className={`msg-row ${msg.role}`}>
                  {msg.role === 'bot' && <div className="msg-av">PB</div>}
                  <div className="msg-body">
                    <div className={`msg-bubble ${msg.role}`}>{msg.text}</div>
                    <div className="msg-time">{msg.time}</div>
                  </div>
                </div>
              ))}
              {loading && (
                <div className="msg-row bot">
                  <div className="msg-av">PB</div>
                  <div className="msg-body">
                    <div className="msg-bubble bot typing">
                      <span className="dot" /><span className="dot" /><span className="dot" />
                    </div>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            <form className="cp-input-row" onSubmit={sendMessage}>
              <input
                ref={inputRef}
                className="cp-input"
                type="text"
                placeholder="Ask me anything…"
                value={input}
                onChange={e => setInput(e.target.value)}
                disabled={loading}
              />
              <button className="cp-send" type="submit" disabled={loading || !input.trim()}>
                <IconSend />
              </button>
            </form>
          </div>
        )}

        <button
          className={`chat-fab ${isChatOpen ? 'open' : ''}`}
          onClick={() => setIsChatOpen(p => !p)}
        >
          {isChatOpen ? <IconX size={20} /> : <><IconChat /><span>Ask us</span></>}
        </button>
      </div>

      {/* ── Login modal ── */}
      {showLogin && (
        <div className="overlay" onClick={() => setShowLogin(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <button className="modal-close icon-btn" onClick={() => setShowLogin(false)}><IconX /></button>
            <div className="modal-brand">
              <span className="brand-mark sm">PB</span>
              <span>PalBank</span>
            </div>
            <h2 className="modal-h2">Welcome back</h2>
            <p className="modal-sub">Sign in to manage your accounts.</p>

            <form onSubmit={handleLogin}>
              <div className="field">
                <label className="field-label">Username</label>
                <input className="field-input" type="text" placeholder="Enter your username"
                  value={loginForm.username} onChange={e => setLoginForm(f => ({ ...f, username: e.target.value }))}
                  autoFocus required />
              </div>
              <div className="field">
                <label className="field-label">Password</label>
                <input className="field-input" type="password" placeholder="Enter your password"
                  value={loginForm.password} onChange={e => setLoginForm(f => ({ ...f, password: e.target.value }))}
                  required />
              </div>
              {loginError && <div className="field-error">{loginError}</div>}
              <button className="btn-navy btn-block" type="submit" disabled={loginLoading}>
                {loginLoading ? 'Signing in…' : 'Sign in'}
              </button>
            </form>

            <div className="modal-hint">
              <strong>Demo accounts</strong><br />
              admin / admin123 &nbsp;·&nbsp; jsmith / password123
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
