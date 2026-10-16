import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useTheme } from "../theme";

// An element that enters: it fades in and moves from `from` (up, down, left, right or none), with a spring of the theme.
// `at` is the frame of the scene it enters on (use `useAt("word")` to make it the word that names it).

export type EnterProps = { at?: number; from?: "up" | "down" | "left" | "right" | "none"; distance?: number; scale?: boolean;
  children: React.ReactNode; style?: React.CSSProperties };

export const useEnter = (at = 0) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { motion } = useTheme();
  return spring({ frame: frame - at, fps, config: { damping: motion.damping }, durationInFrames: motion.enter });
};

export const Enter: React.FC<EnterProps> = ({ at = 0, from = "up", distance = 40, scale = false, children, style }) => {
  const k = useEnter(at);
  const shift = (1 - k) * distance;
  const move = { up: `translateY(${shift}px)`, down: `translateY(${-shift}px)`, left: `translateX(${shift}px)`,
    right: `translateX(${-shift}px)`, none: "" }[from];
  return (
    <div style={{ opacity: k, transform: `${move} ${scale ? `scale(${0.92 + 0.08 * k})` : ""}`.trim(), ...style }}>{children}</div>
  );
};
