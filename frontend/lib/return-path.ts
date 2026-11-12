import { HOME_PATH } from "@/lib/constants";

/**
 * Where to go after login: a path on this origin, or the dashboard (AC-0010-16).
 *
 * Only a single leading slash is accepted. `//evil.example` and `/\evil.example`
 * are protocol-relative to a browser, and anything with a scheme leaves SIGI.
 */
export function safeReturnPath(raw: string | null | undefined): string {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//") || raw.startsWith("/\\")) {
    return HOME_PATH;
  }
  try {
    const resolved = new URL(raw, "http://sigi.invalid");
    if (resolved.origin !== "http://sigi.invalid" || resolved.pathname === "/login") {
      return HOME_PATH;
    }
    return `${resolved.pathname}${resolved.search}${resolved.hash}`;
  } catch {
    return HOME_PATH;
  }
}
