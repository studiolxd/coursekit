import React from "react";
import { AbsoluteFill } from "remotion";
import { Ring } from "../../atoms/Ring";
import type { LayerProps } from "../../contract";

// A ring on a point of the scene (fractions of the screen): what the narration is talking about, there.
export type HighlightProps = { fx: number; fy: number; size?: number; shape?: "ring" | "box"; dim?: boolean };

export default function Highlight({ props }: LayerProps<HighlightProps>) {
  return (
    <AbsoluteFill>
      <Ring fx={props.fx} fy={props.fy} size={props.size ?? 120} shape={props.shape} dim={props.dim} />
    </AbsoluteFill>
  );
}
