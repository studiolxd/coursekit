import React from "react";
import { useColor, useTheme } from "../theme";

// A panel on the surface colour of the theme, with its radius and a soft shadow: what groups a column, a step or a medium.

export const Card: React.FC<{ children: React.ReactNode; tone?: string; padding?: number; style?: React.CSSProperties }> = (
  { children, tone = "surface", padding = 48, style }) => {
  const { tokens } = useTheme();
  const color = useColor();
  return (
    <div style={{ background: color(tone, "background"), borderRadius: tokens.radius ?? 20, padding,
      boxShadow: "0 18px 48px rgba(0,0,0,0.10)", border: `2px solid ${color("line", "surface")}`, ...style }}>{children}</div>
  );
};
