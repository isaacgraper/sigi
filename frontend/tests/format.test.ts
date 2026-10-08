import { describe, expect, it } from "vitest";

import { formatDate } from "@/lib/format";

describe("dates", () => {
  it("formats dd/MM/yyyy", () => {
    expect(formatDate("2026-09-28T15:00:00Z")).toBe("28/09/2026");
  });

  it("uses America/Sao_Paulo, not UTC", () => {
    // 02:00 UTC on the 1st is still the 30th in São Paulo (UTC−3).
    expect(formatDate("2026-10-01T02:00:00Z")).toBe("30/09/2026");
  });
});
