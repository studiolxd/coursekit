import React from "react";
import { AbsoluteFill } from "remotion";
import { Background } from "../../atoms/Background";
import { Card } from "../../atoms/Card";
import { Enter } from "../../atoms/Enter";
import { MediaSlot } from "../../atoms/MediaSlot";
import { Text } from "../../atoms/Text";
import { TitleBlock } from "../../molecules/TitleBlock";
import type { SceneProps } from "../../contract";

// The cover of a video, of a course, of a unit or of a part: a kicker, a title and a line under it, on the background of the
// style, plain, the surface colour, the accent or a photo. With a photo the text goes beside it (`side`), in a panel over it
// (`panel`) or straight over it (`over`, with `ink: light` on a dark photo). `align` and `valign` place the text; at the
// bottom it keeps clear of the captions.
export type TitleProps = {
  kicker?: string; title: string; text?: string;
  background?: "plain" | "surface" | "accent" | "photo"; photo?: string; layout?: "side" | "panel" | "over";
  align?: "left" | "center" | "right"; valign?: "top" | "middle" | "bottom"; ink?: "dark" | "light";
};

const JUSTIFY = { top: "flex-start", middle: "center", bottom: "flex-end" } as const;
const ITEMS = { left: "flex-start", center: "center", right: "flex-end" } as const;
const CAPTIONS = 200; // px kept free at the bottom of the frame, where the captions go

export default function Title({ props }: SceneProps<TitleProps>) {
  const align = props.align ?? "left";
  const valign = props.valign ?? "middle";
  const photo = props.background === "photo" && props.photo ? props.photo : undefined;
  const layout = photo ? props.layout ?? "side" : undefined;
  const ink = props.background === "accent" ? "on-accent" : layout === "over" && props.ink === "light" ? "background" : undefined;
  const size = layout === "side" ? (props.title.length > 40 ? 64 : 76) : props.title.length > 40 ? 84 : 104;  // half the frame: smaller
  const block = (
    <div style={{ textAlign: align, maxWidth: layout === "side" ? undefined : 1400 }}>
      <TitleBlock kicker={props.kicker} title={props.title} size={size} ink={ink} role="display" />
      {props.text ? (
        <Enter at={14}><Text size={44} tone={ink ?? "text-muted"} role="subheading" style={{ marginTop: 36 }}>{props.text}</Text></Enter>
      ) : null}
    </div>
  );
  const place = (children: React.ReactNode, padding: string) => (
    <AbsoluteFill style={{ flexDirection: "column", justifyContent: JUSTIFY[valign], alignItems: ITEMS[align], padding }}>
      {children}
    </AbsoluteFill>
  );
  const edges = `120px 160px ${valign === "bottom" ? CAPTIONS : 120}px`;

  if (photo && layout === "side") {  // the photo on one half, the text on the other: `align: right` puts the text on the right
    const right = align === "right";
    const media = <div style={{ flex: 1, height: "100%" }}><MediaSlot src={photo} style={{ borderRadius: 0 }} /></div>;
    const text = (
      <div style={{ flex: 1, height: "100%", position: "relative" }}>
        {place(block, `120px 120px ${valign === "bottom" ? CAPTIONS : 120}px`)}
      </div>
    );
    return (
      <AbsoluteFill>
        <Background variant="plain" />
        <AbsoluteFill style={{ flexDirection: "row" }}>{right ? <>{media}{text}</> : <>{text}{media}</>}</AbsoluteFill>
      </AbsoluteFill>
    );
  }
  if (photo) {  // the photo whole, the text in a panel over it or straight over it
    return (
      <AbsoluteFill>
        <AbsoluteFill><MediaSlot src={photo} style={{ borderRadius: 0 }} /></AbsoluteFill>
        {place(layout === "panel" ? <Enter><Card tone="surface" padding={72} style={{ maxWidth: 1200 }}>{block}</Card></Enter> : block,
          edges)}
      </AbsoluteFill>
    );
  }
  const background = props.background && props.background !== "photo" ? props.background : undefined;
  return (
    <AbsoluteFill>
      <Background variant={background} />
      {place(block, edges)}
    </AbsoluteFill>
  );
}
