/**
 * The session, as the browser holds it (SPEC-0010 C1).
 *
 * The access token lives only in this module's memory: never in storage, never
 * in a cookie script can read (AC-0010-17). The refresh token is the API's
 * httpOnly cookie and this code never sees it.
 *
 * The API rotates the refresh token on every use and treats a second use as a
 * replay, revoking the whole family (AC-0001-07). So a refresh must never run
 * twice with the same cookie: one promise per tab (AC-0010-46), and a Web Lock
 * across tabs (AC-0010-47). A tab that waits for the lock refreshes with the
 * cookie the other tab already rotated, which is valid, not a replay.
 */
import { ApiError, readError, unavailable } from "@/lib/errors";

let accessToken: string | null = null;
let inFlight: Promise<string> | null = null;

const LOCK = "sigi-refresh";

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function hasAccessToken(): boolean {
  return accessToken !== null;
}

async function withLock<T>(task: () => Promise<T>): Promise<T> {
  const locks = typeof navigator === "undefined" ? undefined : navigator.locks;
  return locks ? locks.request(LOCK, task) : task();
}

async function send(path: string, init: RequestInit = {}): Promise<Response> {
  try {
    return await fetch(path, { ...init, credentials: "same-origin", cache: "no-store" });
  } catch {
    throw unavailable();
  }
}

/** Exchange the refresh cookie for a new access token, once per tab at a time. */
export function refresh(): Promise<string> {
  if (!inFlight) {
    inFlight = withLock(async () => {
      const response = await send("/api/v1/auth/refresh", { method: "POST" });
      if (!response.ok) {
        accessToken = null;
        throw await readError(response);
      }
      const body = (await response.json()) as { access_token: string };
      accessToken = body.access_token;
      return body.access_token;
    }).finally(() => {
      inFlight = null;
    });
  }
  return inFlight;
}

function withBearer(init: RequestInit, token: string | null): RequestInit {
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return { ...init, headers };
}

async function isExpired(response: Response): Promise<boolean> {
  if (response.status !== 401) return false;
  try {
    const body = (await response.clone().json()) as { error?: { code?: string } };
    return body.error?.code === "TOKEN_EXPIRED";
  } catch {
    return false;
  }
}

/**
 * Call the API as the signed-in usuario. An expired token is refreshed and the
 * call retried once (AC-0010-12); a second failure is the caller's to show.
 */
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  if (accessToken === null) await refresh();
  let response = await send(path, withBearer(init, accessToken));
  if (await isExpired(response)) {
    await refresh();
    response = await send(path, withBearer(init, accessToken));
  }
  return response;
}

/** `apiFetch`, then the parsed body, or the API's error thrown. */
export async function apiJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await apiFetch(path, init);
  if (!response.ok) throw await readError(response);
  return (await response.json()) as T;
}

export async function login(email: string, password: string): Promise<void> {
  const response = await send("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) throw await readError(response);
  accessToken = ((await response.json()) as { access_token: string }).access_token;
}

export async function adopt(response: Response): Promise<void> {
  if (!response.ok) throw await readError(response);
  accessToken = ((await response.json()) as { access_token: string }).access_token;
}

export async function logout(): Promise<void> {
  try {
    await send("/api/v1/auth/logout", { method: "POST" });
  } finally {
    accessToken = null;
  }
}

export { ApiError };
