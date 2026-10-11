// The player of a unit: lesson navigation, the components and the tracking. Everything it needs is in the page
// (`#ck-config`: the standard, the lessons and the texts of the interface).
import { initQuestion } from "./questions.js";
import { createTracker } from "./scorm.js";
import { initSimulations, updateAdaptive } from "./simulation.js";
import { initWidgets } from "./widgets.js";

const config = JSON.parse(document.getElementById("ck-config").textContent);
const ui = config.ui;
const lessons = Array.from(document.querySelectorAll(".ck-lesson"));
const links = Array.from(document.querySelectorAll(".ck-nav a"));
const previous = document.querySelector("[data-prev]");
const next = document.querySelector("[data-next]");
const bar = document.querySelector(".ck-progress");
const tracker = createTracker(config);
const saved = tracker.restore();
let current = 0;

document.body.classList.add("ck-js");
initWidgets(document, ui);
const simulations = initSimulations(document, ui, tracker);
const adapt = () => updateAdaptive(document, tracker);
simulations.forEach((sim) => sim.onChange(adapt));

function format(text, values) {
  return Object.entries(values).reduce((out, [key, val]) => out.replace(`{${key}}`, val), text);
}

function updateProgress() {
  const done = tracker.state.visited.length;
  const percent = Math.round((100 * done) / lessons.length);
  if (bar) {
    bar.setAttribute("aria-valuenow", String(percent));
    bar.querySelector("span").style.width = `${percent}%`;
  }
}

function show(index, focus) {
  current = Math.max(0, Math.min(lessons.length - 1, index));
  lessons.forEach((lesson, i) => {
    lesson.hidden = i !== current;
  });
  links.forEach((link, i) => {
    if (i === current) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
    link.parentNode.classList.toggle("is-visited", tracker.state.visited.includes(i) || i === current);
  });
  previous.disabled = current === 0;
  next.disabled = current === lessons.length - 1;
  tracker.visit(current, lessons[current].dataset.lesson);
  adapt();
  updateProgress();
  window.scrollTo(0, 0);
  if (focus) lessons[current].querySelector(".ck-lesson-title").focus();
}

previous.addEventListener("click", () => show(current - 1, true));
next.addEventListener("click", () => show(current + 1, true));
links.forEach((link, i) => link.addEventListener("click", (event) => {
  event.preventDefault();
  show(i, true);
}));

// Questions: every one is enhanced; the lesson of a test grades them together, with its scored simulations (each one weighs
// `weight` questions and counts with its grade).
const inLesson = (lesson) => simulations.filter((sim) => sim.scored && lesson.contains(document.querySelector(`.ck-sim[data-sim="${sim.id}"]`)));
const hasTest = lessons.some((lesson) => lesson.dataset.type === "evaluation");
lessons.forEach((lesson) => {
  const questions = Array.from(lesson.querySelectorAll(".ck-q")).map((q) => initQuestion(q, ui)).filter(Boolean);
  if (lesson.dataset.type !== "evaluation") return;
  const scoredSims = inLesson(lesson);
  const quiz = JSON.parse(lesson.dataset.quiz || "{}");
  const actions = lesson.querySelector(".ck-quiz-actions");
  const report = document.createElement("p");
  report.className = "ck-quiz-report";
  report.setAttribute("role", "status");
  const submit = document.createElement("button");
  submit.type = "button";
  submit.className = "ck-btn ck-btn-primary";
  submit.textContent = ui.submit;
  const again = document.createElement("button");
  again.type = "button";
  again.className = "ck-btn";
  again.textContent = ui.retry;
  again.hidden = true;
  actions.append(submit, again, report);

  const left = () => (quiz.maxAttempts ? Math.max(0, quiz.maxAttempts - tracker.state.attempts) : null);
  const status = (score, passed) => {
    const parts = [format(ui.score, { score }), passed ? ui.passed : format(ui.failed, { min: quiz.passingGrade ?? 0 })];
    if (!passed) parts.push(left() === 0 ? ui.no_attempts : left() === null ? "" : format(ui.attempts, { n: left() }));
    report.textContent = parts.filter(Boolean).join(" ");
  };

  submit.addEventListener("click", () => {
    if (!questions.every((item) => item.answered())) {
      report.textContent = ui.answer_all;
      return;
    }
    if (!scoredSims.every((sim) => sim.finished())) {
      report.textContent = ui.sim_finish_first;
      return;
    }
    const results = questions.map((item) => ({ item, ok: item.grade() }));
    const weights = scoredSims.reduce((sum, sim) => sum + sim.weight, 0);
    const earned = results.filter((r) => r.ok).length + scoredSims.reduce((sum, sim) => sum + (sim.weight * sim.grade()) / 100, 0);
    const score = Math.round((100 * earned) / Math.max(1, results.length + weights));
    const passed = score >= (quiz.passingGrade ?? 0);
    const interactions = results.map((r, i) => ({
      id: r.item.q.dataset.id,
      type: ["single", "multi"].includes(r.item.q.dataset.type) ? "choice" : "fill-in",
      learnerResponse: r.item.response().slice(0, 250),
      result: r.ok ? "correct" : "incorrect",
      weighting: 1,
    }));
    tracker.quiz({ score, passed, interactions });
    submit.disabled = true;
    status(score, passed);
    again.hidden = passed || left() === 0;
  });
  again.addEventListener("click", () => {
    questions.forEach((item) => item.reset());
    scoredSims.forEach((sim) => sim.reset());
    submit.disabled = false;
    again.hidden = true;
    report.textContent = "";
  });
  if (tracker.state.best !== null) {
    const passed = tracker.state.best >= (quiz.passingGrade ?? 0);
    status(tracker.state.best, passed);
    if (passed || left() === 0) submit.disabled = true;
  }
});

// A unit without a test whose content has scored simulations: its score is theirs, once every one has ended.
const formative = simulations.filter((sim) => sim.scored);
if (!hasTest && formative.length) {
  const total = formative.reduce((sum, sim) => sum + sim.weight, 0);
  const report = () => {
    if (!formative.every((sim) => sim.finished())) return;
    tracker.score(Math.round(formative.reduce((sum, sim) => sum + sim.weight * sim.grade(), 0) / total));
  };
  formative.forEach((sim) => sim.onChange(report));
}

window.addEventListener("pagehide", () => tracker.finish());
window.addEventListener("beforeunload", () => tracker.finish());

const start = lessons.findIndex((lesson) => lesson.dataset.lesson === saved.location);
show(start >= 0 ? start : 0, false);
