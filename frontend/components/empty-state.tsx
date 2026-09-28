import { Illustration } from "@/components/illustration";

/**
 * What a table shows when it has no rows (AC-0011-19): the empty illustration,
 * one sentence saying what is missing, and the action that would add a row
 * when the perfil has one.
 */
export function EmptyState({ message, action }: { message: string; action?: React.ReactNode }) {
  return (
    <div data-testid="empty-state" className="flex flex-col items-center gap-3 py-8 text-center">
      <Illustration name="empty" className="max-h-40" />
      <p className="text-sm font-light text-muted-foreground">{message}</p>
      {action}
    </div>
  );
}
