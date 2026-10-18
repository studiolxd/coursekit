import React from "react";
import { AbsoluteFill } from "remotion";
import { Card } from "../../atoms/Card";
import { Enter } from "../../atoms/Enter";
import { Text } from "../../atoms/Text";
import { useColor } from "../../theme";
import type { LayerProps } from "../../contract";

// A short note over the scene, at a corner, with a mark at its side: in the accent (a tip, a key word), in the colour of what is
// right or wrong (a good practice, a warning), or none (`surface`, the panel alone). `look: fill` fills the whole note with
// that colour instead (the accent: the highlighted note of the brand), its text in the colour that reads on it.
export type CalloutProps = { text: string; corner?: "top-left" | "top-right" | "bottom-left" | "bottom-right";
  tone?: "accent" | "correct" | "wrong" | "surface"; look?: "bar" | "fill" };

const FILL: Record<string, [string, string]> = {  // the fill of each tone and the text on it
  accent: ["surface-highlight", "text"], correct: ["correct", "on-correct"], wrong: ["wrong", "on-wrong"], surface: ["surface", "text"],
};

export default function Callout({ props }: LayerProps<CalloutProps>) {
  const color = useColor();
  const [v, h] = (props.corner ?? "top-right").split("-");
  const tone = props.tone ?? "accent";
  const filled = props.look === "fill";
  const side = filled || tone === "surface" ? {} : { borderLeft: `10px solid ${color(`${tone}-ink`)}` };
  const [fill, ink] = FILL[tone] ?? FILL.accent;
  return (
    <AbsoluteFill style={{ justifyContent: v === "top" ? "flex-start" : "flex-end", alignItems: h === "left" ? "flex-start" : "flex-end",
      padding: 90 }}>
      <Enter scale from="none">
        <Card padding={32} tone={filled ? fill : "surface"} style={{ maxWidth: 720, display: "flex", gap: 22, alignItems: "center", ...side,
          ...(filled ? { borderColor: color(fill, "surface") } : {}) }}>
          <Text size={44} weight={700} tone={filled ? ink : "text"}>{props.text}</Text>
        </Card>
      </Enter>
    </AbsoluteFill>
  );
}
