---
name: media-production
description: Production and upload of a course's media assets (images, diagrams, infographics, GIFs, terminal demos, simulations, video, audio) with the available providers. Use with /produce-media or to produce or redo the assets of courses/<CODE>.
---

# Media production

Providers and order of preference: `coursekit config media`. Design tokens: `theme/tokens.json`
and `theme/tokens.css` of the project (`coursekit theme tokens` derives them from the theme).

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

- **Image** — generated with the configured provider (prompt from the description and
  specifications, sober and coherent style, no embedded text) or licensed stock
  (`search_stock_images` + `import_stock_image`).
- **Infographic, Diagram** — SVG written by you, with the colours and fonts of `tokens.json`,
  real text in {{language_name}}, `<title>` and `<desc>` for accessibility, readable at 1280 px.
  If the learner should keep it, also a PDF (`media set --download`).
- **Animated GIF** — if it shows a terminal, VHS (`media/src/<id>.tape`, light theme; relative
  or quoted `Output` path). Otherwise animated SVG or a short Remotion composition.
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
1. Upload to the unit's content: `request_asset_upload` (image, video, audio) or
   `request_embed_upload` (simulations and demos); upload the file with the `curlCommand` it
   returns and keep the `path` / `embedFolderPrefix`:
   `coursekit media set <CODE> <id> --status uploaded --asset-path <path>`.
2. `/assemble <CODE> <N>` replaces each placeholder with its media block.
3. Summarise for the person what was produced and with what, to review it in the preview.
