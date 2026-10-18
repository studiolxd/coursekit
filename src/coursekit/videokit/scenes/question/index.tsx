import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { Ground } from "../../atoms/Ground";
import { Enter } from "../../atoms/Enter";
import { Heading } from "../../atoms/Heading";
import { Kicker } from "../../atoms/Kicker";
import { Text } from "../../atoms/Text";
import { Place, type Placing } from "../../atoms/Place";
import { Track } from "../../atoms/Track";
import { useTheme } from "../../theme";
import { useAt } from "../../timing";
import type { SceneProps } from "../../contract";

// A question to the learner and a pause to think it, shown as a bar that fills; then the answer, if it has one, when the
// narration says it (`answer_say`) or when the pause ends. Give the scene the time of the pause (`hold` of the scene).
export type QuestionProps = { kicker?: string; question: string; say?: string; answer?: string; answer_say?: string; pause?: number } & Placing;

export default function Question({ props }: SceneProps<QuestionProps>) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { style } = useTheme();  // the bar: config/video.yaml › progress, across the whole width of the content
  const asked = useAt(props.say, 6);
  const pause = Math.max(0, props.pause ?? 3) * fps;
  const answered = useAt(props.answer_say, asked + 12 + pause);
  const filled = interpolate(frame, [asked + 12, asked + 12 + Math.max(1, pause)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <Ground variant={props.background} photo={props.photo} veil={props.veil} veilOpacity={props.veil_opacity} credit={props.credit}>
      <Place align={props.align} valign={props.valign} gap={40}>
        {props.kicker ? <Kicker>{props.kicker}</Kicker> : null}
        <Enter at={asked}><Heading size={props.question.length > 70 ? 76 : 92} role="statement" style={{ maxWidth: 1400 }}>{props.question}</Heading></Enter>
        {pause > 0 ? (
          <div style={{ alignSelf: "stretch" }}><Track done={filled} width="100%" height={style?.progress?.height ?? 10} /></div>
        ) : null}
        {props.answer ? (
          <Enter at={answered}><Text size={52} weight={600} role="subheading" style={{ maxWidth: 1400 }}>{props.answer}</Text></Enter>
        ) : null}
      </Place>
    </Ground>
  );
}
