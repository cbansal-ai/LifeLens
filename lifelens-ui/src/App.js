import { useRef, useState } from "react";
import "./App.css";
import Timeline from "./Timeline";

const API_BASE = "http://127.0.0.1:8000";

function App() {
  const [page, setPage] = useState("ask");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [notice, setNotice] = useState("");
  const [userEmail, setUserEmail] = useState("bansalchhaya100@gmail.com");
  const [editingUser, setEditingUser] = useState(false);
  const [nextUserEmail, setNextUserEmail] = useState(userEmail);
  const [userError, setUserError] = useState("");
  const [switchingUser, setSwitchingUser] = useState(false);
  const fileInputRef = useRef(null);
  const switchUserAbortRef = useRef(null);

  const displayName = userEmail.split("@")[0] || "User";

  const askQuestion = async () => {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || loading) return;

    setMessages((prev) => [
      ...prev,
      { sender: "user", text: trimmedQuestion },
    ]);
    setQuestion("");
    setLoading(true);
    setNotice("");

    try {
      const response = await fetch(`${API_BASE}/agent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: trimmedQuestion,
          account_email: userEmail,
        }),
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Unable to answer.");

      setMessages((prev) => [
        ...prev,
        {
          sender: "ai",
          text: data.answer,
          tool: data.tool || null,
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          sender: "ai",
          text: error.message || "Something went wrong.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const uploadPdf = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      setNotice("Please choose a PDF file.");
      return;
    }

    setUploading(true);
    setNotice("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE}/documents/upload`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Upload failed.");

      setNotice(`${file.name} is ready for questions.`);
    } catch (error) {
      setNotice(error.message || "Could not upload the PDF.");
    } finally {
      setUploading(false);
    }
  };

  const saveUser = async () => {
    const trimmed = nextUserEmail.trim().toLowerCase();
    setUserError("");

    if (!trimmed) {
      setUserError("Please enter a Gmail address.");
      return;
    }

    const gmailPattern = /^[A-Z0-9._%+-]+@gmail\.com$/i;
    if (!gmailPattern.test(trimmed)) {
      setUserError("LifeLens currently supports Gmail accounts only.");
      return;
    }

    setSwitchingUser(true);

    const controller = new AbortController();
    switchUserAbortRef.current = controller;

    try {
      const response = await fetch(`${API_BASE}/auth/change-user`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: trimmed }),
        signal: controller.signal,
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Unable to authenticate this Gmail account.");
      }

      setUserEmail(data.email);
      setMessages([]);
      setNotice(`Connected to ${data.email}.`);
      setEditingUser(false);
    } catch (error) {
      if (error.name !== "AbortError") {
        setUserError(error.message || "Unable to change user.");
      }
    } finally {
      if (switchUserAbortRef.current === controller) {
        switchUserAbortRef.current = null;
        setSwitchingUser(false);
      }
    }
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <div className="brand">LifeLens</div>
          <div className="tagline">Your Personal AI Memory</div>
        </div>

        <div className="user-area">
          {editingUser ? (
            <div className="user-editor-wrap">
              <div className="user-editor">
                <input
                  aria-label="Gmail address"
                  type="email"
                  placeholder="name@gmail.com"
                  value={nextUserEmail}
                  onChange={(e) => {
                    setNextUserEmail(e.target.value);
                    setUserError("");
                  }}
                  onKeyDown={(e) => e.key === "Enter" && !switchingUser && saveUser()}
                  disabled={switchingUser}
                />
                <button
                  className="secondary-button compact"
                  onClick={saveUser}
                  disabled={switchingUser}
                >
                  {switchingUser ? "Connecting..." : "Continue"}
                </button>
                <button
                  className="text-button"
                  onClick={() => {
                    if (switchUserAbortRef.current) {
                      switchUserAbortRef.current.abort();
                      switchUserAbortRef.current = null;
                    }
                    setSwitchingUser(false);
                    setEditingUser(false);
                    setUserError("");
                    setNextUserEmail(userEmail);
                  }}
                >
                  Cancel
                </button>
              </div>
              {userError && <div className="user-error">{userError}</div>}
              <div className="user-help">
                Continue opens Google OAuth. The selected Google account must match this Gmail address.
              </div>
            </div>
          ) : (
            <>
              <div className="user-copy">
                <strong>{displayName}</strong>
                <span>{userEmail}</span>
              </div>
              <button
                className="secondary-button"
                onClick={() => {
                  setNextUserEmail(userEmail);
                  setUserError("");
                  setEditingUser(true);
                }}
              >
                Change User
              </button>
            </>
          )}
        </div>
      </header>

      <nav className="tabs" aria-label="LifeLens navigation">
        <button
          className={page === "ask" ? "tab active" : "tab"}
          onClick={() => setPage("ask")}
        >
          Ask
        </button>
        <button
          className={page === "timeline" ? "tab active" : "tab"}
          onClick={() => setPage("timeline")}
        >
          Timeline
        </button>
      </nav>

      <main className="content">
        {page === "ask" ? (
          <section className="ask-page">
            <div className="hero-copy">
              <h1>Ask LifeLens</h1>
              <p>Ask anything about your personal data.</p>
            </div>

            <div className="composer-card">
              <textarea
                rows="2"
                placeholder="Ask me anything..."
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    askQuestion();
                  }
                }}
              />

              <div className="composer-actions">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="application/pdf,.pdf"
                  hidden
                  onChange={uploadPdf}
                />
                <button
                  className="upload-button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                >
                  {uploading ? "Uploading..." : "Upload PDF"}
                </button>
                <button className="ask-button" onClick={askQuestion} disabled={loading}>
                  {loading ? "Thinking..." : "Ask"}
                </button>
              </div>
            </div>

            <p className="helper-text">
              LifeLens automatically chooses the right source for your question.
            </p>
            {notice && <div className="notice">{notice}</div>}

            {(messages.length > 0 || loading) && (
              <div className="conversation">
                {messages.map((message, index) => (
                  <div
                    key={`${message.sender}-${index}`}
                    className={`message-row ${message.sender}`}
                  >
                    <div className="message-label">
                      {message.sender === "user" ? "You" : "LifeLens"}
                      {message.tool && <span className="tool-badge">Used {message.tool}</span>}
                    </div>
                    <div className="message-text">{message.text}</div>
                  </div>
                ))}

                {loading && (
                  <div className="message-row ai">
                    <div className="message-label">LifeLens</div>
                    <div className="message-text muted">Finding the answer...</div>
                  </div>
                )}
              </div>
            )}

            <section className="about-lifelens" aria-labelledby="about-lifelens-title">
              <div className="about-heading">
                <h2 id="about-lifelens-title">What LifeLens does</h2>
                <p>Your personal AI memory assistant.</p>
              </div>

              <div className="feature-grid">
                <div className="feature-card">
                  <div className="feature-icon">✦</div>
                  <div>
                    <h3>Ask anything</h3>
                    <p>LifeLens automatically chooses Gmail or your uploaded documents to find the answer.</p>
                    <div className="example-row">
                      <span>When is my next trip?</span>
                      <span>What was that hotel name?</span>
                    </div>
                  </div>
                </div>

                <div className="feature-card">
                  <div className="feature-icon">✉</div>
                  <div>
                    <h3>Gmail insights</h3>
                    <p>Finds useful information from Gmail such as bookings, receipts, purchases, and confirmations.</p>
                    <div className="example-row">
                      <span>Find my flight confirmation</span>
                      <span>Show my recent purchases</span>
                    </div>
                  </div>
                </div>

                <div className="feature-card">
                  <div className="feature-icon">◷</div>
                  <div>
                    <h3>Build your timeline</h3>
                    <p>Creates a personal timeline from Gmail events such as travel, purchases, and appointments.</p>
                    <div className="timeline-preview" aria-label="Example LifeLens timeline">
                      <div className="timeline-preview-item">
                        <span className="timeline-dot"></span>
                        <div>
                          <strong>Aug 30</strong>
                          <span>Flight to Mumbai</span>
                        </div>
                      </div>
                      <div className="timeline-preview-item">
                        <span className="timeline-dot"></span>
                        <div>
                          <strong>Aug 18</strong>
                          <span>Amazon purchase</span>
                        </div>
                      </div>
                      <div className="timeline-preview-item">
                        <span className="timeline-dot"></span>
                        <div>
                          <strong>Aug 10</strong>
                          <span>Doctor appointment</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="feature-card">
                  <div className="feature-icon">▤</div>
                  <div>
                    <h3>Search documents with RAG</h3>
                    <p>Upload PDFs and ask questions using semantic retrieval over your personal documents.</p>
                    <div className="example-row">
                      <span>Summarize this document</span>
                      <span>Find policy details</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="secure-strip">
                <div className="feature-icon">✓</div>
                <div>
                  <h3>Secure &amp; private</h3>
                  <p>Uses OAuth so LifeLens only accesses the Gmail data you authorize.</p>
                </div>
              </div>
            </section>
          </section>
        ) : (
          <Timeline userEmail={userEmail} />
        )}
      </main>
    </div>
  );
}

export default App;
