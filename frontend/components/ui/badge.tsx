import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/lib/utils";

// Status never relies on colour alone: the badge text carries it (DESIGN.md §4).
const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-normal",
  {
    variants: {
      tone: {
        success: "border-success/30 bg-success/10 text-success",
        attention: "border-attention/30 bg-attention/10 text-attention",
        neutral: "border-neutral/30 bg-neutral/10 text-neutral",
        danger: "border-danger/30 bg-danger/10 text-danger",
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
