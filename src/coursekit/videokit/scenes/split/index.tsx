import React from "react";
import { AbsoluteFill } from "remotion";
import { Ground } from "../../atoms/Ground";
import { SCENE_TITLE } from "../../atoms/SceneTitle";
import { ITEMS, JUSTIFY, SIDE, edges, type Placing, type Titled } from "../../atoms/Place";
import { Enter } from "../../atoms/Enter";
import { MediaSlot } from "../../atoms/MediaSlot";
import { BulletList, type Bullet, type Marker } from "../../molecules/BulletList";
import { TitleBlock } from "../../molecules/TitleBlock";
import type { SceneProps } from "../../contract";

// Text and a medium side by side: a title, points that enter when the narration names them, and an image or a video, cropped to
// its box (`fit: cover`) or whole (`contain`, for a screenshot), on half the width or more or less of it (`ratio`).
export type SplitProps = { kicker?: string; title: string; points?: Bullet[]; media?: string; side?: "left" | "right"; marker?: Marker;
  fit?: "cover" | "contain"; ratio?: "half" | "wide-media" | "wide-text" } & Placing & Titled;

export default function Split({ props }: SceneProps<SplitProps>) {
  const align = props.align ?? "left";
  const valign = props.valign ?? "middle";
  const apart = props.title_valign === "top";  // the title at the top of its column, the points and the medium where valign says
  const grow = { "wide-media": { media: 3, text: 2 }, "wide-text": { media: 2, text: 3 }, half: { media: 1, text: 1 } }[props.ratio ?? "half"];
  const media = props.media ? (
    <Enter at={10} from={props.side === "left" ? "right" : "left"} style={{ flex: grow.media, minWidth: 0, height: 720, alignSelf: JUSTIFY[valign] }}>
      <MediaSlot src={props.media} fit={props.fit ?? "cover"} />
    </Enter>
  ) : null;
  const text = (
    <div style={{ flex: grow.text, minWidth: 0, alignSelf: apart ? "stretch" : JUSTIFY[valign], display: "flex", flexDirection: "column", gap: 56, alignItems: ITEMS[align], textAlign: align }}>
      <TitleBlock kicker={props.kicker} title={props.title} size={SCENE_TITLE} />
      {props.points?.length ? (
        apart ? (
          <div style={{ flex: 1, alignSelf: "stretch", display: "flex", flexDirection: "column", justifyContent: JUSTIFY[valign],
            alignItems: ITEMS[align] }}><BulletList items={props.points} at={24} marker={props.marker} /></div>
        ) : <BulletList items={props.points} at={24} marker={props.marker} />
      ) : null}
    </div>
  );
  return (
    <Ground variant={props.background} photo={props.photo} veil={props.veil} veilOpacity={props.veil_opacity} credit={props.credit}>
      <AbsoluteFill style={{ flexDirection: "row", alignItems: JUSTIFY[valign], gap: 96, padding: edges(valign, SIDE) }}>
        {props.side === "left" ? <>{media}{text}</> : <>{text}{media}</>}
      </AbsoluteFill>
    </Ground>
  );
}
