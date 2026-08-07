const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
import { notifyUnauthorized } from "../auth/authEvents";

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

function csrfToken(): string | undefined {
  return document.cookie.split("; ").find((item) => /^(?:__Host-)?mra_csrf=/.test(item))?.split("=").slice(1).join("=");
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  const csrf = csrfToken();
  if (csrf && !["GET", "HEAD"].includes(init.method ?? "GET")) headers.set("X-CSRF-Token", decodeURIComponent(csrf));
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers, credentials: "include" });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    if (response.status === 401) notifyUnauthorized();
    throw new ApiError(response.status, body?.detail ?? `Errore API (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
