import React from "react";
import { AbsoluteFill } from "remotion";

// Where the content of a scene goes in the frame: across (`align`) and up and down (`valign`), inside the margins of the
// frame (`side`, the margin left and right); at the bottom it keeps clear of the captions. A scene with a title over its content
// (`head`) may keep the title at the top of the frame (`apart`) while the content goes where `valign` says.

export type Align = "left" | "center" | "right";
export type VAlign = "top" | "middle" | "bottom";

/** The props every scene takes to place itself: its background, and where its content goes across and up and down. */
export type Placing = { background?: "plain" | "surface" | "accent" | "photo"; photo?: string;
  veil?: "background" | "surface" | "accent" | "none"; veil_opacity?: number; credit?: string; align?: "left" | "center"; valign?: VAlign };
/** A scene with a title over its content: the title with the content (`content`, by default) or at the top of the frame. */
export type Titled = { title_valign?: "content" | "top" };

export const JUSTIFY = { top: "flex-start", middle: "center", bottom: "flex-end" } as const;
export const ITEMS = { left: "flex-start", center: "center", right: "flex-end" } as const;
export const MARGIN = 120;  // px above and below the content
export const CAPTIONS = 200;  // px kept free at the bottom of the frame, where the captions go
export const SIDE = 160;  // px left and right of the content: the same in every scene, so a title does not move from one to the next

export const edges = (valign: VAlign, side: number) => `${MARGIN}px ${side}px ${valign === "bottom" ? CAPTIONS : MARGIN}px`;

export const Place: React.FC<{ align?: Align; valign?: VAlign; side?: number; gap?: number; head?: React.ReactNode; apart?: boolean;
  style?: React.CSSProperties; children: React.ReactNode }> = (
  { align = "left", valign = "middle", side = SIDE, gap, head, apart = false, style, children }) => (
  apart && head ? (
    <AbsoluteFill style={{ flexDirection: "column", alignItems: ITEMS[align], textAlign: align, padding: edges(valign, side), gap, ...style }}>
      {head}
      <div style={{ flex: 1, alignSelf: "stretch", display: "flex", flexDirection: "column", justifyContent: JUSTIFY[valign],
        alignItems: ITEMS[align], gap }}>{children}</div>
    </AbsoluteFill>
  ) : (
    <AbsoluteFill style={{ flexDirection: "column", justifyContent: JUSTIFY[valign], alignItems: ITEMS[align], textAlign: align,
      padding: edges(valign, side), gap, ...style }}>
      {head}{children}
    </AbsoluteFill>
  )
);
