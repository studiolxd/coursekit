import React from "react";
import { Badge } from "../atoms/Badge";
import { Card } from "../atoms/Card";
import { Heading } from "../atoms/Heading";
import { Text } from "../atoms/Text";

// A step of a process: its number (unless `n` is left out), its name and, if it has one, a line that explains it. It fills the height it is given, so
// the steps of a row are as tall as the tallest.

export const StepNode: React.FC<{ n?: number | string; label: string; text?: string; width?: number }> = ({ n, label, text, width }) => (
  <Card padding={44} style={{ width: width ?? "100%", height: "100%", boxSizing: "border-box", display: "flex", flexDirection: "column", gap: 24,
    alignItems: "flex-start" }}>
    {n !== undefined ? <Badge size={80}>{n}</Badge> : null}
    <Heading size={60}>{label}</Heading>
    {text ? <Text size={40} tone="text-muted">{text}</Text> : null}
  </Card>
);
