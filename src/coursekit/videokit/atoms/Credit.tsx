import React from "react";
import { AbsoluteFill } from "remotion";
import { Text } from "./Text";
import { useColor, useShapes } from "../theme";

// The credit of the image of a scene (its author and its licence, as a CC-BY photo requires), small, at the bottom right of
// the frame, on a pill of the background colour so it reads over any photo.

export const Credit: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  const color = useColor(true);
  const shapes = useShapes();
  if (!children) return null;
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "flex-end", padding: 28, pointerEvents: "none" }}>
      <div style={{ background: color("background"), opacity: 0.88, padding: "6px 14px", borderRadius: shapes.corner(8) }}>
        <Text size={22} tone="text" role="caption">{children}</Text>
      </div>
    </AbsoluteFill>
  );
};
