import React from "react";
import { Ground } from "../../atoms/Ground";
import { Enter } from "../../atoms/Enter";
import { SceneTitle } from "../../atoms/SceneTitle";
import { Place, type Placing, type Titled } from "../../atoms/Place";
import { Badge } from "../../atoms/Badge";
import { Text } from "../../atoms/Text";
import { useColor, useShapes } from "../../theme";
import { useSteps } from "../../timing";
import type { SceneProps } from "../../contract";

// A list (steps, rules, keys): each item enters when the narration says it. Each item is marked with its number (`marker:
// number`, by default), a bullet in the accent (`bullet`) or nothing (`none`).
export type ListItem = { text: string; say?: string };
export type ListProps = { kicker?: string; title: string; items: ListItem[]; marker?: "number" | "bullet" | "none" } & Placing & Titled;

export default function List({ props }: SceneProps<ListProps>) {
  const times = useSteps(props.items.map((i) => i.say), 20, 14);
  const color = useColor();
  const shapes = useShapes();
  const marker = props.marker ?? "number";
  return (
    <Ground variant={props.background} photo={props.photo} veil={props.veil} veilOpacity={props.veil_opacity} credit={props.credit}>
      <Place align={props.align} valign={props.valign} gap={72} apart={props.title_valign === "top"}
        head={<SceneTitle title={props.title} kicker={props.kicker} />}>
        <div style={{ display: "flex", flexDirection: "column", gap: 44, textAlign: "left" }}>
          {props.items.map((item, i) => (
            <Enter key={i} at={times[i]} from="left" style={{ display: "flex", gap: 32, alignItems: "center" }}>
              {marker === "number" ? <Badge size={88}>{i + 1}</Badge> : null}
              {marker === "bullet" ? (
                <div style={{ width: 26, height: 26, borderRadius: shapes.corner(13), background: color("accent-ink"), flex: "none" }} />
              ) : null}
              <Text size={60} weight={600}>{item.text}</Text>
            </Enter>
          ))}
        </div>
      </Place>
    </Ground>
  );
}
