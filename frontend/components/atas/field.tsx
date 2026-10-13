import { Label } from "@/components/ui/label";

/**
 * A labelled control with the API's refusal below it (DESIGN.md §4): the
 * message is linked with `aria-describedby` and the control marked invalid.
 */
export function Field({
  id,
  label,
  error,
  hint,
  children,
}: {
  id: string;
  label: string;
  error?: string;
  hint?: string;
  children: (props: {
    id: string;
    "aria-invalid"?: true;
    "aria-describedby"?: string;
  }) => React.ReactNode;
}) {
  const describedBy = [hint ? `${id}-hint` : null, error ? `${id}-error` : null].filter(Boolean).join(" ");
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      {children({
        id,
        "aria-invalid": error ? true : undefined,
        "aria-describedby": describedBy || undefined,
      })}
      {hint && (
        <p id={`${id}-hint`} className="text-xs font-light text-muted-foreground">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} data-testid="field-error" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}

/** Focus the first control the API named, in the form's own order (AC-0013-08). */
export function focusFirst(order: string[], errors: Record<string, string>, prefix: string): void {
  const first = order.find((key) => errors[key]);
  if (first) document.getElementById(`${prefix}-${first.replace(".", "-")}`)?.focus();
}
