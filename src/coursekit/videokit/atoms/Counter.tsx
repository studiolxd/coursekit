import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { useTheme } from "../theme";

// A number that counts up to `value` from frame `at`, written as the course language writes it (`locale`).

export const Counter: React.FC<{ value: number; at?: number; frames?: number; decimals?: number; locale?: string;
  prefix?: string; suffix?: string }> = ({ value, at = 0, frames, decimals = 0, locale, prefix = "", suffix = "" }) => {
  const frame = useCurrentFrame();
  const { motion } = useTheme();
  const k = interpolate(frame - at, [0, frames ?? motion.enter * 3], [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const shown = (value * k).toLocaleString(locale, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  return <span>{prefix}{shown}{suffix}</span>;
};
