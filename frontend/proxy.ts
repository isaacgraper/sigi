import { type NextRequest, NextResponse } from "next/server";

/**
 * A Content-Security-Policy with a fresh nonce per request (AC-0010-53).
 *
 * Next.js reads the nonce from the request's CSP header and puts it on its own
 * scripts, so only those run: no 'unsafe-inline', and no 'unsafe-eval' outside
 * development, where React needs eval for its error overlays. style-src stays
 * without a nonce on purpose: browsers ignore 'unsafe-inline' next to a
 * nonce, and the dialog and toast libraries set inline styles at runtime.
 */
export function proxy(request: NextRequest) {
  const nonce = Buffer.from(crypto.randomUUID()).toString("base64");
  const dev = process.env.NODE_ENV === "development";
  const policy = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${dev ? " 'unsafe-eval'" : ""}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' blob: data:",
    "font-src 'self'",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
  ].join("; ");

  const headers = new Headers(request.headers);
  headers.set("x-nonce", nonce);
  headers.set("Content-Security-Policy", policy);

  const response = NextResponse.next({ request: { headers } });
  response.headers.set("Content-Security-Policy", policy);
  return response;
}

export const config = {
  matcher: [
    {
      // Pages only: the API proxy's responses carry the API's own policy.
      source: "/((?!api|_next/static|_next/image|favicon.ico).*)",
      missing: [
        { type: "header", key: "next-router-prefetch" },
        { type: "header", key: "purpose", value: "prefetch" },
      ],
    },
  ],
};
