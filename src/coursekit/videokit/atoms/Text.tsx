import React from "react";
import { useColor, useTheme, useWeight } from "../theme";

// Body text in the font and colours of the theme.

export const Text: React.FC<{ children: React.ReactNode; size?: number; tone?: string; weight?: number;
  style?: React.CSSProperties }> = ({ children, size = 48, tone = "text", weight = 400, style }) => {
  const { tokens } = useTheme();
  const color = useColor();
  const weightOf = useWeight();
  return (
    <div style={{ fontFamily: tokens.font.family, fontSize: size, fontWeight: weightOf(weight), lineHeight: 1.35, color: color(tone, "text"),
      ...style }}>{children}</div>
  );
};
