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

/** The style of the project for its videos (config/video.yaml): the background of the scenes that ask for none, and a logo. */
export type Style = { background?: "plain" | "band" | "shape"; logo?: { src: string; corner: string; scenes: string[]; size: number } | null };

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

/** A colour of the theme by its token name, with a fallback for a token the theme lacks. */
export const useColor = () => {
  const { tokens } = useTheme();
  return (name: string, fallback?: string) => tokens.color[name] ?? (fallback ? tokens.color[fallback] : undefined) ?? "#000000";
};
