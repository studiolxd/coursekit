import React from "react";
import { Ground } from "../../atoms/Ground";
import { Kicker } from "../../atoms/Kicker";
import { Place, type Placing } from "../../atoms/Place";
import { Enter } from "../../atoms/Enter";
import { Heading } from "../../atoms/Heading";
import { Text } from "../../atoms/Text";
import type { SceneProps } from "../../contract";

// The close: what to keep, in a line, and what comes next; on the accent and centred unless it says otherwise.
export type OutroProps = { kicker?: string; title: string; next?: string } & Placing;

export default function Outro({ props }: SceneProps<OutroProps>) {
  return (
    <Ground variant={props.background ?? "accent"} photo={props.photo} veil={props.veil} veilOpacity={props.veil_opacity} credit={props.credit}>
      <Place align={props.align ?? "center"} valign={props.valign} gap={40}>
        {props.kicker ? <Kicker>{props.kicker}</Kicker> : null}
        <Enter scale><Heading size={88} style={{ maxWidth: 1400 }}>{props.title}</Heading></Enter>
        {props.next ? <Enter at={16}><Text size={40} role="subheading" style={{ maxWidth: 1400 }}>{props.next}</Text></Enter> : null}
      </Place>
    </Ground>
  );
}
