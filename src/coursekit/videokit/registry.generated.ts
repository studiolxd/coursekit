// Written by coursekit (`coursekit video …`): the scenes and layers of the library, the project and the course that win.
import type React from "react";
import type { LayerProps, SceneProps } from "./contract";
import s_compare from "./scenes/compare";
import s_diagram from "./scenes/diagram";
import s_list from "./scenes/list";
import s_outro from "./scenes/outro";
import s_quote from "./scenes/quote";
import s_screencast from "./scenes/screencast";
import s_split from "./scenes/split";
import s_stat from "./scenes/stat";
import s_title from "./scenes/title";
import l_callout from "./layers/callout";
import l_highlight from "./layers/highlight";
import l_lower_third from "./layers/lower-third";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const scenes: Record<string, React.FC<SceneProps<any>>> = { compare: s_compare, diagram: s_diagram, list: s_list,
  outro: s_outro, quote: s_quote, screencast: s_screencast, split: s_split, stat: s_stat, title: s_title };
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const layers: Record<string, React.FC<LayerProps<any>>> = { callout: l_callout, highlight: l_highlight, "lower-third": l_lower_third };
