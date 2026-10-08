import { useSyncExternalStore } from "react";

const noop = () => () => {};

/**
 * False during the server render and hydration, true once React owns the page.
 *
 * A credential form clicked before hydration submits natively; without this,
 * the browser's default GET puts the password in the address bar and in every
 * access log between here and the server.
 */
export function useHydrated(): boolean {
  return useSyncExternalStore(
    noop,
    () => true,
    () => false,
  );
}
