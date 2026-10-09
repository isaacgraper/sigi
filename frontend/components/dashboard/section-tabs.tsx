"use client";

import { useRef } from "react";

import type { Section } from "@/lib/dashboard";
import { cn } from "@/lib/utils";

export const tabId = (section: Section) => `aba-${section.id}`;
export const panelId = (section: Section) => `painel-${section.id}`;

/**
 * The WAI-ARIA tabs pattern (AC-0012-02): one tab stop, arrows move the
 * selection, Home and End jump to the ends. Selection follows focus, because
 * showing a section is cheap and has no side effect.
 */
export function SectionTabs({
  sections,
  selected,
  onSelect,
}: {
  sections: Section[];
  selected: Section;
  onSelect: (section: Section) => void;
}) {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});

  function move(event: React.KeyboardEvent, index: number) {
    const last = sections.length - 1;
    const next =
      event.key === "ArrowRight"
        ? (index + 1) % sections.length
        : event.key === "ArrowLeft"
          ? (index - 1 + sections.length) % sections.length
          : event.key === "Home"
            ? 0
            : event.key === "End"
              ? last
              : null;
    if (next === null) return;
    event.preventDefault();
    onSelect(sections[next]);
    refs.current[sections[next].id]?.focus();
  }

  return (
    <div
      role="tablist"
      aria-label="Seções do painel"
      className="flex gap-1 overflow-x-auto border-b border-border"
    >
      {sections.map((section, index) => {
        const active = section.id === selected.id;
        return (
          <button
            key={section.id}
            ref={(node) => {
              refs.current[section.id] = node;
            }}
            id={tabId(section)}
            type="button"
            role="tab"
            aria-selected={active}
            aria-controls={panelId(section)}
            tabIndex={active ? 0 : -1}
            onClick={() => onSelect(section)}
            onKeyDown={(event) => move(event, index)}
            className={cn(
              "-mb-px shrink-0 border-b-2 px-4 py-2.5 text-sm whitespace-nowrap transition-[color,border-color] duration-150 focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              active
                ? "border-primary font-normal text-primary"
                : "border-transparent font-light text-muted-foreground [@media(hover:hover)_and_(pointer:fine)]:hover:text-foreground",
            )}
          >
            {section.title}
          </button>
        );
      })}
    </div>
  );
}
