import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Card } from "../../atoms/Card";
import { Credit } from "../../atoms/Credit";
import { Enter } from "../../atoms/Enter";
import { MediaSlot } from "../../atoms/MediaSlot";
import { Text } from "../../atoms/Text";
import { CAPTIONS, SIDE } from "../../atoms/Place";
import { useSceneMotion } from "../../theme";
import { useSceneTime } from "../../timing";
import type { SceneProps } from "../../contract";

// An image on the whole frame (a photo, an illustration) while the narration talks over it, with a slow movement across the
// scene (`move`: it closes in, it opens out, it pans; none, still) and, if it has one, a caption in a panel at the bottom left.
export type ImageProps = { image: string; caption?: string; move?: "zoom-in" | "zoom-out" | "pan-left" | "pan-right" | "none";
  fit?: "cover" | "contain"; credit?: string };

const ZOOM = 0.08;  // how much it closes in or opens out over the scene
const PAN = 4;  // % of the frame it travels across the scene

export default function ImageScene({ props }: SceneProps<ImageProps>) {
  const frame = useCurrentFrame();
  const { frames } = useSceneTime();
  const { entrance } = useSceneMotion();
  const move = entrance === "none" ? "none" : props.move ?? "zoom-in";
  const k = interpolate(frame, [0, Math.max(1, frames)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const transform = {
    "zoom-in": `scale(${1 + ZOOM * k})`, "zoom-out": `scale(${1 + ZOOM * (1 - k)})`,
    "pan-left": `scale(${1 + ZOOM}) translateX(${PAN / 2 - PAN * k}%)`, "pan-right": `scale(${1 + ZOOM}) translateX(${PAN * k - PAN / 2}%)`, none: "",
  }[move];
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <AbsoluteFill style={{ transform }}><MediaSlot src={props.image} fit={props.fit ?? "cover"} style={{ borderRadius: 0 }} /></AbsoluteFill>
      {props.caption ? (
        <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "flex-start", padding: `0 ${SIDE}px ${CAPTIONS}px` }}>
          <Enter at={12}><Card padding={32} style={{ maxWidth: 1100 }}><Text size={40} role="body">{props.caption}</Text></Card></Enter>
        </AbsoluteFill>
      ) : null}
      <Credit>{props.credit}</Credit>
    </AbsoluteFill>
  );
}
