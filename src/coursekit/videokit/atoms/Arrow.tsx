import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { useColor, useTheme } from "../theme";

// An arrow that draws itself from frame `at`, horizontal (`length` px) or vertical: what joins two steps of a diagram.

export const Arrow: React.FC<{ at?: number; length?: number; vertical?: boolean; tone?: string; thickness?: number }> = (
  { at = 0, length = 120, vertical = false, tone = "accent-ink", thickness = 6 }) => {
  const frame = useCurrentFrame();
  const { motion } = useTheme();
  const color = useColor();
  const k = interpolate(frame - at, [0, motion.enter], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const head = thickness * 3;
  const w = vertical ? head * 2 : length;
  const h = vertical ? length : head * 2;
  const drawn = (length - head) * k;
  return (
    <svg width={w} height={h} style={{ flex: "none", overflow: "visible" }}>
      {vertical ? (
        <>
          <line x1={head} y1={0} x2={head} y2={drawn} stroke={color(tone)} strokeWidth={thickness} strokeLinecap="round" />
          {k > 0.95 ? <polygon points={`${head - head},${length - head} ${head + head},${length - head} ${head},${length}`} fill={color(tone)} /> : null}
        </>
      ) : (
        <>
          <line x1={0} y1={head} x2={drawn} y2={head} stroke={color(tone)} strokeWidth={thickness} strokeLinecap="round" />
          {k > 0.95 ? <polygon points={`${length - head},${0} ${length - head},${head * 2} ${length},${head}`} fill={color(tone)} /> : null}
        </>
      )}
    </svg>
  );
};
