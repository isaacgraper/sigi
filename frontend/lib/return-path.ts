export const HOME = "/dashboard";

/**
 * Where to go after login: a path on this origin, or the dashboard (AC-0010-16).
 *
 * Only a single leading slash is accepted. `//evil.example` and `/\evil.example`
 * are protocol-relative to a browser, and anything with a scheme leaves SIGI.
 */
export function safeReturnPath(raw: string | null | undefined): string {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//") || raw.startsWith("/\\")) {
    return HOME;
  }
  try {
    const resolved = new URL(raw, "http://sigi.invalid");
    if (resolved.origin !== "http://sigi.invalid" || resolved.pathname === "/login") {
      return HOME;
    }
    return `${resolved.pathname}${resolved.search}${resolved.hash}`;
  } catch {
    return HOME;
  }
}
