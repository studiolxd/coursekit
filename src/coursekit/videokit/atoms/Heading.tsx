import React from "react";
import { useColor, useText, useTheme } from "../theme";

// A heading in the font and colours of the theme. `size` is in px of a 1920 x 1080 frame; `tone` picks the colour token; `role`
// is the role of the text (heading by default: display, quote, statement, stat…), whose typography the project fixes
// (config/video.yaml › text) over what the piece asks for here.

export const Heading: React.FC<{ children: React.ReactNode; size?: number; tone?: string; weight?: number; role?: string;
  style?: React.CSSProperties }> = ({ children, size = 84, tone = "headings", weight = 800, role = "heading", style }) => {
  const { tokens } = useTheme();
  const color = useColor();
  const typeOf = useText();
  const { tone: ink, ...type } = typeOf(role, { family: tokens.font.headings ?? tokens.font.family, size, weight, tone, leading: 1.1,
    tracking: -0.5 });
  return <div style={{ ...style, ...type, color: color(ink, "text") }}>{children}</div>;
};
