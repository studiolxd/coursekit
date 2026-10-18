import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { useColor, useShapes, useTheme } from "../theme";

// A line that draws itself under (or over, as a highlight) its children from frame `at`: the line in the accent that reads on
// the background, the highlight (a fill behind the words) in the accent itself.

export const Underline: React.FC<{ at?: number; tone?: string; thickness?: number; highlight?: boolean;
  children: React.ReactNode }> = ({ at = 0, tone, thickness = 8, highlight = false, children }) => {
  const frame = useCurrentFrame();
  const { motion, style } = useTheme();
  const mode = highlight ? "highlight" : style?.stress ?? "underline";  // config/video.yaml › stress
  const color = useColor();
  const shapes = useShapes();
  const k = interpolate(frame - at, [0, Math.max(1, motion.enter)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  if (mode === "colour") return <span style={{ color: k >= 0.5 ? color(tone ?? "accent-ink") : undefined }}>{children}</span>;
  const band = mode === "highlight";  // the accent whole behind the word, which takes the text that reads on it
  return (
    <span style={{ position: "relative", display: "inline-block" }}>
      <span style={{ position: "absolute", left: band ? "-0.12em" : 0, right: band ? "-0.12em" : undefined, bottom: band ? "4%" : -thickness,
        height: band ? "86%" : thickness, width: band ? undefined : `${k * 100}%`, transformOrigin: "left", transform: band ? `scaleX(${k})` : undefined,
        background: color(tone ?? (band ? "accent" : "accent-ink")), borderRadius: shapes.corner(thickness) }} />
      <span style={{ position: "relative", color: band && k >= 0.5 ? color("on-accent") : undefined }}>{children}</span>
    </span>
  );
};
