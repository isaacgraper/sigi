import * as React from "react";

import { cn } from "@/lib/utils";

// Scrolls sideways inside its own border, so a wide table never widens the page
// (SPEC-0010 AC-0010-43). `relative` matters: without it an absolutely
// positioned cell child, such as an sr-only header, escapes the scroll frame
// and widens the document.
export function Table({ className, ...props }: React.HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="relative w-full overflow-auto rounded-lg border border-border bg-card shadow-sm">
      <table className={cn("w-full caption-bottom text-sm", className)} {...props} />
    </div>
  );
}

export function TableHeader(props: React.HTMLAttributes<HTMLTableSectionElement>) {
  return <thead className="bg-muted/50 [&_tr]:border-b" {...props} />;
}

export function TableBody(props: React.HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className="[&_tr:last-child]:border-0" {...props} />;
}

export function TableRow({ className, ...props }: React.HTMLAttributes<HTMLTableRowElement>) {
  // Gated to a real pointer: a tap on a touch screen would leave the tint stuck.
  return <tr className={cn("border-b [@media(hover:hover)_and_(pointer:fine)]:hover:bg-muted/40", className)} {...props} />;
}

export function TableHead({ className, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn("h-10 px-3 text-left align-middle font-normal text-muted-foreground", className)}
      {...props}
    />
  );
}

export function TableCell({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={cn("px-3 py-2.5 align-middle", className)} {...props} />;
}
