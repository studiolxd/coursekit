#!/usr/bin/env node
/**
 * Descargador de documentación web -> Markdown.
 *
 * Parte de una URL, descubre todas las páginas que cuelgan de su ruta (scope),
 * extrae el contenido principal de cada una, lo convierte a Markdown (con
 * frontmatter YAML), descarga las imágenes a assets/ y reescribe los enlaces
 * internos para que funcionen entre ficheros .md.
 *
 * Sin dependencias externas (Node >= 18: fetch, fs, path, crypto).
 * Pensado para sitios Starlight/Astro, pero el conversor es genérico
 * (cabeceras, listas, tablas, código, citas, imágenes, pestañas y avisos).
 *
 * Uso:
 *   node web2md.js <url> [--out <dir>] [--scope </ruta/>] [--content <selector>]
 *                              [--concurrency 4] [--delay 150] [--no-images] [--merge]
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

/* ---------- CLI ---------- */

function parseArgs(argv) {
  const opts = { concurrency: 4, delay: 150, images: true, merge: false, content: null, scope: null, out: null };
  const rest = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--out') opts.out = argv[++i];
    else if (a === '--scope') opts.scope = argv[++i];
    else if (a === '--content') opts.content = argv[++i];
    else if (a === '--concurrency') opts.concurrency = Number(argv[++i]);
    else if (a === '--delay') opts.delay = Number(argv[++i]);
    else if (a === '--no-images') opts.images = false;
    else if (a === '--merge') opts.merge = true;
    else if (a === '-h' || a === '--help') opts.help = true;
    else rest.push(a);
  }
  opts.url = rest[0];
  return opts;
}

/* ---------- Parser HTML mínimo ---------- */

const VOID = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr']);
const RAW = new Set(['script', 'style']);
const NAMED = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', hellip: '…', mdash: '—', ndash: '–', laquo: '«', raquo: '»', copy: '©' };

function decodeEntities(s) {
  return s.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, e) => {
    if (e[0] === '#') {
      const code = e[1].toLowerCase() === 'x' ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10);
      return Number.isFinite(code) ? String.fromCodePoint(code) : m;
    }
    return NAMED[e.toLowerCase()] ?? m;
  });
}

function parseAttrs(s) {
  const attrs = {};
  const re = /([^\s=\/]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+)))?/g;
  let m;
  while ((m = re.exec(s))) attrs[m[1].toLowerCase()] = decodeEntities(m[2] ?? m[3] ?? m[4] ?? '');
  return attrs;
}

function parseHtml(html) {
  const root = { tag: '#root', attrs: {}, children: [], parent: null };
  let cur = root;
  const re = /<!--[\s\S]*?-->|<(\/?)([a-zA-Z][\w:.-]*)((?:"[^"]*"|'[^']*'|[^'">])*?)(\/?)>|<![^>]*>|[^<]+|</g;
  let m;
  while ((m = re.exec(html))) {
    const [full, closing, name, attrStr, selfClose] = m;
    if (name === undefined) {
      if (full.startsWith('<!') || full === '<') continue;
      cur.children.push({ text: decodeEntities(full), parent: cur });
      continue;
    }
    const tag = name.toLowerCase();
    if (closing) {
      let n = cur;
      while (n && n.tag !== tag) n = n.parent;
      if (n && n.parent) cur = n.parent;
      continue;
    }
    const node = { tag, attrs: parseAttrs(attrStr), children: [], parent: cur };
    cur.children.push(node);
    if (RAW.has(tag)) {
      const end = html.toLowerCase().indexOf('</' + tag, re.lastIndex);
      re.lastIndex = end === -1 ? html.length : html.indexOf('>', end) + 1;
    } else if (!VOID.has(tag) && !selfClose) cur = node;
  }
  return root;
}

const isText = (n) => n.text !== undefined;
const classes = (n) => (n.attrs && n.attrs.class ? n.attrs.class.split(/\s+/) : []);
const hasClass = (n, c) => !isText(n) && classes(n).includes(c);

function matches(n, sel) {
  if (isText(n)) return false;
  if (sel[0] === '.') return hasClass(n, sel.slice(1));
  if (sel[0] === '#') return n.attrs.id === sel.slice(1);
  return n.tag === sel;
}

function findAll(node, pred, out = []) {
  for (const c of node.children || []) {
    if (pred(c)) out.push(c);
    if (!isText(c)) findAll(c, pred, out);
  }
  return out;
}
const findFirst = (node, pred) => findAll(node, pred)[0] || null;

function textContent(n) {
  return isText(n) ? n.text : (n.children || []).map(textContent).join('');
}

/* ---------- Conversión HTML -> Markdown ---------- */

const SKIP = new Set(['script', 'style', 'svg', 'button', 'link', 'meta', 'nav', 'footer', 'select', 'option', 'label', 'noscript', 'iframe', 'form', 'input', 'template']);
const INLINE = new Set(['a', 'span', 'strong', 'b', 'em', 'i', 'code', 'kbd', 'img', 'br', 'del', 's', 'sup', 'sub', 'mark', 'abbr', 'small', 'u', 'time', 'cite', 'q', 'samp', 'var']);
const BLOCK = new Set(['p', 'div', 'ul', 'ol', 'li', 'pre', 'table', 'blockquote', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'figure', 'aside', 'details', 'section', 'article']);

function shouldSkip(n) {
  return isText(n) ? false : SKIP.has(n.tag) || hasClass(n, 'sr-only') || n.attrs.role === 'tablist';
}

function hasBlockDesc(n) {
  return findAll(n, (c) => !isText(c) && BLOCK.has(c.tag)).length > 0;
}

function wrap(marker, s) {
  const m = s.match(/^(\s*)([\s\S]*?)(\s*)$/);
  return m[2] ? m[1] + marker + m[2] + marker + m[3] : s;
}

function inlineCode(s) {
  s = s.replace(/\s+/g, ' ');
  const longest = Math.max(0, ...(s.match(/`+/g) || []).map((x) => x.length));
  const fence = '`'.repeat(longest + 1);
  const pad = s.startsWith('`') || s.endsWith('`') ? ' ' : '';
  return fence + pad + s + pad + fence;
}

class Converter {
  constructor({ pageUrl, resolveLink, resolveImage }) {
    this.pageUrl = pageUrl;
    this.resolveLink = resolveLink;
    this.resolveImage = resolveImage;
    this.tabLabels = {};
    this.inCell = false;
  }

  convert(root) {
    for (const t of findAll(root, (n) => n.attrs && n.attrs.role === 'tab')) {
      this.tabLabels[t.attrs.id] = textContent(t).replace(/\s+/g, ' ').trim();
    }
    return this.blocks(root.children).join('\n\n').replace(/\n{3,}/g, '\n\n').trim();
  }

  inline(n, inHeading = false) {
    if (isText(n)) return n.text.replace(/\s+/g, ' ');
    if (shouldSkip(n)) return '';
    const kids = () => n.children.map((c) => this.inline(c, inHeading)).join('');
    switch (n.tag) {
      case 'br': return this.inCell ? '<br>' : '  \n';
      case 'img': return this.image(n);
      case 'a': {
        const text = kids().trim();
        const href = n.attrs.href;
        if (!href || !text) return text;
        if (inHeading && href.startsWith('#')) return text;
        return `[${text}](${this.resolveLink(href, this.pageUrl)})`;
      }
      case 'strong': case 'b': return wrap('**', kids());
      case 'em': case 'i': return wrap('*', kids());
      case 'del': case 's': return wrap('~~', kids());
      case 'code': case 'kbd': case 'samp': return inlineCode(textContent(n));
      default: return kids();
    }
  }

  image(n) {
    const src = n.attrs.src;
    if (!src) return '';
    const alt = (n.attrs.alt || '').replace(/[\[\]\n]/g, ' ').trim();
    return `![${alt}](${this.resolveImage(src, this.pageUrl)})`;
  }

  blocks(nodes) {
    const out = [];
    let buf = '';
    const flush = () => {
      const t = buf.trim().replace(/ {2,}(?!\n)/g, ' ').replace(/\n +/g, '\n');
      if (t) out.push(t);
      buf = '';
    };
    for (const n of nodes) {
      if (isText(n)) { buf += n.text.replace(/\s+/g, ' '); continue; }
      if (shouldSkip(n)) continue;
      if (INLINE.has(n.tag) && !(n.tag !== 'img' && hasBlockDesc(n))) { buf += this.inline(n); continue; }
      flush();
      const b = this.block(n);
      if (Array.isArray(b)) out.push(...b);
      else if (b) out.push(b);
    }
    flush();
    return out;
  }

  heading(n) {
    const level = Number(n.tag[1]);
    const text = n.children.map((c) => this.inline(c, true)).join('').replace(/\s+/g, ' ').trim();
    return text ? '#'.repeat(level) + ' ' + text : null;
  }

  block(n) {
    switch (n.tag) {
      case 'h1': case 'h2': case 'h3': case 'h4': case 'h5': case 'h6': return this.heading(n);
      case 'p': return this.blocks(n.children).join('\n\n') || null;
      case 'ul': case 'ol': return this.list(n);
      case 'pre': return this.codeBlock(n, '');
      case 'blockquote': return this.quote(this.blocks(n.children));
      case 'table': return this.table(n);
      case 'hr': return '---';
      case 'aside': return this.callout(n);
      case 'details': return this.details(n);
      case 'figure': {
        const pre = findFirst(n, (c) => c.tag === 'pre');
        if (pre) {
          const title = findFirst(n, (c) => hasClass(c, 'title'));
          return this.codeBlock(pre, title ? textContent(title).trim() : '');
        }
        return this.blocks(n.children);
      }
      default:
        if (n.attrs.role === 'tabpanel') {
          const label = this.tabLabels[n.attrs['aria-labelledby']];
          return [...(label ? [`**${label}**`] : []), ...this.blocks(n.children)];
        }
        return this.blocks(n.children);
    }
  }

  list(n) {
    const ordered = n.tag === 'ol';
    const start = Number(n.attrs.start) || 1;
    const items = n.children.filter((c) => !isText(c) && c.tag === 'li');
    const loose = items.some((li) => this.blocks(li.children).some((b, j) => j > 0 && !/^(?:[-*]|\d+\.) /.test(b)));
    const rendered = items.map((li, i) => {
      const marker = ordered ? `${start + i}. ` : '- ';
      const indent = ' '.repeat(marker.length);
      let body = '';
      this.blocks(li.children).forEach((b, j) => {
        const isList = /^(?:[-*]|\d+\.) /.test(b);
        body += j === 0 ? b : (isList ? '\n' : '\n\n') + b;
      });
      return body.split('\n').map((l, j) => (j === 0 ? marker + l : l ? indent + l : l)).join('\n');
    });
    return rendered.join(loose ? '\n\n' : '\n');
  }

  quote(blocks) {
    return blocks.join('\n\n').split('\n').map((l) => (l ? '> ' + l : '>')).join('\n') || null;
  }

  callout(n) {
    const titleNode = findFirst(n, (c) => hasClass(c, 'starlight-aside__title'));
    const contentNode = findFirst(n, (c) => hasClass(c, 'starlight-aside__content'));
    const title = titleNode ? textContent(titleNode).replace(/\s+/g, ' ').trim() : '';
    const body = this.blocks((contentNode || n).children);
    return this.quote([...(title ? [`**${title}**`] : []), ...body]);
  }

  details(n) {
    const summary = n.children.find((c) => !isText(c) && c.tag === 'summary');
    const rest = n.children.filter((c) => c !== summary);
    const title = summary ? textContent(summary).replace(/\s+/g, ' ').trim() : '';
    return [...(title ? [`**${title}**`] : []), ...this.blocks(rest)];
  }

  codeBlock(pre, title) {
    const lines = findAll(pre, (c) => hasClass(c, 'ec-line'));
    const raw = lines.length
      ? lines.map((l) => textContent(findFirst(l, (c) => hasClass(c, 'code')) || l)).join('\n')
      : textContent(pre);
    const code = raw.replace(/\n+$/, '');
    let lang = pre.attrs['data-language'] || '';
    if (!lang) {
      const codeEl = findFirst(pre, (c) => c.tag === 'code');
      const cls = codeEl && classes(codeEl).find((c) => c.startsWith('language-'));
      lang = cls ? cls.slice(9) : '';
    }
    if (['plaintext', 'text', 'ansi'].includes(lang)) lang = '';
    const longest = Math.max(0, ...(code.match(/`{3,}/g) || []).map((x) => x.length));
    const fence = '`'.repeat(Math.max(3, longest + 1));
    const block = `${fence}${lang}\n${code}\n${fence}`;
    return title ? [`**${title}**`, block] : block;
  }

  table(n) {
    const rows = findAll(n, (c) => c.tag === 'tr').map((tr) =>
      tr.children.filter((c) => !isText(c) && (c.tag === 'th' || c.tag === 'td')).map((cell) => {
        this.inCell = true;
        const text = this.blocks(cell.children).join('<br>').replace(/\n/g, '<br>').replace(/\|/g, '\\|');
        this.inCell = false;
        return text.trim();
      }));
    if (!rows.length) return null;
    const cols = Math.max(...rows.map((r) => r.length));
    const pad = (r) => [...r, ...Array(cols - r.length).fill('')];
    const hasHead = findFirst(n, (c) => c.tag === 'thead') || findFirst(n, (c) => c.tag === 'th');
    const head = hasHead ? rows.shift() : Array(cols).fill('');
    const fmt = (r) => '| ' + pad(r).join(' | ') + ' |';
    return [fmt(head), '| ' + Array(cols).fill('---').join(' | ') + ' |', ...rows.map(fmt)].join('\n');
  }
}

/* ---------- Crawler ---------- */

const UA = 'Mozilla/5.0 (compatible; web2md/1.0; +documentacion-offline)';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function fetchWithRetry(url, tries = 3) {
  let err;
  for (let i = 0; i < tries; i++) {
    try {
      const res = await fetch(url, { headers: { 'user-agent': UA }, redirect: 'follow' });
      if (res.ok) return res;
      err = new Error(`HTTP ${res.status}`);
      if (res.status === 404) break;
    } catch (e) { err = e; }
    await sleep(500 * (i + 1));
  }
  throw new Error(`${url}: ${err.message}`);
}

const normPath = (p) => (p.replace(/\/+$/, '') || '/');

function inScope(u, origin, scope) {
  if (u.origin !== origin) return false;
  const p = normPath(u.pathname);
  if (!(p === scope || p.startsWith(scope === '/' ? '/' : scope + '/'))) return false;
  if (/\.(png|jpe?g|gif|svg|webp|avif|css|js|mjs|xml|json|pdf|zip|ico|txt|woff2?)$/i.test(p)) return false;
  return !p.split('/').some((s) => s.startsWith('_'));
}

function extractLinks(html, baseUrl) {
  const out = [];
  const re = /<a\b[^>]*?\bhref\s*=\s*(?:"([^"]*)"|'([^']*)')/gi;
  let m;
  while ((m = re.exec(html))) {
    try { out.push(new URL(decodeEntities(m[1] ?? m[2]), baseUrl)); } catch { /* href inválido */ }
  }
  return out;
}

function pageFile(pathname, scope) {
  let rel = normPath(pathname).slice(scope === '/' ? 1 : scope.length).replace(/^\//, '');
  rel = rel ? decodeURIComponent(rel) : 'index';
  return rel.replace(/[^\w\-\/.]+/g, '-') + '.md';
}

function pageMeta(html, tree, contentSel) {
  const h1 = findFirst(tree, (n) => n.tag === 'h1');
  const title = (h1 ? textContent(h1) : (html.match(/<title>([^<]*)/i) || [])[1] || '').replace(/\s+/g, ' ').trim();
  const descNode = findFirst(tree, (n) => hasClass(n, 'page-description'));
  const metaDesc = html.match(/<meta\s+name="description"\s+content="([^"]*)"/i);
  const description = descNode ? textContent(descNode).replace(/\s+/g, ' ').trim() : metaDesc ? decodeEntities(metaDesc[1]) : '';
  const selectors = contentSel ? [contentSel] : ['.sl-markdown-content', 'article', 'main', 'body'];
  let content = null;
  for (const s of selectors) {
    content = findFirst(tree, (n) => matches(n, s));
    if (content) break;
  }
  return { title, description, content: content || tree };
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help || !opts.url) {
    console.log('Uso: node web2md.js <url> [--out dir] [--scope /ruta/] [--content selector] [--concurrency 4] [--delay 150] [--no-images] [--merge]');
    process.exit(opts.help ? 0 : 1);
  }
  const start = new URL(opts.url);
  const origin = start.origin;
  const scope = normPath(opts.scope || start.pathname);
  const outDir = path.resolve(opts.out || ((start.hostname + scope).replace(/[^\w]+/g, '-').replace(/-+$/, '')));
  const assetsDir = path.join(outDir, 'assets');
  fs.mkdirSync(outDir, { recursive: true });

  /* 1. Descubrir y descargar páginas */
  const pages = new Map(); // key (pathname normalizado) -> { url, html }
  const order = [];
  const queued = new Set();
  const enqueue = (u) => {
    const key = normPath(u.pathname);
    if (queued.has(key) || !inScope(u, origin, scope)) return;
    queued.add(key);
    order.push(key);
    queue.push(new URL(key === '/' ? '/' : key + '/', origin));
  };
  const queue = [];
  enqueue(start);
  const failed = [];
  let active = 0;
  await new Promise((resolve) => {
    const pump = () => {
      while (active < opts.concurrency && queue.length) {
        const u = queue.shift();
        active++;
        (async () => {
          await sleep(opts.delay);
          try {
            const res = await fetchWithRetry(u.href);
            if (!(res.headers.get('content-type') || '').includes('html')) return;
            const html = await res.text();
            pages.set(normPath(u.pathname), { url: u.href, html });
            for (const l of extractLinks(html, res.url || u.href)) enqueue(l);
            console.log(`  ✓ ${u.pathname}`);
          } catch (e) {
            failed.push(e.message);
            console.warn(`  ✗ ${e.message}`);
          }
        })().finally(() => { active--; if (!queue.length && !active) resolve(); else pump(); });
      }
      if (!queue.length && !active) resolve();
    };
    pump();
  });
  const keys = order.filter((k) => pages.has(k));
  const fileOf = new Map(keys.map((k) => [k, pageFile(k, scope)]));
  console.log(`${keys.length} páginas descargadas.`);

  /* 2. Convertir */
  const images = new Map(); // url absoluta -> nombre de fichero en assets/
  const usedNames = new Set();
  let currentFile = 'index.md';
  const relFrom = (target) => path.relative(path.dirname(currentFile), target).split(path.sep).join('/');

  const resolveLink = (href, base) => {
    if (/^(mailto:|tel:|javascript:)/i.test(href)) return href;
    let u;
    try { u = new URL(href, base); } catch { return href; }
    if (href.startsWith('#')) return href;
    const key = normPath(u.pathname);
    if (inScope(u, origin, scope) && fileOf.has(key)) {
      const file = fileOf.get(key);
      return (file === currentFile ? '' : relFrom(file)) + u.hash;
    }
    return u.href;
  };

  const resolveImage = (src, base) => {
    let u;
    try { u = new URL(src, base); } catch { return src; }
    if (!opts.images || u.protocol === 'data:') return u.protocol === 'data:' ? '' : u.href;
    if (!images.has(u.href)) {
      let name = decodeURIComponent(path.basename(u.pathname)).replace(/[^\w.\-]+/g, '-') || 'image';
      if (usedNames.has(name)) name = crypto.createHash('sha1').update(u.href).digest('hex').slice(0, 8) + '-' + name;
      usedNames.add(name);
      images.set(u.href, name);
    }
    return relFrom('assets/' + images.get(u.href));
  };

  const today = new Date().toISOString().slice(0, 10);
  const summary = [];
  const merged = [];
  for (const key of keys) {
    const { url, html } = pages.get(key);
    currentFile = fileOf.get(key);
    const tree = parseHtml(html);
    const { title, description, content } = pageMeta(html, tree, opts.content);
    const conv = new Converter({ pageUrl: url, resolveLink, resolveImage });
    const body = conv.convert(content);
    const front = ['---', `title: ${JSON.stringify(title)}`, ...(description ? [`description: ${JSON.stringify(description)}`] : []), `source: ${url}`, `downloaded: ${today}`, '---'].join('\n');
    const md = `${front}\n\n# ${title}\n\n${description ? description + '\n\n' : ''}${body}\n`;
    const target = path.join(outDir, currentFile);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, md);
    summary.push({ title, description, file: currentFile, words: body.split(/\s+/).filter(Boolean).length });
    merged.push(`<!-- ${url} -->\n\n# ${title}\n\n${description ? description + '\n\n' : ''}${body.replace(/^(#{1,5}) /gm, '$1# ')}\n`);
  }

  /* 3. Imágenes */
  if (opts.images && images.size) {
    fs.mkdirSync(assetsDir, { recursive: true });
    let n = 0;
    for (const [url, name] of images) {
      try {
        const res = await fetchWithRetry(url);
        fs.writeFileSync(path.join(assetsDir, name), Buffer.from(await res.arrayBuffer()));
        n++;
      } catch (e) { failed.push(e.message); console.warn(`  ✗ imagen ${e.message}`); }
      await sleep(opts.delay);
    }
    console.log(`${n}/${images.size} imágenes descargadas.`);
  }

  /* 4. Índice y fichero único opcional */
  const idx = [`# Índice de ${start.hostname}${scope}`, '', `Origen: ${opts.url}`, `Descargado: ${today}`, `Páginas: ${summary.length}`, '', '| Página | Descripción | Palabras |', '| --- | --- | ---: |',
    ...summary.map((s) => `| [${s.title}](${s.file}) | ${s.description.replace(/\|/g, '\\|')} | ${s.words} |`)];
  fs.writeFileSync(path.join(outDir, 'README.md'), idx.join('\n') + '\n');
  if (opts.merge) fs.writeFileSync(path.join(outDir, '_completo.md'), merged.join('\n---\n\n'));

  console.log(`Salida: ${path.relative(process.cwd(), outDir) || '.'}`);
  if (failed.length) { console.warn(`${failed.length} errores.`); process.exitCode = 1; }
}

main().catch((e) => { console.error(e); process.exit(1); });
