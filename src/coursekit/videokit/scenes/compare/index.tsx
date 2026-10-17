import React from "react";
import { Ground } from "../../atoms/Ground";
import { Enter } from "../../atoms/Enter";
import { SceneTitle } from "../../atoms/SceneTitle";
import { Place, type Placing, type Titled } from "../../atoms/Place";
import { CompareColumn } from "../../molecules/CompareColumn";
import { useSceneMotion } from "../../theme";
import { useAt } from "../../timing";
import type { SceneProps } from "../../contract";

// Two sides compared: each column enters when the narration names it, and its items when they are said.
export type Side = { title: string; items: string[]; say?: string; mood?: "good" | "bad" | "neutral" };
export type CompareProps = { kicker?: string; title?: string; left: Side; right: Side; marks?: boolean } & Placing & Titled;

export default function Compare({ props }: SceneProps<CompareProps>) {
  const leftAt = useAt(props.left.say, 8);
  const said = useAt(props.right.say, leftAt + 30);
  const rightAt = useSceneMotion().reveal === "together" ? leftAt : said;
  return (
    <Ground variant={props.background} photo={props.photo} veil={props.veil} veilOpacity={props.veil_opacity} credit={props.credit}>
      <Place align={props.align} valign={props.valign} gap={64} apart={props.title_valign === "top"}
        head={<SceneTitle title={props.title} kicker={props.kicker} />}>
        <div style={{ display: "flex", gap: 56, alignItems: "stretch", alignSelf: "stretch", textAlign: "left" }}>
          <Enter at={leftAt} from="left" style={{ flex: 1, display: "flex" }}>
            <CompareColumn {...props.left} mood={props.left.mood ?? "bad"} at={leftAt + 10} marks={props.marks ?? true} />
          </Enter>
          <Enter at={rightAt} from="right" style={{ flex: 1, display: "flex" }}>
            <CompareColumn {...props.right} mood={props.right.mood ?? "good"} at={rightAt + 10} marks={props.marks ?? true} />
          </Enter>
        </div>
      </Place>
    </Ground>
  );
}
