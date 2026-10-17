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

// A piece of code on a panel; the lines of each `highlight` (from, to: numbers of line from 1) light up when the narration
// says its words (`say`), one after another. The font is the brand's for the `code` role, else a monospaced one.
export type Lines = { from: number; to?: number; say?: string };
export type CodeProps = { kicker?: string; title?: string; code: string; highlight?: Lines[] } & Placing & Titled;

const MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";

export default function Code({ props }: SceneProps<CodeProps>) {
  const frame = useCurrentFrame();
  const color = useColor();
  const { motion } = useTheme();
  const marks = props.highlight ?? [];
  const said = useSayTimes(marks.map((m) => m.say));
  const lines = props.code.replace(/\n$/, "").split("\n");
  const lit = (n: number) => marks.reduce((best, m, i) => {
    const at = said[i] ?? 20 + i * 40;
    const next = marks[i + 1] ? said[i + 1] ?? 20 + (i + 1) * 40 : Infinity;
    const on = n >= m.from && n <= (m.to ?? m.from) && frame >= at && frame < next;
    return on ? Math.max(best, interpolate(frame - at, [0, Math.max(1, motion.enter)], [0, 1], { extrapolateRight: "clamp" })) : best;
  }, 0);
  return (
    <Ground variant={props.background} photo={props.photo} veil={props.veil} veilOpacity={props.veil_opacity} credit={props.credit}>
      <Place align={props.align} valign={props.valign} gap={48} apart={props.title_valign === "top"}
        head={<SceneTitle title={props.title} kicker={props.kicker} />}>
        <Enter at={6} style={{ alignSelf: "stretch", textAlign: "left" }}>
          <Card padding={40}>
            {lines.map((line, i) => (
              <div key={i} style={{ display: "flex", gap: 28, position: "relative" }}>
                <div style={{ position: "absolute", inset: "0 -40px", background: color("accent"), opacity: 0.22 * lit(i + 1) }} />
                <Text size={34} tone="text-muted" role="code" family={MONO} style={{ width: 48, textAlign: "right", position: "relative" }}>{i + 1}</Text>
                <Text size={34} role="code" family={MONO} style={{ whiteSpace: "pre", position: "relative" }}>{line || " "}</Text>
              </div>
            ))}
          </Card>
        </Enter>
      </Place>
    </Ground>
  );
}
