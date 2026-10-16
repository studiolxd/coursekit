import React from "react";
import { Badge } from "../atoms/Badge";
import { Card } from "../atoms/Card";
import { Heading } from "../atoms/Heading";
import { Text } from "../atoms/Text";

// A step of a process: its number, its name and, if it has one, a line that explains it.

export const StepNode: React.FC<{ n: number | string; label: string; text?: string; width?: number }> = ({ n, label, text, width = 360 }) => (
  <Card padding={44} style={{ width, display: "flex", flexDirection: "column", gap: 24, alignItems: "flex-start" }}>
    <Badge size={80}>{n}</Badge>
    <Heading size={60}>{label}</Heading>
    {text ? <Text size={40} tone="text-soft">{text}</Text> : null}
  </Card>
);
