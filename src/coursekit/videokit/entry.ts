// The entry of the montage (`coursekit video render` renders it): one composition, Montage, whose props are the montage
// resolved by coursekit. It is apart from src/index.ts, so the compositions made by hand stay as they are.
import { registerRoot } from "remotion";
import { KitRoot } from "./Root";

registerRoot(KitRoot);
