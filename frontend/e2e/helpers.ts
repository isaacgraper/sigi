import AxeBuilder from "@axe-core/playwright";
import { type APIRequestContext, expect, type Page, request } from "@playwright/test";

/**
 * The development gestor, seeded before the suite runs (AC-0001-39). Every
 * other account is invited through the API, the way a real one is, so the
 * suite never writes to the database behind its back.
 */
export const GESTOR = { email: "admin@sc.gov.br", password: "admin" };
export const LONG_ENOUGH = "SenhaLongaOSuficiente-2026";

export type Perfil = "gestor" | "servidor" | "auditor";

export function uniqueEmail(prefix: string): string {
  return `${prefix}${Date.now().toString(36)}${Math.floor(Math.random() * 1e6).toString(36)}@sc.gov.br`;
}

async function api(): Promise<APIRequestContext> {
  return request.newContext({ baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000" });
}

async function tokenFor(ctx: APIRequestContext, email: string, password: string): Promise<string> {
  const response = await ctx.post("/api/v1/auth/login", { data: { email, password } });
  expect(response.status(), await response.text()).toBe(200);
  return ((await response.json()) as { access_token: string }).access_token;
}

/** Invite a member as the seeded gestor; returns the link and the new id. */
export async function invite(perfil: Perfil, email = uniqueEmail(perfil)) {
  const ctx = await api();
  const token = await tokenFor(ctx, GESTOR.email, GESTOR.password);
  const response = await ctx.post("/api/v1/usuarios", {
    data: { email, perfil, name: "Pessoa Convidada", registration: `REG-${Date.now()}` },
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(response.status(), await response.text()).toBe(201);
  const body = (await response.json()) as { id: string; activation_link: string };
  await ctx.dispose();
  return { email, id: body.id, link: body.activation_link };
}

/** An active member with a known password, created as a real one would be. */
export async function member(perfil: Perfil) {
  const invited = await invite(perfil);
  const ctx = await api();
  const token = new URL(invited.link).searchParams.get("token");
  const response = await ctx.post("/api/v1/convites/ativar", {
    data: { token, password: LONG_ENOUGH },
  });
  expect(response.status(), await response.text()).toBe(200);
  await ctx.dispose();
  return { email: invited.email, id: invited.id, password: LONG_ENOUGH };
}

/** Gestor-side action on a member, through the API. */
export async function asGestor(method: "get" | "post", path: string, data?: Record<string, unknown>) {
  const ctx = await api();
  const token = await tokenFor(ctx, GESTOR.email, GESTOR.password);
  const response = await ctx[method](path, { headers: { Authorization: `Bearer ${token}` }, data });
  const body = response.status() === 204 ? null : await response.json();
  await ctx.dispose();
  return { status: response.status(), body };
}

/** Relative path of a link the API built against its configured frontend URL. */
export function pathOf(link: string): string {
  const url = new URL(link);
  return `${url.pathname}${url.search}`;
}

export async function signIn(page: Page, email: string, password: string) {
  await page.goto("/login");
  // The button is disabled until React hydrates. Filling before that loses the
  // values, because hydration resets the controlled inputs to empty.
  await expect(page.getByRole("button", { name: "Entrar", exact: true })).toBeEnabled();
  await page.getByLabel("E-mail institucional").fill(email);
  await page.getByLabel("Senha", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

/**
 * Follow a sidebar entry. The search stays inside the navigation, because a
 * page's own content may name the same module.
 */
export async function openFromSidebar(page: Page, name: string) {
  await page.getByRole("navigation", { name: "Principal" }).getByRole("link", { name }).click();
}

/** A date `days` from today, as the API reads it (`2026-10-13`). */
export function isoDay(days: number): string {
  // Today as the API counts it, in America/Sao_Paulo: from 21h there the UTC date
  // is already tomorrow, and every "N days" would be off by one.
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date());
  const date = new Date(`${today}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

/** A unique ATA number, so the suite can run again on the same database. */
export function ataNumber(): string {
  return `E2E-${Date.now().toString(36)}${Math.floor(Math.random() * 1e6).toString(36)}`;
}

/** An ATA registered through the API by the seeded gestor, and moved on if asked. */
export async function createAta(overrides: Record<string, unknown> = {}, moves: string[] = []) {
  const created = await asGestor("post", "/api/v1/atas", {
    number: ataNumber(),
    subject: "Seringas descartáveis com dispositivo de segurança",
    organ: "Secretaria de Estado da Saúde",
    fornecedor: { cnpj: "11.222.333/0001-81", legal_name: "MedSul Distribuidora Ltda" },
    vigencia_inicio: "2026-01-02",
    vigencia_fim: "2026-12-01",
    total_value: "1234567.89",
    budget_date: "2026-02-10",
    ...overrides,
  });
  expect(created.status, JSON.stringify(created.body)).toBe(201);
  const ata = created.body as { id: string; number: string };
  for (const move of moves) {
    const moved = await asGestor("post", `/api/v1/atas/${ata.id}/${move}`);
    expect(moved.status, JSON.stringify(moved.body)).toBe(200);
  }
  return ata;
}

/** AC-0010-44: no serious or critical axe violation on what settled on screen. */
export async function noSeriousViolations(page: Page) {
  // Measure what settles on screen, not a frame of a fade: text halfway through
  // an opacity transition reads as low contrast. Endless ones (a skeleton's
  // pulse) are left alone, since they never finish.
  await page.evaluate(() =>
    Promise.all(
      document
        .getAnimations()
        .filter((a) => a.effect?.getComputedTiming().endTime !== Infinity)
        .map((a) => a.finished.catch(() => undefined)),
    ),
  );
  const results = await new AxeBuilder({ page }).analyze();
  const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(serious.map((v) => `${v.id}: ${v.nodes.map((n) => n.target).join(", ")}`)).toEqual([]);
}

/** A unique code, so the catalogue suite runs again on the same database. */
export function uniqueSku(): string {
  return `E2E${Date.now().toString(36).toUpperCase()}${Math.floor(Math.random() * 1e6).toString(36).toUpperCase()}`;
}

/** A grupo created through the API by the seeded gestor. */
export async function createGrupo(name = `GRUPO ${uniqueSku()}`, parentId: string | null = null) {
  const created = await asGestor("post", "/api/v1/grupos-materiais", { name, parent_id: parentId });
  expect(created.status, JSON.stringify(created.body)).toBe(201);
  return created.body as { id: string; name: string; level: number };
}

/** An insumo registered through the API by the seeded gestor. */
export async function createInsumo(grupoId: string, overrides: Record<string, unknown> = {}) {
  const created = await asGestor("post", "/api/v1/insumos", {
    sku: uniqueSku(),
    description: `CLOREXIDINA 2% 1 L ${uniqueSku()}`,
    unit: "UN",
    grupo_id: grupoId,
    ...overrides,
  });
  expect(created.status, JSON.stringify(created.body)).toBe(201);
  return created.body as { id: string; sku: string; description: string };
}

/** An item of an ATA, added through the API by the seeded gestor. */
export async function addItem(ataId: string, insumoId: string, overrides: Record<string, unknown> = {}) {
  const created = await asGestor("post", `/api/v1/atas/${ataId}/itens`, {
    insumo_id: insumoId,
    quantity: "100",
    unit_price: "1.5",
    ...overrides,
  });
  expect(created.status, JSON.stringify(created.body)).toBe(201);
  return created.body as { items: { id: string; insumo: { id: string; sku: string } }[] };
}
