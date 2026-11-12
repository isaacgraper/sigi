/**
 * The last answer of each API read, kept in this tab's memory so a page already
 * seen draws at once and refreshes behind (SPEC-0011 AC-0011-18).
 *
 * Memory only, never storage: it holds what the signed-in usuario may read, so
 * it ends with the session. Any successful write clears it, because a write can
 * change what any list shows; the page that made the write puts back the one
 * answer it already holds.
 */

const answers = new Map<string, unknown>();

export function cached<T>(path: string): T | undefined {
  return answers.get(path) as T | undefined;
}

export function remember<T>(path: string, value: T): T {
  answers.set(path, value);
  return value;
}

export function forgetAnswers(): void {
  answers.clear();
}
