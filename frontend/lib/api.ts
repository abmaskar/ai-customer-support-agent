const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8101";

export type TokenResponse = {
  access_token: string;
  user_id: string;
  email: string;
  is_admin: boolean;
};

export type ChatResponse = {
  session_id: string;
  message_id: string;
  answer: string;
  citations: { source: string; preview: string; score?: number }[];
  latency_ms: number;
  grounded: boolean;
  backend_steps: string[];
};

export type MetricsResponse = {
  total_messages: number;
  groundedness_rate: number;
  fallback_rate: number;
  feedback_up: number;
  feedback_down: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  estimated_cost_usd: number;
  documents_count: number;
  sessions_count: number;
  release_gate: {
    status: string;
    checks: Record<string, boolean>;
    targets: Record<string, number>;
  };
};

function authHeaders(token?: string | null): HeadersInit {
  const headers: HeadersInit = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function register(email: string, password: string, isAdmin = false): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ email, password, is_admin: isAdmin }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function sendChat(message: string, sessionId: string | null, token?: string | null): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function sendFeedback(messageId: string, vote: "up" | "down"): Promise<void> {
  const res = await fetch(`${API_BASE}/api/chat/feedback`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ message_id: messageId, vote }),
  });
  if (!res.ok) throw new Error(await res.text());
}

export async function uploadDocument(file: File, token: string) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/admin/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function listDocuments(token: string) {
  const res = await fetch(`${API_BASE}/api/admin/documents`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getMetrics(): Promise<MetricsResponse> {
  const res = await fetch(`${API_BASE}/api/metrics`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
