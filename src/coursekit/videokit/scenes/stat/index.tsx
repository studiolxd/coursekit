import React from "react";
import { AbsoluteFill } from "remotion";
import { Background } from "../../atoms/Background";
import { StatBlock } from "../../molecules/StatBlock";
import { useAt } from "../../timing";
import type { SceneProps } from "../../contract";

// A figure with what it measures and its source; it counts up when the narration says it (`say`).
export type StatProps = { value: number; prefix?: string; suffix?: string; decimals?: number; label: string; source: string;
  say?: string; locale?: string };

export default function Stat({ props }: SceneProps<StatProps>) {
  const at = useAt(props.say, 6);
  return (
    <AbsoluteFill>
      <Background />
      <AbsoluteFill style={{ justifyContent: "center", padding: "0 160px" }}>
        <StatBlock {...props} at={at} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
}
