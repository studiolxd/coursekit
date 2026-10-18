import React from "react";
import { AbsoluteFill, useVideoConfig } from "remotion";
import { Card } from "../../atoms/Card";
import { Text } from "../../atoms/Text";
import { useEnter } from "../../atoms/Enter";
import { useColor } from "../../theme";
import type { LayerProps } from "../../contract";

// A short label with a line that points at a spot of the scene (fractions of the screen, fx and fy): the label goes to one
// side of it (`side`), far enough not to cover it.
export type PointerProps = { fx: number; fy: number; text: string; side?: "left" | "right" | "top" | "bottom"; width?: number };

const REACH = 220;  // px from the spot to the label

export default function Pointer({ props }: LayerProps<PointerProps>) {
  const { width, height } = useVideoConfig();
  const color = useColor();
  const k = useEnter(0);
  const side = props.side ?? "left";
  const x = props.fx * width;
  const y = props.fy * height;
  const [dx, dy] = { left: [-REACH, 0], right: [REACH, 0], top: [0, -REACH * 0.7], bottom: [0, REACH * 0.7] }[side];
  const anchor: React.CSSProperties = {
    left: { right: width - (x + dx), top: y + dy, transform: "translateY(-50%)" },
    right: { left: x + dx, top: y + dy, transform: "translateY(-50%)" },
    top: { left: x + dx, bottom: height - (y + dy), transform: "translateX(-50%)" },
    bottom: { left: x + dx, top: y + dy, transform: "translateX(-50%)" },
  }[side];
  return (
    <AbsoluteFill style={{ opacity: k }}>
      <svg width={width} height={height} style={{ position: "absolute", inset: 0 }}>
        <line x1={x + dx * k} y1={y + dy * k} x2={x} y2={y} stroke={color("accent-ink")} strokeWidth={props.width ?? 5} strokeLinecap="round" />
        <circle cx={x} cy={y} r={Math.max(6, (props.width ?? 5) * 2.4)} fill={color("accent-ink")} />
      </svg>
      <div style={{ position: "absolute", ...anchor }}>
        <Card padding={20} style={{ maxWidth: 520 }}><Text size={34} weight={700} role="label">{props.text}</Text></Card>
      </div>
    </AbsoluteFill>
  );
}
