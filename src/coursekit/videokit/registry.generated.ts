// Written by coursekit (`coursekit video …`) with the scenes of the library, of the project and of the course: a scene of
// the course hides one of the project with its name, and one of the project hides one of the library. Do not edit.
import type React from "react";
import type { SceneProps } from "./contract";
import outro from "./scenes/outro";
import screencast from "./scenes/screencast";
import split from "./scenes/split";
import stat from "./scenes/stat";
import title from "./scenes/title";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const scenes: Record<string, React.FC<SceneProps<any>>> = { outro, screencast, split, stat, title };
