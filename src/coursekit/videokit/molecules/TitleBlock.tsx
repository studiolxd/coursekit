import React from "react";
import { Heading } from "../atoms/Heading";
import { Text } from "../atoms/Text";
import { Enter } from "../atoms/Enter";
import { Underline } from "../atoms/Underline";
import { useAt } from "../timing";

// A kicker over a title; the title is underlined when the narration says `stress` (a word of the title).

export const TitleBlock: React.FC<{ kicker?: string; title: string; stress?: string; size?: number; at?: number }> = (
  { kicker, title, stress, size = 84, at = 0 }) => {
  const underlineAt = useAt(stress, at + 20);
  const parts = stress && title.toLowerCase().includes(stress.toLowerCase())
    ? (() => { const i = title.toLowerCase().indexOf(stress.toLowerCase()); return [title.slice(0, i), title.slice(i, i + stress.length), title.slice(i + stress.length)]; })()
    : null;
  return (
    <div>
      {kicker ? <Enter at={at}><Text size={36} tone="accent-strong" weight={800} style={{ textTransform: "uppercase", letterSpacing: 2, marginBottom: 18 }}>{kicker}</Text></Enter> : null}
      <Enter at={at + 6}>
        <Heading size={size}>{parts ? <>{parts[0]}<Underline at={underlineAt}>{parts[1]}</Underline>{parts[2]}</> : title}</Heading>
      </Enter>
    </div>
  );
};
