import React from "react";
import { AbsoluteFill, OffthreadVideo, useCurrentFrame, useVideoConfig } from "remotion";
import { color } from "./theme";
import { framing, markStyle, spansFromClicks, spansFromFocus, ZOOMING, zoomAt, type Focus, type ScreenEvent, type Word,
  type Zooming } from "./zoom";

// A real screen recording with zooms computed from data, never baked into the video: change a number and render again,
// without recording anything again. What it uses:
//  - the events of the recording (media/recordings/<id>.events.json, written by `coursekit capture replay` or by a terminal
//    session): when and where each click and each point happened, as fractions of the screen, and, when it is known, the
//    box of what a point shows, its shape and the tone of its background;
//  - the words of the narration (`coursekit subtitles` or the ElevenLabs voice write <audio>.words.json): when each word is said.
// How the zooms go (for details only, framed by their box, with a mark that reads on its background): ./zoom.ts.

export type { Box, Focus, ScreenEvent, Shape, Word, Zooming } from "./zoom";
export type ScreenEvents = { video?: string; width: number; height: number; duration: number; events: ScreenEvent[] };

export type ScreencastProps = {
  src: string;
  events?: ScreenEvents;
  words?: Word[] | { words: Word[] };
  focus?: Focus[];
  /** Zoom on the groups of clicks when there is no focus (default true). */
  auto?: boolean;
  /** Seconds of the recording the composition starts from (the narration is timed from there). */
  startFrom?: number;
  /** The values of config/video.yaml › screencast. */
  zooming?: Partial<Zooming>;
  /** A mark around what each focus shows, when its box is known. */
  ring?: boolean;
};

export const Screencast: React.FC<ScreencastProps> = ({ src, events, words, focus, auto = true, startFrom = 0, zooming, ring = true }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const z: Zooming = { ...ZOOMING, ...(zooming ?? {}) };
  const t = frame / fps + startFrom;
  const list = Array.isArray(words) ? words : words?.words ?? [];
  const recorded = events?.events ?? [];
  const spans = React.useMemo(
    () => (focus?.length ? spansFromFocus(focus, recorded, list, z, startFrom) : auto ? spansFromClicks(recorded, z) : []),
    [focus, recorded, list, auto, z.scale, z.lead, z.min_hold, z.margin, startFrom],
  );
  const { s, cx, cy, span, k } = zoomAt(spans, t, z.ease);
  const { tx, ty } = framing(s, cx, cy);
  return (
    <AbsoluteFill style={{ background: color.background, overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `translate(${tx * 100}%, ${ty * 100}%) scale(${s})`, transformOrigin: "0 0" }}>
        <OffthreadVideo src={src} startFrom={Math.round(startFrom * fps)} muted style={{ width: "100%", height: "100%" }} />
        {ring && z.mark && span?.box && s > 1.02 ? <div style={markStyle(span, s, k, color.accent)} /> : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
