// Records the dashboard demonstration as timestamped frames and a log of the
// clicks and keys, for scripts/assemble-demo.py to turn into a video.
// Demo branch only. Needs the stack running with DASHBOARD_DEMO=true.
//
//   node scripts/record-demo.mjs <out-dir>
//
// Frames come from a CDP screencast rather than Playwright's recordVideo,
// whose VP8 output is soft; each frame keeps the browser's own timestamp, and
// the events are logged on the same clock so the sounds land on their frames.
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

import { chromium } from "@playwright/test";

const OUT = process.argv[2] ?? "demo-recording";
const BASE = process.env.DEMO_BASE_URL ?? "http://localhost:3000";
const WIDTH = 1920;
const HEIGHT = 1080;

// A visible cursor for the video only: the page under test is not changed.
// It glides between targets and leaves a ring where it presses.
const CURSOR = () => {
  const install = () => {
    if (document.getElementById("demo-cursor")) return;
    const style = document.createElement("style");
    style.textContent = `
      #demo-cursor { position: fixed; left: 0; top: 0; z-index: 2147483647; pointer-events: none;
        transform: translate(var(--x, 960px), var(--y, 540px));
        transition: transform 900ms cubic-bezier(0.77, 0, 0.175, 1); }
      #demo-cursor svg { display: block; filter: drop-shadow(0 1px 1.5px rgb(0 0 0 / 0.35)); }
      .demo-ring { position: fixed; z-index: 2147483646; pointer-events: none; width: 36px; height: 36px;
        margin: -18px 0 0 -18px; border-radius: 9999px; border: 2px solid rgb(30 52 94 / 0.55);
        animation: demo-ring 320ms cubic-bezier(0.23, 1, 0.32, 1) forwards; }
      @keyframes demo-ring { from { transform: scale(0.55); opacity: 0.9; } to { transform: scale(1); opacity: 0; } }`;
    document.head.append(style);
    const cursor = document.createElement("div");
    cursor.id = "demo-cursor";
    cursor.innerHTML =
      '<svg width="22" height="28" viewBox="0 0 22 28"><path d="M2 2 L2 22 L7.5 17 L11 25.5 L14.5 24 L11 15.8 L18.5 15.8 Z" fill="#fff" stroke="#122343" stroke-width="1.6" stroke-linejoin="round"/></svg>';
    const saved = sessionStorage.getItem("demo-cursor");
    if (saved) {
      const [x, y] = JSON.parse(saved);
      cursor.style.transition = "none";
      cursor.style.setProperty("--x", `${x}px`);
      cursor.style.setProperty("--y", `${y}px`);
      requestAnimationFrame(() => (cursor.style.transition = ""));
    }
    document.body.append(cursor);
  };
  window.__demoCursor = {
    move(x, y) {
      install();
      const cursor = document.getElementById("demo-cursor");
      cursor.style.setProperty("--x", `${x}px`);
      cursor.style.setProperty("--y", `${y}px`);
      sessionStorage.setItem("demo-cursor", JSON.stringify([x, y]));
    },
    press(x, y) {
      const ring = document.createElement("div");
      ring.className = "demo-ring";
      ring.style.left = `${x}px`;
      ring.style.top = `${y}px`;
      document.body.append(ring);
      setTimeout(() => ring.remove(), 400);
    },
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", install);
  else install();
};

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const events = [];
const log = (kind, extra = {}) => events.push({ kind, t: Date.now() / 1000, ...extra });
// A camera keyframe for the assembly: ease towards (x, y) at this zoom.
const focus = (x, y, zoom) => log("focus", { x, y, zoom });
const wide = () => focus(WIDTH / 2, HEIGHT / 2, 1);

async function main() {
  const frameDir = path.join(OUT, "frames");
  await mkdir(frameDir, { recursive: true });

  const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM_PATH || undefined });
  const context = await browser.newContext({ viewport: { width: WIDTH, height: HEIGHT }, deviceScaleFactor: 1 });
  await context.addInitScript(CURSOR);
  const page = await context.newPage();

  const frames = [];
  const cdp = await context.newCDPSession(page);
  let writes = Promise.resolve();
  cdp.on("Page.screencastFrame", ({ data, metadata, sessionId }) => {
    const file = `${String(frames.length).padStart(6, "0")}.jpg`;
    frames.push({ file, t: metadata.timestamp });
    writes = writes.then(() => writeFile(path.join(frameDir, file), Buffer.from(data, "base64")));
    cdp.send("Page.screencastFrameAck", { sessionId }).catch(() => {});
  });

  async function point(locator) {
    await locator.scrollIntoViewIfNeeded();
    const box = await locator.boundingBox();
    return { x: Math.round(box.x + box.width / 2), y: Math.round(box.y + box.height / 2) };
  }
  // The cursor glides for 0.9 s; settle is the rest after it arrives.
  async function moveTo(locator, settle = 1200, zoom = 0) {
    const { x, y } = await point(locator);
    if (zoom) focus(x, y, Math.min(zoom, 1.3));
    await page.evaluate(([px, py]) => window.__demoCursor.move(px, py), [x, y]);
    await page.mouse.move(x, y, { steps: 24 });
    await wait(900 + settle);
    return { x, y };
  }
  async function click(locator) {
    // Rest over the target a moment before pressing, as a person would.
    const { x, y } = await moveTo(locator, 350);
    await page.evaluate(([px, py]) => window.__demoCursor.press(px, py), [x, y]);
    log("click");
    await page.mouse.click(x, y);
  }
  async function type(locator, text) {
    await click(locator);
    await wait(400);
    // One soft breath under the whole word, not a tick per key.
    log("breath");
    for (const ch of text) {
      await page.keyboard.type(ch);
      await wait(110 + Math.random() * 40);
    }
  }
  // One eased 1.2 s scroll, steadier than the browser's own smooth scroll.
  async function glide(top) {
    await page.evaluate(
      (target) =>
        new Promise((resolve) => {
          const from = window.scrollY;
          const to = Math.max(0, Math.min(target, document.documentElement.scrollHeight - innerHeight));
          const start = performance.now();
          const ease = (p) => (p < 0.5 ? 4 * p * p * p : 1 - (-2 * p + 2) ** 3 / 2);
          const step = (now) => {
            const p = Math.min(1, (now - start) / 1200);
            window.scrollTo(0, from + (to - from) * ease(p));
            if (p < 1) requestAnimationFrame(step);
            else resolve();
          };
          requestAnimationFrame(step);
        }),
      top,
    );
  }
  async function scrollTo(locator, block = "center") {
    wide();
    await wait(400);
    log("whoosh");
    const top = await locator.evaluate((el, b) => {
      const box = el.getBoundingClientRect();
      const offset = b === "start" ? 96 : (innerHeight - box.height) / 2;
      return window.scrollY + box.top - Math.max(24, offset);
    }, block);
    await glide(top);
    await wait(1000);
  }
  async function toTop() {
    wide();
    await wait(400);
    log("whoosh");
    await glide(0);
    await wait(1200);
  }
  async function openTab(name, ready) {
    wide();
    await click(page.getByRole("tab", { name }));
    await ready.first().waitFor();
    log("chime");
    await wait(1500);
  }

  await page.goto(`${BASE}/login`);
  await page.getByRole("button", { name: "Entrar", exact: true }).waitFor();
  await page.evaluate(() => window.__demoCursor.move(1500, 820));
  await wait(400);
  await cdp.send("Page.startScreencast", { format: "jpeg", quality: 90, maxWidth: WIDTH, maxHeight: HEIGHT, everyNthFrame: 1 });
  await wait(1000);

  // 1. Sign in, the camera close on the form.
  const form = await point(page.getByLabel("Senha", { exact: true }));
  focus(form.x, form.y - 30, 1.3);
  await wait(1400);
  await type(page.getByLabel("E-mail institucional"), "admin@sc.gov.br");
  await wait(600);
  await type(page.getByLabel("Senha", { exact: true }), "admin");
  await wait(700);
  await click(page.getByRole("button", { name: "Entrar", exact: true }));
  await page.waitForURL(/dashboard/);
  wide();
  const panel = page.getByRole("tabpanel");
  await panel.getByTestId("dashboard-chart").first().waitFor();
  log("chime");
  await wait(2200);

  // 2. Atendimento por unidade.
  await moveTo(panel.getByRole("cell", { name: "Abaixador de língua, pacote com 100" }), 1200, 1.25);
  await scrollTo(panel.getByTestId("dashboard-chart").first());
  await moveTo(panel.locator(".recharts-bar-rectangle").first(), 1200, 1.2);

  // 3. Consumo.
  await toTop();
  await openTab("Consumo", panel.locator(".recharts-line"));
  await moveTo(panel.getByText("Posição de 01/10/2026"), 1200, 1.3);
  const line = panel.locator(".recharts-surface").first();
  const area = await line.boundingBox();
  focus(area.x + area.width * 0.55, area.y + area.height * 0.4, 1.2);
  for (const fraction of [0.3, 0.55, 0.8]) {
    const x = Math.round(area.x + area.width * fraction);
    const y = Math.round(area.y + area.height * 0.35);
    await page.evaluate(([px, py]) => window.__demoCursor.move(px, py), [x, y]);
    await page.mouse.move(x, y, { steps: 24 });
    await wait(1200);
  }

  // 4. Processos licitatórios.
  await openTab("Processos licitatórios", panel.getByText("Processo concluído em 310 dias"));
  await scrollTo(panel.getByTestId("dashboard-chart").first());
  await moveTo(panel.locator(".recharts-bar-rectangle").nth(1), 1200, 1.25);
  await scrollTo(panel.getByRole("heading", { name: "Itens do processo" }), "start");

  // 5. Itens em falta.
  await toTop();
  await openTab("Itens em falta", panel.getByText("CALCSEG"));
  await scrollTo(panel.getByRole("heading", { name: "Disponibilidade" }));
  await moveTo(panel.getByText("Em falta", { exact: true }).last(), 1200, 1.3);
  await scrollTo(panel.getByRole("heading", { name: "Materiais" }), "start");
  await moveTo(panel.getByRole("cell", { name: "Seringa descartável 10 ml com dispositivo de segurança" }), 1200, 1.2);

  // 6. Back to the top and hold.
  await toTop();
  await wait(1500);

  await cdp.send("Page.stopScreencast");
  await writes;
  await writeFile(path.join(OUT, "frames.json"), JSON.stringify(frames));
  await writeFile(path.join(OUT, "events.json"), JSON.stringify(events));
  await browser.close();
  console.log(`${frames.length} frames, ${events.length} events in ${OUT}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
