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

**House style.** If `theme/branding/media-style.md` exists (the course's own `courses/<CODE>/theme/branding/media-style.md` wins
over the project's), read it before producing anything: it is the person's written style for the media of every course, with
measures and positions for each element. What it says about the look and composition (covers, colours, typography, what must **not**
appear) overrides the defaults of this skill for the types it covers; the rest of this skill still applies. If an instruction
cannot be followed (a font that is not available, a type the file does not cover), say so and do the closest thing: never invent
extra elements to fill the gap. It only needs what is in the project: anything it mentions from outside (logos, fonts) is read from
`theme/branding/`, because this session cannot read other folders.

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
5. **Credits.** When an option fixes `model`, `resolution` or `variants` (printed by `media plan` in brackets), use exactly
   those. Generate **one version per image** unless `variants` says more, look at it and generate again only the ones that
   fail; never several versions "to choose from" by default. Before a batch, estimate its cost with the provider's simulator
   when it has one and say it in the summary.
6. Options marked `only: terminal` (VHS, asciinema) are only for assets that show a terminal;
   decide from the placeholder's description.

## Course voice

The whole course uses **one voice**. `coursekit voice list <CODE>` shows the configured
providers and the chosen voice. If there are several and the course has none, **ask the person
which one** (you can generate a sample sentence with each using `--engine`) and set it with
`coursekit voice set <CODE> <provider> [--voice …] [--speaker …]`. Then every voice-over is made
with `coursekit tts --course <CODE> …`. The characters (dialogues, simulations) may have their own voice of the same
provider: propose one per character that fits the story bible (`personality`, `speech`), ask the person, set it with
`coursekit voice set <CODE> <provider> --voice … --character <Name>` and make their lines with `tts --character <Name>`.

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

## 3.1 Simulations (decision-based courses)

`coursekit media extract` adds the images of the simulations (`kind` in the manifest): `BG-…` backgrounds, `LAYER-…` layers
and `CHAR-<NAME>[-<EXPRESSION>]` portraits, with their description and specs. Read `design/story.md` (world, `look` of each
character) and the house style before producing. They must look **high quality and consistent**, never simplistic.

1. **Style.** `coursekit media plan <CODE>` prints the visual style in force (`media › visual › style`: flat, pixel-art, 3d,
   isometric, illustration, photo). Without an image generator it is `visual.fallback` (flat) drawn as SVG, and that drawing is
   for the **illustration role**: the person or the handoff runs `coursekit run produce-media <CODE> --role illustration`. Use
   the reference images in `theme/branding/style/` (or the course's) when there are.
2. **Style sheet first.** Before any image of the simulations, produce in `courses/<CODE>/media/style/` a sample in that style:
   one background of the course, one character of the cast in three expressions (neutral and two the simulations use) and two
   objects as layers. Then **stop**: a person signs it with `coursekit approve style <CODE>` (you cannot);
   `coursekit media set … --status produced` refuses those images until then. Everything after follows the signed sheet.
3. **Backgrounds** (`BG-…`, 1920x1080): the place from the learner's point of view, coherent light and perspective across the
   scenes of the course, free room where the characters and the hotspots go; the objects that can be clicked clearly visible.
4. **Layers** (`LAYER-…`): one object, transparent PNG (or SVG), cropped, in the light and perspective of its background.
5. **Portraits** (`CHAR-…`): the base portrait first (neutral), then each expression **from the base** (image-to-image or the
   provider's reference, or the same SVG drawing with only the face changed), so the person is recognisable in all of them:
   same face, hair, clothes and colours. Transparent background, bust from the waist up.
6. **Never text inside the images** (signs, screens, documents blank or unreadable): the texts are in HTML. No real brands or
   logos, no real people.
7. **Pixel art:** generate at low resolution with a reduced palette and scale up with nearest neighbour; **3d / isometric:** one
   camera and lighting for the whole course; **photo:** consistent people across scenes (same model and seed or reference).
8. **Sizes and SVG, locally and without credits:** `coursekit media fit <CODE> <id> --size 1920x1080` brings a file to
   the size of its specs (scaled and cropped from the centre; never pay a provider to resize); `coursekit media render
   <CODE> <id>` draws an SVG as a PNG next to it, to look at it before marking it `produced` (and the PNG creator needs).
9. **Look at every image** before marking it `produced`: style, consistency with the sheet and with the other images of the
   same character, deformed hands or objects, text that slipped in, contrast with what goes on top. Redo what fails.

**Narration of the scenes** (`VO-…`, simulations with `audio: true`): do not produce them one by one; run
`coursekit media narrate <CODE>` once the voices are set (`coursekit voice`), and it produces and records all of them.

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
   `coursekit media embed <CODE> <id>` wraps it in `media/src/<id>/index.html` with creator's manifest
   `slxd-embed.json` next to it; upload **both files** with `request_embed_upload` (`folderId` = the asset id,
   `relativePath` = `index.html`, `text/html`, and `slxd-embed.json`, `application/json`) and `coursekit media upload`,
   and record the `embedFolderPrefix` as the `--asset-path`. Keep the `.svg` as the
   asset `--file`: the assembly puts an EMBED block where it sees an SVG.
   **A simulation in creator** (`SIM-<id>`, kind `package`, only with the creator backend): once its images are produced,
   `coursekit media embed <CODE> SIM-<id>` builds `media/src/SIM-<id>/` (`index.html`, creator's manifest
   `slxd-embed.json` and `media/` with its images). Upload **every file of the folder** with `request_embed_upload`
   (`folderId` = the asset id, `relativePath` = the path inside the folder: `index.html`, `slxd-embed.json`,
   `media/<file>`), all of them before the folder is written in a brick (creator reads the manifest then), then `coursekit media set <CODE> SIM-<id> --status uploaded --asset-path
   <embedFolderPrefix> --file media/src/SIM-<id>/index.html`. Build and upload it again whenever the simulation or its images
   change.
2. `/assemble <CODE> <N>` replaces each placeholder with its media block.
3. Summarise for the person what was produced and with what, to review it in the preview.
