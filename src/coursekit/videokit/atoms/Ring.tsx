import React from "react";
import { useColor, useShapes } from "../theme";
import { useEnter } from "./Enter";

// A ring that marks a point (fractions of its parent) from frame `at`; `shape: box`, a rounded box instead; `dim` darkens
// everything around it.

export const Ring: React.FC<{ fx: number; fy: number; at?: number; size?: number; tone?: string; shape?: "ring" | "box";
  dim?: boolean }> = ({ fx, fy, at = 0, size = 72, tone = "accent-ink", shape = "ring", dim = false }) => {
  const shapes = useShapes();
  const w = shape === "box" ? size * 1.8 : size;
  const k = useEnter(at);
  const color = useColor();
  return (
    <div style={{ position: "absolute", left: `${fx * 100}%`, top: `${fy * 100}%`, width: w, height: size, marginLeft: -w / 2,
      marginTop: -size / 2, borderRadius: shape === "box" ? shapes.corner(16) : "50%", border: `5px solid ${color(tone)}`, opacity: k,
      transform: `scale(${1.4 - 0.4 * k})`, boxShadow: dim ? `0 0 0 4000px rgba(0,0,0,${(0.45 * k).toFixed(3)})` : undefined }} />
  );
};
