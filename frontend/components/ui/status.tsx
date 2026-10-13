import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * A status as text, never a pill (DESIGN.md §4). The word carries the meaning;
 * a small dot marks only what needs attention, so colour stays rare enough to
 * find. Finished or inactive states recede into muted text.
 */
const TONE = {
  neutral: { text: "text-foreground", dot: null },
  attention: { text: "text-foreground", dot: "bg-attention" },
  danger: { text: "text-foreground", dot: "bg-danger" },
  muted: { text: "text-muted-foreground", dot: null },
} as const;

export type StatusTone = keyof typeof TONE;

export function Status({
  tone = "neutral",
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { tone?: StatusTone }) {
  const { text, dot } = TONE[tone];
  return (
    <span className={cn("inline-flex items-center gap-1.5 whitespace-nowrap text-sm", text, className)} {...props}>
      {dot && <span aria-hidden className={cn("size-1.5 shrink-0 rounded-full", dot)} />}
      {children}
    </span>
  );
}
