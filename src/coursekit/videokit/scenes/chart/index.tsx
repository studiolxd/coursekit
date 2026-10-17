import React from "react";
import { Ground } from "../../atoms/Ground";
import { Enter } from "../../atoms/Enter";
import { SceneTitle } from "../../atoms/SceneTitle";
import { Place, type Placing, type Titled } from "../../atoms/Place";
import { Text } from "../../atoms/Text";
import { interpolate, useCurrentFrame } from "remotion";
import { useColor, useShapes, useTheme } from "../../theme";
import { useSteps } from "../../timing";
import type { SceneProps } from "../../contract";

// A few figures as bars that grow as the narration names them (`say`), with their source (a figure is never shown without
// it). `stress`, the position of one bar (from 1): that one in the accent and the others stepping back.
export type Bar = { label: string; value: number; say?: string };
export type ChartProps = { kicker?: string; title?: string; bars: Bar[]; unit?: string; source: string; stress?: number;
  locale?: string } & Placing & Titled;

export default function Chart({ props }: SceneProps<ChartProps>) {
  const frame = useCurrentFrame();
  const color = useColor();
  const shapes = useShapes();
  const { motion } = useTheme();
  const times = useSteps(props.bars.map((b) => b.say), 16, 14);
  const top = Math.max(...props.bars.map((b) => b.value), 1);
  const number = new Intl.NumberFormat(props.locale);
  return (
    <Ground variant={props.background} photo={props.photo} veil={props.veil} veilOpacity={props.veil_opacity} credit={props.credit}>
      <Place align={props.align} valign={props.valign} gap={56} apart={props.title_valign === "top"}
        head={<SceneTitle title={props.title} kicker={props.kicker} />}>
        <div style={{ display: "flex", flexDirection: "column", gap: 26, alignSelf: "stretch", textAlign: "left" }}>
          {props.bars.map((bar, i) => {
            const k = interpolate(frame - times[i], [0, Math.max(1, motion.enter * 2)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
            const lead = !props.stress || props.stress === i + 1;
            return (
              <div key={i} style={{ display: "grid", gridTemplateColumns: "360px 1fr", alignItems: "center", gap: 32 }}>
                <Text size={40} weight={600} role="label" tone={lead ? "text" : "text-muted"}>{bar.label}</Text>
                <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
                  <div style={{ width: `${(bar.value / top) * 82 * k}%`, height: 56, borderRadius: shapes.corner(6),
                    background: color("accent"), opacity: lead ? 1 : 0.35 }} />
                  <Text size={40} weight={700} role="label" style={{ opacity: k }}>{`${number.format(bar.value)}${props.unit ?? ""}`}</Text>
                </div>
              </div>
            );
          })}
          <Enter at={times[times.length - 1] + 12}><Text size={30} tone="text-muted" role="caption">{props.source}</Text></Enter>
        </div>
      </Place>
    </Ground>
  );
}
