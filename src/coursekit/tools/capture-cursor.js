// Injected by `coursekit capture replay`: a visible pointer for the video (a screencast of the page does not draw the one of
// the system). It follows the mouse events Playwright sends and marks each click with a ring. It remembers where it was across
// pages of the same tab, so it does not jump to a corner after a navigation.
(() => {
  if (window.__ckCursor) return;
  window.__ckCursor = true;
  const KEY = "__ckCursorAt";
  const svg =
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">' +
    '<path d="M3 2l7.5 19 2.4-7.6L20.5 11z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  function place(el, x, y) {
    el.style.transform = `translate(${x}px, ${y}px)`;
  }
  function install() {
    const pointer = document.createElement("div");
    pointer.setAttribute("aria-hidden", "true");
    pointer.style.cssText = "position:fixed;left:-3px;top:-2px;width:24px;height:24px;z-index:2147483647;pointer-events:none;";
    pointer.innerHTML = svg;
    document.documentElement.appendChild(pointer);
    let at = { x: -40, y: -40 };
    try {
      at = JSON.parse(sessionStorage.getItem(KEY)) || at;
    } catch (e) {}
    place(pointer, at.x, at.y);
    document.addEventListener("mousemove", (event) => {
      place(pointer, event.clientX, event.clientY);
      try {
        sessionStorage.setItem(KEY, JSON.stringify({ x: event.clientX, y: event.clientY }));
      } catch (e) {}
    }, true);
    document.addEventListener("mousedown", (event) => {
      const ring = document.createElement("div");
      ring.setAttribute("aria-hidden", "true");
      ring.style.cssText =
        "position:fixed;width:36px;height:36px;margin:-18px 0 0 -18px;border:3px solid rgba(230,30,120,.85);border-radius:50%;" +
        `left:${event.clientX}px;top:${event.clientY}px;z-index:2147483646;pointer-events:none;transition:transform .45s,opacity .45s;`;
      document.documentElement.appendChild(ring);
      requestAnimationFrame(() => {
        ring.style.transform = "scale(1.8)";
        ring.style.opacity = "0";
      });
      setTimeout(() => ring.remove(), 600);
    }, true);
  }
  if (document.documentElement) install();
  else document.addEventListener("DOMContentLoaded", install, { once: true });
})();
