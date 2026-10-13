// The simulations of decision-based courses (:::scenario, :::conversation): scenes with background, layers and characters,
// decisions by choices or by areas of the scene, state, delayed consequences, endings with debriefing, points, and the way
// back to a checkpoint. The data come in the page (`.ck-sim-data`, from coursekit/htmlkit/render.py); the state of every
// simulation is kept by the tracker, so the adaptive blocks can read it and a learner who comes back finds it.
import { test } from "./expr.js";
import { drawSkin, isChat } from "./skins.js";

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
  const voice = el("div", { class: "ck-sim-voice" });  // the narration of the scene (`audio: true`): never plays by itself
  const mechanics = el("div", { class: "ck-sim-mechanics" });  // symptoms, clues, an inbox or an allocation
  play.append(stage, people, voice, log, text, mechanics, hint, feedback, choices, end);
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

  const chatSkin = data.kind === "conversation" && isChat(data.skin);
  let staged = new Set();  // the characters drawn inside the scene
  // where a scene happens: its own skin; else its background (a place); else the skin of the simulation (a screen)
  const skinOf = (scene) => scene.skin || (scene.background ? null : data.skin);

  // In a chat (team chat, messaging, text messages) the messages of each scene the learner goes through add up, as in
  // the real application; any other screen shows what its scene says.
  function feedScene(scene) {
    const key = `${run.at}:${run.path.length}`;
    if (!isChat(skinOf(scene)) || !(scene.screen && scene.screen.messages) || run.fed.includes(key)) return;
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
      if (isChat(skin)) {
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
    voice.replaceChildren();
    voice.hidden = !(scene._audio && scene._audio.path);
    if (!voice.hidden) {
      voice.appendChild(el("audio", { controls: true, preload: "none", src: scene._audio.path, "aria-label": ui.sim_listen }));
    }
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
    drawMechanics(scene);
    const task = scene.inbox ? ["inbox", scene.inbox] : scene.allocation ? ["allocation", scene.allocation] : null;
    if (task) {
      drawTask(scene, task[0], task[1]);
    } else if (scene.next) {
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
    gateByClues(scene);
    persist();
    if (focus) (data.kind === "conversation" ? (log.lastElementChild || choices) : text).focus?.();
  }

  // Diagnosis: the symptoms, listed. Investigation: clues the learner opens; the decisions wait for `min_clues` of them.
  let opened = new Set();
  function drawMechanics(scene) {
    mechanics.replaceChildren();
    opened = new Set();
    if (Array.isArray(scene.symptoms) && scene.symptoms.length) {
      mechanics.appendChild(el("p", { class: "ck-sim-mech-title" }, ui.sim_symptoms));
      const list = el("ul", { class: "ck-sim-symptoms" });
      scene.symptoms.forEach((item) => list.appendChild(el("li", {}, item)));
      mechanics.appendChild(list);
    }
    if (Array.isArray(scene.clues) && scene.clues.length) {
      mechanics.appendChild(el("p", { class: "ck-sim-mech-title" }, ui.sim_clues));
      scene.clues.forEach((clue, i) => {
        const box = el("details", { class: "ck-sim-clue", "data-ck-clue": i });
        box.append(el("summary", {}, clue.label), el("div", { class: "ck-sim-clue-text" }, clue.text));
        box.addEventListener("toggle", () => {
          if (box.open) opened.add(i);
          gateByClues(scene);
        });
        mechanics.appendChild(box);
      });
    }
    mechanics.hidden = !mechanics.children.length;
  }

  function gateByClues(scene) {
    if (!Array.isArray(scene.clues) || !scene.clues.length || scene.ending) return;
    const need = scene.min_clues || scene.clues.length;
    const waiting = opened.size < need;
    choices.hidden = waiting;
    stage.querySelectorAll(".ck-sim-target, .ck-sim-hotspot").forEach((node) => { node.hidden = waiting; });
    hint.hidden = !waiting;
    if (waiting) hint.textContent = format(ui.sim_open_clues, { n: need - opened.size });
  }

  // A task: sort the items of an inbox into their categories, or share a total among options. `k` right sets `store`,
  // adds k × points, and the scene goes on by its `next`.
  function drawTask(scene, kind, body) {
    const points = body.points === undefined ? 1 : Number(body.points);
    const form = el("div", { class: `ck-sim-task ck-sim-${kind}` });
    const confirm = button(ui.sim_confirm, () => {}, "ck-btn-primary", { "data-ck-task": "" });
    let size = 0;
    let right = () => 0;
    let lock = () => {};
    if (kind === "inbox") {
      const items = body.items || [];
      size = items.length;
      const rows = items.map((item, i) => {
        const set = el("fieldset", { class: "ck-sim-item", "data-ck-item": i, "data-ck-answer": item.answer });
        set.appendChild(el("legend", {}, item.text));
        (body.categories || []).forEach((category) => {
          const label = el("label", { class: "ck-sim-category" });
          const input = el("input", { type: "radio", name: `${data.id}-${run.path.length}-${i}`, value: category });
          input.addEventListener("change", () => { confirm.disabled = rows.some((row) => !row.querySelector("input:checked")); });
          label.append(input, document.createTextNode(` ${category}`));
          set.appendChild(label);
        });
        form.appendChild(set);
        return set;
      });
      confirm.disabled = true;
      right = () => rows.filter((row, i) => (row.querySelector("input:checked") || {}).value === items[i].answer).length;
      lock = () => rows.forEach((row, i) => {
        row.querySelectorAll("input").forEach((input) => { input.disabled = true; });
        row.classList.add((row.querySelector("input:checked") || {}).value === items[i].answer ? "is-right" : "is-wrong");
      });
    } else {
      const options = body.options || [];
      const total = Number(body.total) || 0;
      size = options.length;
      const left = el("p", { class: "ck-sim-left", "aria-live": "polite" });
      const inputs = options.map((option, i) => {
        const label = el("label", { class: "ck-sim-option" });
        const input = el("input", { type: "number", min: 0, max: total, step: 1, value: 0, inputmode: "numeric",
          "data-ck-option": i, "data-ck-min": option.target[0] });
        label.append(el("span", {}, option.label), input);
        form.appendChild(label);
        return input;
      });
      const used = () => inputs.reduce((sum, input) => sum + Math.max(0, Math.floor(Number(input.value) || 0)), 0);
      const update = () => {
        left.textContent = format(ui.sim_left, { left: total - used(), total });
        confirm.disabled = used() > total;
      };
      inputs.forEach((input) => input.addEventListener("input", update));
      form.appendChild(left);
      update();
      right = () => options.filter((option, i) => {
        const value = Math.floor(Number(inputs[i].value) || 0);
        return value >= option.target[0] && value <= option.target[1];
      }).length;
      lock = () => inputs.forEach((input, i) => {
        input.disabled = true;
        const value = Math.floor(Number(input.value) || 0);
        input.closest("label").classList.add(value >= options[i].target[0] && value <= options[i].target[1] ? "is-right" : "is-wrong");
      });
    }
    confirm.addEventListener("click", () => {
      const k = right();
      lock();
      run.env[body.store] = k;
      run.score += k * points;
      run.path.push(format(ui.sim_task_result, { k, n: size }));
      run.decisions = (run.decisions || 0) + 1;
      tracker.interaction({
        id: `${data.id}-${run.attempt || 1}-${run.decisions}`, attempt: run.attempt || 1, n: run.decisions, type: "choice",
        choice: k, description: strip(scene.text).slice(0, 250),
        result: k === size ? "correct" : k === 0 ? "incorrect" : "neutral", weighting: Math.abs(size * points) || 1,
      });
      const step = scene.next.find((s) => test(s.if, run.env));
      confirm.remove();
      feedback.textContent = format(ui.sim_task_result, { k, n: size });
      choices.replaceChildren(button(ui.continue, () => go(step.goto), "ck-btn-primary", { "data-ck-continue": "feedback" }));
      run.at = step.goto;
      persist();
    });
    mechanics.hidden = false;
    mechanics.appendChild(form);
    choices.appendChild(confirm);
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

// Adaptive blocks: the first branch whose condition holds (`:::if`, then each `:::elif`), once the simulations it reads
// have ended; else the neutral one (`:::else`). A condition reads the variables of a simulation and its result: grade,
// score, maxScore, ending (the id of its ending scene) and kind (good, mixed or bad).
const simData = {};
function dataOf(root, id) {
  if (!(id in simData)) {
    const node = root.querySelector(`.ck-sim[data-sim="${id}"] .ck-sim-data`);
    try {
      simData[id] = node ? JSON.parse(node.textContent) : null;
    } catch (error) {
      simData[id] = null;
    }
  }
  return simData[id];
}

export function updateAdaptive(root, tracker) {
  const env = {};
  Object.entries(tracker.state.sims || {}).forEach(([id, run]) => {
    if (!run || !run.done) return;  // only a simulation that reached an ending says what the learner decided
    Object.entries(run.env || {}).forEach(([key, value]) => {
      env[`${id}.${key}`] = value;
    });
    const data = dataOf(root, id) || {};
    const ending = run.ending || run.at;
    const max = Number(data.max_score) || 0;
    Object.assign(env, {
      [`${id}.score`]: Number(run.score) || 0,
      [`${id}.maxScore`]: max,
      [`${id}.grade`]: max > 0 ? Math.max(0, Math.min(100, Math.round((100 * (Number(run.score) || 0)) / max))) : 0,
      [`${id}.ending`]: String(ending || ""),
      [`${id}.kind`]: String(((data.scenes || {})[ending] || {}).ending || ""),
    });
  });
  const holds = (condition) => {
    try {
      const played = condition.match(/[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*/g) || [];
      return played.every((name) => Object.prototype.hasOwnProperty.call(env, name)) && test(condition, env);
    } catch (error) {
      return false;
    }
  };
  root.querySelectorAll(".ck-adaptive").forEach((block) => {
    const branches = Array.from(block.querySelectorAll(":scope > .ck-if"));
    const shown = branches.findIndex((branch) => holds(branch.dataset.condition || ""));
    branches.forEach((branch, i) => { branch.hidden = i !== shown; });
    block.querySelector(":scope > .ck-else").hidden = shown >= 0;
  });
}
