import { describe, expect, it } from "vitest";

import { GENERIC_FAILURE, readError } from "@/lib/errors";

function json(status: number, body: unknown, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", ...headers },
  });
}

describe("the API error envelope", () => {
  it("keeps the API's message verbatim (C3)", async () => {
    const error = await readError(
      json(401, { error: { code: "INVALID_CREDENTIALS", message: "E-mail ou senha inválidos." } }),
    );
    expect(error.code).toBe("INVALID_CREDENTIALS");
    expect(error.message).toBe("E-mail ou senha inválidos.");
  });

  it("carries fields and Retry-After", async () => {
    const error = await readError(
      json(
        429,
        { error: { code: "RATE_LIMITED", message: "Muitas requisições.", fields: { email: "x" } } },
        { "retry-after": "30" },
      ),
    );
    expect(error.fields).toEqual({ email: "x" });
    expect(error.retryAfter).toBe(30);
  });

  it("AC-0010-42 a 5xx shows the generic message and its correlation id", async () => {
    const error = await readError(
      json(500, { error: { code: "INTERNAL", message: "boom", correlation_id: "abc-123" } }),
    );
    expect(error.message).toBe(GENERIC_FAILURE);
    expect(error.correlationId).toBe("abc-123");
    expect(error.isGeneric).toBe(true);
  });

  it("AC-0010-42 a body that is not the envelope is the generic failure", async () => {
    const error = await readError(new Response("<html>", { status: 502 }));
    expect(error.message).toBe(GENERIC_FAILURE);
  });
});
