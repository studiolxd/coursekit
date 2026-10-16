import React from "react";
import { AbsoluteFill } from "remotion";
import { Background } from "../../atoms/Background";
import { Badge } from "../../atoms/Badge";
import { Enter } from "../../atoms/Enter";
import { Heading } from "../../atoms/Heading";
import { Text } from "../../atoms/Text";
import { useSayTimes } from "../../timing";
import type { SceneProps } from "../../contract";

// A numbered list (steps, rules, keys): each item enters when the narration says it.
export type ListItem = { text: string; say?: string };
export type ListProps = { title: string; items: ListItem[] };

export default function List({ props }: SceneProps<ListProps>) {
  const times = useSayTimes(props.items.map((i) => i.say));
  return (
    <AbsoluteFill>
      <Background variant="shape" />
      <AbsoluteFill style={{ padding: "0 180px", gap: 72, justifyContent: "center" }}>
        <Enter><Heading size={88}>{props.title}</Heading></Enter>
        <div style={{ display: "flex", flexDirection: "column", gap: 44 }}>
          {props.items.map((item, i) => (
            <Enter key={i} at={times[i] ?? 20 + i * 14} from="left" style={{ display: "flex", gap: 32, alignItems: "center" }}>
              <Badge size={88}>{i + 1}</Badge>
              <Text size={60} weight={600}>{item.text}</Text>
            </Enter>
          ))}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}
