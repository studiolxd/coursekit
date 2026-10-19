import React from "react";
import { AbsoluteFill, Easing, OffthreadVideo, useCurrentFrame, useVideoConfig } from "remotion";
import { color } from "./theme";

// A real screen recording with zooms computed from data, never baked into the video: change a number and render again,
// without recording anything again. What it uses:
//  - the events of the recording (media/recordings/<id>.events.json, written by `coursekit capture replay` or by a terminal
//    session): when and where each click and each point marked without clicking happened, as fractions of the screen, and,
//    when it is known, the box of what a point shows, its shape and the tone of its background;
//  - the words of the narration (`coursekit subtitles` or the ElevenLabs voice write <audio>.words.json): when each word is said.
//
// A zoom is for a detail, not for every sentence: a `focus` starts going in a moment before its words are said, stays at least
// `minHold` seconds or until the end of its sentence, and goes back to the whole screen; two focuses close in time move from one
// to the other without zooming out. With the box of what it shows it goes only as close as the box fits, keeps it whole in the
// frame and draws a mark around it in a tone that reads on its background; without a box it zooms on its point, with no mark.
// Without `focus`, the clicks close in time and space are joined into one sustained zoom.

/** A box as fractions of the screen: left, top, width, height. */
export type Box = [number, number, number, number];
export type Shape = "rect" | "round" | "ellipse";
export type ScreenEvent = { t: number; kind: "click" | "point"; fx: number; fy: number; label?: string; box?: Box; shape?: Shape;
  tone?: "light" | "dark" };
export type ScreenEvents = { video?: string; width: number; height: number; duration: number; events: ScreenEvent[] };
export type Word = { w: string; start: number; end: number };

export type Focus = {
  /** The words of the narration it enters with ("minimum length"): the first time they are said after the previous focus. */
  word?: string;
  /** Or the second of the video it enters at. */
  at?: number;
  /** Where: the label (or the note) of an event of the recording, a box or a point as fractions of the screen. */
  event?: string;
  box?: Box;
  shape?: Shape;
  fx?: number;
  fy?: number;
  /** How close at most (1 is the whole screen) and how long it holds, in seconds. */
  scale?: number;
  hold?: number;
};

/** The zooms (the values of config/video.yaml › screencast). */
export type Zooming = { scale: number; ease: number; lead: number; minHold: number; margin: number; mark: boolean };

export type ScreencastProps = {
  src: string;
  events?: ScreenEvents;
  words?: Word[] | { words: Word[] };
  focus?: Focus[];
  /** Zoom on the groups of clicks when there is no focus (default true). */
  auto?: boolean;
  /** Seconds of the recording the composition starts from (the narration is timed from there). */
  startFrom?: number;
  zooming?: Partial<Zooming>;
  /** A mark around what each focus shows, when its box is known. */
  ring?: boolean;
};

type Span = { from: number; to: number; cx: number; cy: number; s: number; box?: Box; shape: Shape; tone?: "light" | "dark" };

const ZOOMING: Zooming = { scale: 1.4, ease: 1.2, lead: 0.4, minHold: 3.5, margin: 0.06, mark: true };
const JOIN = 0.8; // two spans closer than this move from one to the other without zooming out
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

const normal = (text: string) =>
  text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9ñ]+/g, " ").trim();

/** When a sequence of words is said, from a second on (null when it is not). */
export const whenSaid = (words: Word[], phrase: string, after = -1): number | null => {
  const wanted = normal(phrase).split(" ").filter(Boolean);
  const said = words.map((w) => normal(w.w));
  for (let i = 0; i + wanted.length <= said.length; i++) {
    if (words[i].start < after) continue;
    if (wanted.every((w, k) => said[i + k] === w)) return words[i].start;
  }
  return null;
};

/** How close a zoom goes: at most `max`, and only as close as its box fits with the margin around it. */
export const closeness = (box: Box | undefined, max: number, margin: number) =>
  box ? clamp(Math.min(max, (1 - 2 * margin) / Math.max(box[2], 1e-3), (1 - 2 * margin) / Math.max(box[3], 1e-3)), 1, max) : max;

/** Where the zoomed screen goes: the centre of what it shows in the middle of the frame, as long as no edge of the screen shows. */
export const framing = (s: number, cx: number, cy: number) => ({ tx: clamp(0.5 - cx * s, 1 - s, 0), ty: clamp(0.5 - cy * s, 1 - s, 0) });

export const spansFromFocus = (focus: Focus[], events: ScreenEvent[], words: Word[], z: Zooming): Span[] => {
  const spans: Span[] = [];
  let after = -1;
  for (const f of focus) {
    const said = f.at ?? (f.word ? whenSaid(words, f.word, after) : null);
    if (said == null) continue; // a word that is not said: no zoom (better none than a wrong one)
    const target = f.event ? events.find((e) => normal(e.label ?? "") === normal(f.event!)) : undefined;
    const box = f.box ?? target?.box;
    const cx = box ? box[0] + box[2] / 2 : f.fx ?? target?.fx;
    const cy = box ? box[1] + box[3] / 2 : f.fy ?? target?.fy;
    if (cx == null || cy == null) continue;
    const end = words.find((w) => w.start >= said && /[.!?…:;]$/.test(w.w.trim()));
    const hold = f.hold ?? Math.max(z.minHold, (end ? end.end : said) - said);
    spans.push({ from: said - (f.at != null ? 0 : z.lead), to: said + hold, cx, cy, s: closeness(box, f.scale ?? z.scale, z.margin),
      box, shape: f.shape ?? target?.shape ?? "round", tone: target?.tone });
    after = said + 0.01;
  }
  return spans;
};

export const spansFromClicks = (events: ScreenEvent[], z: Zooming): Span[] => {
  const clicks = events.filter((e) => e.kind === "click").sort((a, b) => a.t - b.t);
  const spans: Span[] = [];
  let group: ScreenEvent[] = [];
  const close = () => {
    if (!group.length) return;
    spans.push({ from: Math.max(0, group[0].t - z.lead), to: group[group.length - 1].t + z.minHold, s: z.scale, shape: "round",
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
    if (joinedOut && t > sp.to) continue; // the next span moves from here
    return { s: sp.s, cx: sp.cx, cy: sp.cy, span: sp, k: 1 };
  }
  return { s: 1, cx: 0.5, cy: 0.5, k: 0 };
};

export const Screencast: React.FC<ScreencastProps> = ({ src, events, words, focus, auto = true, startFrom = 0, zooming, ring = true }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const z: Zooming = { ...ZOOMING, ...(zooming ?? {}) };
  const t = frame / fps + startFrom;
  const list = Array.isArray(words) ? words : words?.words ?? [];
  const recorded = events?.events ?? [];
  const spans = React.useMemo(
    () => (focus?.length ? spansFromFocus(focus, recorded, list, z) : auto ? spansFromClicks(recorded, z) : []),
    [focus, recorded, list, auto, z.scale, z.lead, z.minHold, z.margin],
  );
  const { s, cx, cy, span, k } = zoomAt(spans, t, z.ease);
  const { tx, ty } = framing(s, cx, cy);
  const box = ring && z.mark && span?.box && s > 1.02 ? span.box : null;
  const grow = span?.shape === "ellipse" ? 1.42 : 1; // an ellipse wide enough to hold the whole box
  const pad = 0.006;
  const dark = span?.tone === "dark";
  return (
    <AbsoluteFill style={{ background: color.background, overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `translate(${tx * 100}%, ${ty * 100}%) scale(${s})`, transformOrigin: "0 0" }}>
        <OffthreadVideo src={src} startFrom={Math.round(startFrom * fps)} muted style={{ width: "100%", height: "100%" }} />
        {box ? (
          <div style={{ position: "absolute", boxSizing: "border-box", opacity: k,
            left: `${(box[0] + box[2] / 2 - (box[2] * grow + 2 * pad) / 2) * 100}%`,
            top: `${(box[1] + box[3] / 2 - (box[3] * grow + 2 * pad) / 2) * 100}%`,
            width: `${(box[2] * grow + 2 * pad) * 100}%`, height: `${(box[3] * grow + 2 * pad) * 100}%`,
            border: `${3 / s}px solid ${dark ? "#ffffff" : color.accent}`,
            boxShadow: `0 0 0 ${2 / s}px ${dark ? "rgba(0,0,0,0.55)" : "rgba(255,255,255,0.8)"}`,
            borderRadius: span?.shape === "ellipse" ? "50%" : span?.shape === "rect" ? `${4 / s}px` : `${14 / s}px` }} />
        ) : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
