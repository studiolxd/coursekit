// The interactions as each SCORM standard admits them (used by scorm.js; no dependencies, so it can be tested alone).
const letter = (n) => (n < 26 ? String.fromCharCode(97 + n) : String(n - 26));  // a-z, then 0-9: the options of a choice

// An interaction as the standard asks: in 1.2 a wrong answer is `wrong` and the options of a choice are single characters
// separated by commas; in 2004 it is `incorrect` and they are separated by `[,]`. `choices` (positions of the options
// chosen) or `choice` (one position) become that response; the text goes to `description` (only 2004 keeps it).
export function conform(entry, standard) {
  const out = { ...entry };
  const picked = entry.choices !== undefined ? entry.choices : entry.choice !== undefined ? [entry.choice] : null;
  delete out.choices;
  delete out.choice;
  if (picked) out.learnerResponse = picked.map(letter).join(standard === "2004" ? "[,]" : ",");
  if (out.result === "incorrect" && standard !== "2004") out.result = "wrong";
  if (out.result === "wrong" && standard === "2004") out.result = "incorrect";
  return out;
}
