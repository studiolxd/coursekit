// The live gallery (`coursekit video gallery --serve`): every scene and layer the course can use, played in the browser with the
// player of Remotion and the same components the render uses, in the theme and the style of the project. The interface is
// coursekit's, so it wears the design system of Studio LXD (@studiolxd/brand); the pieces wear the brand of the project. The
// two never mix: the piece is drawn in a frame of its own (stage.html, this same bundle with ?stage) that loads no CSS of
// Studio LXD, and the interface sends it what to draw. coursekit writes the data in window.__GALLERY__ (data.js) and bundles
// this file with esbuild (app.js and app.css).
import React from "react";
import { createRoot } from "react-dom/client";
import { Player, type PlayerRef } from "@remotion/player";
import "@studiolxd/brand/brand.css";
import "@studiolxd/brand/fonts.css";
import { Alert } from "@studiolxd/brand/alert";
import { AppHeader } from "@studiolxd/brand/app-header";
import { AppShell } from "@studiolxd/brand/app-shell";
import { Code } from "@studiolxd/brand/code";
import { CodeBlock } from "@studiolxd/brand/code-block";
import { Heading as BrandHeading } from "@studiolxd/brand/heading";
import { Icon } from "@studiolxd/brand/icon";
import { InputField } from "@studiolxd/brand/input-field";
import { Logo } from "@studiolxd/brand/logo";
import { Paragraph } from "@studiolxd/brand/paragraph";
import { SelectField } from "@studiolxd/brand/select-field";
import { Sidebar } from "@studiolxd/brand/sidebar";
import { SidebarNav, type SidebarNavEntry } from "@studiolxd/brand/sidebar-nav";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@studiolxd/brand/table";
import { Tag } from "@studiolxd/brand/tag";
import { TextareaField } from "@studiolxd/brand/textarea-field";
import { Montage, type MontageProps } from "../Montage";
import { Badge } from "../atoms/Badge";
import { Card } from "../atoms/Card";
import { Heading } from "../atoms/Heading";
import { Text } from "../atoms/Text";
import { ThemeProvider } from "../theme";

type Rule = { type?: string; values?: string[]; required?: boolean; max_chars?: number; max_items?: number; help?: string;
  when?: Record<string, string | string[]> };
type Piece = { kind: "scenes" | "layers"; name: string; label: string; origin: string; description: string; props: Record<string, Rule>;
  example: Record<string, unknown> | null; variants: { name: string; label: string; props: Record<string, unknown> }[] };
type Data = { title: string; base: Record<string, unknown>; samples: string[]; seconds: number; labels: Record<string, string>;
  montage: Omit<MontageProps, "scenes" | "frames">; pieces: Piece[]; swatches: [string, string][];
  /** The rendered gallery: every piece and variant already rendered, a clip each, instead of the player. */
  rendered?: boolean; clips?: Record<string, { clip: string; poster: string }> };
type Show = { type: "piece"; piece: Piece; props: Record<string, unknown> } | { type: "specimen" } | { type: "shapes" };

const data = (window as unknown as { __GALLERY__: Data }).__GALLERY__;
const L = data.labels;
const TYPOGRAPHY = "typography";
const cap = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);
const COLOURS = "colours";
const SHAPES = "shapes";
const STYLE_PAGES = [TYPOGRAPHY, COLOURS, SHAPES];
const NONE = "__none";  // the option of a select that leaves the prop to its default
// The page and its frame talk by messages; opened from the disk (the rendered gallery) the browser gives them no origin.
const TARGET = location.protocol === "file:" ? "*" : location.origin;

// What the person had chosen survives the reload that follows a change of the project (sessionStorage, this tab only).
const saved = (key: string) => { try { return JSON.parse(sessionStorage.getItem(key) ?? "null"); } catch { return null; } };
const keep = (key: string, value: unknown) => { try { sessionStorage.setItem(key, JSON.stringify(value)); } catch { /* private mode */ } };

// A prop that only counts with another value (`when:` of its metadata) is hidden while that value is not chosen.
const applies = (rule: Rule, props: Record<string, unknown>) =>
  Object.entries(rule.when ?? {}).every(([key, want]) => (Array.isArray(want) ? want : [want]).includes(String(props[key] ?? "")));

// A value kept from before that the project no longer allows becomes the first one it does.
const allowedNow = (piece: Piece, props: Record<string, unknown>) => {
  const out: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(props)) {
    const rule = piece.props[key];
    if (!rule) continue;
    out[key] = rule.type === "choice" && rule.values && !rule.values.includes(String(value)) ? rule.values[0] : value;
  }
  return out;
};

// ── the stage: the piece alone, in the brand of the project, in its own frame ──────────────────────────────────────────────

const ROLES = ["display", "heading", "subheading", "kicker", "body", "quote", "statement", "label", "stat", "step", "caption"];
const HEADINGS = new Set(["display", "heading", "quote", "statement", "stat"]);

const Specimen: React.FC = () => {
  const m = data.montage;
  const sample = (role: string) => (role === "stat" ? "1.234" : role === "step" ? "1 2 3" : L[`sample_${role}`] ?? role);
  return (
    <ThemeProvider theme={{ tokens: m.tokens, motion: m.motion, style: m.style }}>
      {m.style?.fonts ? <style>{m.style.fonts.css}</style> : null}
      <div style={{ background: m.tokens.color.background, padding: 24 }}>
        {ROLES.map((role) => {
          const values = Object.entries(m.style?.text?.[role] ?? {}).map(([k, v]) => `${k}: ${v}`).join(" · ");
          const size = m.style?.textBase?.[role] ?? 48;
          return (
            <div key={role} style={{ borderTop: "1px solid #e5e5e5", padding: "12px 0" }}>
              <div style={{ fontFamily: m.tokens.font.family, fontSize: 13, color: m.tokens.color["text-muted"] ?? m.tokens.color.text,
                marginBottom: 6 }}><strong>{role}</strong> {values}</div>
              <div style={{ zoom: 0.5 }}>
                {HEADINGS.has(role) ? <Heading role={role} size={size}>{sample(role)}</Heading> : <Text role={role} size={size}>{sample(role)}</Text>}
              </div>
            </div>
          );
        })}
      </div>
    </ThemeProvider>
  );
};

// The shapes of the project drawn: a panel with its radius, border and shadow, the marks of the steps, and the two weights.
const Shapes: React.FC = () => {
  const m = data.montage;
  return (
    <ThemeProvider theme={{ tokens: m.tokens, motion: m.motion, style: m.style }}>
      {m.style?.fonts ? <style>{m.style.fonts.css}</style> : null}
      <div style={{ background: m.tokens.color.background, padding: 32, zoom: 0.5, display: "grid", gap: 40 }}>
        <div style={{ display: "flex", gap: 40 }}>
          <Card style={{ flex: 1 }}><Heading size={56}>{L.sample_heading}</Heading><Text size={40} tone="text-muted">{L.sample_body}</Text></Card>
          <Card tone="background" style={{ flex: 1 }}><Heading size={56}>{L.sample_heading}</Heading><Text size={40}>{L.sample_body}</Text></Card>
        </div>
        <div style={{ display: "flex", gap: 24, alignItems: "center" }}>
          <Badge size={88}>1</Badge><Badge size={88}>2</Badge><Badge size={88}>3</Badge>
          <Text size={48} weight={400}>{L.weight_normal}</Text><Text size={48} weight={700}>{L.weight_strong}</Text>
        </div>
      </div>
    </ThemeProvider>
  );
};

const Stage: React.FC = () => {
  const [show, setShow] = React.useState<Show | null>(null);
  const player = React.useRef<PlayerRef>(null);
  const m = data.montage;
  const frames = Math.round(data.seconds * m.fps);
  // it plays once and stays on the last frame with everything in (the very last ones fade out to the next scene)
  React.useEffect(() => {
    const current = player.current;
    if (!current) return;
    const rest = () => current.seekTo(Math.max(0, frames - m.motion.fade - 2));
    current.addEventListener("ended", rest);
    return () => current.removeEventListener("ended", rest);
  });
  React.useEffect(() => {
    const listen = (event: MessageEvent) => { if (event.source === window.parent && event.data?.type && event.data.type !== "ready") setShow(event.data); };
    window.addEventListener("message", listen);
    window.parent.postMessage({ type: "ready" }, TARGET);
    return () => window.removeEventListener("message", listen);
  }, []);
  if (!show) return null;
  if (show.type === "specimen") return <Specimen />;
  if (show.type === "shapes") return <Shapes />;
  const { piece, props } = show;
  const scene = piece.kind === "scenes"
    ? { id: piece.name, type: piece.name, props, layers: [] }
    : { id: "base", type: "title", props: data.base, layers: [{ id: piece.name, type: piece.name, from: 0, frames, props }] };
  const input: MontageProps = { ...m, frames, scenes: [{ ...scene, from: 0, frames, audio: null, words: [] }] };
  return (
    <Player ref={player} component={Montage as unknown as React.FC<Record<string, unknown>>} inputProps={input as unknown as Record<string, unknown>}
      durationInFrames={frames} fps={m.fps} compositionWidth={m.width} compositionHeight={m.height}
      style={{ width: "100vw", height: "100vh" }} controls autoPlay initiallyMuted moveToBeginningWhenEnded={false} acknowledgeRemotionLicense />
  );
};

// The frame that shows the piece: it asks for what to draw when it is ready, and gets it again on every change.
const Frame: React.FC<{ show: Show; tall?: boolean }> = ({ show, tall }) => {
  const ref = React.useRef<HTMLIFrameElement>(null);
  const send = React.useCallback(() => ref.current?.contentWindow?.postMessage(show, TARGET), [show]);
  React.useEffect(() => {
    const ready = (event: MessageEvent) => { if (event.source === ref.current?.contentWindow && event.data?.type === "ready") send(); };
    window.addEventListener("message", ready);
    return () => window.removeEventListener("message", ready);
  }, [send]);
  React.useEffect(send, [send]);
  const m = data.montage;
  return (
    <iframe ref={ref} src="stage.html" title={show.type === "piece" ? show.piece.name : L[show.type === "shapes" ? "shapes" : "typography"]}
      style={{ width: "100%", aspectRatio: tall ? undefined : `${m.width} / ${m.height}`, height: tall ? (show.type === "shapes" ? 250 : 1500) : undefined,
        border: "1px solid currentColor", display: "block", background: "#fff" }} />
  );
};

// A piece of the rendered gallery: its clip, played once, with the frame where everything is in as its poster.
const Clip: React.FC<{ id: string }> = ({ id }) => {
  const found = data.clips?.[id];
  if (!found) return <Alert tone="warning" description={L.no_example} />;
  const m = data.montage;
  return (
    <video key={id} src={found.clip} poster={found.poster} controls autoPlay muted playsInline
      onEnded={(e) => { e.currentTarget.currentTime = Math.max(0, (data.seconds * m.fps - m.motion.fade - 2) / m.fps); }}
      style={{ width: "100%", aspectRatio: `${m.width} / ${m.height}`, display: "block", border: "1px solid currentColor", background: "#fff" }} />
  );
};

// ── the interface: coursekit's, in the design system of Studio LXD ───────────────────────────────────────────────────────

// The server builds the gallery again when the project changes and counts it in version.json: the page reloads itself.
const useVersion = () => {
  const [error, setError] = React.useState<string | null>(null);
  React.useEffect(() => {
    if (data.rendered) return;  // the rendered gallery has no server
    let first: number | null = null;
    const id = setInterval(() => {
      fetch("version.json", { cache: "no-store" }).then((r) => r.json()).then((v: { version: number; error: string | null }) => {
        if (first === null) first = v.version;
        setError(v.error);
        if (v.version !== first && !v.error) location.reload();
      }).catch(() => { /* the server stopped */ });
    }, 1000);
    return () => clearInterval(id);
  }, []);
  return error;
};

const Control: React.FC<{ id: string; name: string; rule: Rule; value: unknown; set: (v: unknown) => void }> = ({ id, name, rule, value, set }) => {
  const [text, setText] = React.useState(() => (value === undefined ? "" : JSON.stringify(value, null, 1)));
  if (rule.type === "choice" || rule.type === "media") {
    const first = rule.type === "choice" ? L.default : L.none;
    const values = rule.type === "choice" ? rule.values ?? [] : data.samples;
    return (
      <SelectField id={id} label={name} labelHidden size="sm" value={value === undefined ? NONE : String(value)}
        options={[{ value: NONE, label: first }, ...values.map((v) => ({ value: v, label: v }))]}
        onValueChange={(v) => set(v === NONE ? undefined : v)} />
    );
  }
  if (rule.type === "list" || rule.type === "object") {  // nested props: as JSON, applied when it parses
    return (
      <TextareaField id={id} label={name} labelHidden size="sm" rows={5} value={text}
        onChange={(e) => { setText(e.target.value); try { set(e.target.value.trim() ? JSON.parse(e.target.value) : undefined); } catch { /* typing */ } }} />
    );
  }
  const current = value === undefined ? "" : String(value);
  const over = Boolean(rule.max_chars && current.length > rule.max_chars);
  const count = rule.max_chars ? `${current.length} / ${rule.max_chars}` : undefined;
  return (rule.max_chars ?? 0) > 70
    ? <TextareaField id={id} label={name} labelHidden size="sm" rows={2} value={current} error={over} helperText={count}
        onChange={(e) => set(e.target.value || undefined)} />
    : <InputField id={id} label={name} labelHidden size="sm" value={current} error={over} helperText={count}
        onChange={(e) => set(e.target.value || undefined)} />;
};

const Detail: React.FC<{ piece: Piece }> = ({ piece }) => {
  const start = React.useMemo(() => ({ ...(piece.example ?? {}) }), [piece]);
  const key = `gallery:${piece.kind}:${piece.name}`;
  const [props, setProps] = React.useState<Record<string, unknown>>(() => allowedNow(piece, saved(`${key}:props`) ?? start));
  const [variant, setVariant] = React.useState<string>(() => saved(`${key}:variant`) ?? NONE);
  React.useEffect(() => { keep(`${key}:props`, props); keep(`${key}:variant`, variant); }, [key, props, variant]);
  const pick = (name: string) => {
    setVariant(name);
    const chosen = piece.variants.find((v) => v.name === name);
    setProps({ ...start, ...(chosen?.props ?? {}) });
  };
  const set = (name: string, value: unknown) => setProps((old) => {
    const next = { ...old };
    if (value === undefined) delete next[name]; else next[name] = value;
    return next;
  });
  const show: Show = React.useMemo(() => ({ type: "piece", piece, props }), [piece, props]);
  const lines = Object.entries(props).map(([k, v]) => `    ${k}: ${JSON.stringify(v)}`);
  const snippet = piece.kind === "scenes"
    ? `- id: …\n  type: ${piece.name}\n  props:\n${lines.join("\n")}`
    : `  layers:\n    - type: ${piece.name}\n      props:\n${lines.map((l) => "    " + l).join("\n")}`;
  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr)", gap: 20, maxWidth: 1100, minWidth: 0 }}>
      <div>
        <BrandHeading level={1} size={5}>{piece.label}</BrandHeading>
        <div style={{ display: "flex", gap: 8, margin: "8px 0" }}>
          <Tag tone="primary">{cap(L[piece.kind])}</Tag><Tag tone="neutral">{cap(piece.origin)}</Tag>
          <Tag tone="accent-1" title={L.id_hint}>{piece.name}</Tag>
        </div>
        <Paragraph>{piece.description}</Paragraph>
        {data.rendered ? <Paragraph size="sm">{L.rendered_hint}</Paragraph> : null}
      </div>
      {data.rendered ? <Clip id={variant === NONE ? piece.name : `${piece.name}-${variant}`} />
        : piece.example ? <Frame show={show} /> : <Alert tone="warning" description={L.no_example} />}
      {piece.variants.length ? (
        <div style={{ maxWidth: 360 }}>
          <SelectField id={`${key}-variant`} label={L.variant} size="sm" value={variant}
            options={[{ value: NONE, label: L.example }, ...piece.variants.map((v) => ({ value: v.name, label: v.label }))]}
            onValueChange={pick} />
        </div>
      ) : null}
      <div style={{ overflowX: "auto" }}><Table size="sm">
        <TableHead>
          <TableRow>{["prop", "type", data.rendered ? "value" : "control", "help"].map((c) => <TableHeader key={c}>{L[`col_${c}`]}</TableHeader>)}</TableRow>
        </TableHead>
        <TableBody>
          {Object.entries(piece.props).filter(([, rule]) => applies(rule, props)).map(([name, rule]) => (
            <TableRow key={`${piece.name}-${name}`}>
              <TableCell><Code>{name}</Code>{rule.required ? " *" : ""}</TableCell>
              <TableCell>{rule.type}</TableCell>
              <TableCell style={{ minWidth: 260 }}>{data.rendered
                ? (props[name] === undefined ? L.default : typeof props[name] === "string" ? String(props[name]) : <Code>{JSON.stringify(props[name])}</Code>)
                : <Control key={`${piece.name}-${name}-${variant}`} id={`${key}-${name}`} name={name} rule={rule} value={props[name]}
                    set={(v) => set(name, v)} />}</TableCell>
              <TableCell>{rule.help}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table></div>
      <div>
        <Paragraph size="sm">{L.code}</Paragraph>
        <CodeBlock language="yaml" copyable>{snippet}</CodeBlock>
      </div>
    </div>
  );
};

const Page: React.FC<{ title: string; intro: string; children: React.ReactNode }> = ({ title, intro, children }) => (
  <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr)", gap: 16, maxWidth: 1100, minWidth: 0 }}>
    <BrandHeading level={1} size={5}>{title}</BrandHeading>
    <Paragraph>{intro}</Paragraph>
    {children}
  </div>
);

// The colours of the theme of the project, each role with its value: what the pieces paint with.
const Colours: React.FC = () => (
  <Page title={L.colours} intro={L.colours_intro}>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 16 }}>
      {data.swatches.map(([name, hex]) => (
        <div key={name} style={{ border: "1px solid currentColor" }}>
          <div style={{ height: 72, background: hex, borderBottom: "1px solid currentColor" }} />
          <div style={{ padding: "8px 10px" }}><Code>{name}</Code><div style={{ fontSize: 13 }}>{hex}</div></div>
        </div>
      ))}
    </div>
  </Page>
);

// The shapes and the weights of the style of the project (config/video.yaml), in values and drawn.
const ShapesPage: React.FC<{ show: Show }> = ({ show }) => {
  const s = data.montage.style ?? {};
  const value = (v: unknown) => (v === undefined || v === null ? L.default : String(v));
  const rows: [string, unknown][] = [[L.background, s.background], [L.radius, s.shapes?.radius], [L.border, s.shapes?.border],
    [L.shadow, s.shapes?.shadow], [L.weight_normal, s.weights?.normal], [L.weight_strong, s.weights?.strong]];
  return (
    <Page title={L.shapes} intro={L.shapes_intro}>
      <div style={{ overflowX: "auto" }}><Table size="sm"><TableBody>
        {rows.map(([name, v]) => <TableRow key={name}><TableCell>{name}</TableCell><TableCell><Code>{value(v)}</Code></TableCell></TableRow>)}
      </TableBody></Table></div>
      <Frame show={show} tall />
    </Page>
  );
};

const App: React.FC = () => {
  const error = useVersion();
  const [current, setCurrent] = React.useState(() => decodeURIComponent(location.hash.slice(1)) || data.pieces[0]?.name);
  React.useEffect(() => {
    const follow = () => setCurrent(decodeURIComponent(location.hash.slice(1)) || data.pieces[0]?.name);
    window.addEventListener("hashchange", follow);
    return () => window.removeEventListener("hashchange", follow);
  }, []);
  const piece = STYLE_PAGES.includes(current ?? "") ? undefined : data.pieces.find((p) => p.name === current) ?? data.pieces[0];
  const entry = (p: Piece) => ({ id: `${p.kind}-${p.name}`, label: p.label, href: `#${encodeURIComponent(p.name)}`, active: p === piece });
  const entries: SidebarNavEntry[] = [
    { kind: "group", id: "style", label: L.style_group, icon: <Icon name="sparkles" size="sm" />, items: STYLE_PAGES.map((page) => ({ id: page, label: L[page],
      href: `#${page}`, active: current === page })) },
    { kind: "group", id: "scenes", label: L.scenes_group, icon: <Icon name="gallery-horizontal" size="sm" />, items: data.pieces.filter((p) => p.kind === "scenes").map(entry) },
    { kind: "group", id: "layers", label: L.layers_group, icon: <Icon name="layers" size="sm" />, items: data.pieces.filter((p) => p.kind === "layers").map(entry) },
  ];
  const specimen: Show = React.useMemo(() => ({ type: "specimen" }), []);
  const shapes: Show = React.useMemo(() => ({ type: "shapes" }), []);
  return (
    <AppShell skipLabel={L.skip}
      header={<AppHeader logo={<Logo size="sm" />} logoHref="#" logoLabel="Studio LXD" menuLabel={L.menu} menuCloseLabel={L.menu_close}
        start={<strong>{data.title}</strong>} />}
      sidebar={<Sidebar label={L.navigation}>
        <SidebarNav label={L.navigation} entries={entries} defaultValue={["style", "scenes", "layers"]} />
      </Sidebar>}>
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr)", gap: 16, minWidth: 0 }}>
        {error ? <Alert tone="error" title={L.broken} description={<pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{error}</pre>} /> : null}
        {piece ? <Detail key={`${piece.kind}-${piece.name}`} piece={piece} />
          : current === COLOURS ? <Colours />
          : current === SHAPES ? <ShapesPage show={shapes} />
          : <Page title={L.typography} intro={L.typography_intro}><Frame show={specimen} tall /></Page>}
      </div>
    </AppShell>
  );
};

const stage = location.pathname.endsWith("stage.html");
createRoot(document.getElementById("root")!).render(stage ? <Stage /> : <App />);
