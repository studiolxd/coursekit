import React from "react";
import { AbsoluteFill, Easing, OffthreadVideo, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { useColor } from "../theme";
import { useSceneTime, whenSaid } from "../timing";

// A real screen recording with zooms computed from data (never baked into the video). It uses the events of the recording
// (`coursekit capture replay` writes recordings/<id>.events.json: when and where each click and each point happened) and the
// words of the narration of its scene. A focus enters when its words are said, holds until the end of the sentence (or `hold`
// seconds) and goes back to the whole screen; two focuses close in time move from one to the other without zooming out.
// Without focuses, the clicks close in time and space are joined into one sustained zoom.

export type ScreenEvent = { t: number; kind: "click" | "point"; fx: number; fy: number; label?: string };
export type Focus = { word?: string; at?: number; event?: string; fx?: number; fy?: number; scale?: number; hold?: number };
type Span = { from: number; to: number; fx: number; fy: number; scale: number };

const EASE = 0.5;
const JOIN = 0.8;
const normal = (text: string) =>
  text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9ñ]+/g, " ").trim();

const spansFromFocus = (focus: Focus[], events: ScreenEvent[], words: { w: string; start: number; end: number }[], scale: number,
  offset: number): Span[] => {
  const spans: Span[] = [];
  let after = -1;
  for (const f of focus) {
    const from = f.at ?? (f.word ? whenSaid(words, f.word, after) : null);
    if (from == null) continue;
    const target = f.event ? events.find((e) => normal(e.label ?? "") === normal(f.event!)) : undefined;
    const fx = f.fx ?? target?.fx;
    const fy = f.fy ?? target?.fy;
    if (fx == null || fy == null) continue;
    const end = words.find((w) => w.start >= from && /[.!?…:;]$/.test(w.w.trim()));
    spans.push({ from: from + offset, to: from + offset + (f.hold ?? Math.max(1.5, (end ? end.end : from + 2.5) - from)), fx, fy,
      scale: f.scale ?? scale });
    after = from + 0.01;
  }
  return spans;
};

const spansFromClicks = (events: ScreenEvent[], scale: number): Span[] => {
  const clicks = events.filter((e) => e.kind === "click").sort((a, b) => a.t - b.t);
  const spans: Span[] = [];
  let group: ScreenEvent[] = [];
  const close = () => {
    if (!group.length) return;
    spans.push({ from: Math.max(0, group[0].t - 0.4), to: group[group.length - 1].t + 1.4,
      fx: group.reduce((s, e) => s + e.fx, 0) / group.length, fy: group.reduce((s, e) => s + e.fy, 0) / group.length, scale });
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

const zoomAt = (spans: Span[], t: number) => {
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
    if (joinedOut && t > sp.to) continue;
    return { s: sp.scale, fx: sp.fx, fy: sp.fy };
  }
  return { s: 1, fx: 0.5, fy: 0.5 };
};

export const ScreenRecording: React.FC<{ src: string; events?: ScreenEvent[]; focus?: Focus[]; startFrom?: number;
  scale?: number; ring?: boolean }> = ({ src, events = [], focus, startFrom = 0, scale = 1.8, ring = false }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { words } = useSceneTime();
  const color = useColor();
  const t = frame / fps + startFrom;
  const spans = React.useMemo(
    () => (focus?.length ? spansFromFocus(focus, events, words, scale, startFrom) : spansFromClicks(events, scale)),
    [focus, events, words, scale, startFrom],
  );
  const { s, fx, fy } = zoomAt(spans, t);
  const origin = `${(Math.min(1, Math.max(0, fx)) * 100).toFixed(3)}% ${(Math.min(1, Math.max(0, fy)) * 100).toFixed(3)}%`;
  return (
    <AbsoluteFill style={{ background: color("background"), overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `scale(${s})`, transformOrigin: origin }}>
        <OffthreadVideo src={/^https?:/.test(src) ? src : staticFile(src)} startFrom={Math.round(startFrom * fps)} muted
          style={{ width: "100%", height: "100%" }} />
        {ring && s > 1.05 ? (
          <div style={{ position: "absolute", left: `${fx * 100}%`, top: `${fy * 100}%`, width: 64, height: 64, marginLeft: -32,
            marginTop: -32, borderRadius: "50%", border: `4px solid ${color("accent-strong")}`, opacity: Math.min(1, (s - 1) / (scale - 1)) }} />
        ) : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
