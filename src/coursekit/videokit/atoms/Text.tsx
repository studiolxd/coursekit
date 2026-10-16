import React from "react";
import { useColor, useTheme } from "../theme";

// Body text in the font and colours of the theme.

export const Text: React.FC<{ children: React.ReactNode; size?: number; tone?: string; weight?: number;
  style?: React.CSSProperties }> = ({ children, size = 40, tone = "text", weight = 400, style }) => {
  const { tokens } = useTheme();
  const color = useColor();
  return (
    <div style={{ fontFamily: tokens.font.family, fontSize: size, fontWeight: weight, lineHeight: 1.35, color: color(tone, "text"),
      ...style }}>{children}</div>
  );
};
