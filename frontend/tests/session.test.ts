import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const expired = () => json(401, { error: { code: "TOKEN_EXPIRED", message: "Sua sessão expirou." } });

async function freshSession() {
  vi.resetModules();
  return import("@/lib/session");
}

describe("the session", () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("AC-0010-12 renews an expired token once and retries the call once", async () => {
    const session = await freshSession();
    session.setAccessToken("old");
    fetchMock
      .mockResolvedValueOnce(expired())
      .mockResolvedValueOnce(json(200, { access_token: "new" }))
      .mockResolvedValueOnce(json(200, { ok: true }));

    const response = await session.apiFetch("/api/v1/auth/me");

    expect(response.status).toBe(200);
    const calls = fetchMock.mock.calls.map(([url]) => String(url));
    expect(calls).toEqual(["/api/v1/auth/me", "/api/v1/auth/refresh", "/api/v1/auth/me"]);
    const retried = new Headers(fetchMock.mock.calls[2][1]?.headers);
    expect(retried.get("Authorization")).toBe("Bearer new");
  });

  it("AC-0010-12 a second expiry is not retried again", async () => {
    const session = await freshSession();
    session.setAccessToken("old");
    fetchMock
      .mockResolvedValueOnce(expired())
      .mockResolvedValueOnce(json(200, { access_token: "new" }))
      .mockResolvedValueOnce(expired());

    const response = await session.apiFetch("/api/v1/auth/me");

    expect(response.status).toBe(401);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("AC-0010-46 concurrent expired requests share one refresh", async () => {
    const session = await freshSession();
    session.setAccessToken("old");
    let release: (value: Response) => void = () => {};
    const pendingRefresh = new Promise<Response>((resolve) => {
      release = resolve;
    });
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/refresh")) return pendingRefresh;
      const auth = new Headers(init?.headers).get("Authorization");
      return auth === "Bearer new" ? json(200, { ok: true }) : expired();
    });

    const both = Promise.all([
      session.apiFetch("/api/v1/usuarios"),
      session.apiFetch("/api/v1/auth/me"),
    ]);
    await vi.waitFor(() =>
      expect(fetchMock.mock.calls.filter(([u]) => String(u).endsWith("/refresh"))).toHaveLength(1),
    );
    release(json(200, { access_token: "new" }));
    const [first, second] = await both;

    expect(first.status).toBe(200);
    expect(second.status).toBe(200);
    expect(fetchMock.mock.calls.filter(([u]) => String(u).endsWith("/refresh"))).toHaveLength(1);
  });

  it("AC-0010-17 the access token is never written to browser storage", async () => {
    const session = await freshSession();
    fetchMock.mockResolvedValueOnce(json(200, { access_token: "secret-token" }));

    await session.login("ana@sc.gov.br", "SenhaCorreta-12345");

    const stored = [
      ...Object.values({ ...localStorage }),
      ...Object.values({ ...sessionStorage }),
      document.cookie,
    ].join("|");
    expect(session.hasAccessToken()).toBe(true);
    expect(stored).not.toContain("secret-token");
  });

  it("a refused refresh forgets the token and raises the API's error", async () => {
    const session = await freshSession();
    session.setAccessToken("old");
    fetchMock
      .mockResolvedValueOnce(expired())
      .mockResolvedValueOnce(
        json(401, { error: { code: "INVALID_REFRESH", message: "Sua sessão não é mais válida." } }),
      );

    await expect(session.apiFetch("/api/v1/auth/me")).rejects.toMatchObject({
      code: "INVALID_REFRESH",
    });
    expect(session.hasAccessToken()).toBe(false);
  });
});
