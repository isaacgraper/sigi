"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { AppShell, Content } from "@/components/app-shell";
import { PageSkeleton } from "@/components/skeleton";
import { ApiError } from "@/lib/errors";
import { setFlash } from "@/lib/flash";
import type { Me } from "@/lib/me";
import { apiJson, logout } from "@/lib/session";
import { cn } from "@/lib/utils";

interface SessionContext {
  me: Me;
  /** Ends the session and returns true when the error means it is over. */
  handleSessionError: (error: unknown) => boolean;
}

const Context = createContext<SessionContext | null>(null);

export function useSession(): SessionContext {
  const value = useContext(Context);
  if (!value) throw new Error("useSession outside the authenticated layout");
  return value;
}

// Codes after which no retry can help: the refresh is spent, or the account
// stopped being active mid-session (AC-0010-13, §5).
const SESSION_OVER = new Set(["INVALID_REFRESH", "USUARIO_INATIVO"]);

export function SessionProvider({
  sidebarCollapsed,
  children,
}: {
  sidebarCollapsed: boolean;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const search = useSearchParams().toString();
  const [me, setMe] = useState<Me | null>(null);

  const toLogin = useCallback(() => {
    const here = search ? `${pathname}?${search}` : pathname;
    router.replace(`/login?next=${encodeURIComponent(here)}`);
  }, [pathname, router, search]);

  const handleSessionError = useCallback(
    (error: unknown) => {
      if (error instanceof ApiError && SESSION_OVER.has(error.code)) {
        setFlash(error.message);
        router.replace("/login");
        return true;
      }
      return false;
    },
    [router],
  );

  // On load the page has no token in memory; the refresh cookie restores it
  // (AC-0010-11). No cookie, or a dead one, means no session: go to login
  // without a message, because nothing the user did ended it.
  useEffect(() => {
    let cancelled = false;
    apiJson<Me>("/api/v1/auth/me")
      .then((value) => {
        if (!cancelled) setMe(value);
      })
      .catch(() => {
        if (!cancelled) toLogin();
      });
    return () => {
      cancelled = true;
    };
    // Restoring once per mount; later navigations reuse the session.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onLogout() {
    await logout();
    router.replace("/login");
  }

  if (!me) return <ShellSkeleton sidebarCollapsed={sidebarCollapsed} />;
  return (
    <Context.Provider value={{ me, handleSessionError }}>
      <AppShell me={me} onLogout={onLogout} sidebarCollapsed={sidebarCollapsed}>
        {children}
      </AppShell>
    </Context.Provider>
  );
}

/**
 * While the session is restored nobody knows the perfil yet, so the frame is
 * drawn without entries and the page as placeholders (AC-0011-18). Same widths
 * as the real shell, so nothing jumps when it arrives.
 */
function ShellSkeleton({ sidebarCollapsed }: { sidebarCollapsed: boolean }) {
  return (
    <div className="flex min-h-dvh">
      <div
        aria-hidden
        className={cn("sticky top-0 hidden h-dvh shrink-0 bg-sidebar lg:block", sidebarCollapsed ? "w-16" : "w-60")}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <div aria-hidden className="h-14 border-b bg-card" />
        <Content>
          <PageSkeleton />
        </Content>
      </div>
    </div>
  );
}
