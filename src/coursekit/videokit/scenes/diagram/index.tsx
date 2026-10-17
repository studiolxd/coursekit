import React from "react";
import { Arrow } from "../../atoms/Arrow";
import { Ground } from "../../atoms/Ground";
import { Enter } from "../../atoms/Enter";
import { SceneTitle } from "../../atoms/SceneTitle";
import { ITEMS, Place, type Placing, type Titled } from "../../atoms/Place";
import { StepNode } from "../../molecules/StepNode";
import { useSteps } from "../../timing";
import type { SceneProps } from "../../contract";

// A process that builds itself: each step enters when the narration names it, and the arrow that leads to it draws itself
// just before (`arrows: false`: no arrows, the steps side by side); `numbers: false` leaves out the number of each step. Up to five steps in a row.
export type Step = { label: string; text?: string; say?: string };
export type DiagramProps = { kicker?: string; title?: string; steps: Step[]; arrows?: boolean; numbers?: boolean } & Placing & Titled;

export default function Diagram({ props }: SceneProps<DiagramProps>) {
  const times = useSteps(props.steps.map((s) => s.say), 16, 30);
  const arrows = props.arrows ?? true;
  return (
    <Ground variant={props.background} photo={props.photo} veil={props.veil} veilOpacity={props.veil_opacity} credit={props.credit}>
      <Place align={props.align} valign={props.valign} gap={90} apart={props.title_valign === "top"}
        head={<SceneTitle title={props.title} kicker={props.kicker} />}>
        <div style={{ display: "flex", alignItems: "stretch", justifyContent: ITEMS[props.align ?? "left"], gap: arrows ? 18 : 40, alignSelf: "stretch", textAlign: "left" }}>
          {props.steps.map((step, i) => (
            <React.Fragment key={i}>
              {i > 0 && arrows ? <div style={{ alignSelf: "center", flex: "none" }}><Arrow at={Math.max(0, times[i] - 12)} length={90} thickness={8} /></div> : null}
              <Enter at={times[i]} scale style={{ display: "flex", flex: "1 1 0", minWidth: 0, maxWidth: 440 }}>
                <StepNode n={props.numbers ?? true ? i + 1 : undefined} label={step.label} text={step.text} />
              </Enter>
            </React.Fragment>
          ))}
        </div>
      </Place>
    </Ground>
  );
}
