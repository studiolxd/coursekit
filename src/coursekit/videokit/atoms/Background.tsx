import React from "react";
import { AbsoluteFill } from "remotion";
import { useColor } from "../theme";

// The background of a scene: the background colour of the theme, plain, or with a soft band of its surface colour.

export const Background: React.FC<{ variant?: "plain" | "band" | "accent"; children?: React.ReactNode }> = (
  { variant = "plain", children }) => {
  const color = useColor();
  const base = variant === "accent" ? color("accent") : color("background");
  return (
    <AbsoluteFill style={{ background: base }}>
      {variant === "band" ? (
        <div style={{ position: "absolute", left: 0, top: "62%", width: "100%", height: "38%", background: color("surface", "background") }} />
      ) : null}
      {children}
    </AbsoluteFill>
  );
};
