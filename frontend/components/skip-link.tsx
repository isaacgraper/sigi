"use client";

/**
 * First focusable element on every page (AC-0011-09, eMAG). Following a
 * fragment does not move focus in every engine, so the target is focused by
 * hand; every page's `<main>` carries the id.
 */
export function SkipLink() {
  return (
    <a
      href="#content"
      // Explicit, so Safari reaches it with Tab too: by default it skips plain links.
      tabIndex={0}
      onClick={(event) => {
        const target = document.getElementById("content");
        if (!target) return;
        event.preventDefault();
        target.focus();
        target.scrollIntoView();
      }}
      className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:font-normal focus:text-primary-foreground focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
    >
      Ir para o conteúdo
    </a>
  );
}
