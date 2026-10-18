import React from "react";
import { Ground } from "../../atoms/Ground";
import { Enter } from "../../atoms/Enter";
import { SceneTitle } from "../../atoms/SceneTitle";
import { Place, type Placing, type Titled } from "../../atoms/Place";
import { Badge } from "../../atoms/Badge";
import { Card } from "../../atoms/Card";
import { Text } from "../../atoms/Text";
import { Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import { useSceneMotion, useShapes, useTheme } from "../../theme";
import { useSteps } from "../../timing";
import type { SceneProps } from "../../contract";

// An image or a screenshot with numbered points that enter as the narration names them (`say`), each with its label beside
// it: a screen, a document or a diagram explained without recording it. Points are fractions of the image (fx, fy).
export type Point = { fx: number; fy: number; label: string; say?: string };
// Each label is as tall as the square of its number, as wide as its text up to a limit, and goes to a second line beyond it.
// Entering one by one, the points before stay (`previous: keep`) or give way to the new one (`hide`).
export type AnnotatedProps = { kicker?: string; title?: string; image: string; points: Point[]; height?: number;
  previous?: "keep" | "hide" } & Placing & Titled;

const BADGE = 56;  // px of the square of the number, and the least height of its label
const LABEL = 560;  // px a label may grow to before it goes to a second line

export default function Annotated({ props }: SceneProps<AnnotatedProps>) {
  const times = useSteps(props.points.map((p) => p.say), 20, 26);
  const shapes = useShapes();
  const frame = useCurrentFrame();
  const { motion } = useTheme();
  const { reveal } = useSceneMotion();
  const hide = props.previous === "hide" && reveal !== "together";
  const shown = (i: number) => (hide && i + 1 < times.length  // it fades when the next one enters
    ? interpolate(frame, [times[i + 1], times[i + 1] + Math.max(1, motion.enter)], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : 1);
  const src = /^https?:/.test(props.image) ? props.image : staticFile(props.image);
  return (
    <Ground variant={props.background} photo={props.photo} veil={props.veil} veilOpacity={props.veil_opacity} credit={props.credit}>
      <Place align={props.align} valign={props.valign} gap={48} apart={props.title_valign === "top"}
        head={<SceneTitle title={props.title} kicker={props.kicker} />}>
        {/* as big as the image, so the points (fractions of it) land where they say */}
        <div style={{ position: "relative", display: "inline-block" }}>
          <Img src={src} style={{ display: "block", height: props.height ?? 640, width: "auto", maxWidth: 1600, borderRadius: shapes.radius(16) }} />
          {props.points.map((p, i) => (
            <div key={i} style={{ position: "absolute", left: `${p.fx * 100}%`, top: `${p.fy * 100}%`, transform: `translate(-${BADGE / 2}px, -${BADGE / 2}px)`,
              opacity: shown(i) }}>
              <Enter at={times[i]} scale from="none" style={{ display: "flex", alignItems: "stretch", gap: 10, textAlign: "left" }}>
                <Badge size={BADGE}>{i + 1}</Badge>
                <Card padding={0} style={{ display: "flex", alignItems: "center", minHeight: BADGE, boxSizing: "border-box", padding: "6px 18px",
                  width: "max-content", maxWidth: LABEL }}>
                  <Text size={30} weight={600} role="label">{p.label}</Text>
                </Card>
              </Enter>
            </div>
          ))}
        </div>
      </Place>
    </Ground>
  );
}
