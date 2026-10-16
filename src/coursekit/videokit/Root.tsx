import React from "react";
import { Composition } from "remotion";
import { Montage, type MontageProps } from "./Montage";
import { DEFAULT_MOTION } from "./theme";

const empty: MontageProps = { fps: 30, width: 1920, height: 1080, frames: 30, tokens: { color: { background: "#ffffff" },
  font: { family: "sans-serif" } }, motion: DEFAULT_MOTION, scenes: [] };

export const KitRoot: React.FC = () => (
  <Composition id="Montage" component={Montage as unknown as React.FC<Record<string, unknown>>} defaultProps={empty as unknown as Record<string, unknown>}
    durationInFrames={30} fps={30} width={1920} height={1080}
    calculateMetadata={({ props }) => {
      const p = props as unknown as MontageProps;
      return { durationInFrames: Math.max(1, p.frames), fps: p.fps, width: p.width, height: p.height };
    }} />
);
