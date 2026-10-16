import React from "react";
import { AbsoluteFill } from "remotion";
import { Card } from "../../atoms/Card";
import { Enter } from "../../atoms/Enter";
import { Text } from "../../atoms/Text";
import { useColor } from "../../theme";
import type { LayerProps } from "../../contract";

// A short note over the scene, at a corner, with a mark of the accent: a warning, a tip, a key word.
export type CalloutProps = { text: string; corner?: "top-left" | "top-right" | "bottom-left" | "bottom-right" };

export default function Callout({ props }: LayerProps<CalloutProps>) {
  const color = useColor();
  const [v, h] = (props.corner ?? "top-right").split("-");
  return (
    <AbsoluteFill style={{ justifyContent: v === "top" ? "flex-start" : "flex-end", alignItems: h === "left" ? "flex-start" : "flex-end",
      padding: 90 }}>
      <Enter scale from="none">
        <Card padding={32} style={{ maxWidth: 720, display: "flex", gap: 22, alignItems: "center", borderLeft: `10px solid ${color("accent")}` }}>
          <Text size={44} weight={700}>{props.text}</Text>
        </Card>
      </Enter>
    </AbsoluteFill>
  );
}
