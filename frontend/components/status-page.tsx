import { ShieldCheck } from "lucide-react";

import { Illustration, type IllustrationName } from "@/components/illustration";

/**
 * The frame for pages that replace a screen: not found, and failures
 * (AC-0011-16). The illustration sits above the words and never replaces them.
 */
export function StatusPage({
  illustration,
  title,
  description,
  children,
}: {
  illustration: IllustrationName;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <main
      id="content"
      tabIndex={-1}
      className="flex min-h-dvh items-center justify-center px-4 py-12 focus:outline-none"
    >
      <div className="w-full max-w-md space-y-6 text-center">
        <div className="flex items-center justify-center gap-2 font-semibold text-primary">
          <ShieldCheck aria-hidden className="size-5" />
          SIGI
        </div>
        <Illustration name={illustration} className="mx-auto max-h-60" />
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
        <div className="flex flex-col items-center gap-4">{children}</div>
      </div>
    </main>
  );
}
