import React from "react";
import { AbsoluteFill, Easing, interpolate, OffthreadVideo, useCurrentFrame, useVideoConfig } from "remotion";
import { color } from "./theme";

// A real screen recording with zooms computed from data, never baked into the video: change a number and render again,
// without recording anything again. What it uses:
//  - the events of the recording (`coursekit capture replay` writes media/recordings/<id>.events.json): when and where each
//    click and each point marked without clicking happened, as fractions of the screen;
//  - the words of the narration (`coursekit subtitles` or the ElevenLabs voice write <audio>.words.json): when each word is said.
//
// The zoom follows what the narration names, not every click: a `focus` enters when its word is said, holds and goes back
// to the whole screen. Two focuses close in time move from one to the other without zooming out. Without `focus`, the clicks
// close in time and space are joined into one sustained zoom (never a zoom in and out on each click).

export type ScreenEvent = { t: number; kind: "click" | "point"; fx: number; fy: number; label?: string };
export type ScreenEvents = { video?: string; width: number; height: number; duration: number; events: ScreenEvent[] };
export type Word = { w: string; start: number; end: number };

export type Focus = {
  /** The words of the narration it enters with ("minimum length"): the first time they are said after the previous focus. */
  word?: string;
  /** Or the second of the video it enters at. */
  at?: number;
  /** Where: the label (or the note) of an event of the recording, or a point as fractions of the screen. */
  event?: string;
  fx?: number;
  fy?: number;
  /** How close (1 is the whole screen) and how long it holds, in seconds. */
  scale?: number;
  hold?: number;
};

export type ScreencastProps = {
  src: string;
  events?: ScreenEvents;
  words?: Word[] | { words: Word[] };
  focus?: Focus[];
  /** Zoom on the groups of clicks when there is no focus (default true). */
  auto?: boolean;
  /** Seconds of the recording the composition starts from (the narration is timed from there). */
  startFrom?: number;
  scale?: number;
  /** A ring on the point of each focus. */
  ring?: boolean;
};

type Span = { from: number; to: number; fx: number; fy: number; scale: number };

const EASE = 0.5; // seconds of the zoom in and out
const JOIN = 0.8; // two spans closer than this move from one to the other without zooming out

const normal = (text: string) =>
  text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9ñ]+/g, " ").trim();

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

/** The end of the sentence a word belongs to: how long a focus holds when it says nothing. */
const sentenceEnd = (words: Word[], from: number): number => {
  const next = words.find((w) => w.start >= from && /[.!?…:;]$/.test(w.w.trim()));
  return next ? next.end : from + 2.5;
};

export const spansFromFocus = (focus: Focus[], events: ScreenEvent[], words: Word[], scale: number): Span[] => {
  const spans: Span[] = [];
  let after = -1;
  for (const f of focus) {
    const from = f.at ?? (f.word ? whenSaid(words, f.word, after) : null);
    if (from == null) continue; // a word that is not said: no zoom (better none than a wrong one)
    const target = f.event ? events.find((e) => normal(e.label ?? "") === normal(f.event!)) : undefined;
    const fx = f.fx ?? target?.fx;
    const fy = f.fy ?? target?.fy;
    if (fx == null || fy == null) continue;
    const to = from + (f.hold ?? Math.max(1.5, sentenceEnd(words, from) - from));
    spans.push({ from, to, fx, fy, scale: f.scale ?? scale });
    after = from + 0.01;
  }
  return spans;
};

export const spansFromClicks = (events: ScreenEvent[], scale: number): Span[] => {
  const clicks = events.filter((e) => e.kind === "click").sort((a, b) => a.t - b.t);
  const spans: Span[] = [];
  let group: ScreenEvent[] = [];
  const close = () => {
    if (!group.length) return;
    const fx = group.reduce((s, e) => s + e.fx, 0) / group.length;
    const fy = group.reduce((s, e) => s + e.fy, 0) / group.length;
    spans.push({ from: Math.max(0, group[0].t - 0.4), to: group[group.length - 1].t + 1.4, fx, fy, scale });
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

/** Scale and point of the zoom at a second: zoom in, hold, move to the next span or go back to the whole screen. */
export const zoomAt = (spans: Span[], t: number): { s: number; fx: number; fy: number } => {
  const ease = Easing.inOut(Easing.cubic);
  for (let i = 0; i < spans.length; i++) {
    const sp = spans[i];
    const prev = spans[i - 1];
    const next = spans[i + 1];
    const joinedIn = prev && sp.from - prev.to < JOIN;
    const joinedOut = next && next.from - sp.to < JOIN;
    if (t < sp.from - (joinedIn ? 0 : EASE) || t > sp.to + (joinedOut ? 0 : EASE)) continue;
    if (joinedIn && t < sp.from + EASE) {
      const k = ease(Math.min(1, (t - prev.to) / Math.max(0.01, sp.from + EASE - prev.to)));
      return { s: prev.scale + (sp.scale - prev.scale) * k, fx: prev.fx + (sp.fx - prev.fx) * k, fy: prev.fy + (sp.fy - prev.fy) * k };
    }
    if (!joinedIn && t < sp.from) return { s: 1 + (sp.scale - 1) * ease((t - (sp.from - EASE)) / EASE), fx: sp.fx, fy: sp.fy };
    if (!joinedOut && t > sp.to) return { s: sp.scale - (sp.scale - 1) * ease((t - sp.to) / EASE), fx: sp.fx, fy: sp.fy };
    if (joinedOut && t > sp.to) continue; // the next span moves from here
    return { s: sp.scale, fx: sp.fx, fy: sp.fy };
  }
  return { s: 1, fx: 0.5, fy: 0.5 };
};

export const Screencast: React.FC<ScreencastProps> = ({ src, events, words, focus, auto = true, startFrom = 0, scale = 1.8, ring = false }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps + startFrom;
  const list = Array.isArray(words) ? words : words?.words ?? [];
  const recorded = events?.events ?? [];
  const spans = React.useMemo(
    () => (focus?.length ? spansFromFocus(focus, recorded, list, scale) : auto ? spansFromClicks(recorded, scale) : []),
    [focus, recorded, list, scale, auto],
  );
  const { s, fx, fy } = zoomAt(spans, t);
  // Scaling around a point inside the frame by 1 or more always covers the whole frame: the edges never show.
  const origin = `${(Math.min(1, Math.max(0, fx)) * 100).toFixed(3)}% ${(Math.min(1, Math.max(0, fy)) * 100).toFixed(3)}%`;
  const ringOpacity = ring ? interpolate(s, [1, 1 + (scale - 1) * 0.6, scale], [0, 0.4, 1], { extrapolateRight: "clamp" }) : 0;
  return (
    <AbsoluteFill style={{ background: color.background, overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `scale(${s})`, transformOrigin: origin }}>
        <OffthreadVideo src={src} startFrom={Math.round(startFrom * fps)} muted style={{ width: "100%", height: "100%" }} />
        {ring ? (
          <div style={{ position: "absolute", left: `${fx * 100}%`, top: `${fy * 100}%`, width: 64, height: 64, marginLeft: -32,
            marginTop: -32, borderRadius: "50%", border: `4px solid ${color.accent}`, opacity: ringOpacity }} />
        ) : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
