import React from "react";
import { Ground } from "../../atoms/Ground";
import { Enter } from "../../atoms/Enter";
import { SceneTitle } from "../../atoms/SceneTitle";
import { Place, type Placing, type Titled } from "../../atoms/Place";
import { Text } from "../../atoms/Text";
import { useColor } from "../../theme";
import type { SceneProps } from "../../contract";

// A divider between the parts of a video: the parts in order, the one that starts now (`current`, from 1) stands out and the
// others step back; with `title`, the name of the video or of the section over them.
export type ChapterProps = { kicker?: string; title?: string; parts: string[]; current: number } & Placing & Titled;

export default function Chapter({ props }: SceneProps<ChapterProps>) {
  const color = useColor();
  return (
    <Ground variant={props.background} photo={props.photo} veil={props.veil} veilOpacity={props.veil_opacity} credit={props.credit}>
      <Place align={props.align} valign={props.valign} gap={64} apart={props.title_valign === "top"}
        head={<SceneTitle title={props.title} kicker={props.kicker} />}>
        <div style={{ display: "flex", flexDirection: "column", gap: 28, textAlign: "left" }}>
          {props.parts.map((part, i) => {
            const now = i + 1 === props.current;
            return (
              <Enter key={i} at={10 + i * 6} from="left" style={{ display: "flex", alignItems: "center", gap: 28 }}>
                <div style={{ width: 10, alignSelf: "stretch", background: now ? color("accent-ink") : "transparent" }} />
                <Text size={now ? 60 : 48} weight={now ? 700 : 400} tone={now ? "headings" : "text-muted"} role={now ? "subheading" : "body"}>
                  {`${i + 1}. ${part}`}</Text>
              </Enter>
            );
          })}
        </div>
      </Place>
    </Ground>
  );
}
