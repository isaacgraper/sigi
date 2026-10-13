import { Skeleton, TableSkeleton } from "@/components/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

/** The rows of the due list while it loads. */
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

/** /atas in its own shape: header, the due list, filters and the table (AC-0013-06). */
export function AtasSkeleton() {
  return (
    <div role="status" data-testid="page-skeleton" className="space-y-6">
      <span className="sr-only">Carregando...</span>
      <Header />
      <CardSkeleton>
        <AlertSkeletonRows />
      </CardSkeleton>
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

/** /atas/nova and /atas/{id}/editar in their own shape: header and four sections. */
export function FormSkeleton() {
  return (
    <div role="status" data-testid="page-skeleton" className="space-y-6">
      <span className="sr-only">Carregando...</span>
      <Header />
      <Card aria-hidden className="divide-y">
        {[0, 1, 2, 3].map((section) => (
          <div key={section} className="grid gap-4 p-6 md:grid-cols-[13rem_minmax(0,1fr)]">
            <Skeleton className="h-5 w-32" />
            <div className="grid gap-4 sm:grid-cols-2">
              <Skeleton className="h-10" />
              <Skeleton className="h-10" />
            </div>
          </div>
        ))}
      </Card>
    </div>
  );
}
