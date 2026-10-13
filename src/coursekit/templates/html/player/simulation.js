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

// The part of a screen a hotspot points at; a heading cannot be a button, so its text is wrapped in one.
function targetOf(node) {
  if (!node || !/^H[1-6]$/.test(node.tagName)) return node;
  const inner = el("span", { class: "ck-sim-target-text" });
  inner.append(...node.childNodes);
  node.appendChild(inner);
  return inner;
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

  // `attempt`: each start from the beginning is a new one (it numbers the interactions: `<id>-<attempt>-<n>`)
  const fresh = (attempt = 1) => ({ at: start, env: { ...(data.state || {}) }, score: 0, path: [], done: false, ending: null,
    checkpoints: [], transcript: [], feed: [], fed: [], attempt, decisions: 0 });
  const saved = tracker.simulation(data.id);  // only where it was, the state, the points and whether it ended
  let run = saved && scenes[saved.at] ? { ...fresh(), ...saved } : null;
  const persist = () => {
    tracker.simulation(data.id, run);
    listeners.forEach((fn) => fn());
  };
  const grade = () => (data.max_score > 0 ? Math.max(0, Math.min(100, Math.round((100 * run.score) / data.max_score))) : 0);

  // `attrs`: the marks a checker plays by (`data-ck-decision`, `data-ck-continue`, `data-ck-restart`)
  function button(label, onClick, extra = "", attrs = {}) {
    const node = el("button", { type: "button", class: `ck-btn ${extra}`.trim(), ...attrs }, label);
    node.addEventListener("click", onClick);
    return node;
  }

  // `index`: the place of the decision among the scene's choices and hotspots (a, b, c… in the tracking)
  function decide(decision, label, index) {
    const before = run.score;
    Object.entries(decision.effects || {}).forEach(([key, value]) => {
      run.env[key] = (run.env[key] || 0) + value;
    });
    Object.assign(run.env, decision.set || {});
    run.score += Number(decision.score || 0);
    run.path.push(strip(label));
    if (data.kind === "conversation") run.transcript.push({ me: true, html: label });
    const points = run.score - before;
    run.decisions = (run.decisions || 0) + 1;  // kept on resuming and going back: an interaction id is never repeated
    tracker.interaction({
      id: `${data.id}-${run.attempt || 1}-${run.decisions}`,
      attempt: run.attempt || 1,
      n: run.decisions,
      type: "choice",
      choice: index,
      description: strip(label).slice(0, 250),
      result: points > 0 ? "correct" : points < 0 ? "incorrect" : "neutral",
      weighting: Math.abs(points) || 1,
    });
    if (decision.feedback) {
      choices.replaceChildren();
      stage.querySelectorAll(".ck-sim-hotspot").forEach((node) => node.remove());
      feedback.innerHTML = decision.feedback;
      choices.appendChild(button(ui.continue, () => go(decision.goto), "ck-btn-primary", { "data-ck-continue": "feedback" }));
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
  let staged = new Set();  // the characters drawn inside the scene
  // where a scene happens: its own skin; else its background (a place); else the skin of the simulation (a screen)
  const skinOf = (scene) => scene.skin || (scene.background ? null : data.skin);

  // In a chat (team chat, messaging, text messages) the messages of each scene the learner goes through add up, as in
  // the real application; any other screen shows what its scene says.
  function feedScene(scene) {
    const key = `${run.at}:${run.path.length}`;
    if (!CHAT_SKINS.includes(skinOf(scene)) || !(scene.screen && scene.screen.messages) || run.fed.includes(key)) return;
    run.fed.push(key);
    run.feed = run.feed.concat(scene.screen.messages.map((m) => ({ ...m, skin: skinOf(scene) })));
  }

  function drawStage(scene) {
    stage.replaceChildren();
    stage.classList.remove("is-empty", "is-skin");
    const skin = skinOf(scene);
    if (skin) {
      // the simulation's screen belongs to its own skin; a scene in another application shows only its own screen
      const base = skin === data.skin ? (data.screen || {}) : {};
      const screen = { ...base, ...(scene.screen || {}) };
      if (CHAT_SKINS.includes(skin)) {
        screen.messages = (base.messages || []).concat(run.feed.filter((m) => m.skin === skin));
      }
      const lines = chatSkin ? run.transcript.map((line) => ({ me: line.me === true, from: line.me ? "" : data.character,
        text: line.html, target: false })) : [];
      const node = drawSkin(skin, screen, ui, skin === data.skin ? lines : []);
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
    // On a background, the characters with a portrait stand in the scene (first on the right, then on the left)
    staged = new Set();
    if (!background) return;
    actors(scene).filter((actor) => actor.portrait).slice(0, 3).forEach((actor, i) => {
      const side = actor.position || (i === 0 ? "right" : "left");
      const figure = el("figure", { class: `ck-sim-actor is-${side}` });
      figure.appendChild(el("img", { src: actor.portrait.path, alt: actor.portrait.alt || actor.name }));
      figure.appendChild(el("figcaption", {}, actor.name));
      stage.appendChild(figure);
      staged.add(actor.name);
    });
  }

  function actors(scene) {
    const list = [];
    if (data.kind === "conversation" && data.character && !chatSkin) {
      list.push({ name: data.character, portrait: scene._portrait || data._portrait });
    }
    (scene.characters || []).forEach((person) => list.push({ name: person.name, portrait: person._portrait, position: person.position }));
    return list;
  }

  function drawPeople(scene) {
    people.replaceChildren();
    actors(scene).filter((actor) => !staged.has(actor.name))
      .forEach((actor) => people.appendChild(portraitFigure(actor.portrait, actor.name)));
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
      run = fresh((run.attempt || 1) + 1);
      persist();
      render(true);
    }, "", { "data-ck-restart": "" }));
    end.appendChild(actions);
  }

  function render(focus) {
    const scene = scenes[run.at];
    if (!scene) return;
    feedback.textContent = "";
    hint.hidden = true;
    choices.replaceChildren();
    end.replaceChildren();
    feedScene(scene);
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
      const snap = { at: run.at, env: { ...run.env }, score: run.score, path: run.path.slice(), transcript: run.transcript.slice(),
        feed: run.feed.slice(), fed: run.fed.slice() };
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
      choices.appendChild(button(ui.continue, () => go(step.goto), "ck-btn-primary", { "data-ck-continue": "next" }));
    } else {
      const offset = (scene.choices || []).length;
      (scene.choices || []).forEach((d, i) => {
        if (!test(d.if, run.env)) return;
        choices.appendChild(button(d.text, () => decide(d, d.text, i), "ck-sim-choice", { "data-ck-decision": i }));
      });
      (scene.hotspots || []).forEach((d, j) => {
        if (!test(d.if, run.env)) return;
        const index = offset + j;
        const part = d.target ? targetOf(stage.querySelector(`[data-target="${d.target}"]`)) : null;
        if (part || (scene._background && !d.target)) {
          hint.textContent = ui.sim_hint;
          hint.hidden = false;
        }
        if (part) {
          part.classList.add("ck-sim-target");
          part.setAttribute("role", "button");
          part.setAttribute("tabindex", "0");
          // what the part shows stays its name (as the learner reads it); the decision is its description
          if (part.textContent.trim()) {
            const note = el("span", { class: "ck-visually-hidden", id: `${data.id}-d${index}` }, "");
            note.textContent = strip(d.label);
            stage.appendChild(note);
            part.setAttribute("aria-describedby", note.id);
          } else {
            part.setAttribute("aria-label", strip(d.label));
          }
          part.setAttribute("data-ck-decision", String(index));
          part.addEventListener("click", () => decide(d, d.label, index));
          part.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              decide(d, d.label, index);
            }
          });
        } else if (scene._background && !d.target) {
          const spot = el("button", { type: "button", class: "ck-sim-hotspot", "aria-label": strip(d.label), "data-ck-decision": index });
          area(spot, d.area);
          spot.addEventListener("click", () => decide(d, d.label, index));
          stage.appendChild(spot);
        } else {
          choices.appendChild(button(d.label, () => decide(d, d.label, index), "ck-sim-choice", { "data-ck-decision": index }));
        }
      });
    }
    persist();
    if (focus) (data.kind === "conversation" ? (log.lastElementChild || choices) : text).focus?.();
  }

  if (!run) run = fresh();
  run.feed = run.feed || [];
  run.fed = run.fed || [];
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
      run = fresh((run.attempt || 1) + 1);
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
