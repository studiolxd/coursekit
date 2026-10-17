// The style of a website as it is seen (`coursekit brand`, a link under the websites to infer the style from): the CSS
// variables of its :root, the computed styles of its body, headings, links, buttons and cards, its colours weighted by the area
// they cover, its fonts and where they load from, candidates for its logo, and a screenshot in light and, when it has one,
// dark mode. Playwright drives the Chrome of the machine; it prints one JSON object.
import { readFileSync } from "node:fs";
import { chromium } from "playwright-core";

const input = JSON.parse(readFileSync(process.argv[2], "utf-8"));

async function launch() {
  const tries = input.browser ? [{ executablePath: input.browser }, { channel: "chrome" }] : [{ channel: "chrome" }, { channel: "msedge" }];
  let last;
  for (const options of tries) {
    try { return await chromium.launch({ headless: true, ...options }); } catch (error) { last = error; }
  }
  throw last;
}

// Inside the page: what the style is made of.
function read() {
  const rgb = (value) => {
    const m = String(value).match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const [r, g, b, a = "1"] = m[1].split(/[ ,/]+/).filter(Boolean);
    if (Number(a) < 0.5) return null;
    return "#" + [r, g, b].map((n) => Math.round(Number(n)).toString(16).padStart(2, "0")).join("").toUpperCase();
  };
  const vars = {};
  const sources = [];
  for (const sheet of document.styleSheets) {
    let rules;
    try { rules = sheet.cssRules; } catch { continue; }
    for (const rule of rules || []) {
      if (rule.selectorText && /(^|,)\s*(:root|html)\s*(,|$)/.test(rule.selectorText)) {
        for (const name of rule.style) if (name.startsWith("--")) vars[name] = "";
      }
      if (rule.type === CSSRule.FONT_FACE_RULE) {
        sources.push({ family: rule.style.getPropertyValue("font-family").replace(/["']/g, "").trim(),
          weight: rule.style.getPropertyValue("font-weight"), src: rule.style.getPropertyValue("src").slice(0, 300) });
      }
    }
  }
  const root = getComputedStyle(document.documentElement);
  for (const name of Object.keys(vars)) vars[name] = root.getPropertyValue(name).trim();
  const look = (el) => {
    if (!el) return null;
    const s = getComputedStyle(el);
    return { tag: el.tagName.toLowerCase(), text: (el.innerText || "").trim().slice(0, 40), color: rgb(s.color), background: rgb(s.backgroundColor),
      font: s.fontFamily, weight: s.fontWeight, size: s.fontSize, radius: s.borderRadius, border: `${s.borderTopWidth} ${rgb(s.borderTopColor) || ""}`.trim(),
      shadow: s.boxShadow };
  };
  const pick = (selectors) => { for (const sel of selectors) { const el = document.querySelector(sel); if (el && el.offsetWidth) return el; } return null; };
  const elements = {
    body: look(document.body), h1: look(pick(["h1"])), h2: look(pick(["h2"])), h3: look(pick(["h3"])), paragraph: look(pick(["main p", "p"])),
    link: look(pick(["main a[href]", "p a[href]", "a[href]"])),
    button: look(pick(["button:not([aria-hidden])", "a[class*=button]", "a[class*=btn]", "[role=button]", "input[type=submit]"])),
    card: look(pick(["[class*=card]", "article", "[class*=panel]"])),
  };
  const area = {}, ink = {};
  const viewport = innerWidth * innerHeight;
  for (const el of document.querySelectorAll("body *")) {
    const box = el.getBoundingClientRect();
    if (!box.width || !box.height || box.bottom < 0 || box.top > innerHeight * 3 || el.closest("img,svg,video,picture,iframe,canvas")) continue;
    const s = getComputedStyle(el);
    if (s.visibility === "hidden" || Number(s.opacity) < 0.3) continue;
    const bg = rgb(s.backgroundColor);
    if (bg) area[bg] = (area[bg] || 0) + Math.min(box.width * box.height, viewport);
    const own = [...el.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent.trim()).join("");
    const color = rgb(s.color);
    if (own && color) ink[color] = (ink[color] || 0) + own.length;
  }
  const top = (map) => Object.entries(map).sort((a, b) => b[1] - a[1]).slice(0, 14).map(([color, n]) => ({ color, n: Math.round(n) }));
  const fonts = [...document.fonts].map((f) => ({ family: f.family.replace(/["']/g, ""), weight: f.weight, style: f.style, status: f.status }));
  const google = [...document.querySelectorAll("link[href*='fonts.googleapis.com']")].map((l) => l.href);
  const logos = [];
  for (const l of document.querySelectorAll("link[rel*=icon]")) logos.push({ kind: "icon", src: l.href });
  const og = document.querySelector("meta[property='og:image']");
  if (og) logos.push({ kind: "og:image", src: og.content });
  // the logo of the site is in its header or its navigation; other images named "logo" are often the logos of its clients
  for (const img of document.querySelectorAll("header img, nav img, header [class*=logo] img")) logos.push({ kind: "img", src: img.src });
  const svg = document.querySelector("header a[href='/'] svg, header svg, nav svg");
  if (svg && svg.outerHTML.length < 60000) logos.push({ kind: "svg", markup: svg.outerHTML });
  return { title: document.title, vars, elements, background: top(area), text: top(ink), fonts, sources, google, logos: logos.slice(0, 12) };
}

async function dismiss(page) {
  const words = [/rechaz|reject|decline|solo (las )?necesarias|only necessary|necessary only/i, /acept|accept|agree|entendido|got it|ok\b/i];
  for (const word of words) {
    const button = page.getByRole("button", { name: word }).first();
    try { if (await button.isVisible({ timeout: 500 })) { await button.click({ timeout: 2000 }); await page.waitForTimeout(600); return; } } catch { /* none */ }
  }
}

const browser = await launch();
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: input.locale || "es-ES" });
  const page = await context.newPage();
  await page.goto(input.url, { waitUntil: "networkidle", timeout: 60000 }).catch(() => page.waitForTimeout(3000));
  await dismiss(page);
  await page.evaluate(() => document.fonts.ready);
  const seen = await page.evaluate(read);
  await page.screenshot({ path: input.light, fullPage: false });
  const light = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  await page.emulateMedia({ colorScheme: "dark" });
  await page.waitForTimeout(500);
  const dark = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  let darkShot = null;
  if (dark !== light && input.dark) { await page.screenshot({ path: input.dark }); darkShot = input.dark; }
  console.log(JSON.stringify({ ok: true, url: page.url(), dark: darkShot, ...seen }));
} catch (error) {
  console.log(JSON.stringify({ ok: false, error: String(error && error.message || error).slice(0, 400) }));
} finally {
  await browser.close();
}
