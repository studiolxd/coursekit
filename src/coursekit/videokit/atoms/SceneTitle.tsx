import React from "react";
import { Enter } from "./Enter";
import { Heading } from "./Heading";
import { Kicker } from "./Kicker";

// The title of a scene over its content (a comparison, a diagram, a list, a figure, a phrase, text and a medium), with its kicker
// over it if it has one: one size for every scene, so a video does not change the size of its titles from one scene to the
// next; the `heading` and `kicker` roles of the text (config/video.yaml › text) change them for all of them.

export const SCENE_TITLE = 84;

export const SceneTitle: React.FC<{ title?: string; kicker?: string; at?: number }> = ({ title, kicker, at = 0 }) => {
  if (!title && !kicker) return null;
  return (
    <div>
      {kicker ? <Kicker at={at} style={{ marginBottom: 18 }}>{kicker}</Kicker> : null}
      {title ? <Enter at={at + 6}><Heading size={SCENE_TITLE}>{title}</Heading></Enter> : null}
    </div>
  );
};
