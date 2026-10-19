import React from "react";
import { AbsoluteFill, OffthreadVideo, staticFile, useCurrentFrame, useVideoConfig, Img } from "remotion";
import { useColor, useTheme } from "../theme";
import { useSceneTime } from "../timing";
import { framing, markStyle, spansFromClicks, spansFromFocus, ZOOMING, zoomAt, type Focus, type ScreenEvent, type Zooming } from "./zoom";

// A real screen recording with zooms computed from data (never baked into the video): the events of the recording
// (recordings/<id>.events.json) and the words of the narration of its scene. How the zooms go: ./zoom.ts.

export type { Box, Focus, ScreenEvent, Shape } from "./zoom";

const IMAGE = /\.(svg|png|jpe?g|webp)$/i;  // a still of a screen (the example of the gallery): zoomed the same way

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
        {ring && z.mark && span?.box && s > 1.02 ? <div style={markStyle(span, s, k, color("accent-ink"))} /> : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
