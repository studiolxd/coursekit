import React from "react";
import { AbsoluteFill, useVideoConfig } from "remotion";
import { Background } from "../../atoms/Background";
import { ScreenRecording, type Focus, type ScreenEvent } from "../../atoms/ScreenRecording";
import { useColor, useShapes } from "../../theme";
import type { SceneProps } from "../../contract";

// A real screen recording (recipe screen-recording) with zooms that follow what the narration names. `events` are those of
// recordings/<id>.events.json (coursekit puts them in when `recording` has its events file).
// `frame: window` shows it inside a window on the background of the style instead of the whole frame.
export type ScreencastProps = { recording: string; events?: ScreenEvent[]; focus?: Focus[]; start?: number; scale?: number; ring?: boolean;
  frame?: "none" | "window" };

const BAR = 44;  // px of the top bar of the window

export default function Screencast({ props }: SceneProps<ScreencastProps>) {
  const { width, height } = useVideoConfig();
  const color = useColor();
  const shapes = useShapes();
  const recording = <ScreenRecording src={props.recording} events={props.events} focus={props.focus} startFrom={props.start ?? 0}
    scale={props.scale} ring={props.ring ?? true} />;
  if (props.frame !== "window") return recording;
  const w = Math.round(width * 0.76);
  const h = Math.round((w * height) / width);
  return (
    <AbsoluteFill>
      <Background />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ width: w, borderRadius: shapes.radius(14), overflow: "hidden", border: `${shapes.border(2)}px solid ${color("border", "surface")}`,
          boxShadow: shapes.shadow("0 24px 64px rgba(0,0,0,0.18)") }}>
          <div style={{ height: BAR, background: color("surface", "background"), display: "flex", alignItems: "center", gap: 10, padding: "0 18px" }}>
            {[0, 1, 2].map((i) => <div key={i} style={{ width: 14, height: 14, borderRadius: "50%", background: color("border", "text-muted") }} />)}
          </div>
          <div style={{ width: w, height: h, position: "relative" }}>{recording}</div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}
