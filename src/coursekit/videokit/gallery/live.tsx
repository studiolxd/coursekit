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
import { Checkbox } from "@studiolxd/brand/checkbox";
import { AppHeader } from "@studiolxd/brand/app-header";
import { AppShell } from "@studiolxd/brand/app-shell";
import { Code } from "@studiolxd/brand/code";
import { CodeBlock } from "@studiolxd/brand/code-block";
import { Heading as BrandHeading } from "@studiolxd/brand/heading";
import { Icon } from "@studiolxd/brand/icon";
import { InputField } from "@studiolxd/brand/input-field";
import { Logo } from "@studiolxd/brand/logo";
import { NumberInputField } from "@studiolxd/brand/number-input-field";
import { Paragraph } from "@studiolxd/brand/paragraph";
import { SelectField } from "@studiolxd/brand/select-field";
import { Sidebar } from "@studiolxd/brand/sidebar";
import { SidebarNav, type SidebarNavEntry } from "@studiolxd/brand/sidebar-nav";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@studiolxd/brand/table";
import { Tag } from "@studiolxd/brand/tag";
import { TextareaField } from "@studiolxd/brand/textarea-field";
import { Montage, type MontageProps, type Transition } from "../Montage";
import { Badge } from "../atoms/Badge";
import { Card } from "../atoms/Card";
import { Heading } from "../atoms/Heading";
import { Text } from "../atoms/Text";
import { ThemeProvider } from "../theme";

type Rule = { type?: string; values?: string[]; required?: boolean; max_chars?: number; max_items?: number; help?: string;
  when?: Record<string, string | string[]>; default?: unknown };
type Piece = { kind: "scenes" | "layers"; name: string; label: string; origin: string; description: string; props: Record<string, Rule>;
  example: Record<string, unknown> | null; variants: { name: string; label: string; props: Record<string, unknown> }[] };
type Data = { title: string; base: Record<string, unknown>; samples: string[]; seconds: number; labels: Record<string, string>;
  montage: Omit<MontageProps, "scenes" | "frames">; pieces: Piece[]; swatches: [string, string][];
  /** The rendered gallery: every piece and variant already rendered, a clip each, instead of the player. */
  rendered?: boolean; clips?: Record<string, { clip: string; poster: string }>;
  /** The scene the transitions lead into, after the cover, and the transitions of the project. */
  next: Record<string, unknown>;
  transitions: { types: { name: string; label: string }[]; frames: number; direction: string; directions: string[] } };
type Show = { type: "piece"; piece: Piece; props: Record<string, unknown> } | { type: "specimen" } | { type: "shapes" }
  | { type: "transition"; transition: Transition };

const data = (window as unknown as { __GALLERY__: Data }).__GALLERY__;
const L = data.labels;
const TYPOGRAPHY = "typography";
const cap = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);
const COLOURS = "colours";
const SHAPES = "shapes";
const TRANSITIONS = "transitions";
const STYLE_PAGES = [TYPOGRAPHY, COLOURS, SHAPES, TRANSITIONS];
const NONE = "__none";  // the option of a select that leaves the prop to its default
// The page and its frame talk by messages; opened from the disk (the rendered gallery) the browser gives them no origin.
const TARGET = location.protocol === "file:" ? "*" : location.origin;

// What the person had chosen survives the reload that follows a change of the project (sessionStorage, this tab only): the
// variant and the props they changed by hand, never the rest, so a new default or example of the project shows at once.
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

const ROLES = ["display", "heading", "subheading", "kicker", "body", "quote", "statement", "label", "stat", "step", "caption", "code"];
const MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";  // the family of the code role when the brand fixes none
const HEADINGS = new Set(["display", "heading", "quote", "statement", "stat"]);

const Specimen: React.FC = () => {
  const m = data.montage;
  const sample = (role: string) => (role === "stat" ? "1.234" : role === "step" ? "1 2 3" : role === "code" ? "if len(password) < 12:" : L[`sample_${role}`] ?? role);
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
                {HEADINGS.has(role) ? <Heading role={role} size={size}>{sample(role)}</Heading> : <Text role={role} size={size} family={role === "code" ? MONO : undefined}>{sample(role)}</Text>}
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
  React.useEffect(() => {
    const listen = (event: MessageEvent) => { if (event.source === window.parent && event.data?.type && event.data.type !== "ready") setShow(event.data); };
    window.addEventListener("message", listen);
    window.parent.postMessage({ type: "ready" }, TARGET);
    return () => window.removeEventListener("message", listen);
  }, []);
  if (!show) return null;
  if (show.type === "specimen") return <Specimen />;
  if (show.type === "shapes") return <Shapes />;
  if (show.type === "transition") {  // the cover giving way to the next scene, the two overlapping for the frames of the transition
    const overlap = show.transition.type === "cut" ? 0 : Math.min(show.transition.frames, frames - 1);
    const both = frames * 2 - overlap;
    const input: MontageProps = { ...m, frames: both, scenes: [
      { id: "from", type: "title", props: data.base, from: 0, frames, audio: null, words: [], layers: [] },
      { id: "to", type: "statement", props: data.next, from: frames - overlap, frames, audio: null, words: [], layers: [],
        transition: { ...show.transition, frames: overlap } }] };
    return (
      <Player key={JSON.stringify(show.transition)} component={Montage as unknown as React.FC<Record<string, unknown>>}
        inputProps={input as unknown as Record<string, unknown>} durationInFrames={both} fps={m.fps} compositionWidth={m.width}
        compositionHeight={m.height} style={{ width: "100vw", height: "100vh" }} controls autoPlay initiallyMuted
        moveToBeginningWhenEnded={false} acknowledgeRemotionLicense />
    );
  }
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

// The width at which a piece in the proportion of the video fits under what is above it, so it is seen whole without scrolling:
// its distance from the top of the page (whatever is scrolled) and a margin below set the height left for it.
const FIT_MARGIN = 24;
const useFit = <T extends HTMLElement>(): [React.RefObject<T | null>, string | undefined] => {
  const ref = React.useRef<T>(null);
  const [width, setWidth] = React.useState<string>();
  React.useLayoutEffect(() => {
    const measure = () => {
      let top = 0;
      for (let node: HTMLElement | null = ref.current; node; node = node.offsetParent as HTMLElement | null) top += node.offsetTop;
      const m = data.montage;
      setWidth(`${Math.max(240, ((window.innerHeight - top - FIT_MARGIN) * m.width) / m.height)}px`);
    };
    measure();
    const watch = new ResizeObserver(measure);
    watch.observe(document.body);
    window.addEventListener("resize", measure);
    return () => { watch.disconnect(); window.removeEventListener("resize", measure); };
  }, []);
  return [ref, width];
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
  const [fit, width] = useFit<HTMLIFrameElement>();
  const m = data.montage;
  return (
    <iframe ref={(node) => { ref.current = node; fit.current = node; }} src="stage.html"
      title={show.type === "piece" ? show.piece.name : L[show.type === "shapes" ? "shapes" : show.type === "transition" ? "transitions" : "typography"]}
      style={{ width: "100%", maxWidth: tall ? undefined : width, aspectRatio: tall ? undefined : `${m.width} / ${m.height}`, height: tall ? (show.type === "shapes" ? 250 : 1500) : undefined,
        border: "1px solid currentColor", display: "block", background: "#fff" }} />
  );
};

// A piece of the rendered gallery: its clip, played once, with the frame where everything is in as its poster.
const Clip: React.FC<{ id: string }> = ({ id }) => {
  const found = data.clips?.[id];
  const [fit, width] = useFit<HTMLVideoElement>();
  if (!found) return <Alert tone="warning" description={L.no_example} />;
  const m = data.montage;
  return (
    <video ref={fit} key={id} src={found.clip} poster={found.poster} controls autoPlay muted playsInline
      style={{ width: "100%", maxWidth: width, aspectRatio: `${m.width} / ${m.height}`, display: "block", border: "1px solid currentColor", background: "#fff" }} />
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
  if (rule.type === "boolean") {  // a check: unset, the default of the piece (`default:` in its metadata), else false
    return <Checkbox id={id} aria-label={name} size="sm" checked={Boolean(value ?? rule.default ?? false)} onCheckedChange={(c) => set(c)} />;
  }
  if (rule.type === "number") {
    return (
      <NumberInputField id={id} label={name} labelHidden size="sm" decimal value={typeof value === "number" ? value : null} placeholder={L.empty}
        decrementLabel={L.less} incrementLabel={L.more} onChange={(v) => set(v)} onEmpty={() => set(undefined)} />
    );
  }
  if (rule.type === "list" || rule.type === "object") {  // nested props: as JSON, applied when it parses
    return (
      <TextareaField id={id} label={name} labelHidden size="sm" rows={5} value={text} placeholder={L.empty}
        onChange={(e) => { setText(e.target.value); try { set(e.target.value.trim() ? JSON.parse(e.target.value) : undefined); } catch { /* typing */ } }} />
    );
  }
  const current = value === undefined ? "" : String(value);
  const over = Boolean(rule.max_chars && current.length > rule.max_chars);
  const count = rule.max_chars ? `${current.length} / ${rule.max_chars}` : undefined;
  return (rule.max_chars ?? 0) > 70
    ? <TextareaField id={id} label={name} labelHidden size="sm" rows={2} value={current} error={over} helperText={count} placeholder={L.empty}
        onChange={(e) => set(e.target.value || undefined)} />
    : <InputField id={id} label={name} labelHidden size="sm" value={current} error={over} helperText={count} placeholder={L.empty}
        onChange={(e) => set(e.target.value || undefined)} />;
};

const Detail: React.FC<{ piece: Piece }> = ({ piece }) => {
  const key = `gallery:${piece.kind}:${piece.name}`;
  const [variant, setVariant] = React.useState<string>(() => {
    const was = saved(`${key}:variant`);
    return piece.variants.some((v) => v.name === was) ? was : NONE;
  });
  // what the person changed over the example and the variant: a value, or null for a prop they emptied
  const [edits, setEdits] = React.useState<Record<string, unknown>>(() => saved(`${key}:edits`) ?? {});
  React.useEffect(() => { keep(`${key}:edits`, edits); keep(`${key}:variant`, variant); }, [key, edits, variant]);
  const base = React.useMemo(() => ({ ...(piece.example ?? {}), ...(piece.variants.find((v) => v.name === variant)?.props ?? {}) }),
    [piece, variant]);
  const props = React.useMemo(() => {
    const out: Record<string, unknown> = { ...base };
    for (const [name, value] of Object.entries(edits)) if (value === null) delete out[name]; else out[name] = value;
    return allowedNow(piece, out);
  }, [piece, base, edits]);
  const pick = (name: string) => { setVariant(name); setEdits({}); };
  const set = (name: string, value: unknown) => setEdits((old) => {
    const next = { ...old };
    if (JSON.stringify(value) === JSON.stringify(base[name])) delete next[name];  // back to what the project draws
    else next[name] = value === undefined ? null : value;
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
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 24, flexWrap: "wrap" }}>
          <BrandHeading level={1} size={5}>{piece.label}</BrandHeading>
          {piece.variants.length ? (
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <Paragraph size="sm" aria-hidden="true" style={{ margin: 0 }}>{L.variant}</Paragraph>
              <div style={{ width: 240 }}><SelectField id={`${key}-variant`} label={L.variant} labelHidden size="sm" value={variant}
                options={[{ value: NONE, label: L.example }, ...piece.variants.map((v) => ({ value: v.name, label: v.label }))]}
                onValueChange={pick} /></div>
            </div>
          ) : null}
        </div>
        <div style={{ display: "flex", gap: 8, margin: "8px 0" }}>
          <Tag tone="primary">{cap(L[piece.kind])}</Tag><Tag tone="neutral">{cap(piece.origin)}</Tag>
          <Tag tone="accent-1" title={L.id_hint}>{piece.name}</Tag>
        </div>
        <Paragraph>{piece.description}</Paragraph>
        {data.rendered ? <Paragraph size="sm">{L.rendered_hint}</Paragraph> : null}
      </div>
      {data.rendered ? <Clip id={variant === NONE ? piece.name : `${piece.name}-${variant}`} />
        : piece.example ? <Frame show={show} /> : <Alert tone="warning" description={L.no_example} />}
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

// The transitions of the project: one chosen at a time (and its direction, for those that move), drawn between the cover and the
// next scene; in the rendered gallery, its clip.
const TransitionsPage: React.FC = () => {
  const kinds = data.transitions.types;
  const [kind, setKind] = React.useState(kinds[0]?.name ?? "fade");
  const [direction, setDirection] = React.useState(data.transitions.direction);
  const moves = kind === "push" || kind === "wipe";
  const show: Show = React.useMemo(() => ({ type: "transition", transition: { type: kind as Transition["type"], frames: data.transitions.frames,
    direction: direction as Transition["direction"] } }), [kind, direction]);
  return (
    <Page title={L.transitions} intro={L.transitions_intro}>
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
        <div style={{ width: 280 }}><SelectField id="transition" label={L.transition} size="sm" value={kind}
          options={kinds.map((k) => ({ value: k.name, label: k.label }))} onValueChange={setKind} /></div>
        {moves && !data.rendered ? (
          <div style={{ width: 200 }}><SelectField id="direction" label={L.direction} size="sm" value={direction}
            options={data.transitions.directions.map((d) => ({ value: d, label: d }))} onValueChange={setDirection} /></div>
        ) : null}
      </div>
      {data.rendered ? <Clip id={`transition-${kind}`} /> : <Frame show={show} />}
      <CodeBlock language="yaml" copyable>{`- id: …\n  type: …\n  transition: ${moves ? `{type: ${kind}, direction: ${direction}}` : kind}`}</CodeBlock>
    </Page>
  );
};

// A field with no value says so in a lighter grey of the brand, so it is not taken for a value (still 5.3:1 on white).
const PLACEHOLDER_CSS = `input::placeholder, textarea::placeholder { color: var(--color-grey-dark); }`;

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
    <><style>{PLACEHOLDER_CSS}</style><AppShell skipLabel={L.skip}
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
          : current === TRANSITIONS ? <TransitionsPage />
          : <Page title={L.typography} intro={L.typography_intro}><Frame show={specimen} tall /></Page>}
      </div>
    </AppShell></>
  );
};

const stage = location.pathname.endsWith("stage.html");
createRoot(document.getElementById("root")!).render(stage ? <Stage /> : <App />);
