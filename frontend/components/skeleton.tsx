import { cn } from "@/lib/utils";

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn("animate-pulse rounded-md bg-muted", className)} />;
}

/**
 * The shape of a page while its data is on the way (AC-0011-18): a title bar
 * and a table's rows, never a blank page or a lone spinner. Announced once,
 * in words, for assistive technology.
 */
export function PageSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div role="status" data-testid="page-skeleton" className="space-y-6">
      <span className="sr-only">Carregando...</span>
      <div className="space-y-2">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-72 max-w-full" />
      </div>
      <TableSkeleton rows={rows} />
    </div>
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div aria-hidden className="overflow-hidden rounded-lg border bg-card">
      <div className="border-b bg-muted/60 px-4 py-3">
        <Skeleton className="h-4 w-40 bg-border" />
      </div>
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="flex items-center gap-4 border-b px-4 py-3 last:border-b-0">
          <Skeleton className="h-4 w-1/4" />
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-4 w-16" />
        </div>
      ))}
    </div>
  );
}
