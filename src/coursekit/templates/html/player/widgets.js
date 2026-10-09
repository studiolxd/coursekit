// Behaviour of the components that are plain content without JavaScript: tabs, carousels, cards and hotspots.

const el = (tag, attrs = {}, text = "") => {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([key, val]) => node.setAttribute(key, val));
  if (text) node.textContent = text;
  return node;
};

function initTabs(root) {
  const panels = Array.from(root.querySelectorAll(":scope > .ck-panel"));
  const list = el("div", { class: "ck-tablist", role: "tablist" });
  const buttons = panels.map((panel, i) => {
    const title = panel.querySelector(".ck-panel-title");
    const id = `${root.dataset.id}-t${i}`;
    const button = el("button", { type: "button", role: "tab", id, "aria-controls": `${id}-p`, tabindex: i === 0 ? "0" : "-1" });
    button.innerHTML = title ? title.innerHTML : String(i + 1);
    panel.setAttribute("role", "tabpanel");
    panel.id = `${id}-p`;
    panel.setAttribute("aria-labelledby", id);
    list.appendChild(button);
    return button;
  });
  const show = (index, focus) => {
    buttons.forEach((button, i) => {
      button.setAttribute("aria-selected", i === index ? "true" : "false");
      button.tabIndex = i === index ? 0 : -1;
      panels[i].hidden = i !== index;
    });
    if (focus) buttons[index].focus();
  };
  buttons.forEach((button, i) => {
    button.addEventListener("click", () => show(i, false));
    button.addEventListener("keydown", (event) => {
      const last = buttons.length - 1;
      const target = { ArrowRight: i === last ? 0 : i + 1, ArrowLeft: i === 0 ? last : i - 1, Home: 0, End: last }[event.key];
      if (target !== undefined) {
        event.preventDefault();
        show(target, true);
      }
    });
  });
  root.insertBefore(list, root.firstChild);
  root.classList.add("is-enhanced");
  show(0, false);
}

function initCarousel(root, ui) {
  const slides = Array.from(root.querySelectorAll(":scope > .ck-panel, :scope > .ck-card"));
  if (slides.length < 2) return;
  const status = el("p", { class: "ck-carousel-status", "aria-live": "polite" });
  const previous = el("button", { type: "button", class: "ck-btn" }, ui.previous);
  const next = el("button", { type: "button", class: "ck-btn" }, ui.next);
  const controls = el("div", { class: "ck-carousel-controls" });
  controls.append(previous, status, next);
  root.appendChild(controls);
  let index = 0;
  const show = (to) => {
    index = (to + slides.length) % slides.length;
    slides.forEach((slide, i) => {
      slide.hidden = i !== index;
    });
    status.textContent = ui.slide.replace("{n}", index + 1).replace("{total}", slides.length);
  };
  previous.addEventListener("click", () => show(index - 1));
  next.addEventListener("click", () => show(index + 1));
  root.classList.add("is-enhanced");
  show(0);
}

function initCard(card) {
  const flip = () => {
    const flipped = card.classList.toggle("is-flipped");
    card.setAttribute("aria-pressed", flipped ? "true" : "false");
  };
  card.addEventListener("click", flip);
  card.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      flip();
    }
  });
}

function initHotspots(root, ui) {
  const points = Array.from(root.querySelectorAll(".ck-hs-point"));
  const entries = Array.from(root.querySelectorAll(".ck-hs-list > li"));
  root.classList.add("is-enhanced");
  entries.forEach((entry) => {
    entry.hidden = true;
    const close = el("button", { type: "button", class: "ck-btn ck-hs-close" }, ui.close);
    close.addEventListener("click", () => closeAll(true));
    entry.appendChild(close);
  });
  function closeAll(focus) {
    let last = null;
    points.forEach((point) => {
      if (point.getAttribute("aria-expanded") === "true") last = point;
      point.setAttribute("aria-expanded", "false");
    });
    entries.forEach((entry) => {
      entry.hidden = true;
    });
    if (focus && last) last.focus();
  }
  points.forEach((point) => {
    point.addEventListener("click", () => {
      const open = point.getAttribute("aria-expanded") === "true";
      closeAll(false);
      if (!open) {
        point.setAttribute("aria-expanded", "true");
        document.getElementById(point.getAttribute("aria-controls")).hidden = false;
      }
    });
  });
  root.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeAll(true);
  });
}

export function initWidgets(root, ui) {
  root.querySelectorAll('[data-widget="tabs"]').forEach(initTabs);
  root.querySelectorAll('[data-widget="carousel"]').forEach((node) => initCarousel(node, ui));
  root.querySelectorAll('[data-widget="card"]').forEach(initCard);
  root.querySelectorAll('[data-widget="hotspots"]').forEach((node) => initHotspots(node, ui));
}
