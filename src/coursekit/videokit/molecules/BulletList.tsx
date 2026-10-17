import React from "react";
import { Text } from "../atoms/Text";
import { Stagger } from "../atoms/Stagger";
import { useColor, useShapes } from "../theme";
import { useSayTimes } from "../timing";

// A list whose items enter when the narration names them (`say`: the words of each item that are said; without them, one
// after another from `at`), each with a mark in the accent of the theme (the one that reads on the background).

export type Bullet = { text: string; say?: string };

export const BulletList: React.FC<{ items: Bullet[]; at?: number; size?: number }> = ({ items, at = 0, size = 54 }) => {
  const color = useColor();
  const shapes = useShapes();
  const times = useSayTimes(items.map((item) => item.say));
  return (
    <Stagger at={at} times={times} style={{ display: "flex", flexDirection: "column", gap: 26 }}>
      {items.map((item, i) => (
        <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 22 }}>
          <div style={{ width: 22, height: 22, borderRadius: shapes.corner(5), background: color("accent-ink"), marginTop: size * 0.45, flex: "none" }} />
          <Text size={size}>{item.text}</Text>
        </div>
      ))}
    </Stagger>
  );
};
