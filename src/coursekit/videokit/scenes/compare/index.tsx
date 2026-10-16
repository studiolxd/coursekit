import React from "react";
import { AbsoluteFill } from "remotion";
import { Background } from "../../atoms/Background";
import { Enter } from "../../atoms/Enter";
import { Heading } from "../../atoms/Heading";
import { CompareColumn } from "../../molecules/CompareColumn";
import { useAt } from "../../timing";
import type { SceneProps } from "../../contract";

// Two sides compared: each column enters when the narration names it, and its items when they are said.
export type Side = { title: string; items: string[]; say?: string; mood?: "good" | "bad" | "neutral" };
export type CompareProps = { title?: string; left: Side; right: Side };

export default function Compare({ props }: SceneProps<CompareProps>) {
  const leftAt = useAt(props.left.say, 8);
  const rightAt = useAt(props.right.say, leftAt + 30);
  return (
    <AbsoluteFill>
      <Background />
      <AbsoluteFill style={{ padding: "0 140px", gap: 64, justifyContent: "center" }}>
        {props.title ? <Enter><Heading size={80}>{props.title}</Heading></Enter> : null}
        <div style={{ display: "flex", gap: 56, alignItems: "flex-start" }}>
          <Enter at={leftAt} from="left" style={{ flex: 1, display: "flex" }}>
            <CompareColumn {...props.left} mood={props.left.mood ?? "bad"} at={leftAt + 10} />
          </Enter>
          <Enter at={rightAt} from="right" style={{ flex: 1, display: "flex" }}>
            <CompareColumn {...props.right} mood={props.right.mood ?? "good"} at={rightAt + 10} />
          </Enter>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}
