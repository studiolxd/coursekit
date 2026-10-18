import React from "react";
import { AbsoluteFill } from "remotion";
import { Background } from "./Background";
import { Credit } from "./Credit";
import { MediaSlot } from "./MediaSlot";
import { OnGround, useColor, useTheme } from "../theme";

// The background of a scene and what is drawn on it: `variant` as in Background (without it, the one of the style of the
// project); on the accent or the surface colour the inks of the piece follow it (theme.tsx › Ground). `photo`, with a photo:
// the photo whole under a veil (`veil`, a colour of the theme or none, and `veilOpacity`; without them, config/video.yaml ›
// photo_veil), and the inks of the piece follow the colour of the veil.

export type GroundVariant = "plain" | "surface" | "accent" | "inverse" | "photo";
export type Veil = "background" | "surface" | "accent" | "inverse" | "none";

export const Ground: React.FC<{ variant?: GroundVariant; photo?: string; veil?: Veil; veilOpacity?: number; credit?: string;
  children: React.ReactNode }> = ({ variant, photo, veil, veilOpacity, credit, children }) => {
  const { style } = useTheme();
  const color = useColor(true);
  if (variant === "photo" && photo) {
    const tint = veil ?? (style?.veil?.color as Veil | undefined) ?? "background";
    const opacity = Math.min(1, Math.max(0, veilOpacity ?? style?.veil?.opacity ?? 0.82));
    return (
      <AbsoluteFill>
        <AbsoluteFill><MediaSlot src={photo} style={{ borderRadius: 0 }} /></AbsoluteFill>
        {tint !== "none" ? <AbsoluteFill style={{ background: color(tint === "inverse" ? "text" : tint, "background"), opacity }} /> : null}
        <OnGround ground={tint === "accent" || tint === "inverse" || tint === "surface" ? tint : "base"}>{children}</OnGround>
        <Credit>{credit}</Credit>
      </AbsoluteFill>
    );
  }
  const asked = variant === "photo" ? undefined : variant;  // a photo for background with no photo: the background of the style
  const drawn = asked ?? style?.background ?? "plain";
  return (
    <AbsoluteFill>
      <Background variant={asked} />
      <OnGround ground={drawn === "accent" || drawn === "inverse" || drawn === "surface" ? drawn : "base"}>{children}</OnGround>
      <Credit>{credit}</Credit>
    </AbsoluteFill>
  );
};
