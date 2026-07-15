import {invoke} from "@tauri-apps/api/core";
import {fetch as tauriFetch} from "@tauri-apps/plugin-http";

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
let _access: string | null = null;
let _refresh: string | null = null;

export function setTokens(t: { access: string; refresh?: string } | null) {
    _access = t?.access ?? null;
    if (t?.refresh) _refresh = t.refresh;
}

export function clearTokens() {
    _access = null;
    _refresh = null;
}

export function getAccess() {
    return _access;
}

export function getRefresh() {
    return _refresh;
}

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

    for (; ;) {
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
async function rawRequest<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
    if (!_base) {
        throw new Error("API base not resolved — call waitForBackend() first.");
    }

    const res = await tauriFetch(_base + path, {
        ...init,
        headers: {
            Accept: "application/json",
            ...(init.body ? {"Content-Type": "application/json"} : {}),
            ...(init.headers ?? {}),
        },
    });

    const text = await res.text();
    let data: unknown = text;
    if (text) {
        try {
            data = JSON.parse(text);
        } catch { /* keep raw text */
        }
    }

    if (!res.ok) {
        let detail: string;
        if (data && typeof data === "object") {
            const obj = data as Record<string, unknown>;
            if ("detail" in obj) {
                detail = String(obj.detail);
            } else {
                // DRF field / non-field validation errors: flatten to a readable string.
                detail = Object.entries(obj)
                    .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : String(v)}`)
                    .join(" | ") || `${res.status} ${res.statusText}`;
            }
        } else {
            detail = `${res.status} ${res.statusText}`;
        }
        throw new ApiError(res.status, detail, data);
    }


    return data as T;
}

async function refreshAccess(): Promise<boolean> {
    if (!_refresh) return false;
    try {
        const r = await rawRequest<{ access: string; refresh?: string }>(
            "/api/accounts/auth/refresh/",
            {method: "POST", body: JSON.stringify({refresh: _refresh})}
        );
        setTokens(r);
        return true;
    } catch {
        clearTokens();
        return false;
    }
}

/** Auth-aware JSON request: injects Bearer token, retries once on 401 via refresh. */
export async function request<T = unknown>(
    path: string,
    init: RequestInit = {},
    _retried = false
): Promise<T> {
    const headers: Record<string, string> = {
        ...((init.headers as Record<string, string>) ?? {}),
    };
    if (_access) headers["Authorization"] = `Bearer ${_access}`;
    if (init.body && !("Content-Type" in headers)) {
        headers["Content-Type"] = "application/json";
    }

    try {
        return await rawRequest<T>(path, {...init, headers});
    } catch (e) {
        if (e instanceof ApiError && e.status === 401 && !_retried && (await refreshAccess())) {
            return request<T>(path, init, true);
        }
        throw e;
    }
}

/** Unauthenticated smoke-test endpoint (plain Django view, no auth/CSRF). */
export async function health(): Promise<{ status: string }> {
    return await request<{ status: string }>("/health/");
}

/** Public: whether the single local account has been created yet. */
export async function authState(): Promise<{ initialized: boolean }> {
    return await rawRequest<{ initialized: boolean }>("/api/accounts/auth/state/");
}

/** First-run only: create the local account, receive + store tokens. */
export async function register(username: string, password: string) {
    const r = await rawRequest<{ access: string; refresh: string }>(
        "/api/accounts/auth/register/",
        {method: "POST", body: JSON.stringify({username, password})}
    );
    setTokens(r);
    return r;
}

export async function login(username: string, password: string) {
    const r = await rawRequest<{ access: string; refresh: string }>(
        "/api/accounts/auth/login/",
        {method: "POST", body: JSON.stringify({username, password})}
    );
    setTokens(r);
    return r;
}

export async function logout() {
    if (_refresh) {
        await request("/api/accounts/auth/logout/", {
            method: "POST",
            body: JSON.stringify({refresh: _refresh}),
        }).catch(() => {
        });
    }
    clearTokens();
}

export type Suggestion = { id: number; name: string; [k: string]: unknown };

export async function suggest(
    type: "ITEM" | "PARTY",
    q: string,
    limit = 10,
    signal?: AbortSignal
): Promise<Suggestion[]> {
    const p = new URLSearchParams({type, q, limit: String(limit)});
    return await request<Suggestion[]>(`/api/search/suggest/?${p.toString()}`, {signal});
}

export async function recordUsage(type: "ITEM" | "PARTY", id: number): Promise<void> {
    await request("/api/search/record/", {
        method: "POST",
        body: JSON.stringify({type, id}),
    }).catch(() => {
    }); // ranking is best-effort; never block UX
}