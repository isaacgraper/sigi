import { cookies } from "next/headers";
import { Suspense } from "react";

import { SessionProvider } from "@/components/session-provider";
import { SIDEBAR_COOKIE } from "@/lib/sidebar";

// Every page under here needs a session. The pages are client-rendered,
// because the access token exists only in the browser's memory (C1). This
// layout stays on the server for one reason: to read the sidebar preference
// before the first paint, so a collapsed sidebar never flashes open
// (AC-0011-03).
export default async function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  const collapsed = (await cookies()).get(SIDEBAR_COOKIE)?.value === "collapsed";
  return (
    <Suspense>
      <SessionProvider sidebarCollapsed={collapsed}>{children}</SessionProvider>
    </Suspense>
  );
}
