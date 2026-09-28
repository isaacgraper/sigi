"use client";

import { Breadcrumb } from "@/components/shell/breadcrumb";
import { Footer } from "@/components/shell/footer";
import { MobileNav } from "@/components/shell/mobile-nav";
import { Sidebar } from "@/components/shell/sidebar";
import { UserMenu } from "@/components/shell/user-menu";
import type { Me } from "@/lib/me";

/** The frame of every authenticated page (SPEC-0011 §4.1, DESIGN.md §3). */
export function AppShell({
  me,
  onLogout,
  sidebarCollapsed,
  children,
}: {
  me: Me;
  onLogout: () => void;
  sidebarCollapsed: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-dvh">
      <Sidebar me={me} initiallyCollapsed={sidebarCollapsed} />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b bg-card px-4 sm:px-6">
          <MobileNav me={me} />
          <div className="min-w-0 flex-1">
            <Breadcrumb />
          </div>
          <UserMenu me={me} onLogout={onLogout} />
        </header>
        <Content>{children}</Content>
        <Footer />
      </div>
    </div>
  );
}

/** The skip link's target (AC-0011-09); focusable by script, not by Tab. */
export function Content({ children }: { children: React.ReactNode }) {
  return (
    <main id="content" tabIndex={-1} className="flex-1 focus:outline-none">
      <div className="mx-auto w-full max-w-7xl p-4 sm:p-6">{children}</div>
    </main>
  );
}
