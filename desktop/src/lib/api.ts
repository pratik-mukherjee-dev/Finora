import { invoke } from "@tauri-apps/api/core";
import { fetch as tauriFetch } from "@tauri-apps/plugin-http";

/** Thrown for any non-2xx response, carrying the parsed body for inspection. */
export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, message: string, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

// Resolved once the backend port is known; null until then.
let _base: string | null = null;

/** Single call to the Rust side. Returns 0 while the backend is still booting. */
export async function getDjangoPort(): Promise<number> {
  return await invoke<number>("get_django_port");
}

/** The resolved base URL (e.g. http://127.0.0.1:50146), or null if not ready. */
export function apiBase(): string | null {
  return _base;
}

interface WaitOpts {
  intervalMs?: number;
  timeoutMs?: number;
  onAttempt?: (attempt: number) => void;
}

/**
 * Polls get_django_port until it returns a non-zero port, then caches and
 * returns the base URL. A non-zero port means Rust's readiness loop already
 * saw Django accepting TCP connections, i.e. migrations are done and Waitress
 * is serving — so the very next HTTP request should succeed.
 */
export async function waitForBackend(opts: WaitOpts = {}): Promise<string> {
  const intervalMs = opts.intervalMs ?? 400;
  const timeoutMs = opts.timeoutMs ?? 30000;
  const start = Date.now();
  let attempt = 0;

  for (;;) {
    attempt += 1;
    opts.onAttempt?.(attempt);

    let port = 0;
    try {
      port = await getDjangoPort();
    } catch {
      // IPC hiccup or command not registered yet — treat as "not ready".
      port = 0;
    }

    if (port > 0) {
      _base = `http://127.0.0.1:${port}`;
      return _base;
    }

    if (Date.now() - start > timeoutMs) {
      throw new Error(
        `Backend did not become ready within ${Math.round(
          timeoutMs / 1000
        )}s (attempts=${attempt}).`
      );
    }

    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

/** Thin JSON request wrapper over the Tauri HTTP plugin's fetch. */
export async function request<T = unknown>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  if (!_base) {
    throw new Error("API base not resolved — call waitForBackend() first.");
  }

  const res = await tauriFetch(_base + path, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(init.headers ?? {}),
    },
  });

  const text = await res.text();
  let data: unknown = text;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      /* non-JSON response; keep raw text */
    }
  }

  if (!res.ok) {
    const detail =
      data && typeof data === "object" && "detail" in data
        ? String((data as Record<string, unknown>).detail)
        : `${res.status} ${res.statusText}`;
    throw new ApiError(res.status, detail, data);
  }

  return data as T;
}

/** Unauthenticated smoke-test endpoint (plain Django view, no auth/CSRF). */
export async function health(): Promise<{ status: string }> {
  return await request<{ status: string }>("/health/");
}