import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { useColor } from "../theme";

// The background of a scene, in the colours of the theme: `plain`; `band`, a band of the surface colour; `shape`, a soft
// shape of the accent that drifts slowly; `accent`, the accent colour itself (a close).

export const Background: React.FC<{ variant?: "plain" | "band" | "shape" | "accent"; children?: React.ReactNode }> = (
  { variant = "plain", children }) => {
  const frame = useCurrentFrame();
  const color = useColor();
  const base = variant === "accent" ? color("accent") : color("background");
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
