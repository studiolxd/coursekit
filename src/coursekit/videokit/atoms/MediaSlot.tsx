import React from "react";
import { Img, OffthreadVideo, staticFile } from "remotion";
import { useShapes } from "../theme";

// An image or a video of the course (a path inside its media folder, e.g. files/u1-s2-m1.png or recordings/U1-S2-M1.mp4),
// fitted to its box with the radius of the style or the theme. Nothing is fetched from the network.

export const MediaSlot: React.FC<{ src: string; fit?: "cover" | "contain"; style?: React.CSSProperties; startFrom?: number }> = (
  { src, fit = "cover", style, startFrom = 0 }) => {
  const shapes = useShapes();
  const url = /^https?:/.test(src) ? src : staticFile(src);
  const box: React.CSSProperties = { width: "100%", height: "100%", objectFit: fit, borderRadius: shapes.radius(16), ...style };
  return /\.(mp4|webm|mov)$/i.test(src) ? <OffthreadVideo src={url} startFrom={startFrom} muted style={box} /> : <Img src={url} style={box} />;
};
