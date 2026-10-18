import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Track } from "../../atoms/Track";
import { useTheme } from "../../theme";
import type { LayerProps } from "../../contract";

// Where the video is: one mark per part at the top right, the parts done and the current one full, the rest empty rails
// (config/video.yaml › progress).
export type ProgressProps = { current: number; total: number };

export default function Progress({ props, frames }: LayerProps<ProgressProps>) {
  const frame = useCurrentFrame();
  const { motion } = useTheme();
  const k = interpolate(frame, [0, Math.max(1, motion.enter), frames - motion.fade, frames], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "flex-end", padding: 64 }}>
      <div style={{ display: "flex", gap: 10, opacity: k }}>
        {Array.from({ length: Math.max(1, props.total) }, (_, i) => (
          <Track key={i} done={i + 1 <= props.current ? 1 : 0} width={i + 1 === props.current ? 56 : 28} />
        ))}
      </div>
    </AbsoluteFill>
  );
}
