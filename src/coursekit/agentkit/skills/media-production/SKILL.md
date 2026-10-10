---
name: media-production
description: Production and upload of a course's media assets (images, diagrams, infographics, GIFs, terminal demos, simulations, video, audio) with the available providers. Use with /produce-media or to produce or redo the assets of courses/<CODE>.
---

# Media production

Providers and order of preference: `coursekit config media`. Design tokens: `coursekit theme show --course <CODE>` says
which ones the course uses (its own `courses/<CODE>/theme/`, else the project's `theme/`) and where they come
from; `tokens.json` and `tokens.css` are next to each other. They are derived from the theme of the platform with
`/define-theme`: if there are none, or they were written by hand, stop and tell the person to run it; never
write or edit tokens yourself. Infographics, diagrams, GIFs, simulations and videos need them: `coursekit media
set … --status produced` refuses without them. The Remotion template reads `theme/tokens.json`; for a course with
its own tokens, point the composition at `courses/<CODE>/theme/tokens.json`.

{{> _slxd-tools}}

## 1. Inventory and plan

1. `coursekit media extract <CODE>`: syncs `media/manifest.yaml` with the placeholders. A
   placeholder changed in the `.md` goes back to `pending`.
2. `coursekit media plan <CODE>`: for each pending asset, the available options in order. Use
   **the first one you can really run** (those marked "if the agent has the MCP tool" only if you
   have that tool in this session). If none works, say so and go on.
3. API keys are in the project `.env`: read them only to call the API, never write them in files
   or in the output.
4. If an option needs something not installed (`coursekit doctor`), **do not install it**: ask
   the person to run `coursekit setup --media` and go on with the next option.
5. Options marked `only: terminal` (VHS, asciinema) are only for assets that show a terminal;
   decide from the placeholder's description.

## Course voice

The whole course uses **one voice**. `coursekit voice list <CODE>` shows the configured
providers and the chosen voice. If there are several and the course has none, **ask the person
which one** (you can generate a sample sentence with each using `--engine`) and set it with
`coursekit voice set <CODE> <provider> [--voice …] [--speaker …]`. Then every voice-over is made
with `coursekit tts --course <CODE> …`.

## 2. Script before producing (video, audio, GIF, demo)

Write the script in `media/scripts/<id>.md` (voice-over word by word, scenes or terminal steps,
estimated duration; say which screens come from a real run, with the version, and which from the
documentation) and mark the asset `scripted` (`coursekit media set <CODE> <id> --status scripted`).
For videos and voice-overs, **show the script to the person before producing** if it spends
credits.

## 3. Production by type

- **Portrait of a character (`CHAR-<NAME>`)** — `coursekit media extract` adds one image per character that speaks in a
  dialogue: never leave a character with an initial or without a face. Square 512x512 px, centred bust, plain background in a colour
  of the theme palette (not the same for the two characters of a dialogue), the same style for every character of the course:
  a flat illustration drawn as SVG and exported to PNG, an image generated with the configured provider, or a licensed photograph of a
  person (`search_stock_images`). Alt text describes the person briefly («Retrato ilustrado de Marta, responsable de proyecto»).
  Once uploaded (step 4), the assembly puts it in the dialogue as the avatar of the character.
- **Image** — generated with the configured provider (prompt from the description and
  specifications, sober and coherent style, no embedded text) or licensed stock
  (`search_stock_images` + `import_stock_image`).
- **Infographic, Diagram** — SVG written by you, with the colours and fonts of `tokens.json`,
  real text in {{language_name}}, `<title>` and `<desc>` for accessibility, readable at 1280 px.
  If the learner should keep it, also a PDF (`media set --download`). With the creator backend the
  platform accepts only PNG, JPEG, WebP and GIF as an image: keep the SVG as the source in
  `media/src/` and export a PNG (a Remotion still, or any renderer available) as the asset `--file`.
- **Animated GIF** — if it shows a terminal, VHS (`media/src/<id>.tape`, light theme; relative
  or quoted `Output` path). Otherwise animated SVG (`media/files/<id>.svg`) or a short Remotion
  composition exported to GIF. Creator rejects SVG as an image: an animated SVG goes up as an EMBED
  package, see step 4.
- **Interactive terminal demo** — asciinema recording of the script's commands and an EMBED
  package (`media/src/<id>/index.html` with the player and `tokens.css`).
- **Video** — Remotion composition with the script's scenes, diagrams and tokens; voice-over with
  `coursekit tts`; captions (`.vtt`) always.
- **Audio** — `coursekit tts --course <CODE> …` with the course voice; keep the transcript.
- **Interactive simulation** — self-contained package in `media/src/<id>/` (`index.html` + JS
  without external dependencies) that imports `tokens.css`; keyboard, `aria-*`, visible focus,
  no emojis, text in {{language_name}}, works from `file://`.

Produced files go to `media/files/<id>.<ext>` and become `produced`
(`coursekit media set <CODE> <id> --status produced --recipe <option> --file media/files/… --alt "…"`).
Alt text is mandatory for images and captions for every video.

## 4. Upload

Assets are **not approved one by one**: they are validated in the assembled course (preview).
1. Upload to the unit's content, which exists once `/assemble` has created it (`content_id` of the unit in `course.yaml`):
   until then leave the assets `produced`; after `/assemble`, upload them and run `/assemble` again, which puts each one in place
   of its placeholder. `request_asset_upload` (image, video, audio, subtitles) or `request_embed_upload` (simulations and demos,
   one request per file of the package, all with the same `folderId`) return an `uploadUrl`. Send the file with
   `coursekit media upload <CODE> --file <file> --url "<uploadUrl>" --content-type <MIME>` (the same MIME type the upload was
   requested with); do not use `curl`, a session without an interface cannot run it. Keep the `path` / `embedFolderPrefix`:
   `coursekit media set <CODE> <id> --status uploaded --asset-path <path>`.
   An SVG (animated, or any one you cannot export to PNG) goes up as an EMBED package:
   `coursekit media embed <CODE> <id>` wraps it in `media/src/<id>/index.html`; upload that file with
   `request_embed_upload` (`folderId` = the asset id, `relativePath` = `index.html`, `text/html`) and
   `coursekit media upload`, and record the `embedFolderPrefix` as the `--asset-path`. Keep the `.svg` as the
   asset `--file`: the assembly puts an EMBED block where it sees an SVG.
2. `/assemble <CODE> <N>` replaces each placeholder with its media block.
3. Summarise for the person what was produced and with what, to review it in the preview.
