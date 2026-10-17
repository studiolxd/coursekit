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
    transform?: string }): React.CSSProperties & { tone: string } => {
    const r = style?.text?.[role] ?? {};
    const base = style?.textBase?.[role];
    const family = r.family ? `"${r.family}", ${own.family}` : own.family;
    const out: React.CSSProperties & { tone: string } = {
      fontFamily: family, fontSize: r.size && base ? own.size * (r.size / base) : own.size,
      fontWeight: r.weight ?? weightOf(own.weight), fontStyle: r.style ?? "normal", lineHeight: r.leading ?? own.leading,
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
export const useColor = () => {
  const { tokens } = useTheme();
  return (name: string, fallback?: string) => tokens.color[name] ?? (fallback ? tokens.color[fallback] : undefined)
    ?? (name.endsWith("-ink") ? tokens.color[name.slice(0, -4)] : undefined) ?? "#000000";
};
