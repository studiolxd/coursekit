import React from "react";
import { AbsoluteFill } from "remotion";
import { Background } from "../../atoms/Background";
import { Enter } from "../../atoms/Enter";
import { Heading } from "../../atoms/Heading";
import { Text } from "../../atoms/Text";
import { Underline } from "../../atoms/Underline";
import { useColor } from "../../theme";
import { useAt } from "../../timing";
import type { SceneProps } from "../../contract";

// A quote and who says it; `stress`, a word of the quote, is highlighted when the narration says it.
export type QuoteProps = { quote: string; author: string; role?: string; stress?: string };

export default function Quote({ props }: SceneProps<QuoteProps>) {
  const color = useColor();
  const at = useAt(props.stress, 30);
  const i = props.stress ? props.quote.toLowerCase().indexOf(props.stress.toLowerCase()) : -1;
  const quote = i >= 0 ? <>{props.quote.slice(0, i)}<Underline at={at} highlight>{props.quote.slice(i, i + props.stress!.length)}</Underline>{props.quote.slice(i + props.stress!.length)}</> : props.quote;
  return (
    <AbsoluteFill>
      <Background />
      <AbsoluteFill style={{ justifyContent: "center", padding: "0 220px", gap: 48 }}>
        <Enter scale><div style={{ fontSize: 220, lineHeight: 0.6, color: color("accent"), fontWeight: 900 }}>“</div></Enter>
        <Enter at={6}><Heading size={84} weight={700}>{quote}</Heading></Enter>
        <Enter at={18}>
          <Text size={44} weight={700}>{props.author}</Text>
          {props.role ? <Text size={36} tone="text-soft">{props.role}</Text> : null}
        </Enter>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}
