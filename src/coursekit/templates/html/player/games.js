// The games of the html backend: word search, wordle, hangman, word wheel (pasapalabra), memory and trivia. Each is a
// `.ck-game` with its data (`.ck-game-data`, from htmlkit/render.py) and, without JavaScript, a list of what it is about.
// They are practice: nothing is graded nor sent to the LMS. Everything works with the keyboard and a screen reader (what
// happens is said in a live region), and the order of letters and cards depends only on the id of the game, so every
// learner and every check sees the same board.

const el = (tag, attrs = {}, text = "") => {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== false) node.setAttribute(key, val === true ? "" : String(val));
  });
  if (text) node.textContent = text;
  return node;
};
const html = (tag, attrs, inner) => {
  const node = el(tag, attrs);
  node.innerHTML = inner || "";
  return node;
};
const format = (text, values) => Object.entries(values).reduce((out, [key, val]) => out.split(`{${key}}`).join(val), text || "");

// A random sequence fixed by a text (the id of the game): the same board every time.
function seeded(text) {
  let h = 1779033703 ^ String(text).length;
  for (let i = 0; i < String(text).length; i++) {
    h = Math.imul(h ^ String(text).charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  return () => {
    h = Math.imul(h ^ (h >>> 16), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    h ^= h >>> 16;
    return (h >>> 0) / 4294967296;
  };
}
function shuffle(list, random) {
  const copy = list.slice();
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

// Letters as the games compare them: upper case, without accents (Ñ stays), only letters and digits.
const ACCENTS = { Á: "A", À: "A", Â: "A", Ä: "A", É: "E", È: "E", Ê: "E", Ë: "E", Í: "I", Ì: "I", Î: "I", Ï: "I", Ó: "O", Ò: "O",
  Ô: "O", Ö: "O", Ú: "U", Ù: "U", Û: "U", Ü: "U", Ç: "C" };
const plain = (text) => Array.from(String(text || "").toUpperCase()).map((c) => ACCENTS[c] || c)
  .filter((c) => /[A-Z0-9Ñ]/.test(c)).join("");

function live(root) {
  const region = el("p", { class: "ck-game-live", role: "status", "aria-live": "polite" });
  root.appendChild(region);
  return (text) => { region.textContent = text; };
}

// ── word search ────────────────────────────────────────────────────────────────────────────────

function wordSearch(root, data, ui) {
  const words = (data.items || []).map((i) => plain(i.word)).filter(Boolean);
  const random = seeded(root.dataset.id);
  const longest = Math.max(0, ...words.map((w) => w.length));
  const size = Math.min(14, Math.max(8, longest, Math.ceil(Math.sqrt(words.join("").length * 2))));
  const grid = Array.from({ length: size }, () => Array(size).fill(""));
  const directions = [[0, 1], [1, 0], [1, 1]];
  const placed = [];
  words.forEach((word) => {
    for (let tries = 0; tries < 200; tries++) {
      const [dr, dc] = directions[Math.floor(random() * directions.length)];
      const r0 = Math.floor(random() * (size - (dr ? word.length - 1 : 0)));
      const c0 = Math.floor(random() * (size - (dc ? word.length - 1 : 0)));
      const cells = Array.from(word, (_, k) => [r0 + dr * k, c0 + dc * k]);
      if (cells.every(([r, c], k) => !grid[r][c] || grid[r][c] === word[k])) {
        cells.forEach(([r, c], k) => { grid[r][c] = word[k]; });
        placed.push({ word, cells });
        return;
      }
    }
  });
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  grid.forEach((row) => row.forEach((cell, c) => { if (!cell) row[c] = alphabet[Math.floor(random() * alphabet.length)]; }));

  const say = live(root);
  const list = el("ul", { class: "ck-ws-words", "aria-label": ui.game_words });
  const items = placed.map(({ word }) => list.appendChild(el("li", {}, word)));
  const table = el("div", { class: "ck-ws-grid", role: "grid", "aria-label": ui.game_ws_grid });
  table.style.gridTemplateColumns = `repeat(${size}, 1fr)`;
  const buttons = [];
  grid.forEach((row, r) => {
    const line = el("div", { role: "row", class: "ck-ws-row" });
    row.forEach((letter, c) => {
      const cell = el("button", { type: "button", role: "gridcell", class: "ck-ws-cell", tabindex: r === 0 && c === 0 ? "0" : "-1",
        "aria-label": format(ui.game_ws_cell, { letter, row: r + 1, col: c + 1 }) }, letter);
      cell.dataset.r = r;
      cell.dataset.c = c;
      buttons.push(cell);
      line.appendChild(cell);
    });
    table.appendChild(line);
  });
  const at = (r, c) => buttons[r * size + c];
  let start = null;
  let found = 0;
  const choose = (cell) => {
    const r = Number(cell.dataset.r);
    const c = Number(cell.dataset.c);
    if (!start) {
      start = [r, c];
      cell.classList.add("is-start");
      cell.setAttribute("aria-pressed", "true");
      say(format(ui.game_ws_from, { letter: grid[r][c] }));
      return;
    }
    at(...start).classList.remove("is-start");
    at(...start).removeAttribute("aria-pressed");
    const hit = placed.find((p, i) => !items[i].classList.contains("is-found")
      && ((p.cells[0][0] === start[0] && p.cells[0][1] === start[1] && p.cells.at(-1)[0] === r && p.cells.at(-1)[1] === c)
        || (p.cells.at(-1)[0] === start[0] && p.cells.at(-1)[1] === start[1] && p.cells[0][0] === r && p.cells[0][1] === c)));
    start = null;
    if (!hit) {
      say(ui.game_ws_miss);
      return;
    }
    hit.cells.forEach(([rr, cc]) => at(rr, cc).classList.add("is-found"));
    items[placed.indexOf(hit)].classList.add("is-found");
    found += 1;
    say(found === placed.length ? ui.game_done : format(ui.game_ws_found, { word: hit.word, left: placed.length - found }));
  };
  buttons.forEach((cell) => {
    cell.addEventListener("click", () => choose(cell));
    cell.addEventListener("keydown", (event) => {
      const r = Number(cell.dataset.r);
      const c = Number(cell.dataset.c);
      const move = { ArrowRight: [r, Math.min(size - 1, c + 1)], ArrowLeft: [r, Math.max(0, c - 1)],
        ArrowDown: [Math.min(size - 1, r + 1), c], ArrowUp: [Math.max(0, r - 1), c] }[event.key];
      if (!move) return;
      event.preventDefault();
      cell.tabIndex = -1;
      const next = at(...move);
      next.tabIndex = 0;
      next.focus();
    });
  });
  root.append(el("p", { class: "ck-game-help" }, ui.game_ws_help), table, list);
}

// ── wordle and hangman: one word after another ────────────────────────────────────────────────

function wordByWord(root, data, ui, play) {
  const words = (data.items || []).map((i) => ({ shown: String(i.word || "").toUpperCase(), key: plain(i.word) })).filter((w) => w.key);
  const say = live(root);
  const stage = el("div", { class: "ck-game-stage" });
  const counter = el("p", { class: "ck-game-count" });
  const next = el("button", { type: "button", class: "ck-btn", hidden: true }, ui.game_next_word);
  root.append(counter, stage, next);
  let index = 0;
  const open = () => {
    counter.textContent = format(ui.game_word_of, { n: index + 1, total: words.length });
    stage.replaceChildren();
    next.hidden = true;
    play(stage, words[index], say, () => {
      if (index < words.length - 1) next.hidden = false;
      else say(ui.game_done);
    });
  };
  next.addEventListener("click", () => {
    index += 1;
    open();
    stage.querySelector("input, button")?.focus();
  });
  if (words.length) open();
}

function wordle(root, data, ui) {
  const TRIES = 6;
  wordByWord(root, data, ui, (stage, word, say, done) => {
    const board = el("ol", { class: "ck-wd-board", "aria-label": ui.game_wd_tries });
    const form = el("form", { class: "ck-wd-form" });
    const input = el("input", { type: "text", maxlength: word.key.length, autocomplete: "off", spellcheck: "false",
      "aria-label": format(ui.game_wd_input, { n: word.key.length }) });
    const send = el("button", { type: "submit", class: "ck-btn ck-btn-primary" }, ui.game_try);
    form.append(input, send);
    stage.append(el("p", { class: "ck-game-help" }, format(ui.game_wd_help, { n: word.key.length, tries: TRIES })), board, form);
    let tries = 0;
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const guess = plain(input.value);
      if (guess.length !== word.key.length) {
        say(format(ui.game_wd_length, { n: word.key.length }));
        return;
      }
      tries += 1;
      const left = Array.from(word.key);
      const marks = Array.from(guess, (c, i) => (c === word.key[i] ? "right" : null));
      marks.forEach((m, i) => { if (m) left[i] = null; });
      Array.from(guess).forEach((c, i) => {
        if (marks[i]) return;
        const k = left.indexOf(c);
        marks[i] = k >= 0 ? "present" : "absent";
        if (k >= 0) left[k] = null;
      });
      const row = el("li", { class: "ck-wd-row" });
      const spoken = Array.from(guess).map((c, i) => `${c} ${ui[`game_wd_${marks[i]}`]}`).join(", ");
      Array.from(guess).forEach((c, i) => row.appendChild(el("span", { class: `ck-wd-tile is-${marks[i]}`, "aria-hidden": "true" }, c)));
      row.appendChild(el("span", { class: "ck-visually-hidden" }, spoken));
      board.appendChild(row);
      input.value = "";
      if (guess === word.key || tries === TRIES) {
        input.disabled = send.disabled = true;
        say(guess === word.key ? format(ui.game_wd_won, { word: word.shown }) : format(ui.game_reveal, { word: word.shown }));
        done();
      } else {
        say(`${spoken}. ${format(ui.game_tries_left, { n: TRIES - tries })}`);
      }
    });
  });
}

function hangman(root, data, ui) {
  const MISSES = 6;
  const alphabet = Array.from("ABCDEFGHIJKLMNÑOPQRSTUVWXYZ");
  wordByWord(root, data, ui, (stage, word, say, done) => {
    const blanks = el("p", { class: "ck-hm-word", "aria-hidden": "true" });
    const spoken = el("p", { class: "ck-visually-hidden" });
    const misses = el("p", { class: "ck-hm-misses" });
    const keys = el("div", { class: "ck-hm-keys", role: "group", "aria-label": ui.game_letters });
    const figure = el("div", { class: "ck-hm-figure", "aria-hidden": "true" });
    stage.append(figure, blanks, spoken, misses, keys);
    const tried = new Set();
    let wrong = 0;
    const draw = () => {
      const shown = Array.from(word.key, (c) => (tried.has(c) ? c : "_"));
      blanks.textContent = shown.join(" ");
      spoken.textContent = format(ui.game_hm_word, { word: shown.map((c) => (c === "_" ? ui.game_blank : c)).join(", ") });
      misses.textContent = format(ui.game_hm_misses, { n: wrong, max: MISSES });
      figure.dataset.stage = String(wrong);
    };
    const pick = (letter, button) => {
      if (tried.has(letter) || stage.dataset.over) return;
      tried.add(letter);
      button.disabled = true;
      const inWord = word.key.includes(letter);
      if (!inWord) wrong += 1;
      button.classList.add(inWord ? "is-right" : "is-wrong");
      draw();
      const won = Array.from(word.key).every((c) => tried.has(c));
      if (won || wrong >= MISSES) {
        stage.dataset.over = "1";
        keys.querySelectorAll("button").forEach((b) => { b.disabled = true; });
        say(won ? format(ui.game_hm_won, { word: word.shown }) : format(ui.game_reveal, { word: word.shown }));
        done();
      } else {
        say(format(inWord ? ui.game_hm_yes : ui.game_hm_no, { letter }));
      }
    };
    alphabet.forEach((letter) => {
      const button = el("button", { type: "button", class: "ck-hm-key" }, letter);
      button.addEventListener("click", () => pick(letter, button));
      keys.appendChild(button);
    });
    draw();
  });
}

// ── word wheel (pasapalabra) ───────────────────────────────────────────────────────────────────

function pasapalabra(root, data, ui) {
  const items = (data.items || []).map((i) => ({ ...i, answers: String(i.answer || "").split("/").map(plain).filter(Boolean), state: "" }));
  const say = live(root);
  const wheel = el("ol", { class: "ck-pp-wheel", "aria-hidden": "true" });
  const letters = items.map((i) => wheel.appendChild(el("li", {}, i.letter)));
  const clue = html("p", { class: "ck-pp-clue" }, "");
  const form = el("form", { class: "ck-pp-form" });
  const input = el("input", { type: "text", autocomplete: "off", spellcheck: "false", "aria-label": ui.game_answer });
  const send = el("button", { type: "submit", class: "ck-btn ck-btn-primary" }, ui.game_answer);
  const pass = el("button", { type: "button", class: "ck-btn" }, ui.game_pp_pass);
  const score = el("p", { class: "ck-pp-score" });
  form.append(input, send, pass);
  root.append(wheel, clue, form, score);
  let current = 0;
  const pending = () => items.map((_, i) => i).filter((i) => !items[i].state);
  const show = () => {
    const right = items.filter((i) => i.state === "right").length;
    const wrongs = items.filter((i) => i.state === "wrong").length;
    score.textContent = format(ui.game_pp_score, { right, wrong: wrongs, left: pending().length });
    letters.forEach((li, i) => {
      li.className = `${items[i].state ? `is-${items[i].state}` : ""}${i === current ? " is-current" : ""}`.trim();
    });
    if (!pending().length) {
      clue.textContent = "";
      input.disabled = send.disabled = pass.disabled = true;
      say(format(ui.game_pp_over, { right, total: items.length }));
      return;
    }
    const item = items[current];
    clue.innerHTML = `<strong>${format(ui[item.mode === "contains" ? "game_pp_contains" : "game_pp_starts"], { letter: item.letter })}</strong> ${item.definition}`;
  };
  const advance = () => {
    const left = pending();
    if (!left.length) return;
    current = left.find((i) => i > current) ?? left[0];
  };
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!input.value.trim()) return;
    const item = items[current];
    const ok = item.answers.includes(plain(input.value));
    item.state = ok ? "right" : "wrong";
    say(ok ? ui.game_right : format(ui.game_pp_was, { word: String(item.answer).split("/")[0] }));
    input.value = "";
    advance();
    show();
    input.focus();
  });
  pass.addEventListener("click", () => {
    advance();
    show();
    input.focus();
  });
  show();
}

// ── memory ─────────────────────────────────────────────────────────────────────────────────────

function memory(root, data, ui) {
  const contents = (data.items || []).map((i) => i.content);
  const deck = shuffle(contents.flatMap((content, pair) => [{ content, pair }, { content, pair }]), seeded(root.dataset.id));
  const say = live(root);
  const board = el("div", { class: "ck-mm-board", role: "group", "aria-label": ui.game_cards });
  const status = el("p", { class: "ck-mm-status" });
  root.append(el("p", { class: "ck-game-help" }, ui.game_mm_help), board, status);
  let open = [];
  let moves = 0;
  let pairs = 0;
  const cards = deck.map((card, i) => {
    const button = el("button", { type: "button", class: "ck-mm-card", "aria-label": format(ui.game_mm_hidden, { n: i + 1 }) });
    const face = html("span", { class: "ck-mm-face", "aria-hidden": "true" }, card.content);
    button.appendChild(face);
    button.addEventListener("click", () => {
      if (button.classList.contains("is-open") || open.length === 2) return;
      button.classList.add("is-open");
      button.setAttribute("aria-label", format(ui.game_mm_shown, { n: i + 1, text: face.textContent }));
      open.push({ button, card });
      if (open.length < 2) return;
      moves += 1;
      const [a, b] = open;
      if (a.card.pair === b.card.pair) {
        a.button.classList.add("is-done");
        b.button.classList.add("is-done");
        a.button.disabled = b.button.disabled = true;
        open = [];
        pairs += 1;
        say(pairs === contents.length ? format(ui.game_mm_won, { moves }) : format(ui.game_mm_pair, { text: face.textContent }));
      } else {
        say(ui.game_mm_no);
        setTimeout(() => {
          open.forEach(({ button: b2 }, k) => {
            b2.classList.remove("is-open");
            b2.setAttribute("aria-label", format(ui.game_mm_hidden, { n: cards.indexOf(b2) + 1 }));
            return k;
          });
          open = [];
        }, 900);
      }
      status.textContent = format(ui.game_mm_status, { pairs, total: contents.length, moves });
    });
    board.appendChild(button);
    return button;
  });
  status.textContent = format(ui.game_mm_status, { pairs, total: contents.length, moves });
}

// ── trivia ─────────────────────────────────────────────────────────────────────────────────────

function trivial(root, data, ui) {
  const categories = ((data.properties || {}).categories || []).map((c) => c.name);
  const items = data.items || [];
  const say = live(root);
  const won = new Set();
  const asked = new Set();
  const chips = el("ul", { class: "ck-tv-categories", "aria-label": ui.game_categories });
  const marks = categories.map((name) => chips.appendChild(el("li", {}, name)));
  const pickers = el("div", { class: "ck-tv-pick", role: "group", "aria-label": ui.game_tv_choose });
  const stage = el("div", { class: "ck-tv-stage" });
  root.append(chips, pickers, stage);
  const draw = () => {
    marks.forEach((li, i) => li.classList.toggle("is-won", won.has(categories[i])));
    pickers.replaceChildren(...categories.filter((c) => !won.has(c)).map((name) => {
      const button = el("button", { type: "button", class: "ck-btn" }, name);
      button.addEventListener("click", () => ask(name));
      return button;
    }));
    if (categories.length && won.size === categories.length) say(ui.game_done);
  };
  function ask(category) {
    const pool = items.filter((q, i) => q.categoryId === category && !asked.has(i));
    const all = items.filter((q) => q.categoryId === category);
    const question = pool[0] || all[Math.floor(Math.random() * all.length)];
    if (!question) return;
    asked.add(items.indexOf(question));
    stage.replaceChildren();
    const set = el("fieldset", { class: "ck-tv-question" });
    set.appendChild(html("legend", {}, `${category}: ${question.content}`));
    const name = `${root.dataset.id}-${items.indexOf(question)}-${asked.size}`;
    (question.options || []).forEach((option, i) => {
      const label = el("label", { class: "ck-opt" });
      const input = el("input", { type: "radio", name, value: i });
      label.append(input, html("span", {}, option.text));
      set.appendChild(label);
    });
    const check = el("button", { type: "button", class: "ck-btn ck-btn-primary" }, ui.check);
    check.addEventListener("click", () => {
      const chosen = set.querySelector("input:checked");
      if (!chosen) return;
      const right = Boolean((question.options || [])[Number(chosen.value)]?.isCorrect);
      set.querySelectorAll("input").forEach((input) => { input.disabled = true; });
      check.disabled = true;
      if (right) won.add(category);
      say(right ? format(ui.game_tv_won, { category }) : ui.game_tv_wrong);
      draw();
    });
    stage.append(set, check);
    set.querySelector("input")?.focus();
  }
  draw();
}

const GAMES = { "word-search": wordSearch, wordle, hangman, pasapalabra, memory, trivial };

export function initGames(root, ui) {
  root.querySelectorAll(".ck-game").forEach((game) => {
    const play = GAMES[game.dataset.widget];
    const source = game.querySelector(".ck-game-data");
    if (!play || !source) return;
    let data = {};
    try {
      data = JSON.parse(source.textContent);
    } catch (error) {
      return;
    }
    game.querySelector(".ck-game-static").hidden = true;
    play(game, data, ui);
    const region = game.querySelector(".ck-game-live");  // what happens is said under the game
    if (region) game.appendChild(region);
  });
}
