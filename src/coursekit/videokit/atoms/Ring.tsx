import React from "react";
import { useColor } from "../theme";
import { useEnter } from "./Enter";

// A ring that marks a point (fractions of its parent) from frame `at`.

export const Ring: React.FC<{ fx: number; fy: number; at?: number; size?: number; tone?: string }> = (
  { fx, fy, at = 0, size = 72, tone = "accent-strong" }) => {
  const k = useEnter(at);
  const color = useColor();
  return (
    <div style={{ position: "absolute", left: `${fx * 100}%`, top: `${fy * 100}%`, width: size, height: size, marginLeft: -size / 2,
      marginTop: -size / 2, borderRadius: "50%", border: `5px solid ${color(tone)}`, opacity: k, transform: `scale(${1.4 - 0.4 * k})` }} />
  );
};
