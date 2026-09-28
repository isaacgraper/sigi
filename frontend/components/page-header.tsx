/**
 * The top of every authenticated page (AC-0011-11, -12): the page's only
 * level-one heading, one line of description, and its primary action beside
 * them. The document title is set by the route's metadata, from the same words.
 */
export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div
      data-testid="page-header"
      className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"
    >
      <div className="min-w-0">
        <h1 className="text-2xl font-normal tracking-tight">{title}</h1>
        <p className="text-sm font-light text-muted-foreground">{description}</p>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
