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
export async function asGestor(method: "post", path: string, data?: Record<string, unknown>) {
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
  await page.getByLabel("E-mail institucional").fill(email);
  await page.getByLabel("Senha", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

/**
 * Follow a sidebar entry. The dashboard's tiles link to the same modules
 * (AC-0011-13), so a link found by name alone is no longer unique.
 */
export async function openFromSidebar(page: Page, name: string) {
  await page.getByRole("navigation", { name: "Principal" }).getByRole("link", { name }).click();
}
