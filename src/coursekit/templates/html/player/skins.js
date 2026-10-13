// The skins of the simulations: the applications a situation happens in, drawn in HTML with real text (readable, translatable,
// accessible). They recall the look of the applications people use every day without their names, logos or icons.
// Each one draws the `screen` of the scene and marks the parts a hotspot can point at with `data-target`
// (`sender`, `subject`, `link:1`, `message:2`…).

const ICONS = {
  search: "M10 4a6 6 0 1 0 3.9 10.6l4.7 4.7 1.4-1.4-4.7-4.7A6 6 0 0 0 10 4zm0 2a4 4 0 1 1 0 8 4 4 0 0 1 0-8z",
  reply: "M10 8V4l-7 7 7 7v-4c5 0 8.5 1.6 11 5-1-5-4-10-11-11z",
  forward: "M14 8V4l7 7-7 7v-4c-5 0-8.5 1.6-11 5 1-5 4-10 11-11z",
  trash: "M7 4V3h10v1h4v2H3V4h4zm-1 4h12l-1 13H7L6 8zm4 2v9h1v-9h-1zm3 0v9h1v-9h-1z",
  clip: "M16.5 6.5 9 14a1.8 1.8 0 0 0 2.5 2.5L19 9a3.5 3.5 0 0 0-5-5l-8 8a5.2 5.2 0 0 0 7.4 7.4l6.6-6.6-1.4-1.4-6.6 6.6a3.2 3.2 0 0 1-4.6-4.6l8-8a1.5 1.5 0 0 1 2.1 2.1L10 17a.2.2 0 0 1-.3-.3l7.5-7.5-1.4-1.4z",
  lock: "M7 10V8a5 5 0 0 1 10 0v2h1a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1h1zm2 0h6V8a3 3 0 0 0-6 0v2z",
  warn: "M12 3 2 21h20L12 3zm-1 6h2v6h-2V9zm0 8h2v2h-2v-2z",
  back: "M15.4 5.4 14 4l-8 8 8 8 1.4-1.4L8.8 12z",
  next: "M8.6 5.4 10 4l8 8-8 8-1.4-1.4 6.6-6.6z",
  reload: "M12 5V2L7 6l5 4V7a5 5 0 1 1-5 5H5a7 7 0 1 0 7-7z",
  phone: "M6.6 10.8a15 15 0 0 0 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1A17 17 0 0 1 3 4c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.3 0 .7-.2 1l-2.3 2.2z",
  video: "M17 10.5V7a1 1 0 0 0-1-1H4a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-3.5l4 4v-11l-4 4z",
  more: "M12 8a2 2 0 1 0 0-4 2 2 0 0 0 0 4zm0 2a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm0 6a2 2 0 1 0 0 4 2 2 0 0 0 0-4z",
  pencil: "M3 17.2V21h3.8L17.8 10l-3.8-3.8L3 17.2zM20.7 7a1 1 0 0 0 0-1.4l-2.3-2.3a1 1 0 0 0-1.4 0l-1.8 1.8 3.8 3.8L20.7 7z",
  inbox: "M19 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2zm0 12h-4a3 3 0 0 1-6 0H5V5h14v10z",
  send: "M2 21 23 12 2 3v7l15 2-15 2z",
  star: "m12 17.3 6.2 3.7-1.6-7 5.4-4.7-7.2-.6L12 2 9.2 8.7l-7.2.6 5.4 4.7-1.6 7z",
  people: "M16 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm-8 0a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm0 2c-2.3 0-7 1.2-7 3.5V19h14v-2.5C15 14.2 10.3 13 8 13zm8 0h-1a4.6 4.6 0 0 1 2 3.5V19h6v-2.5c0-2.3-4.7-3.5-7-3.5z",
  chat: "M20 2H4a2 2 0 0 0-2 2v18l4-4h14a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2z",
  bell: "M12 22a2 2 0 0 0 2-2h-4a2 2 0 0 0 2 2zm6-6V11a6 6 0 0 0-5-5.9V4a1 1 0 0 0-2 0v1.1A6 6 0 0 0 6 11v5l-2 2v1h16v-1l-2-2z",
  check: "M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z",
  mic: "M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.9V21h2v-3.1A7 7 0 0 0 19 11h-2z",
  hang: "M12 9c-1.6 0-3.2.3-4.6.7v3.1c0 .4-.2.7-.6.9-1 .5-1.9 1.1-2.6 1.8-.2.2-.4.3-.7.3-.3 0-.5-.1-.7-.3L.3 13c-.2-.2-.3-.4-.3-.7 0-.3.1-.5.3-.7A17 17 0 0 1 12 7c4.5 0 8.6 1.7 11.7 4.6.2.2.3.4.3.7 0 .3-.1.5-.3.7l-2.5 2.5c-.2.2-.4.3-.7.3-.3 0-.5-.1-.7-.3-.7-.7-1.6-1.3-2.6-1.8-.3-.2-.6-.5-.6-.9V9.7C15.2 9.3 13.6 9 12 9z",
};

const PALETTE = ["#0f6cbd", "#c239b3", "#038387", "#ca5010", "#8764b8", "#498205", "#d13438", "#005b70"];

function el(tag, attrs = {}, html = "") {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== false) node.setAttribute(key, val === true ? "" : String(val));
  });
  if (html) node.innerHTML = html;
  return node;
}

function icon(name, label) {
  const attrs = label ? `role="img" aria-label="${label}"` : 'aria-hidden="true"';
  return `<svg class="ck-icon" viewBox="0 0 24 24" ${attrs}><path d="${ICONS[name]}"/></svg>`;
}

const plain = (html) => {
  const box = document.createElement("div");
  box.innerHTML = html || "";
  return (box.textContent || "").trim();
};

function avatar(name, size = "") {
  const text = plain(name) || "?";
  const sum = Array.from(text).reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
  const words = text.replace(/[^\p{L}\p{N}\s]/gu, " ").split(/\s+/).filter(Boolean);
  const initials = words.slice(0, 2).map((w) => w[0]).join("").toUpperCase() || "?";
  return el("span", { class: `ck-avatar ${size}`.trim(), style: `background:${PALETTE[sum % PALETTE.length]}`, "aria-hidden": "true" }, initials);
}

// Links inside a screen never leave the course: they are numbered as targets (`link:1`…).
function numberLinks(root) {
  root.querySelectorAll("a").forEach((link, i) => {
    link.dataset.target = `link:${i + 1}`;
    link.addEventListener("click", (event) => event.preventDefault());
    link.setAttribute("title", link.getAttribute("href") || "");
  });
}

// ── mail ───────────────────────────────────────────────────────────────────────────────────────

function mailMessage(message, ui) {
  const pane = el("article", { class: "ck-mail-read" });
  if (!message) {
    pane.appendChild(el("p", { class: "ck-mail-empty" }, ui.skin_no_message));
    return pane;
  }
  pane.appendChild(el("h4", { class: "ck-mail-subject", "data-target": "subject" }, message.subject || ""));
  const head = el("div", { class: "ck-mail-head" });
  head.appendChild(avatar(message.from, "is-lg"));
  const who = el("div", { class: "ck-mail-who" });
  const from = el("p", { class: "ck-mail-from" });
  from.appendChild(el("strong", { "data-target": "sender" }, message.from || ""));
  if (message.address) from.appendChild(el("span", { class: "ck-mail-address", "data-target": "address" }, `&lt;${message.address}&gt;`));
  who.appendChild(from);
  if (message.to) who.appendChild(el("p", { class: "ck-mail-to" }, `${ui.skin_to}: ${message.to}`));
  head.appendChild(who);
  if (message.time) head.appendChild(el("span", { class: "ck-mail-time" }, message.time));
  pane.appendChild(head);
  const body = el("div", { class: "ck-mail-body" }, message.body || "");
  numberLinks(body);
  pane.appendChild(body);
  const files = message.attachments || [];
  if (files.length) {
    const list = el("ul", { class: "ck-mail-files", "aria-label": ui.skin_attachments });
    files.forEach((name, i) => {
      const item = el("li", { "data-target": `attachment:${i + 1}` }, `${icon("clip")}<span>${name}</span>`);
      list.appendChild(item);
    });
    pane.appendChild(list);
  }
  const actions = el("div", { class: "ck-mail-actions", "aria-hidden": "true" });
  actions.innerHTML = [["reply", ui.skin_reply], ["forward", ui.skin_forward]]
    .map(([name, label]) => `<span class="ck-chip">${icon(name)}${label}</span>`).join("");
  pane.appendChild(actions);
  return pane;
}

function mailList(screen, ui) {
  const list = el("ol", { class: "ck-mail-list", "aria-label": screen.folder || ui.skin_inbox });
  // without an inbox of its own, the list shows the open message (an empty list does not look like a real mail client)
  const inbox = (screen.inbox || []).length ? screen.inbox : screen.message
    ? [{ from: screen.message.from, subject: screen.message.subject, time: screen.message.time,
      preview: plain(screen.message.body).slice(0, 90) }] : [];
  inbox.forEach((item, i) => {
    const open = screen.message && plain(item.subject) === plain(screen.message.subject);
    const row = el("li", { class: `ck-mail-row${item.unread ? " is-unread" : ""}${open ? " is-open" : ""}`, "data-target": `inbox:${i + 1}` });
    row.appendChild(avatar(item.from));
    const text = el("div", { class: "ck-mail-row-text" });
    text.appendChild(el("p", { class: "ck-mail-row-from" }, `<span>${item.from || ""}</span><time>${item.time || ""}</time>`));
    text.appendChild(el("p", { class: "ck-mail-row-subject" }, item.subject || ""));
    if (item.preview) text.appendChild(el("p", { class: "ck-mail-row-preview" }, item.preview));
    row.appendChild(text);
    list.appendChild(row);
  });
  return list;
}

function mailDesktop(screen, ui) {
  const app = el("div", { class: "ck-skin ck-skin-mail-desktop" });
  const bar = el("div", { class: "ck-md-bar" });
  bar.innerHTML = `<span class="ck-md-grid" aria-hidden="true"></span><strong>${screen.app || ui.skin_mail_app}</strong>`
    + `<span class="ck-md-search">${icon("search")}${ui.skin_search}</span><span class="ck-md-me">${screen.account ? plain(screen.account).slice(0, 1) : ""}</span>`;
  const ribbon = el("div", { class: "ck-md-ribbon", "aria-hidden": "true" });
  ribbon.innerHTML = `<span class="ck-md-new">${icon("pencil")}${ui.skin_new_mail}</span>`
    + [["trash", ui.skin_delete], ["reply", ui.skin_reply], ["forward", ui.skin_forward]].map(([n, l]) => `<span>${icon(n)}${l}</span>`).join("");
  const body = el("div", { class: "ck-md-body" });
  const folders = el("nav", { class: "ck-md-folders", "aria-hidden": "true" });
  folders.innerHTML = `<p>${screen.account || ""}</p><span class="is-active">${icon("inbox")}${screen.folder || ui.skin_inbox}</span>`
    + `<span>${icon("send")}${ui.skin_sent}</span><span>${icon("trash")}${ui.skin_deleted}</span>`;
  body.append(folders, mailList(screen, ui), mailMessage(screen.message, ui));
  app.append(bar, ribbon, body);
  return app;
}

function mailWeb(screen, ui) {
  const app = el("div", { class: "ck-skin ck-skin-mail-web" });
  const bar = el("div", { class: "ck-mw-bar" });
  bar.innerHTML = `<span class="ck-mw-logo">${icon("inbox")}<strong>${screen.app || ui.skin_mail_app}</strong></span>`
    + `<span class="ck-mw-search">${icon("search")}${ui.skin_search}</span>`
    + `<span class="ck-avatar is-sm" style="background:${PALETTE[2]}" aria-hidden="true">${screen.account ? plain(screen.account).slice(0, 1) : ""}</span>`;
  const body = el("div", { class: "ck-mw-body" });
  const nav = el("nav", { class: "ck-mw-nav", "aria-hidden": "true" });
  nav.innerHTML = `<span class="ck-mw-compose">${icon("pencil")}${ui.skin_compose}</span>`
    + `<span class="is-active">${icon("inbox")}${screen.folder || ui.skin_inbox}</span><span>${icon("star")}${ui.skin_starred}</span>`
    + `<span>${icon("send")}${ui.skin_sent}</span>`;
  const main = el("div", { class: "ck-mw-main" });
  if (screen.message) main.appendChild(mailMessage(screen.message, ui));
  else main.appendChild(mailList(screen, ui));
  body.append(nav, main);
  app.append(bar, body);
  return app;
}

// ── chat ───────────────────────────────────────────────────────────────────────────────────────

// The messages of a chat; it scrolls on its own, so it takes the focus (the keyboard scrolls it) and has a name.
function chatLines(messages, cls, label) {
  const list = el("ol", { class: cls, tabindex: "0", "aria-label": label });
  messages.forEach((msg, i) => {
    const mine = msg.me === true;
    const row = el("li", { class: mine ? "is-me" : "", "data-target": msg.target === false ? null : `message:${i + 1}` });
    if (!mine) row.appendChild(avatar(msg.from));
    const bubble = el("div", { class: "ck-bubble" });
    if (!mine && msg.from) bubble.appendChild(el("p", { class: "ck-bubble-from" }, `<strong>${msg.from}</strong>${msg.time ? `<time>${msg.time}</time>` : ""}`));
    bubble.appendChild(el("div", { class: "ck-bubble-text" }, msg.text || ""));
    if (mine || (!msg.from && msg.time)) bubble.appendChild(el("time", { class: "ck-bubble-time" }, `${msg.time || ""}${mine ? icon("check") : ""}`));
    row.appendChild(bubble);
    list.appendChild(row);
  });
  numberLinks(list);
  return list;
}

function chatWorkspace(screen, ui, messages) {
  const app = el("div", { class: "ck-skin ck-skin-chat-workspace" });
  const rail = el("nav", { class: "ck-cw-rail", "aria-hidden": "true" });
  rail.innerHTML = [["bell", ui.skin_activity], ["chat", ui.skin_chat], ["people", ui.skin_teams]]
    .map(([n, l], i) => `<span class="${i === 2 ? "is-active" : ""}">${icon(n)}<small>${l}</small></span>`).join("");
  const side = el("nav", { class: "ck-cw-side", "aria-hidden": "true" });
  side.innerHTML = `<p class="ck-cw-team">${screen.team || screen.app || ui.skin_chat_app}</p>`
    + (screen.channels || [screen.channel || "General"]).map((c) => `<span class="${plain(c) === plain(screen.channel) ? "is-active" : ""}"># ${c}</span>`).join("");
  const main = el("div", { class: "ck-cw-main" });
  main.appendChild(el("header", { class: "ck-cw-head" }, `<strong># ${screen.channel || "General"}</strong>${icon("video")}${icon("more")}`));
  main.appendChild(chatLines(messages, "ck-cw-lines", ui.skin_chat));
  main.appendChild(el("div", { class: "ck-cw-compose", "aria-hidden": "true" }, `<span>${ui.skin_type_message}</span>${icon("send")}`));
  app.append(rail, side, main);
  return app;
}

function messenger(screen, ui, messages) {
  const app = el("div", { class: "ck-skin ck-skin-messenger" });
  const head = el("header", { class: "ck-ms-head" });
  head.innerHTML = `${icon("back")}`;
  head.appendChild(avatar(screen.contact));
  head.appendChild(el("div", { class: "ck-ms-who" }, `<strong>${screen.contact || ""}</strong><small>${screen.status || ui.skin_online}</small>`));
  head.insertAdjacentHTML("beforeend", `<span class="ck-ms-tools">${icon("video")}${icon("phone")}${icon("more")}</span>`);
  app.appendChild(head);
  app.appendChild(chatLines(messages, "ck-ms-lines", ui.skin_chat));
  app.appendChild(el("div", { class: "ck-ms-compose", "aria-hidden": "true" }, `<span>${ui.skin_type_message}</span><b>${icon("mic")}</b>`));
  return app;
}

function phone(screen, ui, messages) {
  const state = screen.state || "incoming";
  const app = el("div", { class: `ck-skin ck-skin-phone is-${state}` });
  app.appendChild(el("div", { class: "ck-ph-status", "aria-hidden": "true" }, `<span>${screen.time || "9:41"}</span><span>●●●● ▮</span>`));
  if (state === "sms") {
    const head = el("header", { class: "ck-ph-sms-head" });
    head.appendChild(avatar(screen.caller));
    head.appendChild(el("strong", { "data-target": "caller" }, screen.caller || ""));
    if (screen.number) head.appendChild(el("small", { "data-target": "number" }, screen.number));
    app.append(head, chatLines(messages, "ck-ph-lines", ui.skin_chat));
    return app;
  }
  const call = el("div", { class: "ck-ph-call" });
  call.appendChild(el("p", { class: "ck-ph-state" }, state === "incoming" ? ui.skin_incoming : ui.skin_calling));
  call.appendChild(avatar(screen.caller, "is-xl"));
  call.appendChild(el("p", { class: "ck-ph-caller", "data-target": "caller" }, screen.caller || ""));
  if (screen.number) call.appendChild(el("p", { class: "ck-ph-number", "data-target": "number" }, screen.number));
  const buttons = el("div", { class: "ck-ph-buttons", "aria-hidden": "true" });
  buttons.innerHTML = state === "incoming"
    ? `<span class="is-decline">${icon("hang")}<small>${ui.skin_decline}</small></span><span class="is-accept">${icon("phone")}<small>${ui.skin_accept}</small></span>`
    : `<span>${icon("mic")}</span><span class="is-decline">${icon("hang")}</span><span>${icon("more")}</span>`;
  call.appendChild(buttons);
  app.appendChild(call);
  return app;
}

// ── browser ────────────────────────────────────────────────────────────────────────────────────

function browser(screen, ui) {
  const app = el("div", { class: "ck-skin ck-skin-browser" });
  const tabs = el("div", { class: "ck-br-tabs", "aria-hidden": "true" });
  tabs.innerHTML = `<span class="ck-br-dots"><i></i><i></i><i></i></span><span class="ck-br-tab">${screen.title || screen.url || ""}</span>`;
  const bar = el("div", { class: "ck-br-bar" });
  bar.insertAdjacentHTML("beforeend", `<span class="ck-br-nav" aria-hidden="true">${icon("back")}${icon("next")}${icon("reload")}</span>`);
  const address = el("div", { class: `ck-br-address${screen.secure === false ? " is-insecure" : ""}` });
  address.appendChild(el("span", { class: "ck-br-lock", "data-target": "lock" },
    screen.secure === false ? `${icon("warn")}<small>${ui.skin_not_secure}</small>` : icon("lock", ui.skin_secure)));
  address.appendChild(el("span", { class: "ck-br-url", "data-target": "url" }, screen.url || ""));
  bar.appendChild(address);
  const page = el("div", { class: "ck-br-page" }, screen.body || "");
  numberLinks(page);
  app.append(tabs, bar, page);
  return app;
}

const SKINS = { "mail-desktop": mailDesktop, "mail-web": mailWeb, "chat-workspace": chatWorkspace, messenger, phone, browser };

// The screen of a scene: the simulation's `screen` completed by the scene's; `messages` adds the lines of a conversation.
// The skins of the project (`components/skins/<name>.js`) register themselves before the player starts:
//   window.coursekitSkins["<name>"] = { chat: false, draw(screen, ui, messages, helpers) { return node; } };
// `helpers` are the ones the built-in skins use: el(tag, attrs, html), icon(name, label), numberLinks(root), avatar(name)
// and chatLines(messages, className, label). Parts a hotspot can point at carry `data-target`.
const HELPERS = { el, icon, numberLinks, avatar, chatLines };
const projectSkin = (skin) => (typeof window !== "undefined" && window.coursekitSkins && window.coursekitSkins[skin]) || null;

export function drawSkin(skin, screen, ui, transcript = []) {
  const own = projectSkin(skin);
  const draw = SKINS[skin] || (own && ((screen_, ui_, messages) => own.draw(screen_, ui_, messages, HELPERS)));
  if (!draw) return null;
  const messages = (screen.messages || []).concat(transcript);
  return draw(screen, ui, messages);
}

export const CHAT_SKINS = ["chat-workspace", "messenger", "phone"];
// the messages of the scenes add up along the path (a chat)
export const isChat = (skin) => CHAT_SKINS.includes(skin) || Boolean(projectSkin(skin) && projectSkin(skin).chat);
