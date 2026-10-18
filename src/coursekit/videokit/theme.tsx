import React from "react";

// The theme of the video: the tokens of the theme of the course (theme/tokens.json, or the course's own), which reach the
// video as props (a course can have its own theme), and the tokens of motion. Every atom reads them from here: a course with
// another theme gives another video without touching anything.

export type Tokens = {
  color: Record<string, string>;
  font: { family: string; headings?: string; ui?: string };
  radius?: string | number;
  space?: Record<string, string>;
  shadow?: Record<string, string>;
};

export type Motion = {
  /** Frames an element takes to enter. */
  enter: number;
  /** Frames between the elements of a list that enter one after another. */
  stagger: number;
  /** Frames a scene takes to fade in and out. */
  fade: number;
  /** Damping of the springs: higher is calmer. */
  damping: number;
  /** How things enter (config/video.yaml › motion › entrance): auto, each piece its own way. */
  entrance?: Entrance;
};

export type Entrance = "auto" | "fade" | "rise" | "slide" | "scale" | "none";
export type Reveal = "one-by-one" | "together";

/** How the scene being drawn moves: its `entrance` and `reveal` props over those of the project. */
const SceneMotionContext = React.createContext<{ entrance?: Entrance; reveal?: Reveal }>({});
export const SceneMotion: React.FC<{ entrance?: Entrance; reveal?: Reveal; children: React.ReactNode }> = ({ entrance, reveal, children }) => (
  <SceneMotionContext.Provider value={{ entrance, reveal }}>{children}</SceneMotionContext.Provider>
);
/** The entrance and the reveal of the scene: its own, else the project's (auto, one by one). */
export const useSceneMotion = () => {
  const own = React.useContext(SceneMotionContext);
  const { motion } = useTheme();
  return { entrance: own.entrance ?? motion.entrance ?? "auto", reveal: own.reveal ?? "one-by-one" } as { entrance: Entrance; reveal: Reveal };
};

export const DEFAULT_MOTION: Motion = { enter: 18, stagger: 6, fade: 10, damping: 18 };

/** The style of the project for its videos (config/video.yaml): the background of the scenes that ask for none, a logo, the
 *  shapes of the panels and the weights of the text (null: what each piece draws), and the fonts that go inside the video. */
export type Style = {
  background?: "plain" | "band" | "shape";
  /** The veil over a photo for background (config/video.yaml › photo_veil): its colour (a role, or none) and how opaque it is. */
  veil?: { color: string; opacity: number };
  /** The look of the charts (config/video.yaml › chart): the colours of the series, the bars, and the bars that step back. */
  chart?: { series: string[]; single?: string; bar: number; end: number | null; rest: "dim" | "muted"; rest_color: string };
  /** The bars that show an advance (config/video.yaml › progress): the rail, what is done, and a line around the rail. */
  progress?: { track: string; fill: string; outline: boolean; height?: number };
  /** How the stressed word of a scene is marked (config/video.yaml › stress). */
  stress?: "underline" | "highlight" | "colour";
  logo?: { src: string; corner: string; scenes: string[]; size: number } | null;
  shapes?: { radius?: number | null; shadow?: "soft" | "none" | null; border?: number | null };
  weights?: { normal?: number | null; strong?: number | null };
  fonts?: { css: string; families: string[] } | null;
  /** The typography of each role of the text (config/video.yaml › text); null: what each piece draws. */
  text?: Record<string, TextRole>;
  /** The reference size of each role (the package's): a size of the project scales every text of that role in proportion. */
  textBase?: Record<string, number>;
};

export type TextRole = { family?: string | null; size?: number | null; weight?: number | null; style?: "normal" | "italic" | null;
  transform?: "none" | "uppercase" | "lowercase" | "capitalize" | null; tracking?: number | null; leading?: number | null;
  color?: string | null; numeric?: "tabular" | "proportional" | null; measure?: number | null };

export type Theme = { tokens: Tokens; motion: Motion; style?: Style };

const ThemeContext = React.createContext<Theme>({
  tokens: { color: { background: "#ffffff", text: "#1a1a1a", accent: "#0b5fff", "text-muted": "#555555" }, font: { family: "sans-serif" } },
  motion: DEFAULT_MOTION,
  style: { background: "shape", logo: null },
});

export const ThemeProvider: React.FC<{ theme: Theme; children: React.ReactNode }> = ({ theme, children }) => (
  <ThemeContext.Provider value={theme}>{children}</ThemeContext.Provider>
);

export const useTheme = () => React.useContext(ThemeContext);

/** The inks a piece puts on a fill (the accent, a dark photo, a colour of state): the colour of a role never overrides them. */
const INKS = new Set(["background", "on-accent", "on-correct", "on-wrong"]);

/** The typography of a text of a role, over what the piece draws (`own`): the family, the size (the piece's, scaled by the size
 *  of the project over the reference one), the weight, the style, the case, the tracking, the leading, the colour, the figures and
 *  the measure the project fixes for that role (config/video.yaml › text). */
export const useText = () => {
  const { style } = useTheme();
  const weightOf = useWeight();
  return (role: string, own: { family: string; size: number; weight: number; tone: string; leading: number; tracking: number;
    transform?: string; strong?: boolean }): React.CSSProperties & { tone: string } => {
    const r = style?.text?.[role] ?? {};
    const base = style?.textBase?.[role];
    const family = r.family ? `"${r.family}", ${own.family}` : own.family;
    const out: React.CSSProperties & { tone: string } = {
      fontFamily: family, fontSize: r.size && base ? own.size * (r.size / base) : own.size,
      fontWeight: own.strong ? weightOf(700) : r.weight ?? weightOf(own.weight),  // what stands out: the strong weight, over the role's fontStyle: r.style ?? "normal", lineHeight: r.leading ?? own.leading,
      letterSpacing: r.tracking ?? own.tracking, textTransform: (r.transform ?? own.transform ?? "none") as React.CSSProperties["textTransform"],
      fontVariantNumeric: r.numeric === "tabular" ? "tabular-nums" : undefined, maxWidth: r.measure ? `${r.measure}ch` : undefined,
      tone: r.color && !INKS.has(own.tone) ? r.color : own.tone,
    };
    for (const key of Object.keys(out) as (keyof typeof out)[]) if (out[key] === undefined) delete out[key];  // the piece's stays
    return out;
  };
};

/** The shapes of the panels: the radius of the style, else the theme's, else the piece's own; its shadow unless the style
 *  says none; the width of its border. */
export const useShapes = () => {
  const { tokens, style } = useTheme();
  const shapes = style?.shapes ?? {};
  return {
    radius: (own: number) => shapes.radius ?? tokens.radius ?? own,
    /** A small rounding (a marker, a chip): never rounder than the radius of the style. */
    corner: (own: number) => (shapes.radius == null ? own : Math.min(own, shapes.radius)),
    shadow: (own: string) => (shapes.shadow === "none" || tokens.shadow?.soft === "none" ? "none" : own),
    border: (own: number) => shapes.border ?? own,
  };
};

/** The weight a piece asks for, as the style says: what is 600 or more is the strong weight, the rest the normal one. */
export const useWeight = () => {
  const { style } = useTheme();
  const weights = style?.weights ?? {};
  return (weight: number) => (weight >= 600 ? weights.strong ?? weight : weights.normal ?? weight);
};

/** A colour of the theme by its token name, with a fallback for a token the theme lacks. The accent is a fill (a close, the
 *  circle of a number); what is drawn thin on the background with it (a line, an arrow, a mark, a word) is `accent-ink`, the
 *  accent that reads on the background: the same colour when the accent already reads, a darker one when it is only a fill. */
export const useColor = (raw = false) => {
  const { tokens } = useTheme();
  const ground = React.useContext(GroundContext);
  const swap = raw ? undefined : SWAPS[ground];
  return (asked: string, fallback?: string) => {
    const name = swap?.[asked] ?? asked;
    return tokens.color[name] ?? (fallback ? tokens.color[swap?.[fallback] ?? fallback] : undefined)
      ?? (name.endsWith("-ink") ? tokens.color[name.slice(0, -4)] : undefined) ?? "#000000";
  };
};

/** What a scene is drawn on: its background (`base`, the background colour or a shape or a band of the style), the surface colour
 *  whole or the accent whole. On the accent every ink of the piece (the text, the titles, the marks, the accent drawn thin) is
 *  the text on the accent, and what is on the accent (a number in its circle) swaps with it; on the surface a panel takes the
 *  background colour, so it still stands out. On `inverse` (the colour of the text whole) the inks take the background colour
 *  and the accent keeps its own (a fill reads on it). A panel puts its children back on `base`. */
export type Ground = "base" | "surface" | "accent" | "inverse";
const GroundContext = React.createContext<Ground>("base");
const ON_ACCENT = ["text", "headings", "text-muted", "accent-ink", "link", "accent"];
const SWAPS: Record<Ground, Record<string, string> | undefined> = {
  base: undefined,
  surface: { surface: "background" },
  accent: { ...Object.fromEntries(ON_ACCENT.map((name) => [name, "on-accent"])), "on-accent": "accent" },
  inverse: Object.fromEntries(["text", "headings", "text-muted", "accent-ink", "link"].map((name) => [name, "background"])),
};
export const OnGround: React.FC<{ ground: Ground; children: React.ReactNode }> = ({ ground, children }) => (
  <GroundContext.Provider value={ground}>{children}</GroundContext.Provider>
);
