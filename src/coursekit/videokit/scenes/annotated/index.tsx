import React from "react";
import { Ground } from "../../atoms/Ground";
import { Enter } from "../../atoms/Enter";
import { SceneTitle } from "../../atoms/SceneTitle";
import { Place, type Placing, type Titled } from "../../atoms/Place";
import { Badge } from "../../atoms/Badge";
import { Card } from "../../atoms/Card";
import { Text } from "../../atoms/Text";
import { Img, staticFile } from "remotion";
import { useShapes } from "../../theme";
import { useSteps } from "../../timing";
import type { SceneProps } from "../../contract";

// An image or a screenshot with numbered points that enter as the narration names them (`say`), each with its label beside
// it: a screen, a document or a diagram explained without recording it. Points are fractions of the image (fx, fy).
export type Point = { fx: number; fy: number; label: string; say?: string };
export type AnnotatedProps = { kicker?: string; title?: string; image: string; points: Point[]; height?: number } & Placing & Titled;

export default function Annotated({ props }: SceneProps<AnnotatedProps>) {
  const times = useSteps(props.points.map((p) => p.say), 20, 26);
  const shapes = useShapes();
  const src = /^https?:/.test(props.image) ? props.image : staticFile(props.image);
  return (
    <Ground variant={props.background} photo={props.photo} veil={props.veil} veilOpacity={props.veil_opacity} credit={props.credit}>
      <Place align={props.align} valign={props.valign} gap={48} apart={props.title_valign === "top"}
        head={<SceneTitle title={props.title} kicker={props.kicker} />}>
        {/* as big as the image, so the points (fractions of it) land where they say */}
        <div style={{ position: "relative", display: "inline-block", lineHeight: 0 }}>
          <Img src={src} style={{ height: props.height ?? 640, width: "auto", maxWidth: 1600, borderRadius: shapes.radius(16) }} />
          {props.points.map((p, i) => (
            <div key={i} style={{ position: "absolute", left: `${p.fx * 100}%`, top: `${p.fy * 100}%`, transform: "translate(-28px, -28px)" }}>
              <Enter at={times[i]} scale from="none" style={{ display: "flex", alignItems: "center", gap: 14, textAlign: "left" }}>
                <Badge size={56}>{i + 1}</Badge>
                <Card padding={16} style={{ maxWidth: 420 }}><Text size={30} weight={600} role="label">{p.label}</Text></Card>
              </Enter>
            </div>
          ))}
        </div>
      </Place>
    </Ground>
  );
}
