import React from "react";
import { Card } from "../atoms/Card";
import { Heading } from "../atoms/Heading";
import { Stagger } from "../atoms/Stagger";
import { Text } from "../atoms/Text";
import { useColor, useWeight } from "../theme";

// A column of a comparison: a tag if it has one, a title and its items, each with a mark (a tick for the good side, a cross
// for the bad one). Its colour of state (right, wrong, or neutral) goes where `accent` says: nowhere but the marks (`none`), a
// border on top or at the side (`top`, `side`, `width` px), its header filled (`header`) or the whole card filled (`fill`, its
// text in the colour that reads on it). It fills the height of its row, so both columns are as tall as the longer one.

export type Mood = "good" | "bad" | "neutral";
export type Accent = "none" | "top" | "side" | "header" | "fill";

export const CompareColumn: React.FC<{ title: string; items: string[]; tag?: string; mood?: Mood; at?: number;
  times?: (number | null)[]; marks?: boolean; accent?: Accent; width?: number; neutral?: "accent-ink" | "text"; compact?: boolean }> = (
  { title, items, tag, mood = "neutral", at = 0, times, marks = true, accent = "none", width = 10, neutral = "accent-ink", compact = false }) => {
  const color = useColor(true);  // drawn on the card, never on the ground of the scene
  const weightOf = useWeight();
  const fillName = mood === "good" ? "correct" : mood === "bad" ? "wrong" : "surface-highlight";
  const onFill = mood === "good" ? "on-correct" : mood === "bad" ? "on-wrong" : "text";
  const inkName = mood === "good" ? "correct-ink" : mood === "bad" ? "wrong-ink" : neutral;
  const filled = accent === "fill";
  const ink = color(filled ? onFill : inkName, "text");
  const mark = mood === "good" ? "✔" : mood === "bad" ? "✘" : "·";
  const pad = compact ? 36 : 56;  // compact: one column over the other, so both fit in the frame
  const space = compact ? 20 : 40;
  const edge = accent === "top" ? { borderTop: `${width}px solid ${color(inkName)}` }
    : accent === "side" ? { borderLeft: `${width}px solid ${color(inkName)}` } : {};
  const heading = (
    <div>
      {tag ? <Text size={32} weight={700} tone={filled || accent === "header" ? onFill : inkName} role="label" style={{ marginBottom: 12 }}>{tag}</Text> : null}
      <Heading size={64} tone={filled || accent === "header" ? onFill : "headings"}>{title}</Heading>
    </div>
  );
  return (
    <Card padding={pad} tone={filled ? fillName : "surface"} style={{ flex: 1, ...edge, ...(filled ? { borderColor: color(fillName) } : {}) }}>
      {accent === "header" ? (
        <div style={{ background: color(fillName), margin: `-${pad}px -${pad}px ${space}px`, padding: `${compact ? 22 : 32}px ${pad}px` }}>{heading}</div>
      ) : <div style={{ marginBottom: space }}>{heading}</div>}
      <Stagger at={at} times={times} style={{ display: "flex", flexDirection: "column", gap: compact ? 14 : 24 }}>
        {items.map((item, i) => (
          <div key={i} style={{ display: "flex", gap: 20, alignItems: "baseline" }}>
            {marks ? <span style={{ color: ink, fontSize: 50, fontWeight: weightOf(800), flex: "none" }}>{mark}</span> : null}
            <Text size={50} tone={filled ? onFill : "text"}>{item}</Text>
          </div>
        ))}
      </Stagger>
    </Card>
  );
};
