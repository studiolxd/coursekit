import React from "react";
import { AbsoluteFill } from "remotion";
import { Background } from "../../atoms/Background";
import { Enter } from "../../atoms/Enter";
import { Heading } from "../../atoms/Heading";
import { Text } from "../../atoms/Text";
import type { SceneProps } from "../../contract";

// The close: what to keep, in a line, and what comes next.
export type OutroProps = { title: string; next?: string };

export default function Outro({ props }: SceneProps<OutroProps>) {
  return (
    <AbsoluteFill>
      <Background variant="accent" />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", textAlign: "center", padding: "0 200px", gap: 40 }}>
        <Enter scale><Heading size={88} tone="on-accent">{props.title}</Heading></Enter>
        {props.next ? <Enter at={16}><Text size={40} tone="on-accent" role="subheading">{props.next}</Text></Enter> : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
}
