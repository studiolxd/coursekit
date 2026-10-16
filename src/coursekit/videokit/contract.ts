// The contract of a scene: what every scene receives, the ones of the library and the ones an agent writes. A scene is a
// folder with `index.tsx` (its component, `export default`) and `scene.yaml` (what it is, its props, what it is built from).
// Everything else a scene needs comes from hooks: `useTheme()` and `useColor()` (the theme of the course), `useAt("word")`
// (when the narration says something), `useSceneTime()` (its words and its frames), and Remotion's `useCurrentFrame()`.
// Rules: everything moves with the frame (no CSS animations, no timers); only the tokens of the theme for colours and
// fonts; media by their path inside the media folder of the course (`MediaSlot`); nothing from the network.

export type SceneProps<P = Record<string, unknown>> = {
  /** The props of the scene in the montage. */
  props: P;
  /** Its id in the montage. */
  id: string;
};
