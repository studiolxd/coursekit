import React from "react";
import { Card } from "../atoms/Card";
import { Heading } from "../atoms/Heading";
import { Stagger } from "../atoms/Stagger";
import { Text } from "../atoms/Text";
import { useColor, useWeight } from "../theme";

// A column of a comparison: a title and its items, each with a mark (a tick for the good side, a cross for the bad one).

export const CompareColumn: React.FC<{ title: string; items: string[]; mood?: "good" | "bad" | "neutral"; at?: number;
  times?: (number | null)[] }> = ({ title, items, mood = "neutral", at = 0, times }) => {
  const color = useColor();
  const weightOf = useWeight();
  const tone = mood === "good" ? color("correct", "accent") : mood === "bad" ? color("wrong", "text-soft") : color("accent");
  const mark = mood === "good" ? "✔" : mood === "bad" ? "✘" : "·";
  return (
    <Card padding={56} style={{ flex: 1, borderTop: `10px solid ${tone}` }}>
      <Heading size={64} style={{ marginBottom: 40 }}>{title}</Heading>
      <Stagger at={at} times={times} style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        {items.map((item, i) => (
          <div key={i} style={{ display: "flex", gap: 20, alignItems: "baseline" }}>
            <span style={{ color: tone, fontSize: 50, fontWeight: weightOf(800), flex: "none" }}>{mark}</span>
            <Text size={50}>{item}</Text>
          </div>
        ))}
      </Stagger>
    </Card>
  );
};
