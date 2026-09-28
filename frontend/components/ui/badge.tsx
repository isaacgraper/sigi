import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/lib/utils";

// Status never relies on colour alone: the badge text carries it (SPEC-0010 §9).
const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium",
  {
    variants: {
      tone: {
        success: "border-accent/30 bg-accent/15 text-accent",
        attention: "border-amber-500/30 bg-amber-500/15 text-amber-800",
        neutral: "border-slate-400/40 bg-slate-500/10 text-slate-700",
        danger: "border-destructive/30 bg-destructive/15 text-destructive",
        muted: "border-border bg-muted text-muted-foreground",
      },
    },
    defaultVariants: { tone: "muted" },
  },
);

export function Badge({
  className,
  tone,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}
