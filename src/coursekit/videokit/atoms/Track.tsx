import React from "react";
import { useColor, useShapes, useTheme } from "../theme";

// A rail with what is done of it (`done`, from 0 to 1): the pause of a question, a part of the progress of a video. Its colours
// and the line around it come from config/video.yaml › progress; each a role of the theme or a hex.

export const useProgress = () => {
  const { style } = useTheme();
  const color = useColor();
  const look = style?.progress ?? { track: "border", fill: "accent-ink", outline: false };
  const paint = (name: string) => (name.startsWith("#") ? name : color(name, "border"));
  return { track: paint(look.track), fill: paint(look.fill), outline: look.outline };
};

export const Track: React.FC<{ done: number; width: number | string; height?: number }> = ({ done, width, height = 10 }) => {
  const look = useProgress();
  const shapes = useShapes();
  return (
    <div style={{ width, height, boxSizing: "border-box", borderRadius: shapes.corner(height / 2), background: look.track, overflow: "hidden",
      border: look.outline ? `1px solid ${look.fill}` : undefined, flex: "none" }}>
      <div style={{ width: `${Math.max(0, Math.min(1, done)) * 100}%`, height: "100%", background: look.fill }} />
    </div>
  );
};
