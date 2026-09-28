import { Suspense } from "react";

import { SessionProvider } from "@/components/session-provider";

// Every page under here needs a session. Client-rendered, because the access
// token exists only in the browser's memory (C1).
export default function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense>
      <SessionProvider>{children}</SessionProvider>
    </Suspense>
  );
}
