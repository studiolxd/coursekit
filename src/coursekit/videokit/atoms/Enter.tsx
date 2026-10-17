import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useSceneMotion, useTheme } from "../theme";

// An element that enters: it fades in and moves from `from` (up, down, left, right or none), with a spring of the theme.
// `at` is the frame of the scene it enters on (use `useAt("word")` to make it the word that names it). The entrance of the
// scene or of the project (config/video.yaml › motion › entrance) changes how: auto, the piece's own way (`from`, `scale`);
// fade, it only appears; rise, it rises; slide, it comes from its side; scale, it grows; none, it is there at its moment.

export type EnterProps = { at?: number; from?: "up" | "down" | "left" | "right" | "none"; distance?: number; scale?: boolean;
  children: React.ReactNode; style?: React.CSSProperties };

export const useEnter = (at = 0) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { motion } = useTheme();
  const { entrance } = useSceneMotion();
  if (entrance === "none" || motion.enter <= 0) return frame >= at ? 1 : 0;
  return spring({ frame: frame - at, fps, config: { damping: motion.damping }, durationInFrames: motion.enter });
};

export const Enter: React.FC<EnterProps> = ({ at = 0, from = "up", distance = 40, scale = false, children, style }) => {
  const k = useEnter(at);
  const { entrance } = useSceneMotion();
  const shift = (1 - k) * distance;
  const way = entrance === "rise" ? "up" : entrance === "slide" ? (from === "right" ? "right" : "left") : entrance === "auto" ? from : "none";
  const move = { up: `translateY(${shift}px)`, down: `translateY(${-shift}px)`, left: `translateX(${shift}px)`,
    right: `translateX(${-shift}px)`, none: "" }[way];
  const grow = entrance === "scale" || (entrance === "auto" && scale) ? `scale(${0.92 + 0.08 * k})` : "";
  return <div style={{ opacity: k, transform: `${move} ${grow}`.trim(), ...style }}>{children}</div>;
};
