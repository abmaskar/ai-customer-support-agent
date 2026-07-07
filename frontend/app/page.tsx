"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ChatResponse,
  MetricsResponse,
  getHealth,
  getMetrics,
  listDocuments,
  login,
  register,
  sendChat,
  sendFeedback,
  uploadDocument,
} from "@/lib/api";

type Tab = "chat" | "admin" | "metrics" | "auth";

type ChatItem = {
  role: "user" | "assistant";
  content: string;
  messageId?: string;
  citations?: ChatResponse["citations"];
  backendSteps?: string[];
  latencyMs?: number;
  grounded?: boolean;
};

export default function HomePage() {
  const [tab, setTab] = useState<Tab>("chat");
  const [token, setToken] = useState<string | null>(null);
  const [email, setEmail] = useState("admin@support.local");
  const [password, setPassword] = useState("admin123");
  const [isAdmin, setIsAdmin] = useState(true);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [chat, setChat] = useState<ChatItem[]>([]);
  const [steps, setSteps] = useState<string[]>([]);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [docs, setDocs] = useState<any[]>([]);
  const [health, setHealth] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth(null));
    const saved = localStorage.getItem("support_token");
    if (saved) setToken(saved);
  }, []);

  useEffect(() => {
    if (tab === "metrics") {
      getMetrics().then(setMetrics).catch((e) => setError(String(e)));
    }
    if (tab === "admin" && token) {
      listDocuments(token).then(setDocs).catch((e) => setError(String(e)));
    }
  }, [tab, token]);

  const canAdmin = useMemo(() => Boolean(token), [token]);

  async function handleLogin() {
    setError(null);
    setLoading(true);
    try {
      const res = await login(email, password);
      setToken(res.access_token);
      localStorage.setItem("support_token", res.access_token);
      setIsAdmin(res.is_admin);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleRegister() {
    setError(null);
    setLoading(true);
    try {
      const res = await register(email, password, isAdmin);
      setToken(res.access_token);
      localStorage.setItem("support_token", res.access_token);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleSend() {
    if (!message.trim()) return;
    setError(null);
    setLoading(true);
    const userText = message;
    setMessage("");
    setChat((prev) => [...prev, { role: "user", content: userText }]);
    try {
      const res = await sendChat(userText, sessionId, token);
      setSessionId(res.session_id);
      setSteps(res.backend_steps);
      setChat((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.answer,
          messageId: res.message_id,
          citations: res.citations,
          backendSteps: res.backend_steps,
          latencyMs: res.latency_ms,
          grounded: res.grounded,
        },
      ]);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload(file?: File | null) {
    if (!file || !token) return;
    setLoading(true);
    setError(null);
    try {
      await uploadDocument(file, token);
      const updated = await listDocuments(token);
      setDocs(updated);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="container">
      <div className="header">
        <div>
          <h1>AI Customer Support Agent</h1>
          <p className="muted">Full-stack demo: Auth + PostgreSQL + Qdrant + LLM + Metrics</p>
        </div>
        <div>
          <span className="badge">{health?.provider || "backend"}</span>{" "}
          <span className="badge">{health?.qdrant || "qdrant"}</span>
        </div>
      </div>

      <div className="tabs">
        <button className={`tab ${tab === "chat" ? "active" : ""}`} onClick={() => setTab("chat")}>Chat (RAG)</button>
        <button className={`tab ${tab === "admin" ? "active" : ""}`} onClick={() => setTab("admin")}>Admin Upload</button>
        <button className={`tab ${tab === "metrics" ? "active" : ""}`} onClick={() => setTab("metrics")}>Metrics Dashboard</button>
        <button className={`tab ${tab === "auth" ? "active" : ""}`} onClick={() => setTab("auth")}>Auth</button>
      </div>

      {error && <div className="card bad" style={{ marginBottom: 12 }}>{error}</div>}

      {tab === "chat" && (
        <div className="grid">
          <section className="card">
            <h3>Customer Chat UI</h3>
            <p className="muted">Ask support questions. Backend retrieves docs from Qdrant and answers with citations.</p>
            <div className="chat-box">
              {chat.map((m, i) => (
                <div key={i} className={`msg ${m.role}`}>
                  <div>{m.content}</div>
                  {m.citations && m.citations.length > 0 && (
                    <div className="citations">
                      Sources: {m.citations.map((c) => c.source).join(", ")}
                    </div>
                  )}
                  {m.role === "assistant" && m.messageId && (
                    <div className="feedback">
                      <button className="button secondary" onClick={() => sendFeedback(m.messageId!, "up")}>👍</button>
                      <button className="button secondary" onClick={() => sendFeedback(m.messageId!, "down")}>👎</button>
                      <span className="muted">{m.latencyMs}ms · {m.grounded ? "grounded" : "fallback"}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
            <div className="row" style={{ marginTop: 10 }}>
              <input className="input" value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Ask about refund policy, product, API..." />
              <button className="button" disabled={loading} onClick={handleSend}>Send</button>
            </div>
          </section>

          <section className="card">
            <h3>What Backend Did</h3>
            <p className="muted">Each chat request follows this pipeline:</p>
            <ul className="steps">
              {(steps.length ? steps : [
                "1) Save user message in PostgreSQL",
                "2) Embed query + search Qdrant",
                "3) Retrieve top chunks",
                "4) Call LLM with grounded context",
                "5) Save answer + citations + metrics",
              ]).map((s) => <li key={s}>{s}</li>)}
            </ul>
          </section>
        </div>
      )}

      {tab === "admin" && (
        <div className="grid">
          <section className="card">
            <h3>Admin Document Upload</h3>
            <p className="muted">Requires JWT admin token. Upload PDF/TXT → chunk → embed → store in Qdrant.</p>
            {!canAdmin && <p className="warn">Login as admin first (default: admin@support.local / admin123)</p>}
            <input className="file" type="file" accept=".pdf,.txt" disabled={!canAdmin || loading}
              onChange={(e) => handleUpload(e.target.files?.[0])} />
          </section>
          <section className="card">
            <h3>Uploaded Documents (PostgreSQL)</h3>
            <table className="table">
              <thead><tr><th>Filename</th><th>Chunks</th><th>Created</th></tr></thead>
              <tbody>
                {docs.map((d) => (
                  <tr key={d.id}><td>{d.filename}</td><td>{d.chunk_count}</td><td>{new Date(d.created_at).toLocaleString()}</td></tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>
      )}

      {tab === "metrics" && metrics && (
        <section className="card">
          <h3>Production Metrics Dashboard</h3>
          <p className="muted">Eval + observability signals used for release gate decisions.</p>
          <div className="metric-grid" style={{ marginTop: 12 }}>
            <div className="metric"><div className="muted">Groundedness</div><div className="value">{(metrics.groundedness_rate * 100).toFixed(1)}%</div></div>
            <div className="metric"><div className="muted">Fallback Rate</div><div className="value">{(metrics.fallback_rate * 100).toFixed(1)}%</div></div>
            <div className="metric"><div className="muted">p95 Latency</div><div className="value">{metrics.p95_latency_ms} ms</div></div>
            <div className="metric"><div className="muted">Cost</div><div className="value">${metrics.estimated_cost_usd}</div></div>
            <div className="metric"><div className="muted">Feedback 👍/👎</div><div className="value">{metrics.feedback_up}/{metrics.feedback_down}</div></div>
            <div className="metric"><div className="muted">Release Gate</div><div className={`value ${metrics.release_gate.status === "GO" ? "ok" : "bad"}`}>{metrics.release_gate.status}</div></div>
          </div>
        </section>
      )}

      {tab === "auth" && (
        <section className="card" style={{ maxWidth: 480 }}>
          <h3>Authentication (JWT)</h3>
          <p className="muted">Admin upload requires login. Seeded admin: admin@support.local / admin123</p>
          <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email" />
          <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="password" />
          <label className="muted"><input type="checkbox" checked={isAdmin} onChange={(e) => setIsAdmin(e.target.checked)} /> Register as admin</label>
          <div className="row" style={{ marginTop: 10 }}>
            <button className="button" disabled={loading} onClick={handleLogin}>Login</button>
            <button className="button secondary" disabled={loading} onClick={handleRegister}>Register</button>
            <button className="button secondary" onClick={() => { setToken(null); localStorage.removeItem("support_token"); }}>Logout</button>
          </div>
          {token && <p className="ok" style={{ marginTop: 10 }}>Token active</p>}
        </section>
      )}
    </main>
  );
}
