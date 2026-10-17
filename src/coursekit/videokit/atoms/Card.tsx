import React from "react";
import { OnGround, useColor, useShapes } from "../theme";

// A panel on the surface colour of the theme, with its radius and a soft shadow (config/video.yaml › shapes changes both):
// what groups a column, a step or a medium. What is in it is drawn as on the background (theme.tsx › Ground).

export const Card: React.FC<{ children: React.ReactNode; tone?: string; padding?: number; style?: React.CSSProperties }> = (
  { children, tone = "surface", padding = 48, style }) => {
  const shapes = useShapes();
  const color = useColor();
  return (
    <div style={{ background: color(tone, "background"), borderRadius: shapes.radius(20), padding,
      boxShadow: shapes.shadow("0 18px 48px rgba(0,0,0,0.10)"), border: `${shapes.border(2)}px solid ${color("border", "surface")}`,
      ...style }}><OnGround ground="base">{children}</OnGround></div>
  );
};
