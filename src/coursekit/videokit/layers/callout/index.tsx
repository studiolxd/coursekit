import React from "react";
import { AbsoluteFill } from "remotion";
import { Card } from "../../atoms/Card";
import { Enter } from "../../atoms/Enter";
import { Text } from "../../atoms/Text";
import { useColor } from "../../theme";
import type { LayerProps } from "../../contract";

// A short note over the scene, at a corner, with a mark at its side: in the accent (a tip, a key word), in the colour of what is
// right or wrong (a good practice, a warning), or none (`surface`, the panel alone).
export type CalloutProps = { text: string; corner?: "top-left" | "top-right" | "bottom-left" | "bottom-right";
  tone?: "accent" | "correct" | "wrong" | "surface" };

export default function Callout({ props }: LayerProps<CalloutProps>) {
  const color = useColor();
  const [v, h] = (props.corner ?? "top-right").split("-");
  const tone = props.tone ?? "accent";
  const side = tone === "surface" ? {} : { borderLeft: `10px solid ${color(`${tone}-ink`)}` };
  return (
    <AbsoluteFill style={{ justifyContent: v === "top" ? "flex-start" : "flex-end", alignItems: h === "left" ? "flex-start" : "flex-end",
      padding: 90 }}>
      <Enter scale from="none">
        <Card padding={32} style={{ maxWidth: 720, display: "flex", gap: 22, alignItems: "center", ...side }}>
          <Text size={44} weight={700}>{props.text}</Text>
        </Card>
      </Enter>
    </AbsoluteFill>
  );
}
