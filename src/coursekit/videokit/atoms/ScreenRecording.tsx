import React from "react";
import { AbsoluteFill, Easing, OffthreadVideo, staticFile, useCurrentFrame, useVideoConfig, Img } from "remotion";
import { useColor, useTheme } from "../theme";
import { useSceneTime, whenSaid } from "../timing";

// A real screen recording with zooms computed from data (never baked into the video). It uses the events of the recording
// (recordings/<id>.events.json: when and where each click and each point happened, and, when it is known, the box of what a
// point shows, its shape and the tone of its background) and the words of the narration of its scene.
// A zoom is for a detail: a focus starts going in a moment before its words are said (`lead`), stays at least `min_hold`
// seconds or until the end of its sentence, and goes back to the whole screen; two focuses close in time move from one to the
// other without zooming out. With the box of what it shows it goes only as close as the box fits (with `margin` around it),
// keeps the box whole in the frame (never centred on a point that leaves its start outside) and draws a mark around it, in a
// tone that reads on its background; without a box it zooms on the point and draws no mark. The numbers come from
// config/video.yaml › screencast. Without focuses, the clicks close in time and space are joined into one sustained zoom.

/** A box as fractions of the screen: left, top, width, height. */
export type Box = [number, number, number, number];
export type Shape = "rect" | "round" | "ellipse";
export type ScreenEvent = { t: number; kind: "click" | "point"; fx: number; fy: number; label?: string; box?: Box; shape?: Shape;
  tone?: "light" | "dark" };
export type Focus = { word?: string; at?: number; event?: string; fx?: number; fy?: number; box?: Box; shape?: Shape; scale?: number;
  hold?: number };
export type Zooming = { scale: number; ease: number; lead: number; min_hold: number; margin: number; mark: boolean };
type Span = { from: number; to: number; cx: number; cy: number; s: number; box?: Box; shape: Shape; tone?: "light" | "dark" };

const ZOOMING: Zooming = { scale: 1.4, ease: 1.2, lead: 0.4, min_hold: 3.5, margin: 0.06, mark: true };  // config/video.yaml's
const IMAGE = /\.(svg|png|jpe?g|webp)$/i;  // a still of a screen (the example of the gallery): zoomed the same way
const JOIN = 0.8;
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
const normal = (text: string) =>
  text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9ñ]+/g, " ").trim();

/** How close a zoom goes: at most `max`, and only as close as its box fits with the margin around it. */
export const closeness = (box: Box | undefined, max: number, margin: number) =>
  box ? clamp(Math.min(max, (1 - 2 * margin) / Math.max(box[2], 1e-3), (1 - 2 * margin) / Math.max(box[3], 1e-3)), 1, max) : max;

/** Where the zoomed screen goes: the centre of what it shows in the middle of the frame, as long as no edge of the screen shows. */
export const framing = (s: number, cx: number, cy: number) => ({ tx: clamp(0.5 - cx * s, 1 - s, 0), ty: clamp(0.5 - cy * s, 1 - s, 0) });

export const spansFromFocus = (focus: Focus[], events: ScreenEvent[], words: { w: string; start: number; end: number }[],
  z: Zooming, offset: number): Span[] => {
  const spans: Span[] = [];
  let after = -1;
  for (const f of focus) {
    const said = f.at ?? (f.word ? whenSaid(words, f.word, after) : null);
    if (said == null) continue;  // a word that is not said: no zoom (better none than a wrong one)
    const target = f.event ? events.find((e) => normal(e.label ?? "") === normal(f.event!)) : undefined;
    const box = f.box ?? target?.box;
    const cx = box ? box[0] + box[2] / 2 : f.fx ?? target?.fx;
    const cy = box ? box[1] + box[3] / 2 : f.fy ?? target?.fy;
    if (cx == null || cy == null) continue;
    const end = words.find((w) => w.start >= said && /[.!?…:;]$/.test(w.w.trim()));
    const hold = f.hold ?? Math.max(z.min_hold, (end ? end.end : said) - said);
    spans.push({ from: said + offset - (f.at != null ? 0 : z.lead), to: said + offset + hold, cx, cy,
      s: closeness(box, f.scale ?? z.scale, z.margin), box, shape: f.shape ?? target?.shape ?? "round", tone: target?.tone });
    after = said + 0.01;
  }
  return spans;
};

const spansFromClicks = (events: ScreenEvent[], z: Zooming): Span[] => {
  const clicks = events.filter((e) => e.kind === "click").sort((a, b) => a.t - b.t);
  const spans: Span[] = [];
  let group: ScreenEvent[] = [];
  const close = () => {
    if (!group.length) return;
    spans.push({ from: Math.max(0, group[0].t - z.lead), to: group[group.length - 1].t + z.min_hold, s: z.scale, shape: "round",
      cx: group.reduce((s, e) => s + e.fx, 0) / group.length, cy: group.reduce((s, e) => s + e.fy, 0) / group.length });
    group = [];
  };
  for (const e of clicks) {
    const last = group[group.length - 1];
    if (last && (e.t - last.t > 1.6 || Math.hypot(e.fx - last.fx, e.fy - last.fy) > 0.18)) close();
    group.push(e);
  }
  close();
  return spans;
};

/** The zoom at a second: how close, where, the span it shows (for its mark) and how far in it is (0 to 1). */
export const zoomAt = (spans: Span[], t: number, ease: number): { s: number; cx: number; cy: number; span?: Span; k: number } => {
  const curve = Easing.inOut(Easing.cubic);
  for (let i = 0; i < spans.length; i++) {
    const sp = spans[i];
    const prev = spans[i - 1];
    const next = spans[i + 1];
    const joinedIn = prev && sp.from - prev.to < JOIN;
    const joinedOut = next && next.from - sp.to < JOIN;
    if (t < sp.from - (joinedIn ? 0 : ease) || t > sp.to + (joinedOut ? 0 : ease)) continue;
    if (joinedIn && t < sp.from + ease) {
      const k = curve(Math.min(1, (t - prev.to) / Math.max(0.01, sp.from + ease - prev.to)));
      return { s: prev.s + (sp.s - prev.s) * k, cx: prev.cx + (sp.cx - prev.cx) * k, cy: prev.cy + (sp.cy - prev.cy) * k,
        span: k > 0.5 ? sp : prev, k: Math.abs(2 * k - 1) };
    }
    if (!joinedIn && t < sp.from) {
      const k = curve((t - (sp.from - ease)) / ease);
      return { s: 1 + (sp.s - 1) * k, cx: sp.cx, cy: sp.cy, span: sp, k };
    }
    if (!joinedOut && t > sp.to) {
      const k = 1 - curve((t - sp.to) / ease);
      return { s: 1 + (sp.s - 1) * k, cx: sp.cx, cy: sp.cy, span: sp, k };
    }
    if (joinedOut && t > sp.to) continue;
    return { s: sp.s, cx: sp.cx, cy: sp.cy, span: sp, k: 1 };
  }
  return { s: 1, cx: 0.5, cy: 0.5, k: 0 };
};

/** The mark around what a focus shows: its shape, a line that keeps its width whatever the zoom, in a tone of its background. */
const MarkAround: React.FC<{ span: Span; s: number; k: number; ink: string }> = ({ span, s, k, ink }) => {
  const [x, y, w, h] = span.box!;
  const grow = span.shape === "ellipse" ? 1.42 : 1;  // an ellipse wide enough to hold the whole box
  const pad = 0.006;
  const width = w * grow + 2 * pad;
  const height = h * grow + 2 * pad;
  const dark = span.tone === "dark";
  return (
    <div style={{ position: "absolute", left: `${(x + w / 2 - width / 2) * 100}%`, top: `${(y + h / 2 - height / 2) * 100}%`,
      width: `${width * 100}%`, height: `${height * 100}%`, boxSizing: "border-box", opacity: k,
      border: `${3 / s}px solid ${dark ? "#ffffff" : ink}`,
      boxShadow: `0 0 0 ${2 / s}px ${dark ? "rgba(0,0,0,0.55)" : "rgba(255,255,255,0.8)"}`,
      borderRadius: span.shape === "ellipse" ? "50%" : span.shape === "rect" ? `${4 / s}px` : `${14 / s}px` }} />
  );
};

export const ScreenRecording: React.FC<{ src: string; events?: ScreenEvent[]; focus?: Focus[]; startFrom?: number;
  scale?: number; ring?: boolean }> = ({ src, events = [], focus, startFrom = 0, scale, ring = false }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { words } = useSceneTime();
  const color = useColor();
  const z: Zooming = { ...ZOOMING, ...(useTheme().style?.screencast ?? {}), ...(scale ? { scale } : {}) };
  const t = frame / fps + startFrom;
  const spans = React.useMemo(
    () => (focus?.length ? spansFromFocus(focus, events, words, z, startFrom) : spansFromClicks(events, z)),
    [focus, events, words, z.scale, z.lead, z.min_hold, z.margin, startFrom],
  );
  const { s, cx, cy, span, k } = zoomAt(spans, t, z.ease);
  const { tx, ty } = framing(s, cx, cy);
  return (
    <AbsoluteFill style={{ background: color("background"), overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `translate(${tx * 100}%, ${ty * 100}%) scale(${s})`, transformOrigin: "0 0" }}>
        {IMAGE.test(src)
          ? <Img src={/^https?:/.test(src) ? src : staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          : <OffthreadVideo src={/^https?:/.test(src) ? src : staticFile(src)} startFrom={Math.round(startFrom * fps)} muted
              style={{ width: "100%", height: "100%" }} />}
        {ring && z.mark && span?.box && s > 1.02 ? <MarkAround span={span} s={s} k={k} ink={color("accent-ink")} /> : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
