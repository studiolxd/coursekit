import React from "react";
import { useColor, useShapes, useText, useTheme } from "../theme";

// A number (or a short mark) on the accent of the theme: the order of a step or of an item of a list. A circle, unless the style
// sets a radius (config/video.yaml › shapes): then a square with that rounding, as a brand with square corners marks its steps.

export const Badge: React.FC<{ children: React.ReactNode; size?: number; tone?: string }> = ({ children, size = 72, tone = "accent" }) => {
  const { tokens } = useTheme();
  const color = useColor();
  const typeOf = useText();
  const shapes = useShapes();
  const { tone: _ink, ...type } = typeOf("step", { family: tokens.font.headings ?? tokens.font.family, size: size * 0.45, weight: 800,
    tone: `on-${tone}`, leading: 1, tracking: 0 });
  return (
    <div style={{ width: size, height: size, borderRadius: shapes.corner(size / 2), background: color(tone), color: color(`on-${tone}`, "background"),
      display: "flex", alignItems: "center", justifyContent: "center", ...type, flex: "none" }}>{children}</div>
  );
};
