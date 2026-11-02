import React from "react";
import { staticFile } from "remotion";
import { useColor } from "../theme";

// An icon of the set of the project (a path inside the media folder of the course, e.g. files/icons/lock.svg, which
// `coursekit media extract` copies from theme/branding/icons/), painted in a colour of the theme with a mask, as the notes of the
// course paint it: the shape is the brand's, the colour the theme's. Nothing is fetched from the network.

export const Icon: React.FC<{ src: string; size?: number; tone?: string; style?: React.CSSProperties }> = (
  { src, size = 72, tone = "accent-ink", style }) => {
  const color = useColor();
  const url = /^https?:/.test(src) ? src : staticFile(src);
  const mask = `url("${url}") center / contain no-repeat`;
  return <div aria-hidden style={{ width: size, height: size, flex: "none", background: color(tone), WebkitMask: mask, mask, ...style }} />;
};
