import React from "react";
import { AbsoluteFill, Audio, Img, interpolate, Sequence, staticFile, useCurrentFrame } from "remotion";
import { ThemeProvider, type Motion, type Style, type Tokens } from "./theme";
import { SceneTimeProvider, type Word } from "./timing";
import { layers as layerRegistry, scenes as registry } from "./registry.generated";

// The montage: the scenes one after another, each with its narration, its words and its duration (computed by coursekit from
// the voice: changing a text changes the timing, not the code), in the theme of the course.

export type ResolvedLayer = { id: string; type: string; from: number; frames: number; props: Record<string, unknown> };
export type ResolvedScene = { id: string; type: string; from: number; frames: number; props: Record<string, unknown>;
  audio?: string | null; words: Word[]; layers?: ResolvedLayer[] };
export type MontageProps = { fps: number; width: number; height: number; frames: number; tokens: Tokens; motion: Motion;
  style?: Style; scenes: ResolvedScene[] };

const Logo: React.FC<{ logo: NonNullable<Style["logo"]> }> = ({ logo }) => {
  const [v, h] = logo.corner.split("-");
  return (
    <AbsoluteFill style={{ justifyContent: v === "top" ? "flex-start" : "flex-end", alignItems: h === "left" ? "flex-start" : "flex-end",
      padding: 56, pointerEvents: "none" }}>
      <Img src={logo.src} style={{ height: logo.size, width: "auto" }} />
    </AbsoluteFill>
  );
};

const Fade: React.FC<{ frames: number; fade: number; children: React.ReactNode }> = ({ frames, fade, children }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, fade, frames - fade, frames], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>;
};

export const Montage: React.FC<MontageProps> = ({ tokens, motion, style, scenes }) => (
  <ThemeProvider theme={{ tokens, motion, style }}>
    <AbsoluteFill style={{ background: tokens.color.background }}>
      {scenes.map((scene) => {
        const Scene = registry[scene.type];
        return (
          <Sequence key={scene.id} from={scene.from} durationInFrames={scene.frames} name={scene.id}>
            <SceneTimeProvider value={{ words: scene.words, frames: scene.frames }}>
              <Fade frames={scene.frames} fade={motion.fade}>
                {Scene ? <Scene id={scene.id} props={scene.props} /> : null}
                {style?.logo && style.logo.scenes.includes(scene.type) ? <Logo logo={style.logo} /> : null}
                {(scene.layers ?? []).map((layer) => {
                  const Layer = layerRegistry[layer.type];
                  return Layer ? (
                    <Sequence key={layer.id} from={layer.from} durationInFrames={layer.frames} name={layer.id}>
                      <Layer id={layer.id} props={layer.props} frames={layer.frames} />
                    </Sequence>
                  ) : null;
                })}
              </Fade>
              {scene.audio ? <Audio src={staticFile(scene.audio)} /> : null}
            </SceneTimeProvider>
          </Sequence>
        );
      })}
    </AbsoluteFill>
  </ThemeProvider>
);
