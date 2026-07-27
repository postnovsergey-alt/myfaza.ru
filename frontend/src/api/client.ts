/**
 * HTTP-клиент. Тонкий: fetch + Authorization + автоматический refresh на 401.
 *
 * Access-токен живёт в памяти (в auth-сторе). Refresh-токен — в
 * localStorage, потому что httpOnly-cookie нельзя использовать в Mini App
 * (документа Telegram и нашего сайта — разные origin). Компромисс задокументирован
 * в DECISIONS.md.
 */

import { useAuth } from "@/store/auth";

const BASE = "/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function refreshAccess(): Promise<string | null> {
  const state = useAuth.getState();
  if (!state.refreshToken) return null;
  const r = await fetch(`${BASE}/auth/refresh`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ refresh_token: state.refreshToken }),
  });
  if (!r.ok) {
    useAuth.getState().logout();
    return null;
  }
  const body = await r.json();
  useAuth.getState().setSession(body);
  return body.access_token as string;
}

async function raw(
  method: string,
  path: string,
  body?: unknown,
  attempt = 0,
): Promise<Response> {
  const state = useAuth.getState();
  const headers: Record<string, string> = { accept: "application/json" };
  if (body !== undefined) headers["content-type"] = "application/json";
  if (state.accessToken) headers.authorization = `Bearer ${state.accessToken}`;

  const r = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (r.status === 401 && attempt === 0 && state.refreshToken) {
    const next = await refreshAccess();
    if (next) return raw(method, path, body, 1);
  }
  return r;
}

async function parse<T>(r: Response): Promise<T> {
  if (r.status === 204) return undefined as T;
  const text = await r.text();
  const data = text ? JSON.parse(text) : undefined;
  if (!r.ok) {
    const err = data?.detail?.error;
    throw new ApiError(
      r.status,
      err?.code ?? "HTTP_ERROR",
      err?.message ?? `HTTP ${r.status}`,
    );
  }
  return data as T;
}

export const api = {
  get: async <T>(path: string) => parse<T>(await raw("GET", path)),
  post: async <T>(path: string, body?: unknown) => parse<T>(await raw("POST", path, body)),
  put:  async <T>(path: string, body?: unknown) => parse<T>(await raw("PUT",  path, body)),
  patch:async <T>(path: string, body?: unknown) => parse<T>(await raw("PATCH",path, body)),
  del:  async <T>(path: string, body?: unknown) => parse<T>(await raw("DELETE", path, body)),
};

// --- Модель ответа /auth/*, повторяет схему бэкенда 8.1 ---
export interface UserOut {
  id: string;
  email: string | null;
  telegram_id: number | null;
  telegram_username: string | null;
  display_name: string | null;
  locale: string;
  timezone: string;
  consent_given_at: string | null;
  consent_version: string | null;
  onboarding_completed: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
  user: UserOut;
}

// --- Циклы, логи, прогноз ---
export interface Cycle {
  id: string;
  start_date: string;
  end_date: string | null;
  cycle_length: number | null;
  period_length: number | null;
  is_predicted: boolean;
  is_anomaly: boolean;
  source: string;
}

export interface DailyLogRow {
  id: string;
  date: string;
  flow: string | null;
  mood: string | null;
  symptoms: string[] | null;
  note: string | null;
}

export interface PredictionOut {
  predicted_start: string;
  predicted_end: string;
  margin_days: number;
  confidence: "low" | "medium" | "high";
  based_on_cycles: number;
  ovulation_date: string;
  fertile_window: { start: string; end: string };
  current_cycle_day: number;
  days_until_period: number;
  is_overdue: boolean;
  overdue_days: number;
}

export interface CalendarDay {
  date: string;
  state: "period_actual" | "period_predicted" | "fertile" | "ovulation" | "normal";
  has_log: boolean;
  is_today: boolean;
  cycle_day: number | null;
}

export interface CalendarOut {
  month: string;
  days: CalendarDay[];
}
