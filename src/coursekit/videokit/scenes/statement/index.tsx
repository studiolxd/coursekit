import React from "react";
import { Ground } from "../../atoms/Ground";
import { Kicker } from "../../atoms/Kicker";
import { SceneTitle } from "../../atoms/SceneTitle";
import { Place, type Placing, type Titled } from "../../atoms/Place";
import { Enter } from "../../atoms/Enter";
import { Heading } from "../../atoms/Heading";
import { Stressed } from "../../atoms/Stressed";
import type { SceneProps } from "../../contract";

// A phrase to keep, large (under a title if it has one); `stress`, a word of the phrase, is underlined when the narration says it.
export type StatementProps = { title?: string; kicker?: string; text: string; stress?: string } & Placing & Titled;

export default function Statement({ props }: SceneProps<StatementProps>) {
  const phrase = <Stressed text={props.text} stress={props.stress} />;
  return (
    <Ground variant={props.background} photo={props.photo} veil={props.veil} veilOpacity={props.veil_opacity} credit={props.credit}>
      <Place align={props.align} valign={props.valign} gap={32} apart={props.title_valign === "top"}
        head={props.title ? <div style={{ marginBottom: 32 }}><SceneTitle title={props.title} kicker={props.kicker} /></div> : null}>
        {props.kicker && !props.title ? <Kicker>{props.kicker}</Kicker> : null}
        <Enter at={6}><Heading size={props.text.length > 70 ? 76 : 92} tone="headings" role="statement" style={{ maxWidth: 1400 }}>
          {phrase}</Heading></Enter>
      </Place>
    </Ground>
  );
}
