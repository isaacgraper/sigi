import { describe, expect, it } from "vitest";

import { HOME, safeReturnPath } from "@/lib/return-path";

describe("AC-0010-16 the return address cannot leave SIGI", () => {
  it.each([
    ["/membros?page=2", "/membros?page=2"],
    ["/dashboard", "/dashboard"],
  ])("keeps the same-origin path %s", (raw, expected) => {
    expect(safeReturnPath(raw)).toBe(expected);
  });

  it.each([
    null,
    "",
    "https://evil.example/",
    "//evil.example/membros",
    "/\\evil.example",
    "javascript:alert(1)",
    "membros",
    "/login",
  ])("sends %s to the dashboard", (raw) => {
    expect(safeReturnPath(raw)).toBe(HOME);
  });
});
