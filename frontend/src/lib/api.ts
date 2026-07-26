import { useAuthStore } from "@/store/authStore";
import type {
  ApiKeyCreate,
  ApiKeyCreated,
  ApiKeyRead,
  ChainVerification,
  ChatMessage,
  ChatSession,
  Dispute,
  DisputeCreate,
  DisputeHistoryEntry,
  DisputeVerdict,
  LayeredReport,
  Reputation,
  StreamEvent,
  TelegramLinkStart,
  TelegramLinkStatus,
  TokenPair,
  User,
  WalletWatchCreate,
  WalletWatchRead,
} from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

// Access tokens are short-lived (60 min). Concurrent requests that all hit a
// 401 at once (e.g. the sidebar's session list and the chat view's message
// history loading together) must share a single refresh call rather than
// each firing their own - otherwise the second refresh invalidates/races the
// first and both retries can still fail.
let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const refreshToken = useAuthStore.getState().refreshToken;
      if (!refreshToken) return null;
      try {
        const response = await fetch(`${API_URL}/api/v1/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!response.ok) return null;
        const tokens = (await response.json()) as TokenPair;
        useAuthStore.setState({
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
        });
        return tokens.access_token;
      } catch {
        return null;
      }
    })().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

async function request<T>(path: string, options: RequestInit = {}, isRetry = false): Promise<T> {
  const token = useAuthStore.getState().accessToken;
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (response.status === 401 && !isRetry) {
    const newToken = await refreshAccessToken();
    if (newToken) return request<T>(path, options, true);
    useAuthStore.getState().clearSession();
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(body.detail ?? "Request failed", response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const authApi = {
  register: (email: string, password: string, fullName?: string) =>
    request<User>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name: fullName }),
    }),
  login: (email: string, password: string) =>
    request<TokenPair>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<User>("/api/v1/auth/me"),
};

export const chatApi = {
  listSessions: () => request<ChatSession[]>("/api/v1/chat/sessions"),
  createSession: (title?: string) =>
    request<ChatSession>("/api/v1/chat/sessions", {
      method: "POST",
      body: JSON.stringify({ title }),
    }),
  getMessages: (sessionId: string) =>
    request<ChatMessage[]>(`/api/v1/chat/sessions/${sessionId}/messages`),
};

export const reportsApi = {
  getBySession: (sessionId: string) =>
    request<LayeredReport[]>(`/api/v1/reports/by-session/${sessionId}`),
};

export const courtApi = {
  fileDispute: (payload: DisputeCreate) =>
    request<Dispute>("/api/v1/disputes", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listDisputes: () => request<Dispute[]>("/api/v1/disputes"),
  getDispute: (disputeId: string) => request<Dispute>(`/api/v1/disputes/${disputeId}`),
  getVerdict: (disputeId: string) =>
    request<DisputeVerdict>(`/api/v1/disputes/${disputeId}/verdict`),
  // Works with or without auth - reputation is publicly checkable either
  // way. Uses the authenticated request() helper (not a raw fetch) so that,
  // when the caller IS logged in, the backend can identify them and push a
  // Telegram alert on a Flagged result - anonymous callers are unaffected.
  getReputation: (walletId: string) =>
    request<Reputation>(`/api/v1/reputation/${encodeURIComponent(walletId)}`),
  getReputationHistory: (walletId: string) =>
    fetch(`${API_URL}/api/v1/reputation/${encodeURIComponent(walletId)}/history`).then(
      (r) => r.json() as Promise<DisputeHistoryEntry[]>,
    ),
  // No auth - a quick "is this tx real" preview before submitting evidence.
  verifyTx: (chain: string, txHash: string, claimedAmount?: number | null) => {
    const params = new URLSearchParams({ chain, tx_hash: txHash });
    if (claimedAmount != null) params.set("claimed_amount", String(claimedAmount));
    return fetch(`${API_URL}/api/v1/disputes/verify-tx?${params.toString()}`).then(
      (r) => r.json() as Promise<ChainVerification>,
    );
  },
};

export const apiKeysApi = {
  create: (payload: ApiKeyCreate) =>
    request<ApiKeyCreated>("/api/v1/api-keys", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  list: () => request<ApiKeyRead[]>("/api/v1/api-keys"),
  revoke: (keyId: string) => request<void>(`/api/v1/api-keys/${keyId}`, { method: "DELETE" }),
};

export const telegramApi = {
  startLink: () => request<TelegramLinkStart>("/api/v1/telegram/link/start", { method: "POST" }),
  linkStatus: () => request<TelegramLinkStatus>("/api/v1/telegram/link/status"),
  unlink: () => request<void>("/api/v1/telegram/link", { method: "DELETE" }),
  createWatch: (payload: WalletWatchCreate) =>
    request<WalletWatchRead>("/api/v1/telegram/watches", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listWatches: () => request<WalletWatchRead[]>("/api/v1/telegram/watches"),
  deleteWatch: (watchId: string) =>
    request<void>(`/api/v1/telegram/watches/${watchId}`, { method: "DELETE" }),
};

/**
 * Parses a `text/event-stream` response body into individual StreamEvents.
 * Shared by streamQuery (research pipeline) and streamArbitration (Court
 * pipeline) - both drive their live "agent trace" UI off this same framing.
 */
async function consumeSSE(response: Response, onEvent: (event: StreamEvent) => void): Promise<void> {
  if (!response.body) throw new ApiError("Response had no body", response.status);

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";

    for (const rawEvent of events) {
      const line = rawEvent.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      onEvent(JSON.parse(line.slice("data: ".length)) as StreamEvent);
    }
  }
}

/** POSTs with auth (retrying once on 401 via token refresh) and streams the
 * SSE response into onEvent. */
async function streamPost(
  path: string,
  body: unknown,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  async function post(): Promise<Response> {
    const token = useAuthStore.getState().accessToken;
    return fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
      signal,
    });
  }

  let response = await post();
  if (response.status === 401) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      response = await post();
    } else {
      useAuthStore.getState().clearSession();
    }
  }

  if (!response.ok) {
    throw new ApiError("Failed to start stream", response.status);
  }
  await consumeSSE(response, onEvent);
}

/**
 * Streams the courtroom pipeline's SSE events. Can't use native EventSource
 * here since it needs a POST body + Authorization header, so we parse the
 * `text/event-stream` framing manually off a fetch() ReadableStream.
 */
export function streamQuery(
  query: string,
  sessionId: string | null,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  return streamPost("/api/v1/chat/query", { query, session_id: sessionId }, onEvent, signal);
}

/** Streams TruthOS Court's arbitration pipeline for an already-filed dispute. */
export function streamArbitration(
  disputeId: string,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  return streamPost(`/api/v1/disputes/${disputeId}/arbitrate`, {}, onEvent, signal);
}

export { ApiError };
