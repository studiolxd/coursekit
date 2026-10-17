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
  const band = mode === "highlight";
  return (
    <span style={{ position: "relative", display: "inline-block" }}>
      <span style={{ position: "absolute", left: 0, bottom: band ? "8%" : -thickness, height: band ? "40%" : thickness,
        width: `${k * 100}%`, background: color(tone ?? (band ? "accent" : "accent-ink")), opacity: band ? 0.35 : 1, borderRadius: shapes.corner(thickness) }} />
      <span style={{ position: "relative" }}>{children}</span>
    </span>
  );
};
