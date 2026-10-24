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

export interface DonorListItem {
  donor_id: number;
  account_number: string;
  first_name: string;
  last_name: string;
  email: string | null;
  city: string | null;
  state: string | null;
  has_address: boolean;
  gift_count: number;
  direct_gift_count: number;
  total_given: string | null;
  direct_total: string | null;
  last_gift_date: string | null;
  raise_ride_only: boolean;
  last_note_sent_at: string | null;
  pending_note_id: number | null;
  pending_note_status: string | null;
}

export interface DonorListResponse {
  items: DonorListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface SayThankYouResponse {
  note_id: number;
  status: string;
  batch_week: string;
  gift_id: number;
  gift_date: string;
  amount: string;
  warnings: string[];
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
  }
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
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

export const api = {
  healthReady: (env?: EnvReader) => request<HealthReady>(env, "/health/ready"),
  listDocuments: (env?: EnvReader, limit = 50) =>
    request<Document[]>(env, `/documents?limit=${limit}`),
  listDonors: (env?: EnvReader, q = "", limit = 100, offset = 0) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (q) params.set("q", q);
    return request<DonorListResponse>(env, `/donors?${params}`);
  },
  sayThankYou: (env: EnvReader | undefined, donorId: number) =>
    request<SayThankYouResponse>(env, `/donors/${donorId}/thank-you`, { method: "POST" }),
  agentChat: (env: EnvReader | undefined, prompt: string) =>
    request<AgentResponse>(env, "/agent/chat", {
      method: "POST",
      body: JSON.stringify({ prompt }),
    }),
};
