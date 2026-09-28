import type { NextConfig } from "next";

// The invitation and reset links carry their token as a query parameter
// (OQ-30). The pages strip it from the address bar, and no-referrer stops it
// leaving in a Referer header in the meantime (AC-0010-18, -24).
const noReferrer = [{ key: "Referrer-Policy", value: "no-referrer" }];

const nextConfig: NextConfig = {
  output: "standalone",
  headers() {
    return Promise.resolve([
      { source: "/convite", headers: noReferrer },
      { source: "/redefinir-senha", headers: noReferrer },
    ]);
  },
};

export default nextConfig;
