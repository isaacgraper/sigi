/**
 * Same-origin proxy to the API (SPEC-0010 §3, deployment assumption).
 *
 * The refresh cookie and the OIDC state cookie are scoped by path under
 * /api/v1, so they only reach the API if the browser believes it is talking to
 * this origin. A route handler rather than `next.config` rewrites: under
 * `output: "standalone"` rewrites are fixed at build time, and `API_ORIGIN`
 * differs per deployment.
 */
import type { NextRequest } from "next/server";

// Hop-by-hop headers, and the ones `fetch` recomputes after decoding the body.
const DROPPED = new Set([
  "connection",
  "content-encoding",
  "content-length",
  "host",
  "keep-alive",
  "transfer-encoding",
]);

async function forward(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  const origin = process.env.API_ORIGIN ?? "http://localhost:8000";
  const { path } = await context.params;
  const target = new URL(`/api/v1/${path.map(encodeURIComponent).join("/")}`, origin);
  target.search = request.nextUrl.search;

  const headers = new Headers();
  request.headers.forEach((value, name) => {
    if (!DROPPED.has(name)) headers.set(name, value);
  });

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const upstream = await fetch(target, {
    method: request.method,
    headers,
    body: hasBody ? await request.arrayBuffer() : undefined,
    // The OIDC authorize route answers 302 to the provider; the browser must
    // follow it, not this server.
    redirect: "manual",
    cache: "no-store",
  });

  const responseHeaders = new Headers();
  upstream.headers.forEach((value, name) => {
    if (!DROPPED.has(name) && name !== "set-cookie") responseHeaders.set(name, value);
  });
  // Each Set-Cookie must survive as its own header; joining them breaks cookies
  // whose attributes contain commas (Expires).
  for (const cookie of upstream.headers.getSetCookie()) {
    responseHeaders.append("set-cookie", cookie);
  }

  return new Response(upstream.status === 204 ? null : upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

export const GET = forward;
export const POST = forward;
export const PUT = forward;
export const PATCH = forward;
export const DELETE = forward;

export const dynamic = "force-dynamic";
