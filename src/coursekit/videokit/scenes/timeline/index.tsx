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
// the versions of a rule. Up to six. The line goes from the first milestone to the last, which falls at its end. Their texts
// go under the line (`labels: below`, by default) or one under and the next over it (`alternate`), so long texts have room:
// each can then take more than its share of the width without stepping on its neighbours.
export type Milestone = { date: string; label: string; say?: string };
export type TimelineProps = { kicker?: string; title?: string; events: Milestone[]; labels?: "below" | "alternate" } & Placing & Titled;

const DOT = 28;  // px of the mark of a milestone
const GAP = 22;  // px between the mark and its texts
const LAST = 340;  // px of the column of the last milestone, whose mark ends the line
const ABOVE = 230;  // px kept over the line for the texts that go over it, alternating

export default function Timeline({ props }: SceneProps<TimelineProps>) {
  const color = useColor();
  const shapes = useShapes();
  const times = useSteps(props.events.map((e) => e.say), 16, 24);
  const line = shapes.border(4);  // the line, as thin as the borders of the style
  const alternate = props.labels === "alternate";
  const n = props.events.length;
  const date = (e: Milestone) => <Text size={36} weight={800} tone="accent-ink" role="kicker">{e.date}</Text>;
  const label = (e: Milestone) => <Text size={40} weight={600} role="body">{e.label}</Text>;
  const top = alternate ? ABOVE : 52;  // where the marks sit: under the dates, or under the room for the texts over the line
  return (
    <Ground variant={props.background} photo={props.photo} veil={props.veil} veilOpacity={props.veil_opacity} credit={props.credit}>
      <Place align={props.align} valign={props.valign} gap={72} apart={props.title_valign === "top"}
        head={<SceneTitle title={props.title} kicker={props.kicker} />}>
        <div style={{ position: "relative", alignSelf: "stretch", display: "flex", textAlign: "left" }}>
          <div style={{ position: "absolute", left: DOT / 2, right: n > 1 ? LAST - DOT / 2 : undefined, width: n > 1 ? undefined : 0,
            top: top + GAP + DOT / 2 - line / 2, height: line, background: color("border", "surface") }} />
          {props.events.map((e, i) => {
            const last = i === n - 1 && n > 1;
            const over = alternate && i % 2 === 1;
            const room = alternate && !last ? "175%" : "100%";  // alternating, a text may reach over the next column
            return (
              <Enter key={i} at={times[i]} style={{ flex: last ? `0 0 ${LAST}px` : "1 1 0", minWidth: 0, paddingRight: last ? 0 : 32 }}>
                <div style={{ height: top, display: "flex", flexDirection: "column", justifyContent: "flex-end", gap: 10, width: room }}>
                  {over ? <>{label(e)}{date(e)}</> : alternate ? null : date(e)}
                </div>
                <div style={{ width: DOT, height: DOT, margin: `${GAP}px 0`, borderRadius: shapes.corner(DOT / 2), background: color("accent-ink") }} />
                <div style={{ display: "flex", flexDirection: "column", gap: 10, width: room }}>
                  {over ? null : alternate ? <>{date(e)}{label(e)}</> : label(e)}
                </div>
              </Enter>
            );
          })}
        </div>
      </Place>
    </Ground>
  );
}
