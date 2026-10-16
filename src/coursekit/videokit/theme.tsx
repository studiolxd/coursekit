import React from "react";

// The theme of the video: the tokens of the theme of the course (theme/tokens.json, or the course's own), which reach the
// video as props (a course can have its own theme), and the tokens of motion. Every atom reads them from here: a course with
// another theme gives another video without touching anything.

export type Tokens = {
  color: Record<string, string>;
  font: { family: string; headings?: string; ui?: string };
  radius?: string | number;
  space?: Record<string, string>;
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
};

export const DEFAULT_MOTION: Motion = { enter: 18, stagger: 6, fade: 10, damping: 18 };

/** The style of the project for its videos (config/video.yaml): the background of the scenes that ask for none, a logo, the
 *  shapes of the panels and the weights of the text (null: what each piece draws), and the fonts that go inside the video. */
export type Style = {
  background?: "plain" | "band" | "shape";
  logo?: { src: string; corner: string; scenes: string[]; size: number } | null;
  shapes?: { radius?: number | null; shadow?: "soft" | "none" | null; border?: number | null };
  weights?: { normal?: number | null; strong?: number | null };
  fonts?: { css: string; families: string[] } | null;
};

export type Theme = { tokens: Tokens; motion: Motion; style?: Style };

const ThemeContext = React.createContext<Theme>({
  tokens: { color: { background: "#ffffff", text: "#1a1a1a", accent: "#0b5fff", "text-soft": "#555555" }, font: { family: "sans-serif" } },
  motion: DEFAULT_MOTION,
  style: { background: "shape", logo: null },
});

export const ThemeProvider: React.FC<{ theme: Theme; children: React.ReactNode }> = ({ theme, children }) => (
  <ThemeContext.Provider value={theme}>{children}</ThemeContext.Provider>
);

export const useTheme = () => React.useContext(ThemeContext);

/** The shapes of the panels: the radius of the style, else the theme's, else the piece's own; its shadow unless the style
 *  says none; the width of its border. */
export const useShapes = () => {
  const { tokens, style } = useTheme();
  const shapes = style?.shapes ?? {};
  return {
    radius: (own: number) => shapes.radius ?? tokens.radius ?? own,
    /** A small rounding (a marker, a chip): never rounder than the radius of the style. */
    corner: (own: number) => (shapes.radius == null ? own : Math.min(own, shapes.radius)),
    shadow: (own: string) => (shapes.shadow === "none" ? "none" : own),
    border: (own: number) => shapes.border ?? own,
  };
};

/** The weight a piece asks for, as the style says: what is 600 or more is the strong weight, the rest the normal one. */
export const useWeight = () => {
  const { style } = useTheme();
  const weights = style?.weights ?? {};
  return (weight: number) => (weight >= 600 ? weights.strong ?? weight : weights.normal ?? weight);
};

/** A colour of the theme by its token name, with a fallback for a token the theme lacks. */
export const useColor = () => {
  const { tokens } = useTheme();
  return (name: string, fallback?: string) => tokens.color[name] ?? (fallback ? tokens.color[fallback] : undefined) ?? "#000000";
};
