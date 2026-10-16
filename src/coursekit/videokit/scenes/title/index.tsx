import React from "react";
import { AbsoluteFill } from "remotion";
import { Background } from "../../atoms/Background";
import { TitleBlock } from "../../molecules/TitleBlock";
import type { SceneProps } from "../../contract";

// The opening of a video or of a part of it: a kicker and a title, the title underlined where the narration stresses it.
export type TitleProps = { kicker?: string; title: string; stress?: string };

export default function Title({ props }: SceneProps<TitleProps>) {
  return (
    <AbsoluteFill>
      <Background variant="band" />
      <AbsoluteFill style={{ justifyContent: "center", padding: "0 160px" }}>
        <TitleBlock kicker={props.kicker} title={props.title} stress={props.stress} size={104} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
}
