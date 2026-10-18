import React from "react";
import { Ground } from "../../atoms/Ground";
import { Enter } from "../../atoms/Enter";
import { SceneTitle } from "../../atoms/SceneTitle";
import { Place, type Placing, type Titled } from "../../atoms/Place";
import { Text } from "../../atoms/Text";
import { useColor, useShapes } from "../../theme";
import type { SceneProps } from "../../contract";

// A divider between the parts of a video: the parts in order and the one that starts now (`current`, from 1), marked as the
// brand marks what is active: a bar, a fill behind it, a line under it or nothing (`mark`), a stronger weight, a bigger size,
// both or neither (`emphasis`); the others step back or not (`others`), and those already seen (`done`) like the rest, stepped
// back or with a tick. In a column (`layout: list`) or in a row (`row`, like tabs or the steps of a process).
export type ChapterProps = { kicker?: string; title?: string; parts: string[]; current: number;
  mark?: "bar" | "fill" | "underline" | "none"; emphasis?: "weight" | "size" | "both" | "none";
  fill?: "surface" | "accent" | "surface-highlight"; others?: "muted" | "normal"; done?: "same" | "muted" | "check";
  numbers?: boolean; layout?: "list" | "row" } & Placing & Titled;

const SIZE = 48;  // px of a part
const BIG = 60;  // px of the current part, with emphasis by size

export default function Chapter({ props }: SceneProps<ChapterProps>) {
  const color = useColor();
  const shapes = useShapes();
  const mark = props.mark ?? "bar";
  const emphasis = props.emphasis ?? "both";
  const fill = props.fill ?? "surface-highlight";
  const row = props.layout === "row";
  return (
    <Ground variant={props.background} photo={props.photo} veil={props.veil} veilOpacity={props.veil_opacity} credit={props.credit}>
      <Place align={props.align} valign={props.valign} gap={64} apart={props.title_valign === "top"}
        head={<SceneTitle title={props.title} kicker={props.kicker} />}>
        <div style={{ display: "flex", flexDirection: row ? "row" : "column", flexWrap: row ? "wrap" : undefined, gap: row ? 48 : 28,
          alignItems: row ? "flex-end" : "flex-start", textAlign: "left" }}>
          {props.parts.map((part, i) => {
            const now = i + 1 === props.current;
            const seen = i + 1 < props.current;
            const filled = now && mark === "fill";
            // stepping back: every other part with others muted (the default); with others normal, only the seen ones with done muted
            const quiet = !now && ((props.others ?? "muted") === "muted" || (seen && props.done === "muted"));
            const tone = filled ? (fill === "accent" ? "on-accent" : "text") : now || !quiet ? "headings" : "text-muted";
            const strong = now && (emphasis === "weight" || emphasis === "both");
            const big = now && (emphasis === "size" || emphasis === "both");
            const label = `${props.numbers ?? true ? `${i + 1}. ` : ""}${part}`;
            const bar = now && mark === "bar";
            return (
              <Enter key={i} at={10 + i * 6} from={row ? "up" : "left"} style={{ display: "flex", alignItems: "center", gap: 20,
                ...(bar && !row ? { borderLeft: `10px solid ${color("accent-ink")}`, paddingLeft: 24 } : {}),
                ...(!row && !bar && mark === "bar" ? { paddingLeft: 34 } : {}),
                // the fill reaches out around the text, so the text stays in line with the others
                ...(filled ? { background: color(fill, "surface"), padding: "10px 24px", margin: "-10px -24px", borderRadius: shapes.corner(8) } : {}),
                ...((bar && row) || (now && mark === "underline") ? { borderBottom: `6px solid ${color("accent-ink")}`, paddingBottom: 10 } : {}) }}>
                {seen && props.done === "check" ? <Text size={SIZE} tone="accent-ink" weight={700} role="body">✔</Text> : null}
                <Text size={big ? BIG : SIZE} strong={strong} tone={tone} role="body">{label}</Text>
              </Enter>
            );
          })}
        </div>
      </Place>
    </Ground>
  );
}
