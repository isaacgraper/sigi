import { describe, expect, it } from "vitest";

import { SECTIONS, sectionFor } from "@/lib/dashboard";

describe("AC-0012-03 the tab named in the URL is the one shown", () => {
  it.each(SECTIONS.map((section) => [section.id, section.title]))("?aba=%s opens %s", (aba, title) => {
    expect(sectionFor(aba).title).toBe(title);
  });

  it.each([null, "", "nao-existe"])("an absent or unknown ?aba=%s opens the first section", (aba) => {
    expect(sectionFor(aba)).toBe(SECTIONS[0]);
  });
});

describe("AC-0012-09 saldo and estoque are never one figure", () => {
  it("every table keeps Saldo apart from any estoque column", () => {
    for (const section of SECTIONS) {
      for (const block of Object.values(section.blocks)) {
        if (block.kind !== "table") continue;
        for (const column of block.columns) {
          const lower = column.toLowerCase();
          expect(lower.includes("saldo") && lower.includes("estoque"), column).toBe(false);
        }
      }
    }
  });
});
