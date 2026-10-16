import React from "react";
import { AbsoluteFill } from "remotion";
import { Arrow } from "../../atoms/Arrow";
import { Background } from "../../atoms/Background";
import { Enter } from "../../atoms/Enter";
import { Heading } from "../../atoms/Heading";
import { StepNode } from "../../molecules/StepNode";
import { useSayTimes } from "../../timing";
import type { SceneProps } from "../../contract";

// A process that builds itself: each step enters when the narration names it, and the arrow that leads to it draws itself
// just before. Up to five steps in a row.
export type Step = { label: string; text?: string; say?: string };
export type DiagramProps = { title?: string; steps: Step[] };

export default function Diagram({ props }: SceneProps<DiagramProps>) {
  const said = useSayTimes(props.steps.map((s) => s.say));
  const times = said.map((t, i) => t ?? 16 + i * 30);
  const width = props.steps.length > 4 ? 300 : props.steps.length > 3 ? 360 : 440;
  return (
    <AbsoluteFill>
      <Background />
      <AbsoluteFill style={{ padding: "0 90px", gap: 90, justifyContent: "center" }}>
        {props.title ? <Enter><Heading size={84}>{props.title}</Heading></Enter> : null}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 18 }}>
          {props.steps.map((step, i) => (
            <React.Fragment key={i}>
              {i > 0 ? <Arrow at={Math.max(0, times[i] - 12)} length={90} thickness={8} /> : null}
              <Enter at={times[i]} scale><StepNode n={i + 1} label={step.label} text={step.text} width={width} /></Enter>
            </React.Fragment>
          ))}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}
