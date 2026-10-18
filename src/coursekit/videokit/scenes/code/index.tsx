import React from "react";
import { Ground } from "../../atoms/Ground";
import { Enter } from "../../atoms/Enter";
import { SceneTitle } from "../../atoms/SceneTitle";
import { Place, type Placing, type Titled } from "../../atoms/Place";
import { Card } from "../../atoms/Card";
import { Text } from "../../atoms/Text";
import { interpolate, useCurrentFrame } from "remotion";
import { useColor, useTheme } from "../../theme";
import { useSayTimes } from "../../timing";
import type { SceneProps } from "../../contract";

// A piece of code on a panel; the lines of each `highlight` (from, to: numbers of line from 1) are marked when the narration
// says its words (`say`), one group after another: with a fill of a colour of the theme whole behind them (`mark: fill`, the
// text taking the colour that reads on it), a bar at their side (`bar`), both or neither, in the strong weight or not
// (`emphasis`); the other lines can step back while a group is marked (`others: dim`), and the groups explained can stay
// marked (`keep`). The font is the brand's for the `code` role, else a monospaced one.
export type Lines = { from: number; to?: number; say?: string };
export type CodeProps = { kicker?: string; title?: string; code: string; highlight?: Lines[];
  mark?: "fill" | "bar" | "both" | "none"; fill?: "surface-highlight" | "accent" | "surface"; emphasis?: "weight" | "none";
  others?: "normal" | "dim"; keep?: boolean; numbers?: boolean } & Placing & Titled;

const MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
const DIM = 0.4;  // the opacity of the lines that step back
const PAD = 40;  // px of the panel around the code

export default function Code({ props }: SceneProps<CodeProps>) {
  const frame = useCurrentFrame();
  const color = useColor();
  const { motion } = useTheme();
  const marks = props.highlight ?? [];
  const said = useSayTimes(marks.map((m) => m.say));
  const lines = props.code.replace(/\n$/, "").split("\n");
  const mark = props.mark ?? "fill";
  const fill = props.fill ?? "surface-highlight";
  const starts = marks.map((_, i) => said[i] ?? 20 + i * 40);
  const lit = (n: number) => marks.reduce((best, m, i) => {
    const next = i + 1 < marks.length ? starts[i + 1] : Infinity;
    const on = n >= m.from && n <= (m.to ?? m.from) && frame >= starts[i] && (props.keep || frame < next);
    return on ? Math.max(best, interpolate(frame - starts[i], [0, Math.max(1, motion.enter)], [0, 1], { extrapolateRight: "clamp" })) : best;
  }, 0);
  const marking = marks.length > 0 && frame >= starts[0];  // a group is marked: the others may step back
  return (
    <Ground variant={props.background} photo={props.photo} veil={props.veil} veilOpacity={props.veil_opacity} credit={props.credit}>
      <Place align={props.align} valign={props.valign} gap={48} apart={props.title_valign === "top"}
        head={<SceneTitle title={props.title} kicker={props.kicker} />}>
        <Enter at={6} style={{ alignSelf: "stretch", textAlign: "left" }}>
          <Card padding={PAD}>
            {lines.map((line, i) => {
              const k = lit(i + 1);
              const tone = k >= 0.5 && (mark === "fill" || mark === "both") && fill === "accent" ? "on-accent" : "text";
              const faded = props.others === "dim" && marking && k === 0;
              return (
                <div key={i} style={{ display: "flex", gap: 28, position: "relative", opacity: faded ? DIM : 1 }}>
                  {mark === "fill" || mark === "both" ? (
                    <div style={{ position: "absolute", inset: `0 -${PAD}px`, background: color(fill, "surface"), opacity: k }} />
                  ) : null}
                  {mark === "bar" || mark === "both" ? (
                    <div style={{ position: "absolute", left: -PAD, top: 0, bottom: 0, width: 8, background: color("accent-ink"), opacity: k }} />
                  ) : null}
                  {props.numbers ?? true ? (
                    <Text size={34} tone="text-muted" role="code" family={MONO} style={{ width: 48, textAlign: "right", position: "relative" }}>{i + 1}</Text>
                  ) : null}
                  <Text size={34} tone={tone} role="code" family={MONO} strong={props.emphasis === "weight" && k >= 0.5}
                    style={{ whiteSpace: "pre", position: "relative" }}>{line || " "}</Text>
                </div>
              );
            })}
          </Card>
        </Enter>
      </Place>
    </Ground>
  );
}
