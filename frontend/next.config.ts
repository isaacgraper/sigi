import type { NextConfig } from "next";

// The invitation and reset links carry their token as a query parameter
// (OQ-30). The pages strip it from the address bar, and no-referrer stops it
// leaving in a Referer header in the meantime (AC-0010-18, -24).
const noReferrer = [{ key: "Referrer-Policy", value: "no-referrer" }];

// Every response (AC-0010-54). The Content-Security-Policy is set per request
// in proxy.ts, because it carries a nonce.
const everywhere = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

const nextConfig: NextConfig = {
  output: "standalone",
  headers() {
    // Later entries win for the same header, so the two stricter
    // Referrer-Policy values come after the general one.
    return Promise.resolve([
      { source: "/:path*", headers: everywhere },
      { source: "/invite", headers: noReferrer },
      { source: "/reset-password", headers: noReferrer },
    ]);
  },
};

export default nextConfig;
