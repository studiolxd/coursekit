import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { useColor, useShapes, useTheme } from "../theme";

// A line that draws itself under (or over, as a highlight) its children from frame `at`: the line in the accent that reads on
// the background, the highlight (a fill behind the words) in the accent itself.

export const Underline: React.FC<{ at?: number; tone?: string; thickness?: number; highlight?: boolean;
  children: React.ReactNode }> = ({ at = 0, tone, thickness = 8, highlight = false, children }) => {
  const frame = useCurrentFrame();
  const { motion } = useTheme();
  const color = useColor();
  const shapes = useShapes();
  const k = interpolate(frame - at, [0, motion.enter], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <span style={{ position: "relative", display: "inline-block" }}>
      <span style={{ position: "absolute", left: 0, bottom: highlight ? "8%" : -thickness, height: highlight ? "40%" : thickness,
        width: `${k * 100}%`, background: color(tone ?? (highlight ? "accent" : "accent-strong")), opacity: highlight ? 0.35 : 1, borderRadius: shapes.corner(thickness) }} />
      <span style={{ position: "relative" }}>{children}</span>
    </span>
  );
};
