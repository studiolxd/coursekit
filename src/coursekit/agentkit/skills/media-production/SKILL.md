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
`theme/branding/`, because this session cannot read other folders. It must be signed (the project's guide with
`coursekit approve media-style`, a course's own with `coursekit approve media-style <CODE>`) before a visual resource is marked
produced: when `coursekit media plan` warns that it is not, stop and ask the person to read and sign it; never sign it yourself. Where the guide and `tokens.css` differ, the guide wins; the material behind it is in
`theme/branding/index.md` (fonts in `fonts/fonts.css`, logos in `logo/`, icons, the converted brand pages in `text/`).
Read also the `notes.md` next to the guide (the person's indications the guide was written from): where they and the guide
differ, the notes win; say so in your report, so that the guide is written again.

**An icon the brand's library lacks.** Look for it in the library first (also under other names). If it is not there, draw
it with the rules of the guide for icons (grid, stroke, joins, corners, live area), measured on the icons of the library,
never with another set; save it in `media/files/icons/<name>.svg` and list it in your report under "Icons drawn", so that a
person can add it to the library of the brand.

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
6. Options marked `only: terminal` (VHS, asciinema) are only for assets that show a terminal, and options marked
   `only: decorative` only for decorative images (see **Image** below); decide from the placeholder's description. When a
   limited option does not apply, or gives nothing that fits, go on with the next one.

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
   replace the placeholder with it (`coursekit videos propose <CODE> <address> --why "…" --for <id>`). While it waits for a
   person, and once approved, the resource is not made (the capture and the voice refuse it): go on with the other resources.
   Never put an address in the content yourself.
2. **Real material that a person provides**, in `courses/<CODE>/media/recordings/<id>.mp4` (or `.png` for a capture, `.cast`
   for a terminal demo). If it is there, work from it: for a **video**, the recipe `screen-recording` (Remotion over the real recording: narration with the
   voice of the course, captions, zooms, highlights, the cursor of the recording; nothing of the screen is redrawn), with
   the `Screencast` component of `tools/remotion/src/Screencast.tsx`: its zooms follow what the narration names (`focus` with
   the `word` said and the `event` of `media/recordings/<id>.events.json`, or `fx`/`fy`), with the words of the narration
   (`<audio>.words.json`, written by `coursekit subtitles`); never guess a coordinate when there is an event. **A zoom is
   for a detail** that does not read at full size (a word, an indicator, one line of a change, a single field): never to go
   with every sentence, at most one per scene, and none when what matters is the whole screen or the narration only
   describes what happens; how calm it is and how close it goes come from `coursekit config video` › `screencast`, and
   `coursekit video check` warns of zooms too many or too close; for an
   **image**, the recipe `screenshot` (crop it and mark it with numbers, frames or arrows; never redraw it); for a **GIF**, cut
   and convert the recording with ffmpeg; for a **terminal demo**, the recipe `asciinema` (the person's `.cast` in the EMBED
   package of the player; never retype or rerecord it). Record it with the recipe and `--depicts interface`. When the project captures
   (`coursekit config capture` › `enabled`), first cover the personal data of what the person provided:
   `coursekit capture redact <CODE> <id>` (the original leaves the project), and work from the covered file only after a
   person approved it (`coursekit capture approve`, which you may not run: tell them `coursekit capture review <CODE> <id>`).
3. **A capture you make yourself**, when the tools of the `coursekit-capture` MCP server are available and a person allowed
   it (`coursekit capture allow`; you may not run it, nor `login`): write first the brief of item 4 (its steps and its
   narration: the script a person approves with `coursekit approve script <CODE> --asset <id>`, which you may not run; tell them,
   and go on with the other resources until it is signed) and, in it, a `capture`
   block with where it starts (`start: /path`; for a resource that shows the course itself, the profile `course` and
   `start: unit:N`, its package or its review link) and what must always be hidden (`mask: [{selector: ...}, {text: ...}]`). Then
   `session_start` with the code and the id, follow the steps of the brief looking at each `screenshot` (use `zoom` to read
   small text; `mark`, with a `note`, on the whole box of a detail the narration will name and the shape that fits it
   (`rect`, `round` or `ellipse`): the video zooms only as close as that box fits and draws the mark around all of it; only
   for a detail, as above, and never `point` alone for something larger than a word), `save_shot` when the screen is the one the resource needs (for a video, `record_start` and `record_stop`
   around the steps it shows), and `session_end`. The personal data on screen is already replaced with invented data: never
   try to undo it, never log in or type a password or a code, never leave the application. If a tool says that the
   permission or the session is gone, stop and tell the person what to run. The capture then waits for a person
   (`coursekit capture review` and `approve`; in the handoff, coursekit approves it when your run ends, and you compose it in
   the next one); compose the resource from it only once approved. For a video, after
   `session_end` run `coursekit capture replay <CODE> <id>`: it repeats the steps at the pace of a person and records the
   stretches you marked (if a step is not found, fix the `capture` block of the brief and run it again).

   **In terminal mode** (the permission says `--mode terminal`: a program of the terminal, a command line, an installation)
   the session is a shell of its own in a **stage** of the course, recorded as it goes, with no window of the person. Before
   it, write the stage the brief needs in `courses/<CODE>/media/stages/<name>/`: `stage.yaml` (`title`; `setup`, the
   commands that leave it ready, such as `git init` and a first commit; `home: clean` for a machine as just installed;
   `hide: [<command>]` for a machine without that program; `env`) and `files/`, the project as it starts, with invented
   data only. One stage serves every resource that shows the same project; what a resource needs on top (a file taken away,
   a change already made) goes in `prepare: [...]` of its `capture` block, with `mode: terminal`, `stage: <name>` and, if
   it needs another size, `terminal: {cols, rows}`. The block is a fenced block of its own kind with its keys at the top:
   ```` ```capture ```` on the first line, then `mode: terminal`, `stage: <name>`, `prepare: [...]`, and ```` ``` ````. In the
   handoff coursekit signs the script itself (and again when a session starts): do not wait for a person. Try it with `coursekit capture stage <CODE> <name>` (it mounts it from
   scratch and says where). Then `session_start`: read the screen with `read_screen` (the image with `screenshot` only
   when the look matters), `type` and `key` as a person would, `wait_for` the text that says a program answered (a model
   can take a while), `point_text` on a detail the narration names (the box of its text, or with `until` the lines from it
   to the one with that other text, and the `shape` of its mark; only for a detail), `save_shot` for a capture, `record_start` and
   `record_stop` around what the resource shows (without them, the whole session), and `session_end`: it writes
   `media/recordings/<id>.cast` for a terminal demo (recipe `asciinema`), `<id>.mp4` and its `<id>.events.json` for a
   video, `<id>.png` for a capture. The application is recorded as it is configured on this machine (its theme, its
   colors, its size of text): never change its theme for a recording. There is no replay: if a take goes wrong, start another session (the stage is mounted
   again from scratch). Never type a password, a key or a token, and never print the environment.
4. **Nothing of the above exists yet: do not produce it.** Write the **brief for the person** in
   `courses/<CODE>/media/scripts/<id>.md` and leave the asset waiting:
   `coursekit media set <CODE> <id> --status scripted --recipe screen-recording|screenshot|asciinema --depicts interface`.
   The brief says: what the resource teaches; the exact account, application and version to use (as it is configured: never
   ask for another theme or other colors); the steps in order (what to
   click or type, what must be on screen at each moment, with the labels as the application shows them); how long each one
   takes; the narration, sentence by sentence, ready to be spoken over the recording; the file name and format to deliver
   (`media/recordings/<id>.mp4`, 1920 × 1080, no personal data on screen; for a terminal demo `media/recordings/<id>.cast`) and, for a video, what to highlight and where to
   zoom. Never mark it `produced`. The handoff does not stop for it: the course is assembled with the placeholder showing,
   and the final report lists every resource that waits for a person.

If you doubt whether a resource shows a real interface, it does: classify it `interface`.

## Course voice

The whole course uses **one voice**: its own, or the one of the project, which every course without its own inherits.
`coursekit voice list <CODE>` shows the configured providers and the voice in force (and whether it is the project's). If
there are several and neither the course nor the project has one, **ask the person which one** (you can generate a sample
sentence with each using `--engine`) and whether it is for the whole project (`coursekit voice set <provider> [--voice …]`)
or for this course alone (`coursekit voice set <CODE> <provider> [--voice …] [--speaker …]`). Then every voice-over is made
with `coursekit tts --course <CODE> …`. The characters (dialogues, simulations) may have their own voice of the same
provider: propose one per character that fits the story bible (`personality`, `speech`), ask the person, set it with
`coursekit voice set <CODE> <provider> --voice … --character <Name>` and make their lines with `tts --character <Name>`.

**Gemini batch.** With the Gemini voice, the person may want the narrations of the course in batch (half the price, the
audio in hours): ask once, before the first narration, unless the person already said. If so, add `--batch` to
`coursekit video voice`, `coursekit media narrate` and `coursekit tts --course <CODE>`: they queue instead of voicing.
Then run `coursekit tts-batch send <CODE>` once, at the end, and go on with everything that does not need that audio
(images, scripts, other assets). Do not wait for it, do not send twice, and do not mark as produced what is still in the
queue: `coursekit tts-batch collect <CODE>` (the person, or the handoff, later) writes it, and then you finish the render
or the upload of what depended on it. `coursekit tts-batch list <CODE>` shows what is queued.

## 2. Script before producing (video, audio, GIF, demo)

Write the script in `media/scripts/<id>.md` (voice-over word by word, scenes or terminal steps,
estimated duration; any screen of a real application comes from a real run or a real recording, with its version, never from the
documentation: see 1.1) and mark the asset `scripted` (`coursekit media set <CODE> <id> --status scripted`).
**Voice and screen do not repeat each other** (cognitive load): the voice explains, the screen shows (a diagram, a few key
words, the step on the real interface); never a paragraph on screen that the voice reads aloud. Each scene, one idea.
For videos and voice-overs, **show the script to the person before producing** if it spends
credits.

## 3. Production by type

- **An image with points** (`points` in the manifest: the points of a `:::labelled-graphic` that names it, or the hotspots
  with an `area` of a simulation on that background) — draw it so that what each point names is clearly visible and has room
  for its marker. Once it is produced, `coursekit media anchors <CODE> <id>` draws a numbered crosshair on the image where each
  point goes, from the content, and records them: they stay in the final image, so whoever reviews it sees where each point
  will be. A point without a position: look at the image and give it one, `--set "<point>=x,y"` (in % of the image, from the
  top left corner), which writes it in the content too. Check that every crosshair falls on what its point names; if not, move
  it the same way (a hotspot: its `area` in the content, then `anchors` again). Draw the crosshairs before exporting an SVG to
  PNG (`coursekit media render`) and before uploading; `coursekit verify` fails when a point moved and the image was not drawn
  again.

- **Job aid (`job_aid`)** — a checklist or a quick guide the learner downloads as a PDF. Its text is the body of the
  placeholder, written and reviewed with the unit: never write, add or change its content; if it is wrong or missing, say so
  for the writer. `coursekit media render <CODE> <id>` lays it out with the template of the theme
  (`theme/templates/job-aid.html`, or the one of coursekit) and prints `media/<id>.pdf`; open it, check that nothing is cut
  or overflows, and record it with the command it prints (`--status produced --recipe agent-html-pdf --file …`). The look is
  the template's, never fixed by hand in one PDF: what has to change for every job aid is a change of the template (the theme
  step). Creator: upload it to the content of its unit with `request_asset_upload` of kind `attachment` and record its
  `--asset-path`; the assembly puts the download in place of the placeholder.

- **Portrait of a character (`CHAR-<NAME>`)** — `coursekit media extract` adds one image per character that speaks in a
  dialogue: never leave a character with an initial or without a face. Square 512x512 px, centred bust, plain background in a colour
  of the theme palette (not the same for the two characters of a dialogue), the same style for every character of the course:
  a flat illustration drawn as SVG and exported to PNG, an image generated with the configured provider, or a licensed photograph of a
  person (`search_stock_images`). Alt text describes the person briefly («Retrato ilustrado de Marta, responsable de proyecto»).
  Once uploaded (step 4), the assembly puts it in the dialogue as the avatar of the character.
- **Image** — first decide what it is, from its description and the text around it:
  - **Decorative**: it explains nothing but conveys the concept of its paragraph (a place, people at work, an object that
    says the idea; never a generic picture that could go anywhere). Search the licensed catalog first (`search_stock_images` + `import_stock_image`): no credits. Take a result only
    if it fits the visual style of the course (`visual.style`) and the other images of the unit (one stock photograph
    among illustrations stands out), shows nothing that contradicts the text and, when it shows people, varied people. If
    nothing fits, generate it as a necessary one.
  - **Necessary**: it shows something specific of the content. The style guide says how each kind of illustration looks;
    the script of the resource says which kind it is (the guide of a course can add kinds):
    - a **concept illustration** goes with a concept of the content and reinforces it. When the brand has illustration
      sources (`coursekit media plan` offers `magnific-stock`), look there first: `coursekit media stock <CODE> <id> --find
      "<terms in English>"` lists illustrations of those sources as SVG; look at their previews, take the one that tells
      the concept with `--take <resource id>` (it comes recoloured to the ink and the paper of the brand, and the manifest
      records where it comes from) and add by hand only what the script asks for (the accent on one element, for example).
      A colour version is refused: take the line version of the same concept. When nothing fits, combine elements of
      several or generate it in the same style, with the previews of `theme/branding/style/` as reference;
    - a **scene** (a simulation, a story) has characters who look the same in every image: generate it with the configured
      provider in the style of the guide, or draw it as SVG without a generator. When the brand has reference scenes
      (`theme/branding/style/scenes/` or the course's), follow the method of 3.1: a model sheet per character, the closest
      reference scene as a style reference, a simple composition, edits one at a time and a look at the hands;
    - a **diagram** is a resource of its own type (`diagram`), drawn as SVG with the tokens.
    Generated images: prompt from the description and specifications, sober and coherent style, no embedded text.
  - The portraits of characters and the images of the simulations are never decorative: they follow their own rules
    (above, and the style sheet of the simulations).
  Record in the manifest the recipe actually used (`creator-stock` or the generator).
- **Illustration (`illustration`)** — a concept illustration, in the line of the reference illustrations of the brand
  (`theme/branding/style/`): the illustration sources of the brand first (`coursekit media stock <CODE> <id> --find`, as a
  concept illustration of the image above), else generated in that style with the previews as reference, else drawn as
  SVG with the theme colours and exported to PNG. It tells the idea its description names; never a generic picture.
- **Icon (`icon`)** — one idea in one sign, large: the icon of the library of the brand that says it (also under other
  names), or one of the catalogue of creator (`search_stock_icons`) in the line of the brand, or one you draw with the rules
  of the guide for icons (above). Place it large, centred, in the theme colours, on a soft shape of the accent with room
  around it, and export it as PNG (`media/src/<id>.svg` as the source); the alt text says the idea, not "icon of".
- **Infographic, Diagram** — SVG written by you, with the colours and fonts of `tokens.json`,
  real text in {{language_name}}, `<title>` and `<desc>` for accessibility, readable at 1280 px.
  If the learner should keep it, also a PDF (`media set --download`). With the creator backend the
  platform accepts only PNG, JPEG, WebP and GIF as an image: keep the SVG as the source in
  `media/src/` and export a PNG (a Remotion still, or any renderer available) as the asset `--file`.
- **Animated GIF** — if it shows a terminal, VHS (`media/src/<id>.tape`, light theme; relative
  or quoted `Output` path). Otherwise animated SVG (`media/files/<id>.svg`) or a short Remotion
  composition exported to GIF. Creator rejects SVG as an image: an animated SVG goes up as an EMBED
  package, see step 4.
- **Interactive terminal demo** — asciinema recording of the script's commands (when it shows a real application, the
  `.cast` of `media/recordings/`, from a person or a terminal capture) and an EMBED
  package (`media/src/<id>/index.html` with the player and `tokens.css`).
- **Video** — a **montage** first (recipe `montage`, `coursekit video`): the video as data in
  `media/scripts/<id>.video.yaml`, scenes one after another, each with its `type`, its `props` and what it `says`; each lasts
  what its voice lasts, in the theme of the course. The order of decision for each scene:
  1. a scene that exists tells the idea well: use it (`coursekit video catalog <CODE>` lists the scenes of the library, of
     the project and of the course, their props, their limits and what each one is built from; `coursekit video gallery
     <CODE>` draws them in the theme of the course, in a page you can look at). It lists only what the brand allows
     (`config/video.yaml › scenes`): the values of each prop and its default; a scene it leaves out is not used, and
     `coursekit video check` refuses a value it does not allow;
  2. none does: **create one**, composed from the atoms and molecules of the library (`Heading`, `Text`, `Enter`, `Stagger`,
     `Underline`, `Counter`, `MediaSlot`, `Ring`, `Background`, `Card`, `Badge`, `Arrow`, `TitleBlock`, `BulletList`,
     `StatBlock`, `CompareColumn`, `StepNode`, `ScreenRecording`;
     read the scenes of `tools/remotion/kit/scenes/` to see how they are put together). A scene is a folder with
     `index.tsx` (`export default` a component that receives `{props}`, importing from `"../../../kit"`) and `scene.yaml`
     (`description`, `built_from`, its `props` with `type`, `required`, `max_chars`, `on_screen`, `label`, and an
     `example:` with props to draw it in the gallery, one block per language: `en:`, `es:`). It goes in
     `tools/remotion/src/scenes/<name>/` when other courses can use it, or in `courses/<CODE>/video/scenes/<name>/` when it
     only makes sense in this course; the same name hides the scene of the library (or of the project);
  3. an atom is missing: write it inside your scene, with the same rules.
  Over a scene, a **layer** enters when its words are said (`layers: [{type, props, at: "…", until: "…"}]`: `lower-third`,
  `callout`, `highlight`, or one you create the same way, in `src/layers/<name>/` or `video/layers/<name>/` with `layer.yaml`).
  The look of every video comes from the theme and from `coursekit config video` (motion, background, logo): do not
  hard-code colours or timings. When the project wants a piece of the library to look different everywhere (its headings,
  its cards), write it in `tools/remotion/src/atoms/<Name>.tsx` (or `molecules/`) from the file of `tools/remotion/kit/`,
  with the same name and props, instead of changing scene by scene.
  Vary the scenes (do not chain the same one), keep the text on screen short (what is left over goes to the narration) and
  give each item, step or column the words that name it (`say`), so it enters when it is said.
  The library is a starting point, not a limit: if the idea asks for another visual (a diagram that builds itself, a
  timeline, a before and after), create it. The rules of every scene: everything moves with the frame
  (`useCurrentFrame`, no CSS animations or timers); colours and fonts only from the theme (`useColor`, `useTheme`); what
  enters with a word enters when the narration says it (`useAt("…")`); media by their path in the media folder of the
  course; nothing from the network. Never edit `tools/remotion/kit/` (coursekit writes it). The montage is the script of the
  video: a person approves it (`coursekit approve script <CODE> --asset <id>`, which you may not run) before its voice; if you
  change its texts after, it is approved again. The steps:
  `coursekit video new <CODE> <id>`, fill it, `coursekit video check <CODE> <id>` until it passes, `coursekit video voice`,
  `coursekit video preview` (open the image it prints and look at every scene), `coursekit video render`, which leaves the
  video, its captions, its words and its accessible transcript and marks it `produced`. A video made by hand as a Remotion
  composition (recipe `remotion`) is still fine when a montage cannot tell it. When a person wants to retouch a video by
  hand, `coursekit video export <CODE> <id>` leaves its pieces and its timeline for DaVinci Resolve, Final Cut or Premiere.
- **Video made by hand** — Remotion composition with the script's scenes, diagrams and tokens; voice-over with
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
   With a generator and reference scenes (`style/scenes/`), each image follows this method:
   - **Model sheet per character**: front, side and back views, full body, on white, generated with a reference scene as
     the style. Check that clothes and details match in every view before using it.
   - **References**: the model sheets of the characters that appear as image references, and the reference scene closest to
     the case (inside or outside, with or without children) as the style reference. A whole scene goes only as a style
     reference, never as an image reference: as an image, the model copies it.
   - **Simple composition**: people facing each other, at either side of a table, standing or seated. A complex arrangement
     (someone behind a counter while another person sits under a lower section of it) the models do not resolve: rethink it.
   - **Edits one at a time, on the whole image**, never with a mask over a character: an object or the background with an
     edit model that keeps the framing; hands and fine details with a model that redraws them without touching the rest. An
     edit does not change the geometry of what is hidden: regenerate instead.
   - **Finish** with a subtle creative upscale for illustration, which cleans and sharpens the line.
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
9. **Look at every image** before marking it `produced`, the hands up close (five fingers each, no merged hands) and the details
   that give away a real place (a famous skyscraper, a colour outside the palette): style, consistency with the sheet and with the other images of the
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
   **A portrait the dialogues of several units show** (`dialogue_units` in the manifest): creator shows an image only in
   the content it was uploaded to, so upload it to the content of each of those units and record each other one with
   `coursekit media set <CODE> <id> --unit N --asset-path <path>`. `coursekit media plan` lists the units still missing it.
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
