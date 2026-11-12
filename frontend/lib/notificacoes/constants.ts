/** What the bell reads (SPEC-0008 AC-0008-04, -05). */

// The newest notices the bell lists; every one is also on its ATA's page.
export const BELL_SIZE = 20;
export const BELL_PATH = `/api/v1/notificacoes?page=1&size=${BELL_SIZE}`;
// More than this reads as "9+", so the count never widens the header.
export const BELL_MAX_COUNT = 9;

export const BELL_LABEL = "Avisos";
export const BELL_EMPTY = "Nenhum aviso de ATA.";
export const MARK_ALL = "Marcar todas como lidas";
