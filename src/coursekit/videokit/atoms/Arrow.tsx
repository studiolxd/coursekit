import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { useColor, useTheme } from "../theme";

// An arrow that draws itself from frame `at`, horizontal (`length` px) or vertical: what joins two steps of a diagram. Its
// line is `thickness` px, solid or `dashed`; its head filled, open (two strokes) or none.

export type ArrowHead = "filled" | "open" | "none";

export const Arrow: React.FC<{ at?: number; length?: number; vertical?: boolean; tone?: string; thickness?: number; head?: ArrowHead;
  dashed?: boolean }> = ({ at = 0, length = 120, vertical = false, tone = "accent-ink", thickness = 6, head = "filled", dashed = false }) => {
  const frame = useCurrentFrame();
  const { motion } = useTheme();
  const color = useColor();
  const k = interpolate(frame - at, [0, Math.max(1, motion.enter)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const tip = head === "none" ? 0 : Math.max(thickness * 3, 14);  // a thin arrow keeps a head that can be seen
  const side = Math.max(tip, thickness);  // half of the width of the drawing across the line
  const ink = color(tone);
  const drawn = (length - (head === "filled" ? tip : 0)) * k;
  const dash = dashed ? `${thickness * 3} ${thickness * 2.5}` : undefined;
  // drawn along x and turned for a vertical one
  return (
    <svg width={vertical ? side * 2 : length} height={vertical ? length : side * 2} style={{ flex: "none", overflow: "visible" }}>
      <g transform={vertical ? `rotate(90 ${side} ${side})` : undefined}>
        <line x1={0} y1={side} x2={drawn} y2={side} stroke={ink} strokeWidth={thickness} strokeLinecap="round" strokeDasharray={dash} />
        {k > 0.95 && head === "filled" ? <polygon points={`${length - tip},${side - tip} ${length - tip},${side + tip} ${length},${side}`} fill={ink} /> : null}
        {k > 0.95 && head === "open" ? (
          <polyline points={`${length - tip},${side - tip} ${length},${side} ${length - tip},${side + tip}`} fill="none" stroke={ink}
            strokeWidth={thickness} strokeLinecap="round" strokeLinejoin="round" />
        ) : null}
      </g>
    </svg>
  );
};
