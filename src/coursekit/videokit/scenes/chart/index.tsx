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

// A few figures that grow as the narration names them (`say`), with their source (a figure is never shown without it): as
// bars (`kind: bars`, by default), as columns (`columns`) or as the parts of a circle (`pie`, the parts of a whole). Bars and
// columns are one series, in the colour of config/video.yaml › chart › single; the parts of a circle sit together, each in the
// next colour of the series of the brand (`chart › series`), with a gap of the background between them. `stress`, the position
// of one figure (from 1): that one stands out and the others step back, as `chart › rest` says.
export type Bar = { label: string; value: number; say?: string };
export type ChartProps = { kicker?: string; title?: string; bars: Bar[]; unit?: string; source: string; stress?: number;
  locale?: string; kind?: "bars" | "columns" | "pie" } & Placing & Titled;

const COLUMNS = 380;  // px of height of the tallest column
const PIE = 420;  // px of the circle
const RING = 0.58;  // the hole of the circle, a fraction of its radius (0: a whole pie)

export default function Chart({ props }: SceneProps<ChartProps>) {
  const frame = useCurrentFrame();
  const color = useColor();
  const shapes = useShapes();
  const { motion, style } = useTheme();
  const chart = style?.chart ?? { series: ["accent"], single: undefined, bar: 56, end: null, rest: "dim" as const, rest_color: "border" };
  const paint = (name: string) => (name.startsWith("#") ? name : color(name, "accent"));  // a hex of the brand, or a role
  const end = chart.end ?? shapes.corner(6);
  const times = useSteps(props.bars.map((b) => b.say), 16, 14);
  const top = Math.max(...props.bars.map((b) => b.value), 1);
  const number = new Intl.NumberFormat(props.locale);
  const grow = (i: number) => interpolate(frame - times[i], [0, Math.max(1, motion.enter * 2)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const lead = (i: number) => !props.stress || props.stress === i + 1;
  const kind = props.kind ?? "bars";
  // the colour of a figure: the one of a single series, or (a circle) the next of the series; the rest, as chart › rest says
  const fill = (i: number) => {
    const own = kind === "pie" ? chart.series[i % chart.series.length] ?? "accent" : chart.single ?? chart.series[0] ?? "accent";
    return paint(!lead(i) && chart.rest === "muted" ? chart.rest_color : own);
  };
  const faded = (i: number) => (!lead(i) && chart.rest === "dim" ? 0.35 : 1);
  const value = (bar: Bar) => `${number.format(bar.value)}${props.unit ?? ""}`;
  const strong = (i: number) => Boolean(props.stress) && lead(i);

  const body = kind === "columns" ? (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 56, height: COLUMNS + 140 }}>
      {props.bars.map((bar, i) => (
        <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 14, width: Math.max(chart.bar * 4, 180) }}>
          <Text size={40} role="label" strong={strong(i)} style={{ opacity: grow(i) }}>{value(bar)}</Text>
          <div style={{ width: chart.bar, height: (bar.value / top) * COLUMNS * grow(i), borderRadius: `${end}px ${end}px 0 0`,
            background: fill(i), opacity: faded(i) }} />
          <Text size={34} role="label" strong={strong(i)} style={{ textAlign: "center" }}>{bar.label}</Text>
        </div>
      ))}
    </div>
  ) : kind === "pie" ? (() => {
    const total = props.bars.reduce((sum, b) => sum + Math.max(0, b.value), 0) || 1;
    const r = PIE / 2;
    const hole = r * RING;
    let start = -Math.PI / 2;
    const arc = (from: number, to: number) => {  // a slice of the ring, from one angle to another
      const big = to - from > Math.PI ? 1 : 0;
      const p = (a: number, d: number) => `${r + d * Math.cos(a)} ${r + d * Math.sin(a)}`;
      return `M ${p(from, r)} A ${r} ${r} 0 ${big} 1 ${p(to, r)} L ${p(to, hole)} A ${hole} ${hole} 0 ${big} 0 ${p(from, hole)} Z`;
    };
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 96 }}>
        <svg width={PIE} height={PIE} style={{ flex: "none", overflow: "visible" }}>
          {props.bars.map((bar, i) => {
            const sweep = (Math.max(0, bar.value) / total) * Math.PI * 2;
            const from = start;
            start += sweep;
            const k = grow(i);
            return k > 0 ? (
              <path key={i} d={arc(from, from + Math.max(0.0001, sweep * k))} fill={fill(i)} opacity={faded(i)}
                stroke={color("background")} strokeWidth={2} />  // a gap of the background between the parts, not a border
            ) : null;
          })}
        </svg>
        <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
          {props.bars.map((bar, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 18, opacity: grow(i) }}>
              <div style={{ width: 28, height: 28, borderRadius: shapes.corner(4), background: fill(i), opacity: faded(i), flex: "none" }} />
              <Text size={40} role="label" strong={strong(i)}>{bar.label}</Text>
              <Text size={40} role="label" strong={strong(i)}>{value(bar)}</Text>
            </div>
          ))}
        </div>
      </div>
    );
  })() : (
    <div style={{ display: "flex", flexDirection: "column", gap: 26 }}>
      {props.bars.map((bar, i) => (
        <div key={i} style={{ display: "grid", gridTemplateColumns: "360px 1fr", alignItems: "center", gap: 32 }}>
          <Text size={40} role="label" strong={strong(i)}>{bar.label}</Text>
          <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
            <div style={{ width: `${(bar.value / top) * 82 * grow(i)}%`, height: chart.bar, borderRadius: `0 ${end}px ${end}px 0`,
              background: fill(i), opacity: faded(i) }} />
            <Text size={40} role="label" strong={strong(i)} style={{ opacity: grow(i) }}>{value(bar)}</Text>
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <Ground variant={props.background} photo={props.photo} veil={props.veil} veilOpacity={props.veil_opacity} credit={props.credit}>
      <Place align={props.align} valign={props.valign} gap={56} apart={props.title_valign === "top"}
        head={<SceneTitle title={props.title} kicker={props.kicker} />}>
        <div style={{ display: "flex", flexDirection: "column", gap: 26, alignSelf: "stretch", textAlign: "left" }}>
          {body}
          <Enter at={times[times.length - 1] + 12}><Text size={30} tone="text-muted" role="caption">{props.source}</Text></Enter>
        </div>
      </Place>
    </Ground>
  );
}
