/**
 * One message carried across a navigation, e.g. the API's reason a session
 * died, shown verbatim on /login (C3). sessionStorage holds the sentence only,
 * never a token (C1), and it is read once.
 */
const KEY = "sigi.flash";
const NEXT = "sigi.next";

function storage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.sessionStorage;
  } catch {
    return null;
  }
}

export function setFlash(message: string): void {
  storage()?.setItem(KEY, message);
}

export function takeFlash(): string | null {
  const store = storage();
  const message = store?.getItem(KEY) ?? null;
  store?.removeItem(KEY);
  return message;
}

/** The return path survives the round trip to the identity provider. */
export function rememberNext(path: string): void {
  storage()?.setItem(NEXT, path);
}

export function takeNext(): string | null {
  const store = storage();
  const path = store?.getItem(NEXT) ?? null;
  store?.removeItem(NEXT);
  return path;
}
