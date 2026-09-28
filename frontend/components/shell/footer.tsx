import { ContactGestor } from "@/components/contact";

// Inlined at build time from package.json (next.config.ts), so the footer names
// the version this bundle was built from (AC-0011-10).
const VERSION = process.env.NEXT_PUBLIC_SIGI_VERSION ?? "dev";

export function Footer() {
  return (
    <footer
      data-testid="footer"
      className="flex flex-col gap-1 border-t px-4 py-4 text-xs font-light text-muted-foreground sm:flex-row sm:items-center sm:gap-2 sm:px-6 [&_p]:text-xs"
    >
      <span>
        SIGI <span data-testid="footer-version">v{VERSION}</span>
      </span>
      <span aria-hidden className="hidden sm:inline">
        ·
      </span>
      <ContactGestor testId="footer-contact" />
    </footer>
  );
}
