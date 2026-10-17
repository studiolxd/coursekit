import React from "react";
import { Ground } from "../../atoms/Ground";
import { SceneTitle } from "../../atoms/SceneTitle";
import { Place, type Placing, type Titled } from "../../atoms/Place";
import { StatBlock } from "../../molecules/StatBlock";
import { useAt } from "../../timing";
import type { SceneProps } from "../../contract";

// A figure with what it measures and its source, under a title if it has one; it counts up when the narration says it (`say`).
export type StatProps = { kicker?: string; title?: string; value: number; prefix?: string; suffix?: string; decimals?: number; label: string; source: string;
  say?: string; locale?: string; layout?: "stacked" | "side" } & Placing & Titled;

export default function Stat({ props }: SceneProps<StatProps>) {
  const at = useAt(props.say, 6);
  return (
    <Ground variant={props.background} photo={props.photo} veil={props.veil} veilOpacity={props.veil_opacity} credit={props.credit}>
      <Place align={props.align} valign={props.valign} gap={64} apart={props.title_valign === "top"}
        head={<SceneTitle title={props.title} kicker={props.kicker} />}>
        <StatBlock {...props} at={at} />
      </Place>
    </Ground>
  );
}
