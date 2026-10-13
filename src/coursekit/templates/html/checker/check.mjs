// `coursekit assemble check`: plays one built unit inside the preview page (its strict simulated LMS) with a headless
// browser and writes what it saw as JSON. It only observes: what is right or wrong is decided by coursekit
// (htmlkit/playcheck.py), which sends the scenario (the paths to play) and compares.
//
//   node check.mjs scenario.json  →  stdout: {"ok": true, ...observations} or {"ok": false, "error": "..."}
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { chromium } from "playwright-core";

const require = createRequire(import.meta.url);
const scenario = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const out = { ok: true, console: [], failed: [], axe: [], lessons: [], tests: [], formative: null, paths: [], resume: null };
const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function launch() {
  const tries = [];
  if (scenario.browser) tries.push({ executablePath: scenario.browser });
  tries.push({ channel: "chrome" }, { channel: "msedge" }, {});
  const reasons = [];
  for (const options of tries) {
    try {
      return await chromium.launch({ headless: true, ...options });
    } catch (error) {
      reasons.push(String(error.message || error).split("\n")[0]);
    }
  }
  throw new Error(`no browser: ${reasons.join(" | ")}`);
}

// ── in the unit (run inside the frame) ───────────────────────────────────────────────────────

// Answers every question of a lesson with its right answer (the markup holds it).
function answerAll(key) {
  const lesson = document.querySelector(`.ck-lesson[data-lesson="${key}"]`);
  const questions = Array.from(lesson.querySelectorAll(".ck-q"));
  questions.forEach((q) => {
    const type = q.dataset.type;
    if (type === "single" || type === "multi") {
      q.querySelectorAll("input").forEach((input) => { input.checked = input.dataset.correct === "1"; });
    } else if (type === "sorting") {
      const list = q.querySelector(".ck-sort");
      Array.from(list.children).sort((x, y) => Number(x.dataset.i) - Number(y.dataset.i)).forEach((li) => list.appendChild(li));
    } else if (type === "match") {
      (q._pairs || []).forEach((pair) => { pair._select.value = String(pair._index); });
    } else if (type === "groups") {
      (q._rows || []).forEach((row) => { row._select.value = row.dataset.group; });
    } else if (type === "blanks") {
      q.querySelectorAll(".ck-blank").forEach((input) => { input.value = input.dataset.answers.split("|")[0]; });
    } else if (type === "short") {
      const input = q.querySelector(".ck-short");
      input.value = input.dataset.answers.split("|")[0];
    } else if (type === "order") {
      (q._lines || []).forEach((line) => {
        line.words.forEach((word) => {
          const chip = Array.from(line.pool.children).find((c) => c.textContent === word);
          if (chip) chip.click();
        });
      });
    }
  });
  return questions.length;
}

// Plays one path of a simulation from its start: `steps` are decision positions (null: the scene's "continue").
function playPath([id, steps]) {
  const root = document.querySelector(`.ck-sim[data-sim="${id}"]`);
  if (!root) return { missing: "simulation" };
  const restart = root.querySelector("[data-ck-restart]");
  if (restart) restart.click();
  const skipFeedback = () => {
    const button = root.querySelector('[data-ck-continue="feedback"]');
    if (button) button.click();
  };
  // a task: exactly k things right (the first k items or options), then confirm
  const task = (k) => {
    root.querySelectorAll("details.ck-sim-clue").forEach((box) => { box.open = true; });
    root.querySelectorAll("[data-ck-item]").forEach((set, i) => {
      const inputs = Array.from(set.querySelectorAll("input"));
      const pick = i < k ? inputs.find((input) => input.value === set.dataset.ckAnswer) : inputs.find((input) => input.value !== set.dataset.ckAnswer);
      if (pick) {
        pick.checked = true;
        pick.dispatchEvent(new Event("change"));
      }
    });
    root.querySelectorAll("[data-ck-option]").forEach((input, i) => {
      input.value = i < k ? input.dataset.ckMin : "0";
      input.dispatchEvent(new Event("input"));
    });
    return root.querySelector("[data-ck-task]");
  };
  // the clues of an investigation are opened before deciding
  const openClues = () => root.querySelectorAll("details.ck-sim-clue").forEach((box) => {
    if (!box.open) {
      box.open = true;
      box.dispatchEvent(new Event("toggle"));
    }
  });
  for (let i = 0; i < steps.length; i++) {
    skipFeedback();
    openClues();
    const step = steps[i];
    const target = step === null ? root.querySelector('[data-ck-continue="next"]')
      : typeof step === "object" ? task(step.task) : root.querySelector(`[data-ck-decision="${step}"]`);
    if (!target) return { missing: step === null ? "continue" : `decision ${step}`, step: i };
    target.click();
  }
  skipFeedback();
  return { missing: null };
}

function adaptive() {
  return Array.from(document.querySelectorAll(".ck-adaptive")).map((block) => ({
    condition: block.dataset.condition, shown: !block.querySelector(".ck-if").hidden,
  }));
}

function show(key) {
  const links = Array.from(document.querySelectorAll(".ck-nav a"));
  const lessons = Array.from(document.querySelectorAll(".ck-lesson"));
  const index = lessons.findIndex((lesson) => lesson.dataset.lesson === key);
  if (index >= 0) links[index].click();
  return index;
}

// ── the run ──────────────────────────────────────────────────────────────────────────────────

async function unitFrame(page) {
  for (let i = 0; i < 100; i++) {
    const frame = page.frames().find((f) => f.url().includes("/unit/"));
    if (frame) {
      try {
        if (await frame.evaluate(() => document.body && document.body.classList.contains("ck-js"))) return frame;
      } catch (error) { /* still loading */ }
    }
    await pause(100);
  }
  throw new Error("the unit did not start (no player in the page)");
}

const record = (page) => page.evaluate(() => ({ cmi: (window.ckPreview.record() || {}).cmi || {}, errors: window.ckPreview.errors,
  maxSuspend: window.ckPreview.maxSuspend() }));
const sims = (cmi) => {
  try {
    return JSON.parse(cmi["cmi.suspend_data"] || "{}").s || {};
  } catch (error) {
    return {};
  }
};

async function main() {
  const browser = await launch();
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    page.on("console", (message) => {
      if (message.type() === "error") out.console.push(message.text().slice(0, 300));
    });
    page.on("pageerror", (error) => out.console.push(String(error.message || error).slice(0, 300)));
    page.on("requestfailed", (request) => {
      const reason = request.failure()?.errorText || "failed";
      // audio and video stop loading once they have what they need (preload): not a failure
      if (request.resourceType() === "media" && reason.includes("ERR_ABORTED")) return;
      out.failed.push(`${request.url()} (${reason})`);
    });
    page.on("response", (response) => {
      if (response.status() >= 400) out.failed.push(`${response.url()} (${response.status()})`);
    });
    await page.goto(scenario.url);
    await page.evaluate(() => localStorage.clear());
    await page.goto(scenario.url);
    let frame = await unitFrame(page);
    const axeSource = readFileSync(require.resolve("axe-core/axe.min.js"), "utf-8");
    await frame.evaluate(axeSource);

    // each test answered right, after the best path of its scored simulations
    for (const test of scenario.tests) {
      await frame.evaluate(show, test.lesson);
      for (const sim of test.sims) out.paths.push({ sim: sim.id, n: -1, ...(await frame.evaluate(playPath, [sim.id, sim.steps])) });
      const questions = await frame.evaluate(answerAll, test.lesson);
      await frame.evaluate((key) => {
        const button = document.querySelector(`.ck-lesson[data-lesson="${key}"] .ck-quiz-actions .ck-btn-primary`);
        if (button && !button.hidden && !button.disabled) button.click();
      }, test.lesson);
      await pause(100);
      const { cmi } = await record(page);
      out.tests.push({ lesson: test.lesson, questions, score: cmi[scenario.keys.score] ?? null, status: cmi[scenario.keys.status] ?? null,
        success: scenario.keys.success ? cmi[scenario.keys.success] ?? null : null });
    }
    if (scenario.formative.length) {
      for (const sim of scenario.formative) {
        out.paths.push({ sim: sim.id, n: -1, ...(await frame.evaluate(playPath, [sim.id, sim.steps])) });
      }
      await pause(100);
      const { cmi } = await record(page);
      out.formative = { score: cmi[scenario.keys.score] ?? null };
    }

    // every path of every simulation
    for (const sim of scenario.sims) {
      for (let n = 0; n < sim.paths.length; n++) {
        const played = await frame.evaluate(playPath, [sim.id, sim.paths[n]]);
        const { cmi } = await record(page);
        out.paths.push({ sim: sim.id, n, ...played, run: sims(cmi)[sim.id] || null, sims: sims(cmi),
          adaptive: await frame.evaluate(adaptive) });
      }
    }

    // every lesson, as the learner sees it, through axe (last: the simulations that hold their lesson have ended)
    const keys = await frame.evaluate(() => Array.from(document.querySelectorAll(".ck-lesson")).map((l) => [l.dataset.lesson, l.dataset.type]));
    for (const [key, type] of keys) {
      await frame.evaluate(show, key);
      await pause(80);
      const result = await frame.evaluate(() => window.axe.run(document, { resultTypes: ["violations"] }));
      result.violations.forEach((v) => {
        const data = ((v.nodes[0] && v.nodes[0].any[0]) || {}).data || {};
        const detail = v.id === "color-contrast" && data.contrastRatio
          ? `${data.contrastRatio}:1, ${data.fgColor} / ${data.bgColor}, ${data.expectedContrastRatio}` : "";
        out.axe.push({ lesson: key, id: v.id, impact: v.impact, help: v.help, detail,
          targets: v.nodes.slice(0, 3).map((n) => n.target.join(" ")), count: v.nodes.length });
      });
      out.lessons.push({ key, type });
    }

    // out and back in: the unit resumes where it was
    const before = await record(page);
    out.lms = before.errors.slice();
    out.maxSuspend = before.maxSuspend;
    await page.click("#reopen");
    await pause(300);
    frame = await unitFrame(page);
    await pause(200);
    const after = await record(page);
    out.resume = { location: before.cmi[scenario.keys.location] ?? "", entry: after.cmi[scenario.keys.entry] ?? "",
      locationAfter: after.cmi[scenario.keys.location] ?? "", simsBefore: sims(before.cmi), simsAfter: sims(after.cmi) };
    out.lms = out.lms.concat(after.errors);
    out.maxSuspend = Math.max(out.maxSuspend, after.maxSuspend);
  } finally {
    await browser.close();
  }
}

main().then(() => process.stdout.write(JSON.stringify(out))).catch((error) => {
  process.stdout.write(JSON.stringify({ ok: false, error: String(error.message || error) }));
});
