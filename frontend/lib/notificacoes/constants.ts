/** What the bell reads (SPEC-0008 AC-0008-04, -05). */

// The newest notices the bell lists; every one is also on its ATA's page.
export const BELL_SIZE = 20;
export const BELL_PATH = `/api/v1/notificacoes?page=1&size=${BELL_SIZE}`;
// More than this reads as "9+", so the count never widens the header.
export const BELL_MAX_COUNT = 9;

export const BELL_LABEL = "Avisos";
export const BELL_EMPTY = "Nenhum aviso de ATA.";
export const MARK_ALL = "Marcar todas como lidas";

// ── Configurações: the e-mail summary (SPEC-0008 AC-0008-07) ───────────────

export const FREQUENCIAS = [
  { value: "diario", label: "Diário", hint: "Todo dia, com os dados do dia." },
  { value: "semanal", label: "Semanal", hint: "Uma vez por semana, no dia escolhido." },
  { value: "nenhum", label: "Nenhum", hint: "Sem e-mail; os avisos continuam no sino." },
] as const;

// ISO weekdays: 1 is Monday, 7 is Sunday, as the API reads them.
export const DIAS_SEMANA = [
  { value: 1, label: "Segunda-feira" },
  { value: 2, label: "Terça-feira" },
  { value: 3, label: "Quarta-feira" },
  { value: 4, label: "Quinta-feira" },
  { value: 5, label: "Sexta-feira" },
  { value: 6, label: "Sábado" },
  { value: 7, label: "Domingo" },
] as const;

export const PREFS_PATH = "/api/v1/preferencias/email";
export const PREFS_SAVED = "Preferência salva.";
export const SETTINGS_LABEL = "Configurações";
