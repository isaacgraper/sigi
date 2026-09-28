/**
 * The cookie that remembers a collapsed sidebar (AC-0011-03). Kept out of the
 * sidebar component so the server layout can read the name: a constant
 * imported from a client module arrives on the server as a reference, not a
 * string.
 */
export const SIDEBAR_COOKIE = "sigi_sidebar";
