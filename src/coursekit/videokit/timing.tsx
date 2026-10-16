import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";

// The time of a scene: its duration and the words of its narration (seconds from the start of the scene). `useAt("word")`
// is the frame of the scene in which the narration says it, so a layer, a highlight or a step of a diagram enters when the
// voice names it, not at a second guessed by eye.

export type Word = { w: string; start: number; end: number };
type SceneTime = { words: Word[]; frames: number };

const SceneContext = React.createContext<SceneTime>({ words: [], frames: 0 });

export const SceneTimeProvider: React.FC<{ value: SceneTime; children: React.ReactNode }> = ({ value, children }) => (
  <SceneContext.Provider value={value}>{children}</SceneContext.Provider>
);

export const useSceneTime = () => React.useContext(SceneContext);

const normal = (text: string) =>
  text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9ñ]+/g, " ").trim();

/** The second of the scene in which a phrase is said (the first time, from `after` on), or null when it is not said. */
export const whenSaid = (words: Word[], phrase: string, after = -1): number | null => {
  const wanted = normal(phrase).split(" ").filter(Boolean);
  const said = words.map((w) => normal(w.w));
  for (let i = 0; i + wanted.length <= said.length; i++) {
    if (words[i].start < after) continue;
    if (wanted.every((w, k) => said[i + k] === w)) return words[i].start;
  }
  return null;
};

/** The frame of the scene in which a phrase is said; `fallback` (a frame) when it is not. */
export const useAt = (phrase: string | undefined, fallback = 0): number => {
  const { words } = useSceneTime();
  const { fps } = useVideoConfig();
  if (!phrase) return fallback;
  const at = whenSaid(words, phrase);
  return at == null ? fallback : Math.round(at * fps);
};

/** Frames since a moment of the scene (negative before it). */
export const useSince = (frame: number) => useCurrentFrame() - frame;

/** The frame of the scene in which each phrase is said, one after another (null for one that is not said, or not given). */
export const useSayTimes = (phrases: (string | undefined)[]): (number | null)[] => {
  const { words } = useSceneTime();
  const { fps } = useVideoConfig();
  let after = -1;
  return phrases.map((phrase) => {
    const s = phrase ? whenSaid(words, phrase, after) : null;
    if (s != null) after = s;
    return s == null ? null : Math.round(s * fps);
  });
};
