import React from "react";
import { Ground } from "../../atoms/Ground";
import { ITEMS, Place, type Placing } from "../../atoms/Place";
import { Enter } from "../../atoms/Enter";
import { Heading } from "../../atoms/Heading";
import { Text } from "../../atoms/Text";
import { MediaSlot } from "../../atoms/MediaSlot";
import { Stressed } from "../../atoms/Stressed";
import { useColor, useWeight } from "../../theme";
import type { SceneProps } from "../../contract";

// A quote and who says it; `stress`, a word of the quote, is underlined when the narration says it, as in a key phrase.
export type QuoteProps = { quote: string; author: string; role?: string; stress?: string; mark?: "quote" | "bar" | "none";
  portrait?: string } & Placing;

export default function Quote({ props }: SceneProps<QuoteProps>) {
  const color = useColor();
  const weightOf = useWeight();
  const mark = props.mark ?? "quote";
  const quote = <Stressed text={props.quote} stress={props.stress} after={30} />;
  return (
    <Ground variant={props.background} photo={props.photo} veil={props.veil} veilOpacity={props.veil_opacity} credit={props.credit}>
      <Place align={props.align} valign={props.valign}>
        <div style={{ display: "flex", alignItems: "center", gap: 96 }}>
          {props.portrait ? (
            <Enter from="left" style={{ width: 420, height: 420, flex: "none" }}><MediaSlot src={props.portrait} /></Enter>
          ) : null}
          <div style={{ display: "flex", flexDirection: "column", gap: 48, alignItems: ITEMS[props.align ?? "left"], textAlign: props.align ?? "left",
            ...(mark === "bar" ? { borderLeft: `10px solid ${color("accent-ink")}`, paddingLeft: 56 } : {}) }}>
            {mark === "quote" ? (
              <Enter scale><div style={{ fontSize: 220, lineHeight: 0.6, color: color("accent-ink"), fontWeight: weightOf(900) }}>“</div></Enter>
            ) : null}
            <Enter at={6}><Heading size={84} weight={700} role="quote">{quote}</Heading></Enter>
            <Enter at={18}>
              <Text size={44} weight={700} role="label">{props.author}</Text>
              {props.role ? <Text size={36} tone="text-muted" role="caption">{props.role}</Text> : null}
            </Enter>
          </div>
        </div>
      </Place>
    </Ground>
  );
}
