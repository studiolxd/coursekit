import React from "react";
import { Counter } from "../atoms/Counter";
import { Enter } from "../atoms/Enter";
import { Heading } from "../atoms/Heading";
import { Text } from "../atoms/Text";

// A figure that counts up, what it measures, and where it comes from (a figure is never shown without its source): one over
// the other (`stacked`) or the figure beside the rest (`side`).

export const StatBlock: React.FC<{ value: number; prefix?: string; suffix?: string; decimals?: number; label: string;
  source: string; at?: number; locale?: string; layout?: "stacked" | "side" }> = (
  { value, prefix, suffix, decimals, label, source, at = 0, locale, layout = "stacked" }) => (
  <div style={layout === "side" ? { display: "flex", alignItems: "center", gap: 72 } : undefined}>
    <Enter at={at} scale>
      <Heading size={220} tone="accent-ink" weight={900} role="stat">
        <Counter value={value} at={at} prefix={prefix} suffix={suffix} decimals={decimals} locale={locale} />
      </Heading>
    </Enter>
    <div style={layout === "side" ? { maxWidth: 900 } : undefined}>
      <Enter at={at + 14}><Heading size={72} style={{ marginTop: layout === "side" ? 0 : 20 }}>{label}</Heading></Enter>
      <Enter at={at + 26}><Text size={36} tone="text-muted" role="caption" style={{ marginTop: 28 }}>{source}</Text></Enter>
    </div>
  </div>
);
