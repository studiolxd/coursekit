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

## 1.1 What a resource shows: the interface of a real application is never invented

Before producing a resource of the types in `media › depicts › required_for` (image, infographic, diagram, GIF, video), decide
what it shows and record it: `coursekit media set <CODE> <id> --depicts interface|concept`.

- **`concept`**: an idea, a process, a diagram, a scene, a person. You may draw it, generate it or animate it.
- **`interface`**: the screen of a real application, platform, program, website or app (a tutorial of how to use it, "click
  here", a menu, a dialog, a chat window). **You never draw, recreate, imitate or "approximate" it**, with SVG, with
  Remotion, with a generator or any other way, not even schematically, not even with fictional names or a note saying it is
  a recreation: a learner would take it for the real thing and look for buttons that are not there or are named otherwise.
  `coursekit media plan` offers only real material for it and `coursekit media set --status produced` refuses a generated
  recipe. The decision-based simulations (`:::scenario`, `:::conversation`) are the only place where an invented interface is
  fine: there the application is fictional and the course says so.

What you may do with an `interface` resource, in this order:

1. **A video of an official channel** (the producer of the application): it is not an asset to produce but an address in the
   content (`coursekit videos`, see the writing skill), which you cannot change. Look for it (`WebSearch`, `WebFetch`) among the
   channels of `rules › forbidden › allow_channels` (`coursekit config rules --course <CODE>`) and the official site of the
   application, and write in the brief of the resource the candidates you find: address, channel, why it is official (the
   official page that links to it), what it shows and whether it covers the same steps, so that the writer or a person can
   replace the placeholder with it (`coursekit videos propose`). Never put an address in the content yourself.
2. **Real material that a person provides**, in `courses/<CODE>/media/recordings/<id>.mp4` (or `.png` for a capture). If it is
   there, work from it: for a **video**, the recipe `screen-recording` (Remotion over the real recording: narration with the
   voice of the course, captions, zooms, highlights, the cursor of the recording; nothing of the screen is redrawn), with
   the `Screencast` component of `tools/remotion/src/Screencast.tsx`: its zooms follow what the narration names (`focus` with
   the `word` said and the `event` of `media/recordings/<id>.events.json`, or `fx`/`fy`), with the words of the narration
   (`<audio>.words.json`, written by `coursekit subtitles`); never guess a coordinate when there is an event; for an
   **image**, the recipe `screenshot` (crop it and mark it with numbers, frames or arrows; never redraw it); for a **GIF**, cut
   and convert the recording with ffmpeg. Record it with the recipe and `--depicts interface`. When the project captures
   (`coursekit config capture` › `enabled`), first cover the personal data of what the person provided:
   `coursekit capture redact <CODE> <id>` (the original leaves the project), and work from the covered file only after a
   person approved it (`coursekit capture approve`, which you may not run: tell them `coursekit capture review <CODE> <id>`).
3. **A capture you make yourself**, when the tools of the `coursekit-capture` MCP server are available and a person allowed
   it (`coursekit capture allow`; you may not run it, nor `login`): write first the brief of item 4 and, in it, a `capture`
   block with where it starts (`start: /path`; for a resource that shows the course itself, the profile `course` and
   `start: unit:N`, its package or its review link) and what must always be hidden (`mask: [{selector: ...}, {text: ...}]`). Then
   `session_start` with the code and the id, follow the steps of the brief looking at each `screenshot` (use `zoom` to read
   small text; `point`, with a `note`, on each thing the narration will name, so the video can zoom there), `save_shot` when the screen is the one the resource needs (for a video, `record_start` and `record_stop`
   around the steps it shows), and `session_end`. The personal data on screen is already replaced with invented data: never
   try to undo it, never log in or type a password or a code, never leave the application. If a tool says that the
   permission or the session is gone, stop and tell the person what to run. The capture then waits for a person
   (`coursekit capture review` and `approve`); compose the resource from it only once approved. For a video, after
   `session_end` run `coursekit capture replay <CODE> <id>`: it repeats the steps at the pace of a person and records the
   stretches you marked (if a step is not found, fix the `capture` block of the brief and run it again).
4. **Nothing of the above exists yet: do not produce it.** Write the **brief for the person** in
   `courses/<CODE>/media/scripts/<id>.md` and leave the asset waiting:
   `coursekit media set <CODE> <id> --status scripted --recipe screen-recording|screenshot --depicts interface`.
   The brief says: what the resource teaches; the exact account, application and version to use; the steps in order (what to
   click or type, what must be on screen at each moment, with the labels as the application shows them); how long each one
   takes; the narration, sentence by sentence, ready to be spoken over the recording; the file name and format to deliver
   (`media/recordings/<id>.mp4`, 1920 × 1080, no personal data on screen) and, for a video, what to highlight and where to
   zoom. Never mark it `produced`. The handoff does not stop for it: the course is assembled with the placeholder showing,
   and the final report lists every resource that waits for a person.

If you doubt whether a resource shows a real interface, it does: classify it `interface`.

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
estimated duration; any screen of a real application comes from a real run or a real recording, with its version, never from the
documentation: see 1.1) and mark the asset `scripted` (`coursekit media set <CODE> <id> --status scripted`).
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
  `coursekit tts`; captions (`.vtt`) always. Describe its scenes in `media/scripts/<id>.scenes.yaml` (the `text` on screen,
  what it `shows`, what it `says`): what matters on screen is also said. Look at the render with
  `coursekit media sheet <CODE> <id>` (open the image it prints) instead of guessing, and once it is produced,
  `coursekit media transcript <CODE> <id>` writes its accessible transcript and its track of descriptions.
- **Audio** — `coursekit tts --course <CODE> …` with the course voice; keep the transcript.

After producing audios and videos, `coursekit media check <CODE>`: loudness, captions too fast to read and what is on screen
and not said (the limits are those of `media › checks`). Fix what it reports (`--fix` for the loudness; split the captions or
shorten the text; say what is missing or describe it with `shows`) and run it again until it passes.
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
   Before uploading to creator, run `coursekit media optimize <CODE>`: it scales down and recompresses images and re-encodes
   MP4 videos in place (the html backend does it by itself when it builds the package).
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
