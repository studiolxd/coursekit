import React from "react";
import { Underline } from "./Underline";
import { useAt } from "../timing";

// A text with one of its words (`stress`) underlined when the narration says it (from frame `after` if it is never said): the
// same stress in every scene that has one, a quote, a key phrase.

export const Stressed: React.FC<{ text: string; stress?: string; after?: number }> = ({ text, stress, after = 24 }) => {
  const at = useAt(stress, after);
  const i = stress ? text.toLowerCase().indexOf(stress.toLowerCase()) : -1;
  if (i < 0) return <>{text}</>;
  const end = i + stress!.length;
  return <>{text.slice(0, i)}<Underline at={at}>{text.slice(i, end)}</Underline>{text.slice(end)}</>;
};
