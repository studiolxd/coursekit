import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Text } from "../../atoms/Text";
import { useColor, useShapes, useTheme } from "../../theme";
import type { LayerProps } from "../../contract";

// A name and a role in the lower third of the screen, from the word it is anchored to until its end.
export type LowerThirdProps = { title: string; subtitle?: string };

export default function LowerThird({ props, frames }: LayerProps<LowerThirdProps>) {
  const frame = useCurrentFrame();
  const { motion } = useTheme();
  const color = useColor();
  const shapes = useShapes();
  const k = interpolate(frame, [0, motion.enter, frames - motion.fade, frames], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", padding: "0 0 110px 120px" }}>
      <div style={{ opacity: k, transform: `translateX(${(1 - k) * -60}px)`, display: "flex", alignItems: "stretch", gap: 0 }}>
        <div style={{ width: 12, background: color("accent-ink") }} />
        <div style={{ background: color("background"), padding: "22px 36px", boxShadow: shapes.shadow("0 12px 32px rgba(0,0,0,0.12)") }}>
          <Text size={40} weight={800} tone="headings" role="label">{props.title}</Text>
          {props.subtitle ? <Text size={28} tone="text-muted" role="caption">{props.subtitle}</Text> : null}
        </div>
      </div>
    </AbsoluteFill>
  );
}
