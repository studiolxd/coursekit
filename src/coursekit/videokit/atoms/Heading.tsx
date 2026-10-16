import React from "react";
import { useColor, useTheme, useWeight } from "../theme";

// A heading in the font and colours of the theme. `size` is in px of a 1920 x 1080 frame; `tone` picks the colour token.

export const Heading: React.FC<{ children: React.ReactNode; size?: number; tone?: string; weight?: number;
  style?: React.CSSProperties }> = ({ children, size = 84, tone = "headings", weight = 800, style }) => {
  const { tokens } = useTheme();
  const color = useColor();
  const weightOf = useWeight();
  return (
    <div style={{ fontFamily: tokens.font.headings ?? tokens.font.family, fontSize: size, fontWeight: weightOf(weight), lineHeight: 1.1,
      color: color(tone, "text"), letterSpacing: -0.5, ...style }}>{children}</div>
  );
};
