// The simulations of decision-based courses (:::scenario, :::conversation): scenes with background, layers and characters,
// decisions by choices or by areas of the scene, state, delayed consequences, endings with debriefing, points, and the way
// back to a checkpoint. The data come in the page (`.ck-sim-data`, from coursekit/htmlkit/render.py); the state of every
// simulation is kept by the tracker, so the adaptive blocks can read it and a learner who comes back finds it.
import { test } from "./expr.js";
import { CHAT_SKINS, drawSkin } from "./skins.js";

const el = (tag, attrs = {}, html = "") => {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== false) node.setAttribute(key, val === true ? "" : String(val));
  });
  if (html) node.innerHTML = html;
  return node;
};

const format = (text, values) => Object.entries(values).reduce((out, [key, val]) => out.replace(`{${key}}`, val), text);
const strip = (html) => {
  const box = document.createElement("div");
  box.innerHTML = html || "";
  return (box.textContent || "").trim();
};

function area(node, box) {
  if (!Array.isArray(box)) return;
  node.style.left = `${box[0]}%`;
  node.style.top = `${box[1]}%`;
  if (box.length === 4) {
    node.style.width = `${box[2]}%`;
    node.style.height = `${box[3]}%`;
  } else {
    node.classList.add("is-point");
  }
}

function portraitFigure(person, name) {
  const figure = el("figure", { class: "ck-sim-person" });
  if (person && person.path) figure.appendChild(el("img", { src: person.path, alt: person.alt || name }));
  else figure.appendChild(el("span", { class: "ck-sim-initial", "aria-hidden": "true" }, (name || "?").slice(0, 1)));
  figure.appendChild(el("figcaption", {}, name));
  return figure;
}

function initSimulation(root, ui, tracker) {
  const data = JSON.parse(root.querySelector(".ck-sim-data").textContent);
  const scenes = data.scenes || {};
  const start = data.start || Object.keys(scenes)[0];
  const scored = data.scored === true;
  const listeners = [];
  const play = el("div", { class: "ck-sim-play" });
  const stage = el("div", { class: "ck-sim-stage" });
  const people = el("div", { class: "ck-sim-people" });
  const log = el("div", { class: "ck-sim-log" });
  const text = el("div", { class: "ck-sim-text", tabindex: "-1" });
  const hint = el("p", { class: "ck-sim-hint" });
  const feedback = el("div", { class: "ck-sim-feedback", "aria-live": "polite" });
  const choices = el("div", { class: "ck-sim-choices", role: "group", "aria-label": ui.sim_choices });
  const end = el("div", { class: "ck-sim-end" });
  play.append(stage, people, log, text, hint, feedback, choices, end);
  root.querySelector(".ck-sim-static").hidden = true;
  root.appendChild(play);

  const fresh = () => ({ at: start, env: { ...(data.state || {}) }, score: 0, path: [], done: false, ending: null,
    checkpoints: [], transcript: [] });
  const saved = tracker.simulation(data.id);  // only where it was, the state, the points and whether it ended
  let run = saved && scenes[saved.at] ? { ...fresh(), ...saved } : null;
  const persist = () => {
    tracker.simulation(data.id, run);
    listeners.forEach((fn) => fn());
  };
  const grade = () => (data.max_score > 0 ? Math.max(0, Math.min(100, Math.round((100 * run.score) / data.max_score))) : 0);

  function button(label, onClick, extra = "") {
    const node = el("button", { type: "button", class: `ck-btn ${extra}`.trim() }, label);
    node.addEventListener("click", onClick);
    return node;
  }

  function decide(decision, label) {
    const before = run.score;
    Object.entries(decision.effects || {}).forEach(([key, value]) => {
      run.env[key] = (run.env[key] || 0) + value;
    });
    Object.assign(run.env, decision.set || {});
    run.score += Number(decision.score || 0);
    run.path.push(strip(label));
    if (data.kind === "conversation") run.transcript.push({ me: true, html: label });
    const points = run.score - before;
    tracker.interaction({
      id: `${data.id}-${run.path.length}`,
      type: "choice",
      learnerResponse: strip(label).slice(0, 250),
      result: points > 0 ? "correct" : points < 0 ? "incorrect" : "neutral",
      weighting: Math.abs(points) || 1,
    });
    if (decision.feedback) {
      choices.replaceChildren();
      stage.querySelectorAll(".ck-sim-hotspot").forEach((node) => node.remove());
      feedback.innerHTML = decision.feedback;
      choices.appendChild(button(ui.continue, () => go(decision.goto), "ck-btn-primary"));
      choices.querySelector("button").focus();
      run.at = decision.goto;
      persist();
      return;
    }
    go(decision.goto);
  }

  function go(target) {
    run.at = target;
    persist();
    render(true);
  }

  const chatSkin = data.kind === "conversation" && CHAT_SKINS.includes(data.skin);

  function drawStage(scene) {
    stage.replaceChildren();
    stage.classList.remove("is-empty", "is-skin");
    if (data.skin) {
      const screen = { ...(data.screen || {}), ...(scene.screen || {}) };
      const lines = chatSkin ? run.transcript.map((line) => ({ me: line.me === true, from: line.me ? "" : data.character,
        text: line.html, target: false })) : [];
      const node = drawSkin(data.skin, screen, ui, lines);
      if (node) {
        stage.hidden = false;
        stage.classList.add("is-skin");
        stage.appendChild(node);
        const scroller = node.querySelector(".ck-ms-lines, .ck-cw-lines, .ck-ph-lines");
        if (scroller) scroller.scrollTop = scroller.scrollHeight;
        return;
      }
    }
    const background = scene._background;
    const layers = (scene.layers || []).filter((layer) => layer._image && test(layer.if, run.env));
    if (!background && !layers.length && !(scene.hotspots || []).length) {
      stage.hidden = true;
      return;
    }
    stage.hidden = false;
    if (background) stage.appendChild(el("img", { class: "ck-sim-bg", src: background.path, alt: background.alt || "" }));
    else stage.classList.add("is-empty");
    layers.forEach((layer) => {
      const node = el("img", { class: "ck-sim-layer", src: layer._image.path, alt: layer._image.alt || "" });
      if (layer.area) area(node, layer.area);
      else node.classList.add("is-full");
      stage.appendChild(node);
    });
  }

  function drawPeople(scene) {
    people.replaceChildren();
    if (data.kind === "conversation" && data.character && !chatSkin) {
      people.appendChild(portraitFigure(scene._portrait || data._portrait, data.character));
    }
    (scene.characters || []).forEach((person) => people.appendChild(portraitFigure(person._portrait, person.name)));
    people.hidden = !people.children.length;
  }

  function sceneText(scene) {
    return [scene.text || ""].concat((scene.variants || []).filter((v) => test(v.if, run.env)).map((v) => v.text)).join("");
  }

  function drawLog() {
    log.replaceChildren();
    log.hidden = data.kind !== "conversation" || chatSkin || !run.transcript.length;
    run.transcript.forEach((line) => log.appendChild(el("div", { class: line.me ? "ck-sim-msg is-me" : "ck-sim-msg" }, line.html)));
  }

  function drawEnd(scene) {
    end.replaceChildren();
    const kind = scene.ending;
    end.appendChild(el("p", { class: `ck-sim-ending is-${kind}` }, ui[`sim_ending_${kind}`] || kind));
    end.appendChild(el("h4", { class: "ck-sim-debrief-title" }, ui.sim_debriefing));
    end.appendChild(el("div", { class: "ck-sim-debrief" }, scene.debriefing || ""));
    if (run.path.length) {
      const list = el("ol", { class: "ck-sim-path", "aria-label": ui.sim_your_path });
      run.path.forEach((step) => list.appendChild(el("li", {}, "")).append(document.createTextNode(step)));
      end.append(el("p", { class: "ck-sim-path-title" }, ui.sim_your_path), list);
    }
    if (scored) end.appendChild(el("p", { class: "ck-sim-score" }, format(ui.sim_score, { score: grade() })));
    const actions = el("div", { class: "ck-sim-actions" });
    if (data.rewind && run.checkpoints.length) actions.appendChild(button(ui.sim_checkpoint, () => {
      const back = run.checkpoints[run.checkpoints.length - 1];
      run = { ...run, ...JSON.parse(JSON.stringify(back)), done: false, ending: null, checkpoints: run.checkpoints.slice(0, -1) };
      persist();
      render(true);
    }));
    actions.appendChild(button(ui.sim_restart, () => {
      run = fresh();
      persist();
      render(true);
    }));
    end.appendChild(actions);
  }

  function render(focus) {
    const scene = scenes[run.at];
    if (!scene) return;
    feedback.textContent = "";
    hint.hidden = true;
    choices.replaceChildren();
    end.replaceChildren();
    drawStage(scene);
    drawPeople(scene);
    const body = sceneText(scene);
    if (data.kind === "conversation") {
      const last = run.transcript[run.transcript.length - 1];
      if (!last || last.scene !== run.at || last.me) run.transcript.push({ scene: run.at, html: body });
      drawStage(scene);
      drawLog();
      text.innerHTML = "";
      text.hidden = true;
    } else {
      text.hidden = false;
      text.innerHTML = body;
      log.hidden = true;
    }
    if (scene.checkpoint && !run.done) {
      const snap = { at: run.at, env: { ...run.env }, score: run.score, path: run.path.slice(), transcript: run.transcript.slice() };
      const top = run.checkpoints[run.checkpoints.length - 1];
      if (!top || top.at !== snap.at || top.path.length !== snap.path.length) run.checkpoints.push(snap);
    }
    if (scene.ending) {
      if (!run.done) {
        run.done = true;
        run.ending = run.at;
        persist();
      }
      drawEnd(scene);
      if (focus) (data.kind === "conversation" ? end : text).focus?.();
      return;
    }
    if (scene.next) {
      const step = scene.next.find((s) => test(s.if, run.env));
      choices.appendChild(button(ui.continue, () => go(step.goto), "ck-btn-primary"));
    } else {
      (scene.choices || []).filter((d) => test(d.if, run.env)).forEach((d) => {
        choices.appendChild(button(d.text, () => decide(d, d.text), "ck-sim-choice"));
      });
      (scene.hotspots || []).filter((d) => test(d.if, run.env)).forEach((d) => {
        const part = d.target ? stage.querySelector(`[data-target="${d.target}"]`) : null;
        if (part || (scene._background && !d.target)) {
          hint.textContent = ui.sim_hint;
          hint.hidden = false;
        }
        if (part) {
          part.classList.add("ck-sim-target");
          part.setAttribute("role", "button");
          part.setAttribute("tabindex", "0");
          part.setAttribute("aria-label", strip(d.label));
          part.addEventListener("click", () => decide(d, d.label));
          part.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              decide(d, d.label);
            }
          });
        } else if (scene._background && !d.target) {
          const spot = el("button", { type: "button", class: "ck-sim-hotspot", "aria-label": strip(d.label) });
          area(spot, d.area);
          spot.addEventListener("click", () => decide(d, d.label));
          stage.appendChild(spot);
        } else {
          choices.appendChild(button(d.label, () => decide(d, d.label), "ck-sim-choice"));
        }
      });
    }
    persist();
    if (focus) (data.kind === "conversation" ? (log.lastElementChild || choices) : text).focus?.();
  }

  if (!run) run = fresh();
  if (data.kind === "conversation" && !run.transcript) run.transcript = [];
  log.setAttribute("aria-live", "polite");
  log.setAttribute("tabindex", "-1");
  render(false);

  return {
    id: data.id,
    scored,
    weight: Number(data.weight || 1),
    finished: () => run.done,
    grade,
    onChange: (fn) => listeners.push(fn),
    reset: () => {
      run = fresh();
      persist();
      render(false);
    },
  };
}

export function initSimulations(root, ui, tracker) {
  return Array.from(root.querySelectorAll(".ck-sim")).map((node) => initSimulation(node, ui, tracker));
}

// Adaptive blocks: the `:::if` branch when the simulations it reads have ended and its condition holds, else the neutral one.
export function updateAdaptive(root, tracker) {
  const env = {};
  Object.entries(tracker.state.sims || {}).forEach(([id, run]) => {
    if (!run || !run.done) return;  // only a simulation that reached an ending says what the learner decided
    Object.entries(run.env || {}).forEach(([key, value]) => {
      env[`${id}.${key}`] = value;
    });
  });
  root.querySelectorAll(".ck-adaptive").forEach((block) => {
    let holds = false;
    try {
      const condition = block.dataset.condition;
      const played = condition.match(/[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*/g) || [];
      holds = played.every((name) => Object.prototype.hasOwnProperty.call(env, name)) && test(condition, env);
    } catch (error) {
      holds = false;
    }
    block.querySelector(".ck-if").hidden = !holds;
    block.querySelector(".ck-else").hidden = holds;
  });
}
