import React from "react";
import { Enter } from "./Enter";
import { Text } from "./Text";

// The kicker of a scene, a short label over its title or its phrase: one size for every scene (the `kicker` role of the text,
// config/video.yaml › text, changes it for all of them), in the accent that reads on the background unless `ink` says otherwise.

export const KICKER = 36;

export const Kicker: React.FC<{ children: React.ReactNode; at?: number; ink?: string; style?: React.CSSProperties }> = (
  { children, at = 0, ink, style }) => (
  <Enter at={at}>
    <Text size={KICKER} tone={ink ?? "accent-ink"} weight={800} role="kicker" style={{ textTransform: "uppercase", letterSpacing: 2, ...style }}>
      {children}</Text>
  </Enter>
);
