import React from "react";
import { Card } from "../atoms/Card";
import { Heading } from "../atoms/Heading";
import { Stagger } from "../atoms/Stagger";
import { Text } from "../atoms/Text";
import { useColor, useWeight } from "../theme";

// A column of a comparison: a title and its items, each with a mark (a tick for the good side, a cross for the bad one). It fills
// the height of its row, so both columns are as tall as the longer one.

export const CompareColumn: React.FC<{ title: string; items: string[]; mood?: "good" | "bad" | "neutral"; at?: number;
  times?: (number | null)[]; marks?: boolean }> = ({ title, items, mood = "neutral", at = 0, times, marks = true }) => {
  const color = useColor(true);  // the marks are drawn on the card, never on the ground of the scene
  const weightOf = useWeight();
  const tone = mood === "good" ? color("correct-ink", "accent") : mood === "bad" ? color("wrong-ink", "text-muted") : color("accent-ink");
  const mark = mood === "good" ? "✔" : mood === "bad" ? "✘" : "·";
  return (
    <Card padding={56} style={{ flex: 1, borderTop: `10px solid ${tone}` }}>
      <Heading size={64} style={{ marginBottom: 40 }}>{title}</Heading>
      <Stagger at={at} times={times} style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        {items.map((item, i) => (
          <div key={i} style={{ display: "flex", gap: 20, alignItems: "baseline" }}>
            {marks ? <span style={{ color: tone, fontSize: 50, fontWeight: weightOf(800), flex: "none" }}>{mark}</span> : null}
            <Text size={50}>{item}</Text>
          </div>
        ))}
      </Stagger>
    </Card>
  );
};
