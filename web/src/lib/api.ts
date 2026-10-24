/**
 * Thin client for the FastAPI backend.
 *
 * - In the browser, `PUBLIC_API_BASE_URL` is used.
 * - During SSR (routeLoader$, server$), pass `requestEvent.env` so the
 *   server-only `API_BASE_URL` (e.g. http://api:8000/api/v1 in compose) wins.
 */

export interface EnvReader {
  get(key: string): string | undefined;
}

export interface HealthReady {
  status: "ok" | "degraded";
  database: boolean;
  ollama: boolean;
}

export interface Document {
  id: string;
  title: string;
  content: string;
  source_path: string | null;
  created_at: string;
  updated_at: string;
}

export interface AgentToolCall {
  step: number;
  name: string;
  arguments: Record<string, unknown>;
  result: string;
  error: boolean;
}

export interface AgentResponse {
  model: string;
  content: string;
  steps: number;
  tool_calls: AgentToolCall[];
}

const DEFAULT_BASE = "http://localhost:8000/api/v1";

export function apiBase(env?: EnvReader): string {
  const serverSide = env?.get("API_BASE_URL");
  if (serverSide) return serverSide.replace(/\/$/, "");
  const pub = env?.get("PUBLIC_API_BASE_URL") ?? import.meta.env.PUBLIC_API_BASE_URL;
  return (pub || DEFAULT_BASE).replace(/\/$/, "");
}

async function request<T>(env: EnvReader | undefined, path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${apiBase(env)}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`API ${res.status} ${res.statusText} on ${path}`);
  }
  return (await res.json()) as T;
}

export const api = {
  healthReady: (env?: EnvReader) => request<HealthReady>(env, "/health/ready"),
  listDocuments: (env?: EnvReader, limit = 50) =>
    request<Document[]>(env, `/documents?limit=${limit}`),
  agentChat: (env: EnvReader | undefined, prompt: string) =>
    request<AgentResponse>(env, "/agent/chat", {
      method: "POST",
      body: JSON.stringify({ prompt }),
    }),
};
