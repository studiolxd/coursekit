import React from "react";
import { ScreenRecording, type Focus, type ScreenEvent } from "../../atoms/ScreenRecording";
import type { SceneProps } from "../../contract";

// A real screen recording (recipe screen-recording) with zooms that follow what the narration names. `events` are those of
// recordings/<id>.events.json (coursekit puts them in when `recording` has its events file).
export type ScreencastProps = { recording: string; events?: ScreenEvent[]; focus?: Focus[]; start?: number; scale?: number; ring?: boolean };

export default function Screencast({ props }: SceneProps<ScreencastProps>) {
  return <ScreenRecording src={props.recording} events={props.events} focus={props.focus} startFrom={props.start ?? 0}
    scale={props.scale} ring={props.ring ?? true} />;
}
