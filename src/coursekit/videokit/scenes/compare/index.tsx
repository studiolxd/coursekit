import React from "react";
import { Ground } from "../../atoms/Ground";
import { Enter } from "../../atoms/Enter";
import { SceneTitle } from "../../atoms/SceneTitle";
import { Place, type Placing, type Titled } from "../../atoms/Place";
import { CompareColumn, type Accent, type Mood } from "../../molecules/CompareColumn";
import { useSceneMotion } from "../../theme";
import { useAt } from "../../timing";
import type { SceneProps } from "../../contract";

// Two sides compared: each column enters when the narration names it, and its items when they are said.
export type Side = { title: string; items: string[]; tag?: string; say?: string; mood?: Mood };
// `accent`, `width` and `neutral`: where each column wears its colour of state (CompareColumn); `layout`: side by side or one
// over the other, for long texts.
export type CompareProps = { kicker?: string; title?: string; left: Side; right: Side; marks?: boolean; accent?: Accent; width?: number;
  neutral?: "accent-ink" | "text"; layout?: "columns" | "rows" } & Placing & Titled;

export default function Compare({ props }: SceneProps<CompareProps>) {
  const leftAt = useAt(props.left.say, 8);
  const said = useAt(props.right.say, leftAt + 30);
  const rightAt = useSceneMotion().reveal === "together" ? leftAt : said;
  const rows = props.layout === "rows";
  const look = { marks: props.marks ?? true, accent: props.accent ?? "none", width: props.width, neutral: props.neutral, compact: rows };
  return (
    <Ground variant={props.background} photo={props.photo} veil={props.veil} veilOpacity={props.veil_opacity} credit={props.credit}>
      <Place align={props.align} valign={props.valign} gap={64} apart={props.title_valign === "top"}
        head={<SceneTitle title={props.title} kicker={props.kicker} />}>
        <div style={{ display: "flex", flexDirection: rows ? "column" : "row", gap: rows ? 32 : 56, alignItems: "stretch", alignSelf: "stretch",
          textAlign: "left" }}>
          <Enter at={leftAt} from={rows ? "up" : "left"} style={{ flex: 1, display: "flex" }}>
            <CompareColumn {...props.left} mood={props.left.mood ?? "bad"} at={leftAt + 10} {...look} />
          </Enter>
          <Enter at={rightAt} from={rows ? "up" : "right"} style={{ flex: 1, display: "flex" }}>
            <CompareColumn {...props.right} mood={props.right.mood ?? "good"} at={rightAt + 10} {...look} />
          </Enter>
        </div>
      </Place>
    </Ground>
  );
}
