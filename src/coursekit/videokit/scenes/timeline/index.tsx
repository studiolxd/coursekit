import React from "react";
import { Ground } from "../../atoms/Ground";
import { Enter } from "../../atoms/Enter";
import { SceneTitle } from "../../atoms/SceneTitle";
import { Place, type Placing, type Titled } from "../../atoms/Place";
import { Text } from "../../atoms/Text";
import { useColor, useShapes } from "../../theme";
import { useSteps } from "../../timing";
import type { SceneProps } from "../../contract";

// Milestones with their date on a line, entering as the narration names them (`say`): a history, the phases of a project,
// the versions of a rule. Up to six.
export type Milestone = { date: string; label: string; say?: string };
export type TimelineProps = { kicker?: string; title?: string; events: Milestone[] } & Placing & Titled;

export default function Timeline({ props }: SceneProps<TimelineProps>) {
  const color = useColor();
  const shapes = useShapes();
  const times = useSteps(props.events.map((e) => e.say), 16, 24);
  return (
    <Ground variant={props.background} photo={props.photo} veil={props.veil} veilOpacity={props.veil_opacity} credit={props.credit}>
      <Place align={props.align} valign={props.valign} gap={72} apart={props.title_valign === "top"}
        head={<SceneTitle title={props.title} kicker={props.kicker} />}>
        <div style={{ position: "relative", alignSelf: "stretch", display: "flex", textAlign: "left" }}>
          <div style={{ position: "absolute", left: 0, right: 0, top: 86, height: 4, background: color("border", "surface") }} />
          {props.events.map((e, i) => (
            <Enter key={i} at={times[i]} style={{ flex: "1 1 0", minWidth: 0, paddingRight: 32 }}>
              <Text size={36} weight={800} tone="accent-ink" role="kicker">{e.date}</Text>
              <div style={{ width: 28, height: 28, margin: "22px 0 26px", borderRadius: shapes.corner(14), background: color("accent-ink") }} />
              <Text size={40} weight={600} role="body">{e.label}</Text>
            </Enter>
          ))}
        </div>
      </Place>
    </Ground>
  );
}
