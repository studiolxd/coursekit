// The questions: their enhancement (shuffling, selects, word chips), their grading and their feedback. A question is a `.ck-q` with a
// `data-type`; the markup already holds the right answers, the player only hides them from the learner's view.

const normalize = (text) =>
  String(text || "").trim().toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/\s+/g, " ");

const el = (tag, attrs = {}, text = "") => {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([key, val]) => node.setAttribute(key, val));
  if (text) node.textContent = text;
  return node;
};

function shuffle(list) {
  const copy = list.slice();
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  if (copy.length > 1 && copy.every((item, i) => item === list[i])) copy.push(copy.shift());
  return copy;
}

const letters = (n) => String.fromCharCode(97 + n);

// Each type: setup(q, ui) once, reset(q) for another try, answered(q), grade(q), lock(q, locked), mark(q), response(q).
const TYPES = {
  single: choiceType(),
  multi: choiceType(),
  sorting: {
    setup(q, ui) {
      const list = q.querySelector(".ck-sort");
      list._items = Array.from(list.children);
      list.querySelectorAll("li").forEach((li) => {
        const up = el("button", { type: "button", class: "ck-move", "aria-label": ui.move_up }, "↑");
        const down = el("button", { type: "button", class: "ck-move", "aria-label": ui.move_down }, "↓");
        up.addEventListener("click", () => move(li, -1));
        down.addEventListener("click", () => move(li, 1));
        li.append(up, down);
      });
      const move = (li, by) => {
        const sibling = by < 0 ? li.previousElementSibling : li.nextElementSibling;
        if (!sibling) return;
        if (by < 0) list.insertBefore(li, sibling);
        else list.insertBefore(sibling, li);
        li.querySelector(`.ck-move:nth-of-type(${by < 0 ? 1 : 2})`).focus();
      };
      this.reset(q);
    },
    reset(q) {
      const list = q.querySelector(".ck-sort");
      shuffle(list._items).forEach((li) => list.appendChild(li));
    },
    answered: () => true,
    grade: (q) => Array.from(q.querySelectorAll(".ck-sort > li")).every((li, i) => Number(li.dataset.i) === i),
    lock: (q, locked) => q.querySelectorAll(".ck-move").forEach((b) => { b.disabled = locked; }),
    mark: (q, ok) => q.classList.toggle("is-right", ok),
    response: (q) => Array.from(q.querySelectorAll(".ck-sort > li")).map((li) => li.dataset.i).join(","),
  },
  match: {
    setup(q, ui) {
      const pairs = Array.from(q.querySelectorAll(".ck-pair"));
      const rights = pairs.map((pair, i) => ({ i, html: pair.querySelector(".ck-right").innerHTML }));
      q._pairs = pairs;
      pairs.forEach((pair, n) => {
        pair.querySelector(".ck-right").hidden = true;
        const select = el("select", { class: "ck-select", "aria-label": pair.querySelector(".ck-left").textContent });
        pair.appendChild(select);
        pair._select = select;
        pair._index = n;
      });
      q._rights = rights;
      q._ui = ui;
      this.reset(q);
    },
    reset(q) {
      q._pairs.forEach((pair) => {
        const select = pair._select;
        select.innerHTML = "";
        select.appendChild(el("option", { value: "" }, q._ui.select));
        shuffle(q._rights).forEach((right) => {
          const holder = document.createElement("div");
          holder.innerHTML = right.html;
          select.appendChild(el("option", { value: String(right.i) }, holder.textContent));
        });
        select.disabled = false;
      });
    },
    answered: (q) => q._pairs.every((pair) => pair._select.value !== ""),
    grade: (q) => q._pairs.every((pair) => Number(pair._select.value) === pair._index),
    lock: (q, locked) => q._pairs.forEach((pair) => { pair._select.disabled = locked; }),
    mark: (q, ok) => q.classList.toggle("is-right", ok),
    response: (q) => q._pairs.map((pair) => pair._select.value).join(","),
  },
  groups: {
    setup(q, ui) {
      const labels = Array.from(q.querySelectorAll(".ck-group-labels > li"));
      q._rows = Array.from(q.querySelectorAll(".ck-group-items > li"));
      q._labels = labels;
      q._ui = ui;
      q._rows.forEach((row) => {
        const select = el("select", { class: "ck-select", "aria-label": row.textContent });
        row.appendChild(select);
        row._select = select;
      });
      this.reset(q);
    },
    reset(q) {
      q._rows.forEach((row) => {
        row._select.innerHTML = "";
        row._select.appendChild(el("option", { value: "" }, q._ui.select));
        q._labels.forEach((label) => row._select.appendChild(el("option", { value: label.dataset.group }, label.textContent)));
        row._select.disabled = false;
      });
    },
    answered: (q) => q._rows.every((row) => row._select.value !== ""),
    grade: (q) => q._rows.every((row) => row._select.value === row.dataset.group),
    lock: (q, locked) => q._rows.forEach((row) => { row._select.disabled = locked; }),
    mark: (q, ok) => q.classList.toggle("is-right", ok),
    response: (q) => q._rows.map((row) => row._select.value).join(","),
  },
  blanks: {
    setup(q) {
      q.querySelectorAll(".ck-key").forEach((key) => { key.hidden = true; });
    },
    reset(q) {
      q.querySelectorAll(".ck-blank").forEach((input) => { input.value = ""; input.disabled = false; });
    },
    answered: (q) => Array.from(q.querySelectorAll(".ck-blank")).every((input) => input.value.trim() !== ""),
    grade: (q) => Array.from(q.querySelectorAll(".ck-blank")).every((input) =>
      input.dataset.answers.split("|").map(normalize).includes(normalize(input.value))),
    lock: (q, locked) => q.querySelectorAll(".ck-blank").forEach((input) => { input.disabled = locked; }),
    mark: (q, ok) => q.classList.toggle("is-right", ok),
    response: (q) => Array.from(q.querySelectorAll(".ck-blank")).map((input) => input.value.trim()).join(","),
  },
  short: {
    setup(q) {
      q.querySelectorAll(".ck-key").forEach((key) => { key.hidden = true; });
    },
    reset(q) {
      const input = q.querySelector(".ck-short");
      input.value = "";
      input.disabled = false;
    },
    answered: (q) => q.querySelector(".ck-short").value.trim() !== "",
    grade: (q) => {
      const input = q.querySelector(".ck-short");
      return input.dataset.answers.split("|").map(normalize).includes(normalize(input.value));
    },
    lock: (q, locked) => { q.querySelector(".ck-short").disabled = locked; },
    mark: (q, ok) => q.classList.toggle("is-right", ok),
    response: (q) => q.querySelector(".ck-short").value.trim(),
  },
  order: {
    setup(q, ui) {
      q._lines = Array.from(q.querySelectorAll(".ck-words")).map((list) => {
        const words = Array.from(list.children).map((li) => li.textContent);
        const answer = el("div", { class: "ck-order-answer", "aria-label": ui.words_answer });
        const pool = el("div", { class: "ck-order-pool", "aria-label": ui.words_pool });
        list.replaceWith(answer, pool);
        return { words, answer, pool };
      });
      this.reset(q);
    },
    reset(q) {
      q._lines.forEach((line) => {
        line.answer.innerHTML = "";
        line.pool.innerHTML = "";
        shuffle(line.words.map((word, i) => ({ word, i }))).forEach((item) => {
          const chip = el("button", { type: "button", class: "ck-word" }, item.word);
          chip.addEventListener("click", () => {
            if (chip.disabled) return;
            (chip.parentNode === line.pool ? line.answer : line.pool).appendChild(chip);
          });
          line.pool.appendChild(chip);
        });
      });
    },
    answered: (q) => q._lines.every((line) => line.pool.children.length === 0),
    grade: (q) => q._lines.every((line) => Array.from(line.answer.children).map((chip) => chip.textContent).join(" ") === line.words.join(" ")),
    lock: (q, locked) => q.querySelectorAll(".ck-word").forEach((chip) => { chip.disabled = locked; }),
    mark: (q, ok) => q.classList.toggle("is-right", ok),
    response: (q) => q._lines.map((line) => Array.from(line.answer.children).map((chip) => chip.textContent).join(" ")).join(" | "),
  },
};

function choiceType() {
  return {
    setup() {},
    reset(q) {
      q.querySelectorAll("input").forEach((input) => { input.checked = false; input.disabled = false; });
      q.querySelectorAll(".ck-opt").forEach((label) => label.classList.remove("is-right", "is-wrong"));
    },
    answered: (q) => Array.from(q.querySelectorAll("input")).some((input) => input.checked),
    grade: (q) => Array.from(q.querySelectorAll("input")).every((input) => input.checked === (input.dataset.correct === "1")),
    lock: (q, locked) => q.querySelectorAll("input").forEach((input) => { input.disabled = locked; }),
    mark(q, ok) {
      q.classList.toggle("is-right", ok);
      q.querySelectorAll(".ck-opt").forEach((label) => {
        const input = label.querySelector("input");
        label.classList.toggle("is-right", input.dataset.correct === "1");
        label.classList.toggle("is-wrong", input.checked && input.dataset.correct !== "1");
      });
    },
    response: (q) => Array.from(q.querySelectorAll("input")).map((input, i) => (input.checked ? letters(i) : "")).join(""),
  };
}

export function showFeedback(q, ok) {
  q.querySelectorAll(".ck-fb").forEach((node) => {
    node.hidden = !(node.classList.contains("ck-fb-general") || node.classList.contains(ok ? "ck-fb-correct" : "ck-fb-incorrect"));
  });
}

function clearFeedback(q) {
  q.querySelectorAll(".ck-fb").forEach((node) => { node.hidden = true; });
  q.classList.remove("is-right", "is-wrong", "is-graded");
  q.querySelectorAll(".ck-opt").forEach((label) => label.classList.remove("is-right", "is-wrong"));
}

export function initQuestion(q, ui, onGraded) {
  const type = TYPES[q.dataset.type];
  if (!type) return null;
  type.setup(q, ui);
  const api = {
    q,
    type,
    answered: () => type.answered(q),
    grade() {
      const ok = type.grade(q);
      type.lock(q, true);
      type.mark(q, ok);
      q.classList.add("is-graded", ok ? "is-right" : "is-wrong");
      showFeedback(q, ok);
      return ok;
    },
    reset() {
      clearFeedback(q);
      type.lock(q, false);
      type.reset(q);
    },
    response: () => type.response(q),
  };
  // Practice questions check themselves; the ones of a test are graded all together by the lesson.
  if (!q.closest('[data-type="evaluation"]')) {
    const actions = q.querySelector(".ck-q-actions");
    const button = el("button", { type: "button", class: "ck-btn" }, ui.check);
    let graded = false;
    button.addEventListener("click", () => {
      if (!graded) {
        if (!api.answered()) return;
        const ok = api.grade();
        graded = true;
        button.textContent = ui.retry;
        if (onGraded) onGraded(api, ok);
      } else {
        api.reset();
        graded = false;
        button.textContent = ui.check;
      }
    });
    actions.appendChild(button);
  }
  return api;
}
