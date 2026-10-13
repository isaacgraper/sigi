import * as React from "react";

import { STATUS_TONE_CLASSES } from "@/lib/constants";
import type { StatusTone } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * A status as text, never a pill (DESIGN.md §4). The word carries the meaning;
 * a small dot marks only what needs attention, so colour stays rare enough to
 * find. Finished or inactive states recede into muted text.
 */

export function Status({
  tone = "neutral",
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { tone?: StatusTone }) {
  const { text, dot } = STATUS_TONE_CLASSES[tone];
  return (
    <span className={cn("inline-flex items-center gap-1.5 whitespace-nowrap text-sm", text, className)} {...props}>
      {dot && <span aria-hidden className={cn("size-1.5 shrink-0 rounded-full", dot)} />}
      {children}
    </span>
  );
}
