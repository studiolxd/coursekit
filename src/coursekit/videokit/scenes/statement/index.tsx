import React from "react";
import { AbsoluteFill } from "remotion";
import { Background } from "../../atoms/Background";
import { Enter } from "../../atoms/Enter";
import { Heading } from "../../atoms/Heading";
import { Text } from "../../atoms/Text";
import { Underline } from "../../atoms/Underline";
import { useAt } from "../../timing";
import type { SceneProps } from "../../contract";

// A phrase to keep, large and alone; `stress`, a word of the phrase, is underlined when the narration says it.
export type StatementProps = {
  kicker?: string; text: string; stress?: string;
  background?: "plain" | "surface" | "accent"; align?: "left" | "center";
};

export default function Statement({ props }: SceneProps<StatementProps>) {
  const at = useAt(props.stress, 24);
  const ink = props.background === "accent" ? "on-accent" : undefined;
  const align = props.align ?? "left";
  const i = props.stress ? props.text.toLowerCase().indexOf(props.stress.toLowerCase()) : -1;
  const phrase = i >= 0
    ? <>{props.text.slice(0, i)}<Underline at={at} tone={ink}>{props.text.slice(i, i + props.stress!.length)}</Underline>{props.text.slice(i + props.stress!.length)}</>
    : props.text;
  return (
    <AbsoluteFill>
      <Background variant={props.background} />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: align === "center" ? "center" : "flex-start", textAlign: align,
        padding: "0 200px", gap: 32 }}>
        {props.kicker ? (
          <Enter><Text size={36} tone={ink ?? "accent-ink"} weight={800} role="kicker" style={{ textTransform: "uppercase", letterSpacing: 2 }}>
            {props.kicker}</Text></Enter>
        ) : null}
        <Enter at={6}><Heading size={props.text.length > 70 ? 76 : 92} tone={ink ?? "headings"} role="statement" style={{ maxWidth: 1400 }}>
          {phrase}</Heading></Enter>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}
