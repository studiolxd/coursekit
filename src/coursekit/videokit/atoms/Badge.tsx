import React from "react";
import { useColor, useTheme } from "../theme";

// A number (or a short mark) in a circle of the accent of the theme: the order of a step or of an item of a list.

export const Badge: React.FC<{ children: React.ReactNode; size?: number; tone?: string }> = ({ children, size = 72, tone = "accent" }) => {
  const { tokens } = useTheme();
  const color = useColor();
  return (
    <div style={{ width: size, height: size, borderRadius: "50%", background: color(tone), color: color(`on-${tone}`, "background"),
      display: "flex", alignItems: "center", justifyContent: "center", fontFamily: tokens.font.headings ?? tokens.font.family,
      fontWeight: 800, fontSize: size * 0.45, flex: "none" }}>{children}</div>
  );
};
