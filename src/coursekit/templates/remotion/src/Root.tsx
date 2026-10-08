import React from "react";
import { AbsoluteFill, Composition, useCurrentFrame, interpolate } from "remotion";
import { color, font } from "./theme";

// Example composition: a title card in the project theme. The agent adds one composition per
// video asset (src/videos/<asset-id>.tsx) and registers it here.
const TitleCard: React.FC<{ title: string; subtitle: string }> = ({ title, subtitle }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: color.background, fontFamily: font, justifyContent: "center", padding: 120 }}>
      <div style={{ opacity, borderLeft: `12px solid ${color.accent}`, paddingLeft: 48 }}>
        <h1 style={{ fontSize: 96, fontWeight: 900, color: color.text, margin: 0 }}>{title}</h1>
        <p style={{ fontSize: 44, color: color["text-soft"], marginTop: 24 }}>{subtitle}</p>
      </div>
    </AbsoluteFill>
  );
};

export const Root: React.FC = () => (
  <>
    <Composition
      id="title-card"
      component={TitleCard}
      durationInFrames={120}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{ title: "Course title", subtitle: "Video template" }}
    />
  </>
);
