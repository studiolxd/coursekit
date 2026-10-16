import React from "react";
import { Counter } from "../atoms/Counter";
import { Enter } from "../atoms/Enter";
import { Heading } from "../atoms/Heading";
import { Text } from "../atoms/Text";

// A figure that counts up, what it measures, and where it comes from (a figure is never shown without its source).

export const StatBlock: React.FC<{ value: number; prefix?: string; suffix?: string; decimals?: number; label: string;
  source: string; at?: number; locale?: string }> = ({ value, prefix, suffix, decimals, label, source, at = 0, locale }) => (
  <div>
    <Enter at={at} scale>
      <Heading size={220} tone="accent" weight={900}>
        <Counter value={value} at={at} prefix={prefix} suffix={suffix} decimals={decimals} locale={locale} />
      </Heading>
    </Enter>
    <Enter at={at + 14}><Heading size={72} style={{ marginTop: 20 }}>{label}</Heading></Enter>
    <Enter at={at + 26}><Text size={36} tone="text-soft" style={{ marginTop: 28 }}>{source}</Text></Enter>
  </div>
);
