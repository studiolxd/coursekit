import React from "react";
import { useColor, useText, useTheme } from "../theme";

// Body text in the font and colours of the theme. `role` is the role of the text (body by default: kicker, label, caption…):
// the typography the project fixes for it (config/video.yaml › text) goes over what the piece asks for here. `family` is the
// piece's own family for its role (a monospaced one for code), when the project fixes none.

export const Text: React.FC<{ children: React.ReactNode; size?: number; tone?: string; weight?: number; role?: string;
  family?: string; style?: React.CSSProperties }> = ({ children, size = 48, tone = "text", weight = 400, role = "body", family, style }) => {
  const { tokens } = useTheme();
  const color = useColor();
  const typeOf = useText();
  const { tone: ink, ...type } = typeOf(role, { family: family ?? tokens.font.family, size, weight, tone, leading: 1.35,
    tracking: Number(style?.letterSpacing ?? 0), transform: style?.textTransform as string | undefined });
  return <div style={{ ...style, ...type, color: color(ink, "text") }}>{children}</div>;
};
