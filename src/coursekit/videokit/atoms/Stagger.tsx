import React from "react";
import { useSceneMotion, useTheme } from "../theme";
import { Enter, type EnterProps } from "./Enter";

// Children that enter one after another, `motion.stagger` frames apart (or `gap`), from frame `at`. Each child can also enter
// on its own frame with `times` (one frame per child, e.g. the frames in which the narration names each one).

export const Stagger: React.FC<{ at?: number; gap?: number; times?: (number | null)[]; from?: EnterProps["from"];
  children: React.ReactNode; style?: React.CSSProperties }> = ({ at = 0, gap, times, from = "up", children, style }) => {
  const { motion } = useTheme();
  const { reveal } = useSceneMotion();
  const step = reveal === "together" ? 0 : gap ?? motion.stagger;
  return (
    <div style={style}>
      {React.Children.toArray(children).map((child, i) => (
        <Enter key={i} at={times?.[i] ?? at + i * step} from={from}>{child}</Enter>
      ))}
    </div>
  );
};
