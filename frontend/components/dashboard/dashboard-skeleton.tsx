import { Skeleton } from "@/components/skeleton";

/**
 * The dashboard's shape on first paint, while the route's code arrives
 * (AC-0012-11): the header, the four tabs, the filters and the blocks of a
 * section, so nothing jumps when the page takes over.
 */
export function DashboardSkeleton() {
  return (
    <div role="status" data-testid="page-skeleton" className="space-y-6">
      <span className="sr-only">Carregando...</span>
      <div aria-hidden className="space-y-6">
        <div className="space-y-2">
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-4 w-64 max-w-full" />
        </div>
        <div className="flex gap-6 border-b pb-3">
          {Array.from({ length: 4 }, (_, index) => (
            <Skeleton key={index} className="h-4 w-28" />
          ))}
        </div>
        <Skeleton className="h-4 w-80 max-w-full" />
        <div className="grid gap-4 rounded-lg border bg-card p-4 sm:grid-cols-2 lg:grid-cols-5">
          {Array.from({ length: 5 }, (_, index) => (
            <div key={index} className="space-y-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-10 w-full" />
            </div>
          ))}
        </div>
        <div className="grid gap-6 xl:grid-cols-2">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
        <Skeleton className="h-72 w-full" />
      </div>
    </div>
  );
}
