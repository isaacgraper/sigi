/**
 * One message carried across a navigation, e.g. the API's reason a session
 * died, shown verbatim on /login (C3). sessionStorage holds the sentence only,
 * never a token (C1), and it is read once.
 */
import { FLASH_STORAGE_KEY, NEXT_STORAGE_KEY } from "@/lib/constants";

function storage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.sessionStorage;
  } catch {
    return null;
  }
}

export function setFlash(message: string): void {
  storage()?.setItem(FLASH_STORAGE_KEY, message);
}

export function takeFlash(): string | null {
  const store = storage();
  const message = store?.getItem(FLASH_STORAGE_KEY) ?? null;
  store?.removeItem(FLASH_STORAGE_KEY);
  return message;
}

/** The return path survives the round trip to the identity provider. */
export function rememberNext(path: string): void {
  storage()?.setItem(NEXT_STORAGE_KEY, path);
}

export function takeNext(): string | null {
  const store = storage();
  const path = store?.getItem(NEXT_STORAGE_KEY) ?? null;
  store?.removeItem(NEXT_STORAGE_KEY);
  return path;
}
