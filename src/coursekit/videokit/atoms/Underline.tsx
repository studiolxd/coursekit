import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { useColor, useTheme } from "../theme";

// A line that draws itself under (or over, as a highlight) its children from frame `at`, in the accent of the theme.

export const Underline: React.FC<{ at?: number; tone?: string; thickness?: number; highlight?: boolean;
  children: React.ReactNode }> = ({ at = 0, tone = "accent", thickness = 8, highlight = false, children }) => {
  const frame = useCurrentFrame();
  const { motion } = useTheme();
  const color = useColor();
  const k = interpolate(frame - at, [0, motion.enter], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <span style={{ position: "relative", display: "inline-block" }}>
      <span style={{ position: "absolute", left: 0, bottom: highlight ? "8%" : -thickness, height: highlight ? "40%" : thickness,
        width: `${k * 100}%`, background: color(tone), opacity: highlight ? 0.35 : 1, borderRadius: thickness }} />
      <span style={{ position: "relative" }}>{children}</span>
    </span>
  );
};
