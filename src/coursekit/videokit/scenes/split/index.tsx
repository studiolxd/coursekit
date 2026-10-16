import React from "react";
import { AbsoluteFill } from "remotion";
import { Background } from "../../atoms/Background";
import { Enter } from "../../atoms/Enter";
import { MediaSlot } from "../../atoms/MediaSlot";
import { BulletList, type Bullet } from "../../molecules/BulletList";
import { TitleBlock } from "../../molecules/TitleBlock";
import type { SceneProps } from "../../contract";

// Text and a medium side by side: a title, points that enter when the narration names them, and an image or a video.
export type SplitProps = { kicker?: string; title: string; points?: Bullet[]; media?: string; side?: "left" | "right" };

export default function Split({ props }: SceneProps<SplitProps>) {
  const media = props.media ? (
    <Enter at={10} from={props.side === "left" ? "right" : "left"} style={{ flex: 1, height: 680 }}>
      <MediaSlot src={props.media} />
    </Enter>
  ) : null;
  const text = (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 56 }}>
      <TitleBlock kicker={props.kicker} title={props.title} size={72} />
      {props.points?.length ? <BulletList items={props.points} at={24} /> : null}
    </div>
  );
  return (
    <AbsoluteFill>
      <Background />
      <AbsoluteFill style={{ flexDirection: "row", alignItems: "center", gap: 96, padding: "0 140px" }}>
        {props.side === "left" ? <>{media}{text}</> : <>{text}{media}</>}
      </AbsoluteFill>
    </AbsoluteFill>
  );
}
