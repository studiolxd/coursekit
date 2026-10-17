import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Card } from "../../atoms/Card";
import { Text } from "../../atoms/Text";
import { useColor, useShapes, useTheme } from "../../theme";
import type { LayerProps } from "../../contract";

// A name and a role in the lower third of the screen, from the word it is anchored to until its end: at the left or the right
// (`corner`), with a bar of the accent beside a panel (`bar`), in a card (`card`) or as text alone (`plain`, for a calm scene).
export type LowerThirdProps = { title: string; subtitle?: string; corner?: "bottom-left" | "bottom-right"; style?: "bar" | "card" | "plain" };

export default function LowerThird({ props, frames }: LayerProps<LowerThirdProps>) {
  const frame = useCurrentFrame();
  const { motion } = useTheme();
  const color = useColor();
  const shapes = useShapes();
  const k = interpolate(frame, [0, motion.enter, frames - motion.fade, frames], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const right = props.corner === "bottom-right";
  const look = props.style ?? "bar";
  const text = (
    <div style={{ textAlign: right ? "right" : "left" }}>
      <Text size={40} weight={800} tone="headings" role="label">{props.title}</Text>
      {props.subtitle ? <Text size={28} tone="text-muted" role="caption">{props.subtitle}</Text> : null}
    </div>
  );
  const bar = <div style={{ width: 12, background: color("accent-ink") }} />;
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: right ? "flex-end" : "flex-start", padding: "0 120px 110px" }}>
      <div style={{ opacity: k, transform: `translateX(${(1 - k) * (right ? 60 : -60)}px)`, display: "flex", alignItems: "stretch" }}>
        {look === "card" ? <Card padding={28}>{text}</Card> : null}
        {look === "plain" ? text : null}
        {look === "bar" ? (
          <>
            {right ? null : bar}
            <div style={{ background: color("background"), padding: "22px 36px", boxShadow: shapes.shadow("0 12px 32px rgba(0,0,0,0.12)") }}>{text}</div>
            {right ? bar : null}
          </>
        ) : null}
      </div>
    </AbsoluteFill>
  );
}
