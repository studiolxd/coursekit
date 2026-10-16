// Injected by `coursekit capture` before the page runs, in every frame: the personal data on screen is replaced in the page
// itself before anything is captured. The text is sent to coursekit (window.__ckRedact, exposed by Playwright), which answers
// with the invented counterparts (the same value always gets the same one); nothing is decided here.
//
// What it never does: change the structure of the page (only the value of text nodes), touch what a person can edit (the value
// of a field, an editable area: a Save would send the invented data to the real application; they are blurred instead) or
// rewrite what the network answers. Until a stretch has been replaced it is hidden, so not even a frame shows it.
(() => {
  if (window.__ckInstalled) return;
  window.__ckInstalled = true;
  const config = window.__ckConfig || { selectors: [], avatars: true };
  const SKIP = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE", "TEXTAREA", "INPUT", "SELECT", "OPTION"]);
  const ATTRIBUTES = ["title", "placeholder", "alt"];
  const EDITABLE = '[contenteditable=""],[contenteditable="true"],[contenteditable="plaintext-only"]';
  const AVATAR = /avatar|profile|photo|user-?pic|headshot|portrait/i;
  const done = new WeakMap(); // text node -> the text it was left with
  window.__ckPending = 1; // the first pass

  const style = document.createElement("style");
  style.textContent =
    "html.ck-hidden{visibility:hidden!important}[data-ck-pending]{visibility:hidden!important}" +
    ".ck-blur{filter:blur(12px)!important}" +
    ".ck-blur-field{color:transparent!important;text-shadow:0 0 7px rgba(0,0,0,.75)!important}";
  const root = document.documentElement;
  if (root) {
    root.appendChild(style); // at once: the page is hidden from its first paint
    root.classList.add("ck-hidden");
  }

  // Closed shadow roots are born open, so their text is reached too.
  const attach = Element.prototype.attachShadow;
  Element.prototype.attachShadow = function (init) {
    const shadow = attach.call(this, Object.assign({}, init, { mode: "open" }));
    queueMicrotask(() => watch(shadow));
    return shadow;
  };

  const waitBinding = () =>
    new Promise((resolve) => {
      const ready = () => (typeof window.__ckRedact === "function" ? resolve() : setTimeout(ready, 10));
      ready();
    });

  function texts(node, out) {
    const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
    for (let current = walker.currentNode; current; current = walker.nextNode()) {
      if (current.nodeType === Node.ELEMENT_NODE) {
        if (current.shadowRoot) texts(current.shadowRoot, out);
        continue;
      }
      const parent = current.parentElement;
      if (!parent || SKIP.has(parent.tagName) || !current.nodeValue.trim()) continue;
      if (done.get(current) === current.nodeValue) continue;
      out.push(current);
    }
    return out;
  }

  function elements(node, selector) {
    const found = [...node.querySelectorAll(selector)];
    for (const host of node.querySelectorAll("*")) if (host.shadowRoot) found.push(...elements(host.shadowRoot, selector));
    return found;
  }

  let queue = Promise.resolve();
  function pass(node) {
    window.__ckPending += 1;
    queue = queue.then(() => run(node)).catch(() => {}).finally(() => {
      window.__ckPending -= 1;
    });
    return queue;
  }

  async function run(node) {
    await waitBinding();
    const nodes = texts(node, []);
    const editable = nodes.filter((n) => n.parentElement.closest(EDITABLE));
    const plain = nodes.filter((n) => !n.parentElement.closest(EDITABLE));
    const fields = elements(node, "input:not([type=password]):not([type=hidden]),textarea");
    const titled = ATTRIBUTES.flatMap((a) => elements(node, `[${a}]`).map((el) => [el, a]));
    const asked = [
      ...plain.map((n) => n.nodeValue),
      ...titled.map(([el, a]) => el.getAttribute(a)),
      ...fields.map((el) => el.value || ""),
      ...editable.map((n) => n.nodeValue),
      document.title || "",
    ];
    const answer = asked.length ? await window.__ckRedact(asked) : [];
    let i = 0;
    for (const n of plain) {
      const value = answer[i++];
      if (value !== n.nodeValue) n.nodeValue = value;
      done.set(n, n.nodeValue);
      n.parentElement && n.parentElement.removeAttribute("data-ck-pending");
    }
    for (const [el, a] of titled) {
      const value = answer[i++];
      if (value !== el.getAttribute(a)) el.setAttribute(a, value);
    }
    for (const el of fields) {
      const value = el.value || "";
      el.classList.toggle("ck-blur-field", answer[i++] !== value); // never its value: it would be saved
    }
    for (const n of editable) {
      n.parentElement.classList.toggle("ck-blur-field", answer[i++] !== n.nodeValue);
      done.set(n, n.nodeValue);
      n.parentElement.removeAttribute("data-ck-pending");
    }
    const title = answer[i++];
    if (title !== undefined && title !== document.title) document.title = title;
    if (config.selectors && config.selectors.length) {
      for (const el of elements(node, config.selectors.join(","))) el.classList.add("ck-blur");
    }
    if (config.avatars) {
      for (const el of elements(node, "img,picture,[style*=background-image]")) {
        const hint = [el.className && el.className.baseVal !== undefined ? el.className.baseVal : el.className, el.id,
          el.getAttribute("alt"), el.getAttribute("aria-label"), el.parentElement && el.parentElement.className].join(" ");
        if (AVATAR.test(hint)) el.classList.add("ck-blur");
      }
    }
    for (const el of elements(node, "[data-ck-pending]")) el.removeAttribute("data-ck-pending");
  }

  const observer = new MutationObserver((mutations) => {
    const roots = new Set();
    for (const m of mutations) {
      const target = m.type === "characterData" ? m.target.parentElement : m.target;
      if (!target || !target.isConnected) continue;
      if (m.type === "characterData" && done.get(m.target) === m.target.nodeValue) continue; // our own change
      if (m.type === "attributes" && !ATTRIBUTES.includes(m.attributeName)) continue;
      if (target.setAttribute && target !== document.documentElement && target !== document.body) {
        target.setAttribute("data-ck-pending", "");
      }
      roots.add(target);
    }
    for (const node of roots) pass(node);
  });

  function watch(node) {
    observer.observe(node, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRIBUTES });
  }

  function start() {
    if (!style.isConnected) (document.head || document.documentElement).appendChild(style);
    watch(document);
    pass(document.documentElement).then(() => {
      document.documentElement.classList.remove("ck-hidden");
      window.__ckPending -= 1; // the first pass is done
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
