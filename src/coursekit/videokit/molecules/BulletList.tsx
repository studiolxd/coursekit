import React from "react";
import { Text } from "../atoms/Text";
import { Stagger } from "../atoms/Stagger";
import { useColor } from "../theme";
import { useSceneTime, whenSaid } from "../timing";
import { useVideoConfig } from "remotion";

// A list whose items enter when the narration names them (`say`: the words of each item that are said; without them, one
// after another from `at`), each with a mark in the accent of the theme.

export type Bullet = { text: string; say?: string };

export const BulletList: React.FC<{ items: Bullet[]; at?: number; size?: number }> = ({ items, at = 0, size = 40 }) => {
  const color = useColor();
  const { words } = useSceneTime();
  const { fps } = useVideoConfig();
  let after = -1;
  const times = items.map((item) => {
    const s = item.say ? whenSaid(words, item.say, after) : null;
    if (s != null) after = s;
    return s == null ? null : Math.round(s * fps);
  });
  return (
    <Stagger at={at} times={times} style={{ display: "flex", flexDirection: "column", gap: 26 }}>
      {items.map((item, i) => (
        <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 22 }}>
          <div style={{ width: 18, height: 18, borderRadius: 4, background: color("accent"), marginTop: size * 0.45, flex: "none" }} />
          <Text size={size}>{item.text}</Text>
        </div>
      ))}
    </Stagger>
  );
};
