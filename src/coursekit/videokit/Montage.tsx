import React from "react";
import { AbsoluteFill, Audio, continueRender, delayRender, Easing, Img, interpolate, Sequence, staticFile, useCurrentFrame } from "remotion";
import { SceneMotion, ThemeProvider, type Entrance, type Motion, type Reveal, type Style, type Tokens } from "./theme";
import { SceneTimeProvider, type Word } from "./timing";
import { layers as layerRegistry, scenes as registry } from "./registry.generated";

// The montage: the scenes one after another, each with its narration, its words and its duration (computed by coursekit from
// the voice: changing a text changes the timing, not the code), in the theme of the course.

export type ResolvedLayer = { id: string; type: string; from: number; frames: number; props: Record<string, unknown> };
/** How a scene enters over the end of the one before (config/video.yaml › transition): they overlap for its frames. */
export type Transition = { type: "cut" | "fade" | "dip" | "push" | "wipe"; frames: number; direction?: "left" | "right" | "up" | "down" };
export type ResolvedScene = { id: string; type: string; from: number; frames: number; props: Record<string, unknown>;
  audio?: string | null; words: Word[]; layers?: ResolvedLayer[]; transition?: Transition | null };
export type MontageProps = { fps: number; width: number; height: number; frames: number; tokens: Tokens; motion: Motion;
  style?: Style; scenes: ResolvedScene[];
  /** What is rendered: the whole video (default), the scenes without their layers ("clean", for an editor), or one layer
   *  alone on a transparent background ({layer: id}). */
  mode?: "full" | "clean" | { layer: string } };

const Logo: React.FC<{ logo: NonNullable<Style["logo"]> }> = ({ logo }) => {
  const [v, h] = logo.corner.split("-");
  return (
    <AbsoluteFill style={{ justifyContent: v === "top" ? "flex-start" : "flex-end", alignItems: h === "left" ? "flex-start" : "flex-end",
      padding: 56, pointerEvents: "none" }}>
      <Img src={logo.src} style={{ height: logo.size, width: "auto" }} />
    </AbsoluteFill>
  );
};

// The fonts of the project (config/video.yaml › fonts), inside the video: the render waits until each family is loaded, so a
// frame never comes out in a font of the machine.
const Fonts: React.FC<{ fonts: NonNullable<Style["fonts"]> }> = ({ fonts }) => {
  const [handle] = React.useState(() => delayRender("fonts"));
  React.useEffect(() => {
    const style = document.createElement("style");
    style.textContent = fonts.css;
    document.head.appendChild(style);
    Promise.all(fonts.families.flatMap((family) => ["300", "400", "500", "700"].map((w) => document.fonts.load(`${w} 40px "${family}"`))))
      .then(() => continueRender(handle), () => continueRender(handle));
    return () => { style.remove(); };
  }, [fonts, handle]);
  return null;
};

// A scene entering (`into`, its transition) and giving way (`out`, the transition of the next): with none, it fades from the
// background and back to it, as the first and the last scenes do. fade: the new one dissolves over the old; dip: the old one goes
// to the background and the new one comes from it; push: the new one pushes the old one aside; wipe: a band of the accent crosses
// the frame uncovering the new one; cut: nothing.
const CLAMP = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const EASE = Easing.inOut(Easing.cubic);
const BAND = 0.035;  // the width of the band of a wipe, a fraction of the frame
const shift = (direction: Transition["direction"], amount: number) => {
  const d = direction ?? "left";
  const pct = `${(amount * 100).toFixed(3)}%`;
  return d === "left" ? `translateX(${pct})` : d === "right" ? `translateX(-${pct})` : d === "up" ? `translateY(${pct})` : `translateY(-${pct})`;
};
const uncover = (direction: Transition["direction"], k: number) => {  // what of the new scene a wipe has uncovered
  const rest = `${((1 - k) * 100).toFixed(3)}%`;
  return { left: `inset(0 0 0 ${rest})`, right: `inset(0 ${rest} 0 0)`, up: `inset(${rest} 0 0 0)`, down: `inset(0 0 ${rest} 0)` }[direction ?? "left"];
};

const Pass: React.FC<{ frames: number; fade: number; into?: Transition | null; out?: Transition | null; accent: string;
  children: React.ReactNode }> = ({ frames, fade, into, out, accent, children }) => {
  const frame = useCurrentFrame();
  let opacity = 1;
  const transforms: string[] = [];
  let clip: string | undefined;
  let band: React.CSSProperties | null = null;
  if (!into) opacity *= interpolate(frame, [0, Math.max(1, fade)], [0, 1], CLAMP);
  else if (into.frames > 0) {
    const k = EASE(interpolate(frame, [0, into.frames], [0, 1], CLAMP));
    if (into.type === "fade") opacity *= k;
    if (into.type === "dip") opacity *= interpolate(frame, [into.frames / 2, into.frames], [0, 1], CLAMP);
    if (into.type === "push") transforms.push(shift(into.direction, 1 - k));
    if (into.type === "wipe" && k < 1) {
      clip = uncover(into.direction, k);
      const d = into.direction ?? "left";
      const edge = `${(((d === "left" || d === "up" ? 1 - k : k) - BAND / 2) * 100).toFixed(3)}%`;  // the band rides the edge it uncovers
      band = d === "up" || d === "down"
        ? { position: "absolute", background: accent, left: 0, right: 0, height: `${BAND * 100}%`, top: edge }
        : { position: "absolute", background: accent, top: 0, bottom: 0, width: `${BAND * 100}%`, left: edge };
    }
  }
  if (!out) opacity *= interpolate(frame, [frames - Math.max(1, fade), frames], [1, 0], CLAMP);
  else if (out.frames > 0) {
    const start = frames - out.frames;
    if (out.type === "dip") opacity *= interpolate(frame, [start, start + out.frames / 2], [1, 0], CLAMP);
    if (out.type === "push") transforms.push(shift(out.direction, -EASE(interpolate(frame, [start, frames], [0, 1], CLAMP))));
  }
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ opacity, transform: transforms.join(" ") || undefined, clipPath: clip }}>{children}</AbsoluteFill>
      {band ? <div style={band} /> : null}
    </AbsoluteFill>
  );
};

const OnlyLayer: React.FC<{ scenes: ResolvedScene[]; id: string }> = ({ scenes, id }) => (
  <AbsoluteFill>
    {scenes.map((scene) => (scene.layers ?? []).filter((l) => l.id === id).map((layer) => {
      const Layer = layerRegistry[layer.type];
      return Layer ? (
        <Sequence key={layer.id} from={scene.from + layer.from} durationInFrames={layer.frames} name={layer.id}>
          <SceneTimeProvider value={{ words: scene.words, frames: scene.frames }}>
            <Layer id={layer.id} props={layer.props} frames={layer.frames} />
          </SceneTimeProvider>
        </Sequence>
      ) : null;
    }))}
  </AbsoluteFill>
);

export const Montage: React.FC<MontageProps> = ({ tokens, motion, style, scenes, mode = "full" }) => (
  <ThemeProvider theme={{ tokens, motion, style }}>
    {style?.fonts ? <Fonts fonts={style.fonts} /> : null}
    {typeof mode === "object" ? <OnlyLayer scenes={scenes} id={mode.layer} /> : (
    <AbsoluteFill style={{ background: tokens.color.background }}>
      {scenes.map((scene, n) => {
        const Scene = registry[scene.type];
        const into = n > 0 ? scene.transition ?? null : null;
        const out = scenes[n + 1]?.transition ?? null;
        return (
          <Sequence key={scene.id} from={scene.from} durationInFrames={scene.frames} name={scene.id}>
            <SceneTimeProvider value={{ words: scene.words, frames: scene.frames }}>
              <Pass frames={scene.frames} fade={motion.fade} into={into} out={out} accent={tokens.color.accent ?? "#000000"}>
                {Scene ? (
                  <SceneMotion entrance={scene.props?.entrance as Entrance | undefined} reveal={scene.props?.reveal as Reveal | undefined}>
                    <Scene id={scene.id} props={scene.props} />
                  </SceneMotion>
                ) : null}
                {style?.logo && style.logo.scenes.includes(scene.type) ? <Logo logo={style.logo} /> : null}
                {(mode === "clean" ? [] : scene.layers ?? []).map((layer) => {
                  const Layer = layerRegistry[layer.type];
                  return Layer ? (
                    <Sequence key={layer.id} from={layer.from} durationInFrames={layer.frames} name={layer.id}>
                      <Layer id={layer.id} props={layer.props} frames={layer.frames} />
                    </Sequence>
                  ) : null;
                })}
              </Pass>
              {scene.audio && mode !== "clean" ? <Audio src={staticFile(scene.audio)} /> : null}
            </SceneTimeProvider>
          </Sequence>
        );
      })}
    </AbsoluteFill>
    )}
  </ThemeProvider>
);
