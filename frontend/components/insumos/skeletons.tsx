import { Skeleton, TableSkeleton } from "@/components/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

function Header() {
  return (
    <div className="space-y-2">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-4 w-72 max-w-full" />
    </div>
  );
}

/** /insumos/{id} in its own shape: header, the insumo's fields and its ATAs. */
export function InsumoSkeleton() {
  return (
    <div role="status" data-testid="page-skeleton" className="reveal-late space-y-6">
      <span className="sr-only">Carregando...</span>
      <Header />
      <Card aria-hidden>
        <CardHeader className="pb-3">
          <Skeleton className="h-5 w-40" />
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }, (_, index) => (
            <div key={index} className="space-y-2">
              <Skeleton className="h-3 w-24" />
              <Skeleton className="h-4 w-40" />
            </div>
          ))}
        </CardContent>
      </Card>
      <TableSkeleton rows={2} />
    </div>
  );
}

/** A form page in its own shape: header and one card of fields. */
export function InsumoFormSkeleton() {
  return (
    <div role="status" data-testid="page-skeleton" className="reveal-late space-y-6">
      <span className="sr-only">Carregando...</span>
      <Header />
      <Card aria-hidden className="grid gap-4 p-6 sm:grid-cols-2">
        {Array.from({ length: 6 }, (_, index) => (
          <Skeleton key={index} className="h-10" />
        ))}
      </Card>
    </div>
  );
}
