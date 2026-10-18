import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { useColor, useTheme } from "../theme";

// The background of a scene, in the colours of the theme (without `variant`, the one of the style of the project): `plain`; `band`, a band of the surface colour; `shape`, a soft
// shape of the accent that drifts slowly; `surface`, the surface colour whole; `accent`, the accent colour itself; `inverse`, the colour of the text (a close in the dark of the brand).

export const Background: React.FC<{ variant?: "plain" | "band" | "shape" | "surface" | "accent" | "inverse"; children?: React.ReactNode }> = (
  { variant: asked, children }) => {
  const frame = useCurrentFrame();
  const color = useColor();
  const { style } = useTheme();
  const variant = asked ?? style?.background ?? "plain"; // a scene that asks for none gets the one of the project
  const base = variant === "accent" ? color("accent") : variant === "inverse" ? color("text")  // the colour of the text whole
    : variant === "surface" ? color("surface", "background") : color("background");
  const drift = interpolate(frame, [0, 600], [0, 40], { extrapolateRight: "extend" });
  return (
    <AbsoluteFill style={{ background: base, overflow: "hidden" }}>
      {variant === "band" ? (
        <div style={{ position: "absolute", left: 0, top: "62%", width: "100%", height: "38%", background: color("surface", "background") }} />
      ) : null}
      {variant === "shape" ? (
        <>
          <div style={{ position: "absolute", width: 900, height: 900, right: -300 + drift, top: -380, borderRadius: "50%",
            background: color("accent"), opacity: 0.07 }} />
          <div style={{ position: "absolute", width: 520, height: 520, left: -220, bottom: -260 - drift / 2, borderRadius: "50%",
            background: color("accent"), opacity: 0.05 }} />
        </>
      ) : null}
      {children}
    </AbsoluteFill>
  );
};
