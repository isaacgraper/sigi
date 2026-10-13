import { Skeleton, TableSkeleton } from "@/components/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

/** The rows of an alert while it loads. */
export function AlertSkeletonRows() {
  return (
    <>
      {[0, 1, 2].map((index) => (
        <div key={index} className="flex justify-between gap-4">
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-4 w-20" />
        </div>
      ))}
    </>
  );
}

function Header() {
  return (
    <div className="space-y-2">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-4 w-72 max-w-full" />
    </div>
  );
}

function CardSkeleton({ children }: { children: React.ReactNode }) {
  return (
    <Card aria-hidden>
      <CardHeader className="pb-3">
        <Skeleton className="h-5 w-40" />
      </CardHeader>
      <CardContent className="space-y-3">{children}</CardContent>
    </Card>
  );
}

/** /atas in its own shape: header, the two alerts, filters and the table (AC-0013-06). */
export function AtasSkeleton() {
  return (
    <div role="status" data-testid="page-skeleton" className="space-y-6">
      <span className="sr-only">Carregando...</span>
      <Header />
      <div className="grid gap-6 md:grid-cols-2">
        <CardSkeleton>
          <AlertSkeletonRows />
        </CardSkeleton>
        <CardSkeleton>
          <AlertSkeletonRows />
        </CardSkeleton>
      </div>
      <div className="flex gap-4">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-10 w-48" />
      </div>
      <TableSkeleton />
    </div>
  );
}

/** /atas/{id} in its own shape: header, the ATA's fields, aditivos and reajustes. */
export function AtaSkeleton() {
  return (
    <div role="status" data-testid="page-skeleton" className="space-y-6">
      <span className="sr-only">Carregando...</span>
      <Header />
      <CardSkeleton>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 9 }, (_, index) => (
            <div key={index} className="space-y-2">
              <Skeleton className="h-3 w-24" />
              <Skeleton className="h-4 w-40" />
            </div>
          ))}
        </div>
      </CardSkeleton>
      <TableSkeleton rows={2} />
      <TableSkeleton rows={2} />
    </div>
  );
}
