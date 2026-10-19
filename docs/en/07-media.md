# Media production

How media placeholders become produced assets: the manifest, the production options, voice-over and captions, the theme tokens and the tools each type needs.

## Placeholders and types

A media placeholder is written in `content.md` (format in [06-content.md](06-content.md#media-placeholders)). Its type is one of nine resource types. Each type has an English **id**, the same in every course, which is what the configuration (`config/media.yaml › types` and `uses_theme`, `config/rules.yaml › content.placeholder_types`), the media manifest (`media/manifest.yaml › assets[].type`), the output of `coursekit media plan` and the theme guard use. What the author **writes** in the placeholder is the word of the course language for that type (for example `Infographic` in an English course and `Infografía` in a Spanish one); the table that maps each id to its words is in [06-content.md](06-content.md#media-placeholders). The word of the other language is a `coursekit verify` error that lists the valid words.

| Id | Meaning | Options, in order of preference (what each one needs) |
|---|---|---|
| `image` | Image | `creator-stock` (agent MCP tool `search_stock_images`; only decorative images) · `magnific-stock` (`MAGNIFIC_API_KEY` and illustration sources; only concept illustrations) · `magnific-api` (`MAGNIFIC_API_KEY`) · `magnific-mcp` (agent MCP tool `images_generate`) · `agent-svg` (nothing) · `creator-stock` (any image) · `screenshot` (only a real interface: a capture from a person) |
| `infographic` | Infographic | `agent-svg` (nothing) · `magnific-api` |
| `diagram` | Diagram | `agent-svg` |
| `animated_gif` | Animated GIF | `vhs` (command `vhs`; terminal content only) · `agent-svg-animated` (nothing; with the creator backend it goes up as an EMBED package, see [Upload](#upload-to-creator)) · `remotion-gif` (`node` and `tools/remotion/node_modules`) |
| `terminal_demo` | Interactive terminal demo | `asciinema` (command `asciinema`; terminal content only) · `vhs` (video alternative; terminal content only) |
| `video` | Video | `remotion` (`node` and `tools/remotion/node_modules`) · `vhs` (terminal content only) |
| `audio` | Audio | `voice` (nothing): the voice chain below |
| `simulation` | Interactive simulation | `agent-html` (nothing): self-contained HTML/JS that uses `tokens.css` |
| `job_aid` | Job aid | `agent-html-pdf` (a Chrome, Chromium or Edge): its text with the template of the theme, printed to PDF ([Job aids](#job-aids)) |

"Nothing" means the agent produces it itself. The agent uses the first option it can actually run and records it in the manifest. The option descriptions that `coursekit media plan` prints come from the configuration and are written in English; a project can write its own in `config/media.yaml`.

## The media manifest

`courses/PWD/media/manifest.yaml` has one entry per placeholder. Every asset has an id `U<unit>-S<section>-M<k>`, where `k` is the position of the placeholder inside its section (`U1-S2-M1` is the first placeholder of section 2 of unit 1). Assemble uses the same ids to swap a placeholder for its produced media. The `type` of each entry is the id of the type (`image`, `infographic`…), whatever the language of the course. Ids are positional: adding a placeholder before another renumbers the ones after it.

| Command | What it does |
|---|---|
| `coursekit media extract CODE` | Syncs the manifest with the placeholders of every `content.md` and prints `manifest: 3 assets (pending 3)` |
| `coursekit media plan CODE` | For every `pending` or `scripted` asset, lists the options available on this machine |
| `coursekit media providers` | Lists every option of every type, voice and subtitles with its availability (`available`, `missing`, `agent MCP`) |
| `coursekit media set CODE ID …` | Updates an asset (used by the media agent while producing) |

`extract` rules: a new placeholder is added as `pending`; an existing one keeps its progress, unless its type, title, description or specifications changed, in which case it goes back to `pending` with a note; an asset whose placeholder disappeared is kept with status `orphaned`, and it stays `orphaned` (also if the placeholder comes back unchanged) until its type, title, description or specifications change, which sends it back to `pending`.

`media set` takes `--status`, `--recipe` (option used), `--file`, `--asset-path` (path in the platform), `--alt`, `--transcript`, `--subtitles-path` and `--made-with`, and `--force` (see [The media guard](#the-media-guard)). For a downloadable companion file (for example a PDF) use `--download FILE`, plus `--download-title` and `--download-asset-path`. When the specifications of a produced asset mention a download (`pdf`, `download`, `docx`, `xlsx`, `pptx`…) and none is registered, `media plan` warns. With the creator backend it also warns when the asset is `uploaded` and a registered download has no `--download-asset-path` yet (upload it with `request_asset_upload`, kind `attachment`).

With the creator backend an image is shown only by the content it was uploaded to. A character's portrait is one asset in the whole course, and the dialogues of several units may show it (`dialogue_units` in the manifest): upload it to the content of each of those units and record each path with `--unit N --asset-path <path>` (without `--unit`, the path is the one of the content of the asset's unit). `media plan` warns of the units whose content still lacks it, and the assembly of such a unit leaves the dialogue without that portrait (the initial) and says so, instead of pointing to the content of another unit.

Several agents can produce media of the same course at once: every command that writes the manifest (`extract`, `set`, `redo`, `stock`, `narrate`, `transcript`, `tts-batch collect`, the captures) locks it from the moment it reads it until it has written it (the file `media/.manifest.lock`, which the `.gitignore` of the project leaves out) and writes it whole in one step, so no agent loses what another wrote and nobody reads it half written. The ones that take long (voicing, downloading) read it again at the end and only lock it to write. A command that waits more than two minutes for the lock stops with a message: wait for the other one to finish and run it again. `media render` is just as careful with the browser: each attempt has a profile of its own and a time limit, the PNG is cropped to its exact size, and a failed or incomplete attempt is repeated, up to three.

### Fields of an entry

The files of the media of a course are in `courses/PWD/media/`: `manifest.yaml`, `scripts/` (the scripts), `files/` (the produced files) and `src/` (the sources: `.tape` scripts and the packages of simulations and demos). Each entry of `manifest.yaml` has these fields:

| Field | Content |
|---|---|
| `id`, `unit`, `section`, `type` | The id of the asset, its unit and section numbers, and the id of its type |
| `title`, `description`, `how`, `specs` | The fields of the placeholder as written in the content: title, description, how it is made and specifications |
| `status` | One of the statuses below, or `orphaned` |
| `note` | Why `extract` sent the asset back to `pending` |
| `recipe`, `made_with` | The option used and the tool or model that produced the asset (`--recipe`, `--made-with`) |
| `file`, `alt`, `transcript`, `subtitles_path` | The produced file and its alternative text, transcript and captions (`--file`, `--alt`, `--transcript`, `--subtitles-path`) |
| `asset_path` | The path of the asset in the platform once uploaded (`--asset-path`), in the content of its unit |
| `uploads` | Creator: the paths of the copies uploaded to the content of other units (`--unit N --asset-path`), by content id |
| `dialogue_units` | A portrait: the units whose dialogues show it |
| `downloads` | The downloadable files: `file`, `title`, `asset_path` and `size` of each one |
| `theme` | The fingerprint of the theme tokens the asset was made with ([The media guard](#the-media-guard)) |
| `depicts` | What the asset shows: `interface` (a real application) or `concept` (`--depicts`; [The interface of a real application is never invented](#the-interface-of-a-real-application-is-never-invented)) |

### Images of the simulations

`extract` also adds the images of the simulations (`:::scenario`, `:::conversation`), one per id in the whole course, with a
`kind`:

| `kind` | Id | What it is |
|---|---|---|
| `background` | `BG-<description>` | The background of a scene (`background` of the scene), 1920x1080, without text inside |
| `layer` | `LAYER-<description>` | An object on top of a background (`layers.image`), transparent PNG |
| `portrait` | `CHAR-<NAME>` (also the `neutral` expression) and `CHAR-<NAME>-<EXPRESSION>` | A character of the story bible, base and with each expression the simulations use, transparent, with the `look` of the bible in its description |

They are produced in the visual style of the course (`media › visual › style`, see [Configuration](04-configuration.md#media-production-options)), which `coursekit media plan` prints. Without an image generator, `plan` warns and the style is `visual.fallback` (`flat`), drawn as SVG by the **illustration** role: `coursekit run produce-media <CODE> --role illustration`.

A simulation with `audio: true` adds one `VO-<SIMULATION>-<SCENE>` per scene (type `audio`, kind `voice`): its text in `narration` and, in a conversation, the `character` who says it. `coursekit media narrate <CODE>` produces them all with the configured voices (no agent is needed), and a scene whose text changes goes back to `pending`.

With the **creator** backend `extract` also adds `SIM-<ID>` (kind `package`, type `simulation`): the package of each simulation, built with `coursekit media embed <CODE> SIM-<ID>` once its images are produced (see [Simulations in creator](08-assembly-and-delivery.md#simulations-in-creator)).

**Style sheet.** Before them, the media agent produces a sample in `courses/<CODE>/media/style/` (a background, a character in several expressions and some objects) and a person signs it with [`coursekit approve style <CODE>`](03-commands.md#coursekit-approve). Until then `coursekit media set … --status produced` refuses those images (unless `--force`) and `plan` warns. In handoff mode the media agent produces the sample and coursekit signs it as Coursekit Handoff. The assembly takes each image by its id; until it is produced the simulation works without it (initials stand for the portraits).

### Portraits of the characters of a dialogue

`extract` also adds one `image` asset, with id `CHAR-<NAME>` (`CHAR-DANIEL`), for every character that speaks in a `:::dialog` directive: a character has one portrait for the whole course, wherever it speaks. The media agent produces it like any other image (a flat illustration drawn as SVG and exported to PNG, an image generated with a provider, or a licensed photograph of a person), square, as a bust on a plain background in a colour of the theme palette, and it never leaves a character with an initial. Once uploaded, the assembly puts it in the dialogue as the avatar of that character, with the alt text of the asset; until then it warns `dialog: the portrait of 'Daniel' is not uploaded yet`.

### Speakers without a portrait

Not every speaker of a dialogue needs a face made for them. `media.yaml › speakers` ([`media`](04-configuration.md#media-production-options)) names them as they are written in the dialogues:

- the learner (`You` in an English course, `Tú` in a Spanish one) never has a portrait; `learner` adds other names that stand for them;
- `anonymous`: speakers that stand for anyone (`Person`, `Client`): no portrait, the dialogue shows their initial, and in a decision-based course they are allowed although they are not in the cast;
- `avatars`: a speaker always shown with the same image of the brand, such as an AI assistant or a mascot (`{Assistant: theme/branding/assistant.png}`): `extract` copies that file as their portrait, already `produced` (recipe `brand-avatar`), and the media agent does not make one. When the file does not exist the asset stays `pending` with a note.


### The interface of a real application is never invented

A video, image, GIF, infographic or diagram that shows the screen of a real application, platform, program, website or app (a tutorial, a menu, a dialog, "click here") is made only from **real material**: it is never drawn, animated, generated or recreated, not even approximately and not even with fictional names, because the learner takes it for the real thing and looks for buttons that are not there or are named otherwise. The only place where an invented interface is fine is a decision-based simulation (`:::scenario`, `:::conversation`), where the application is fictional.

Each resource of the types in `media › depicts › required_for` (image, infographic, diagram, GIF, video) says what it shows, with `coursekit media set CODE ID --depicts interface|concept`: `concept` for an idea, a process, a diagram or a scene (it can be drawn, generated or animated), `interface` for a real screen. In doubt, `interface`.

- `coursekit media plan` offers for an `interface` resource only the options that work from real material (`shows: interface`, plus `imported`, `vhs` and `asciinema`), and tells you that a resource that has not said what it shows has to.
- `coursekit media set --status produced` (or `uploaded`, the first time) refuses a generated recipe for an `interface` resource, and for a resource of those types made with a generated recipe that has not said what it shows. It has no `--force`. Resources already produced are not asked again.
- What can be done with an `interface` resource, in this order: **a video of an official channel** (not an asset: an address in the content, see [`coursekit videos`](03-commands.md#coursekit-videos)); **real material that a person provides** in `courses/CODE/media/recordings/<id>.mp4`, `.png` or `.cast` (a video is composed over the real recording with narration, captions, zooms and highlights, recipe `screen-recording`; an image is a real capture that is only cropped and marked, recipe `screenshot`; a GIF is the recording cut and converted; a terminal demo is the `.cast` of the person in the player, recipe `asciinema`); or, when there is none yet, **nothing is produced**: the agent writes the brief for the person in `media/scripts/<id>.md` (what to show, the account and version to use, the steps with the labels as the application shows them, the narration, the file to deliver) and leaves the resource `scripted`. A resource `scripted` with the recipe `screen-recording`, `screenshot` or `asciinema` waits for a person: the handoff does not stop for it and lists it in its report.
- **The order holds, and the script is approved first.** An official video proposed for the resource (`coursekit videos propose … --for <id>`) stops it from being captured or voiced while it waits for a person, and for good once approved. And the script of a recording or of a montage (its steps and its narration) is approved by a person, `coursekit approve script CODE --asset ID`, before it is captured or voiced, and again if it changes (`rules › review › scripts`; the handoff signs it by itself).
- **The course itself**: a video or a capture of the course (how it is navigated, a demo for the client) is recorded with the built-in profile `course` and `start: unit:N`: the package of the html backend served on this machine, or the review link of the unit in creator, with no login. See [`coursekit capture`](03-commands.md#coursekit-capture).
- **Personal data in a recording**: before a recording or a capture a person provided is used, `coursekit capture redact` takes the original out of the project and covers its personal data (emails, phone numbers, accounts, IDs, names, faces, the terms of the project); a person reviews the result and approves it (`coursekit capture review`, `approve`), and until then the resource cannot be produced. See [`coursekit capture`](03-commands.md#coursekit-capture).
- **Captures that coursekit makes itself** (web applications): a person sets up the profile of the application and gives a permission that expires (`coursekit capture login` and `allow`); then `/produce-media` can drive the application in the browser and save the capture, with the personal data replaced on screen before the agent sees it; the video is recorded by repeating its steps at the pace of a person (`coursekit capture replay`), and a person approves the result. A window of a desktop program works the same way, covered on the pixels, on macOS, Windows and Linux with X11 (Windows and Linux not yet tested on real machines). A program of the terminal is recorded in a shell of its own, in a stage the agent prepares: [Terminal captures and stages](#terminal-captures-and-stages).
- A resource that waits for a recording does not stop the handoff: the course is assembled with the placeholder showing, and the final message of the handoff lists every resource that waits for a person, with the path of its brief, and every capture whose personal data was covered and waits to be reviewed and approved (or was rejected). The captures its own media agent made are approved by the handoff, as it signs every gate, and its report lists them for a person to look at later; `coursekit media plan` says it too, with the command to run. Once the recording is in `media/recordings/`, `/produce-media` composes the resource. When a permission to capture is in force (`coursekit capture allow`) and its mode can make a resource that waits (the terminal mode makes `screenshot`, `screen-recording` and `asciinema`; the browser and the desktop, the first two), that resource is work of the media agent: the handoff gives it its rounds and `coursekit media plan` says so; one it could not capture goes to the report as before. If the course was already delivered when the permission was given, the handoff says so: `coursekit handoff CODE --new-version` records them in a new version.

### Terminal captures and stages

A program of the terminal (a coding agent, an installation, a few commands) is recorded by the media agent itself, in a shell of its own: no window of the person is touched, and no screen permission is needed. A person allows it once: `coursekit capture allow --mode terminal` for the whole project, or `coursekit capture allow CODE --mode terminal` for one course (with `--minutes 0`, until it is revoked).

The environment of a recording is a **stage** of the course, written by the agent with invented data and kept with the course in `courses/CODE/media/stages/<name>/`:

```
media/stages/recipes/
  stage.yaml
  files/          # the project as it starts, copied whole
```

```yaml
title: Recipe website with a search that ignores accents
folder: projects        # inside the home folder (default capture.yaml › terminal.folder)
setup:                  # commands that leave it ready, run before each session (not recorded)
  - git init -q && git add -A && git commit -qm "First version"
home: real              # real: the home folder of this machine (the settings and the session of the programs);
                        # clean: an empty one, as a machine just installed
hide: [opencode]        # commands that are not on the PATH (a machine without the program)
env: {}                 # variables added
```

Before each session coursekit mounts the stage from scratch in `<home>/<folder>/<name>`: it copies `files/`, runs its `setup` and the `prepare` of the `capture` block of the resource (what that one needs on top: a file taken away, a change already made), and starts `bash` there with no startup file of the person, a short prompt, the language of the course and an invented git author. So every take starts clean, and it can be repeated. coursekit writes down the folders it made and never deletes or overwrites one it did not make. `home: clean` gives an empty home folder (in the store of coursekit), and `hide` leaves commands out of the PATH (each folder that has one is replaced by links to everything else in it).

```capture
mode: terminal
stage: recipes
prepare: ["rm -f AGENTS.md"]
terminal: {cols: 120, rows: 34}
```

A ```` ```yaml ```` block whose only key is `capture:` is read the same way. In the handoff, the scripts of what its media agent may capture are signed before it starts. The session is recorded as it goes and its output covered in the text (see [`coursekit capture`](03-commands.md#coursekit-capture)); `session_end` leaves the `.cast` of a terminal demo (shown with the player, the text can be copied), the `.mp4` of a video with the places the narration names (for the zooms of [The Screencast component](#the-screencast-component)) or the `.png` of a capture. It is drawn with the program's own colors, on the palette of `capture.yaml › terminal`. `coursekit capture stage CODE NAME` mounts a stage to look at it or try it.

### Statuses

| Status | Meaning |
|---|---|
| `pending` | Only the placeholder exists |
| `scripted` | The script is written (`media/scripts/<id>.md`); videos, audio, GIFs and demos are scripted before they are produced |
| `produced` | The file exists (`media/files/<id>.<ext>`), with its alt text or captions. With the html backend it is the final status ([Media for the html backend](#media-for-the-html-backend)) |
| `uploaded` | Uploaded to the platform; `asset_path` holds its path |

`orphaned` is set by `extract`, never with `media set`, which accepts only the four above. Assets are not approved one by one: they are validated in the assembled course (the preview). With the creator backend only `uploaded` assets replace their placeholder when the unit is assembled; until then the placeholder shows as a note ([08-assembly-and-delivery.md](08-assembly-and-delivery.md)). With the html backend `produced` assets with their file replace it too.

### How the options are chosen

For each asset, `media plan` takes the options of its type from `src/coursekit/defaults/media.yaml` and keeps those whose `needs:` are met on this machine:

| `needs:` | Met when |
|---|---|
| `env: VAR` | The variable is set (in `.env` or the shell) |
| `bin: CMD` | The command is installed |
| `media: X` | `X` is installed as a command (`coursekit setup --media` installs `piper` and `stable-ts`) |
| `path: P` | The path exists inside the project (for example `tools/remotion/node_modules`) |
| `mcp: TOOL` | Only the agent can know whether it has that MCP tool; shown as `if the agent has the MCP tool` |
| `none` | Always |

An option with several `needs:` must meet all of them. `only:` limits an option to some assets, and the agent decides from the placeholder's description: `only: terminal`, to those that show a terminal; `only: decorative`, to the decorative images, those that set the scene and explain nothing (a header, people at work, a place, a generic object). That is why an image comes first from the licensed catalog of creator when it is decorative, and is generated when it shows something specific of the content (a situation the text describes, a scene of the story, a character); a decorative one with nothing in the catalog that fits the style of the course is generated too. An id may appear twice in a list, once limited and higher, once without the limit and lower. If nothing is available, `media plan` prints `no option available: install a tool or set a key (coursekit config media)`.

```text
U1-S1-M1 [image] Sticky note on a monitor
  - creator-stock (if the agent has the MCP tool, only for decorative content): Licensed stock from creator (Pexels, Pixabay, Unsplash, Freepik) + import_stock_image; nothing that fits the style of the course: go on with the next option
  - magnific-mcp (if the agent has the MCP tool): Claude's Magnific connector
  - agent-svg (yes): Illustration drawn by the agent as SVG with the theme colours and exported to PNG (creator does not take SVG as an image); portraits of characters as flat busts
  - creator-stock (if the agent has the MCP tool): Licensed stock from creator (Pexels, Pixabay, Unsplash, Freepik) + import_stock_image
U1-S2-M1 [video] Building a passphrase
  - vhs (yes, only for terminal content): Terminal video
    voice: elevenlabs-mcp
    subtitles: stable-ts
```

For `video` and `audio`, `plan` also prints the voice and subtitle options that are available. For the types that use the theme tokens it also warns when the tokens are missing or were not derived from the platform theme ([Theme tokens](#theme-tokens)). A project can change the options in `config/media.yaml` (see [04-configuration.md](04-configuration.md)).

## Media for the html backend

With the html backend there is no platform to upload to: the package of a unit carries its media. So a `produced` asset is final, and the `uploaded` status and `--asset-path` are not used. The flow is the same up to producing the file:

```bash
coursekit media set PWD U1-S2-M2 --status produced --recipe agent-svg \
  --file media/files/U1-S2-M2.svg --alt "Diagram of length, variety and uniqueness"
coursekit assemble build PWD --unit 1
```

`coursekit assemble build` copies every `produced` (or `uploaded`) asset whose `--file` exists into `media/` of the package and swaps the placeholder for it. What it does with each kind:

| Asset | What the package gets |
|---|---|
| Image, infographic, diagram, animated GIF, audio, video | The file `--file` points to, copied as `media/<id>.<ext>` (the file is looked for relative to the course folder and to its `media/` folder). Images use `--alt`; audio and video use `--transcript`. |
| Simulation and terminal demo | A folder: `--file` can be the folder of the package (for example `media/src/U1-S3-M1`) or its `index.html`. The folder is copied to `media/<id>/` and embedded in the page. |
| Captions | `--subtitles-path` can be a local `.vtt` file (for example `media/files/U1-S2-M1.vtt`): it is copied to `media/<id>.vtt` and attached to the video. A value that is a path in a platform is ignored. |
| Downloads | The files registered with `--download FILE` are copied to `media/files/` and shown as downloadable attachments after the asset. `--download-asset-path` is not needed. |

An asset that is `produced` but whose file does not exist is a warning in the output of `build` (`the asset U1-S2-M2 is produced but its file does not exist (coursekit media set … --file): the placeholder stays`), and the placeholder stays in the page as a visible note with its description, like an asset that is not produced yet. The media of the theme (infographics, diagrams, simulations, videos) use the same tokens as the package: [Theme tokens](#theme-tokens).

## Lighter media

Heavy images and videos slow the course down in the LMS, so coursekit makes them lighter locally, without spending credits. The limits are in `media.yaml › optimize` (a project overrides them in `config/media.yaml`, a course in `course.yaml › media › optimize`):

| Key | Default | Meaning |
|---|---|---|
| `image.max_width` | `1920` | Wider images are scaled down keeping their proportions (`0` never scales). |
| `image.quality` | `82` | JPEG and WebP quality. |
| `image.webp_from_kb` | `200` | html backend: a PNG or JPEG above this weight goes into the package as WebP. |
| `video.max_height` | `1080` | Taller videos are scaled down (`0` never scales). |
| `video.crf` | `26` | H.264 quality: lower is sharper and heavier. |
| `video.preset` | `medium` | ffmpeg speed: slower is lighter at the same quality. |
| `video.audio_kbps` | `128` | AAC bitrate. |
| `video.from_mb` | `8` | html backend: an MP4 above this weight is re-encoded for the package (needs `ffmpeg`; without it the file is copied). |

- **Creator backend:** run `coursekit media optimize CODE [ID…]` before uploading. It works in place on the file of each `produced` asset and keeps the result only if it weighs less. Creator does not optimise what it receives.
- **html backend:** `coursekit assemble build` optimises the copy it puts in the package and leaves the source file alone; there is nothing to run.
- SVG, GIF, audio and packages are never touched. Only `.mp4` videos are re-encoded (what Remotion and VHS write), so the name in the manifest stays valid.

## Video montage

A video can be data instead of code: a montage of scenes, `media/scripts/<id>.video.yaml`, that [`coursekit video`](03-commands.md#coursekit-video) voices, checks and renders with a library of scenes in the theme of the course (recipe `montage`, the first option for a video). Each scene lasts what its narration lasts, so changing a text changes the timing, not the code. A video made by hand as a Remotion composition (recipe `remotion`) is still fine.

```yaml
version: 1
format: {width: 1920, height: 1080, fps: 30}
scenes:
  - id: opening
    type: title
    props: {kicker: "Unit 1", title: "Long passwords", stress: "Long"}
    says: "Today we see why long passwords protect more."
  - id: length
    type: split
    props:
      title: "Length first"
      points: [{text: "Twelve characters or more", say: "twelve characters"}]
      media: files/u1-lock.png
    says: "Length first: twelve characters or more."
  - id: close
    type: outro
    props: {title: "Long and unique"}
    duration: 3
    shows: "The close, on the accent colour: «Long and unique»"
```

A scene has an `id`, a `type`, its `props`, what it `says` (or a `duration` when it says nothing; `hold`, seconds it stays after it is said, for a pause to think or to look; `transition`, how it enters over the end of the one before: a type, or `{type, direction}`, over `config/video.yaml › transition`) and, optionally, `shows` (what is seen, when the narration does not say it) and `layers`: each one a `type`, its `props`, `at` (the words of the narration it enters with), and `until` (the words it leaves with) or `hold` (seconds, default 3), for example `{type: callout, props: {text: "Twelve or more"}, at: "twelve", until: "more"}`. A layer whose words are not said is left out, and `coursekit video check` warns of it (`ANCHOR_NOT_SAID`). After the render, the voice is brought to the loudness of `media › checks`.

**The pieces.** Everything is built in levels, each one only from the one below:

| Level | What | In the library |
|---|---|---|
| Tokens | the theme of the course (its own, else the project's) and the tokens of motion | colours, fonts, radius; how long things take to enter |
| Atoms | the smallest pieces, moved by the frame | `Heading`, `Text`, `Enter`, `Stagger`, `Underline`, `Counter`, `MediaSlot`, `Ring`, `Background`, `Card`, `Badge`, `Arrow`, `ScreenRecording`; `useAt("word")` and `useSayTimes([...])`: when the narration says it |
| Molecules | small combinations | `TitleBlock`, `BulletList`, `StatBlock`, `CompareColumn`, `StepNode` |
| Scenes | whole compositions | `title` (the cover: plain, surface, accent or a photo beside the text, under a panel or under the text, placed across and up and down), `statement` (a phrase to keep, a word underlined when it is said), `split` (its points with a bullet, their number or nothing, `marker`), `stat`, `compare`, `list` (each item with its number, a bullet or nothing, `marker`), `quote`, `diagram` (a process that builds itself, with arrows between the steps or without them, `arrows: false`, drawn as the brand asks (`arrow_width`, `arrow_head` filled, open or none, `arrow_line` solid or dashed, `arrow_tone`), and with their numbers or without them, `numbers: false`), `outro`, `screencast` (inside a window or not, `frame`), `image` (an image on the whole frame with a slow movement and a caption), `annotated` (an image or a screenshot with numbered points that enter as they are named, the ones before staying or giving way, `previous`), `question` (a question to the learner, a pause shown as a bar that fills, and the answer), `chapter` (a divider with the parts of the video and the current one, marked with a bar, a fill, a line or nothing, by its weight, its size or both, the others stepping back or not and the ones seen ticked, in a column or in a row), `chart` (a few figures as bars, as columns or as the parts of a circle, with their source), `timeline` (milestones with their date on a line that ends at the last one, their texts under it or alternating under and over it) and `code` (code whose lines are marked as they are explained: a fill, a bar, both or neither, the strong weight, the rest stepping back or not, and the lines explained staying marked or not). Every scene with an image takes `credit`, its author and licence small at the bottom right (a CC-BY photo requires it). `compare` may leave out its marks (`marks: false`), wear the colour of state of each column only in its marks, in a border on top or at its side, in its header or on the whole card (`accent`, with the text in the colour that reads on it), give each column a `tag` and put them one over the other (`layout: rows`), `quote` takes a mark (quotation marks, a bar or none) and a `portrait`, `stat` a `layout` (the figure over or beside what it measures), and `split` the `fit` of its medium (cropped or whole) and how it shares the width (`ratio`). All scenes keep the same margin left and right, so a title does not move from one to the next. Every scene but `screencast` takes `entrance` (how its elements enter, over `config/video.yaml › motion › entrance`), and `compare`, `diagram`, `list` and `split` take `reveal` (`one-by-one`, as the narration names each item, or `together`); when each thing enters is always set by the narration, never by a second in the script. Every scene but `screencast` takes `background` (`plain`, `surface`, `accent`, `inverse`, the colour of the text whole with the texts in the background colour, or `photo`, with its `photo` under a veil whose colour and opacity the scene may change, `veil` (a colour of the theme, `inverse` or `none`) and `veil_opacity`, else `config/video.yaml › photo_veil`; without it, the one of the style, and the accent for `outro`), `align` (`left` or `center`) and `valign` (`top`, `middle` or `bottom`, which keeps clear of the captions), so one rule of `config/video.yaml › scenes › "*"` places them all; every title of a scene may have a `kicker` over it, and titles and kickers have one size in every scene (the `heading` and `kicker` roles of `config/video.yaml › text`); `compare`, `diagram`, `list`, `split`, `stat` and `statement` (these two may have a `title`) also take `title_valign` (`content`, the title with the content, or `top`, the title at the top of the frame while the content goes where `valign` says); on the accent the texts and marks of a scene take the text on the accent, and on the surface its cards take the background colour |
| Layers | over a scene, from a word of its narration | `lower-third` (a name and a role, at the left or the right, with a bar, in a card or as text alone), `callout` (a short note at a corner, with a mark in the accent, the colour of right or wrong, or none, or filled with that colour, `look: fill`), `highlight` (a ring or a box on a point, with the rest darkened or not), `pointer` (a label with a line, of `width` px, that points at a spot), `progress` (one mark per part of the video, the current one in the accent) |

The tokens reach the video as data, so a course with another theme gives another video with no change. The accent is a fill (the close, the circle of a number); what is drawn thin on the background with it (an underline, an arrow, the mark of a list, a word) takes `accent-ink`, the accent that reads on the background: the same colour when the accent already reads, a darker one, or the one the project fixes, when the accent is only a fill. A brand with its own rules (square corners, no shadows, two weights, its font files) sets them in `config/video.yaml` (`shapes`, `weights`, `fonts`; see [Configuration](04-configuration.md#video-the-style-of-the-videos-made-as-a-montage)), and every piece of the library follows them. A scene is a folder with `index.tsx` (its component) and `scene.yaml` (a layer, `layer.yaml`) (what it is, what it is built from, and its props: type, required, maximum characters, on screen, label; its name to show (`label`), its `description` and the `help` of each prop may be one text or one per language, `en:` and `es:`, and they are shown in the language of the person, as the `label` of each of its `variants:`; the id of the piece, what the script writes, never changes); `coursekit video catalog` lists them all, so the pieces and how they are put together can be seen. `coursekit video gallery` draws them: each piece with the props of its `example:` (in its `scene.yaml` or `layer.yaml`, one block per language of the courses, `en:` and `es:`), in the theme and the style of the course, rendered, in `.cache/media/<CODE>/gallery/`: a clip of each piece and each variant, in the same interface as the live gallery (it opens from the disk). Without a code, `coursekit video gallery` draws the project's (its theme, its `config/video.yaml`, its scenes and the library's), in `.cache/media/project/gallery/`: the one to look at before signing the style guide of the project. A scene of the project or of a course is drawn too when it brings its `example:`, and `variants:` (each a `name` and the `props` it changes over the example) draws it again in other ways. The cover goes first, and each piece shows its props as a table: name, type, the values it takes, whether it is required and what it is for; a prop that only counts with another value says so (`when:` in its metadata, e.g. `when: {background: photo}`). The transitions of the project have their own page in both galleries (Style › Transitions): the cover giving way to the next scene with each type; the export for an editor keeps them inside the clips of the scenes, each clip up to where the next scene starts. `coursekit video gallery --serve` opens the same pieces live in the browser, as a component library does (the page is coursekit's and wears the design system of Studio LXD; each piece is drawn apart, in a frame that only has the theme and the style of the project): a control for each prop, its variants in a select, a button to go back to what the project (or the course) draws, and the props to copy into the script; a prop with `when:` is hidden while that value is not chosen. A change of the project (its `config/video.yaml`, the theme, a scene) shows by itself while it is open. What the browser plays is very close to the render, but the rendered gallery is the proof. The pieces that take a photo are drawn with a photo in the public domain that coursekit brings (CC0); the live gallery of a course also offers the images of its `media/files/`.

**The typography of the videos.** Every text of a piece has a role (`display`, `heading`, `kicker`, `body`, `quote`, `statement`, `stat`, `step`…), and `config/video.yaml › text` gives each role its family (one of the fonts of the brand), size, weight, style, case, tracking, leading and colour (a role of the theme). The pieces of the library, of the project and of a course follow it without being touched; the Typography page of the live gallery shows the scale at a glance. See [`video`](04-configuration.md#video-the-style-of-the-videos-made-as-a-montage).

**What the brand allows.** The library offers every possibility; the project narrows them in `config/video.yaml › scenes` (and a course in `course.yaml › video › scenes`): the values each prop may take (`allow`), the one it takes when the script says nothing (`defaults`), and the pieces left out (`<name>: false`); `"*"` is for every piece with that prop. A brand without centred texts, for example, writes `scenes: {"*": {allow: {align: [left]}}}`. The catalog and the galleries show only that, and `coursekit video check` refuses the rest (a warning in the handoff, listed in its log). `/define-theme` proposes these rules from the brand. See [`video`](04-configuration.md#video-the-style-of-the-videos-made-as-a-montage).

**Where the scenes are, and which one wins.** A scene of the course hides one of the project with the same name, and one of the project hides one of the library:

| Where | What |
|---|---|
| `courses/<CODE>/video/scenes/<name>/`, `video/layers/<name>/` | scenes and layers of one course |
| `tools/remotion/src/scenes/<name>/`, `src/layers/<name>/` | scenes and layers of the project, for every course |
| `tools/remotion/kit/` | the library of coursekit: every `coursekit video` command writes it from the package; it is ignored by git and never edited |

**Pieces of the project in place of the library's.** An atom or a molecule of the project (`tools/remotion/src/atoms/<Name>.tsx` or `src/molecules/<Name>.tsx`), or of a course (`video/atoms/<Name>.tsx`, `video/molecules/<Name>.tsx`), takes the place of the one of the library with that name in every scene: a project with a strong brand redoes its `Heading` or its `Card` and every scene shows it, without touching the scenes. It exports the same name with the same props (`coursekit video` refuses another name, or one the library does not have); start from the file of the library in `tools/remotion/kit/`. `coursekit video catalog` marks the pieces replaced. The style of the videos (motion, background, logo) is set in [`video`](04-configuration.md#video-the-style-of-the-videos-made-as-a-montage).

**To retouch it by hand.** `coursekit video export CODE ID` leaves the pieces of the video apart (each scene clean, each layer with transparency, each voice, the captions) and its timeline in FCPXML 1.10 and OpenTimelineIO, which DaVinci Resolve, Final Cut and Premiere open with every piece in its place.

When no scene tells an idea, the media agent creates one, composed from the atoms and molecules (importing them from `"../../../kit"`, the same in a scene of the project and of a course), so the library of the project grows with use. The rules of a scene: everything moves with the frame; colours and fonts only from the theme; what enters with a word enters when the narration says it; media by their path inside the media folder of the course; nothing from the network.

## Accessibility of videos

What a video shows also exists as text, so that whoever cannot see it gets it (WCAG 1.2.3, 1.2.5 and 1.2.8). The scenes of a video are described next to its brief, in `media/scripts/<id>.scenes.yaml`:

```yaml
words: media/files/u1-s2-m1.words.json      # the timings of the narration (default: <file of the video>.words.json)
scenes:
  - text: "Minimum length: 12"              # the text on screen (one or a list)
    says: "Open the security settings and set the minimum length to twelve."
  - text: "History"
    shows: "The list of saved changes, with the date of each one"   # what is seen, in a sentence
    says: "And that is all."
```

- **Integrated audio description.** What matters on screen is also said: `coursekit media check` reports (`NOT_SAID`) the text on screen whose narration does not say most of its meaningful words (four letters or more, and numbers, also when they are said in words), unless the scene describes what is seen in `shows`. Fix it in the narration or with `shows`.
- **Accessible transcript and descriptions.** `coursekit media transcript CODE ID` writes, scene by scene, the minute (from the words of the narration), what is seen (`shows`, else the text on screen, after `On screen:` in the language of the course) and what is said, in `<file>.transcript.txt`, and the same as a WebVTT track of descriptions (`kind="descriptions"`) in `<file>.descriptions.vtt`. The transcript becomes the one of the asset, so the assembly puts it in the course under the video.

## Checking audios and videos

Before an audio or a video goes to the course, `coursekit media check CODE` looks at its loudness (EBU R128 for the web: -16 LUFS, peak -1 dBTP; `--fix` brings it there), at its captions (none faster than 17 characters per second) and at what it shows and does not say; `coursekit media sheet CODE ID` puts frames of a video in one image, to look at it without playing it. The limits are in `media.yaml › checks`. See [`coursekit media`](03-commands.md#coursekit-media).

## Images with points

An image that a `:::labelled-graphic` names, or the background of a simulation with hotspots that have an `area`, has
**points**: `coursekit media extract` lists them in the manifest (`points`), so the media agent draws the image with room for
them. Once the image is produced, [`coursekit media anchors CODE ID`](03-commands.md#coursekit-media) draws on it a numbered
crosshair where each point goes, taken from the content (the `position` of the point, the centre of the `area` of the
hotspot), and records them (`anchors`). The crosshairs **stay in the final image**: whoever reviews it sees where each point
will be and can ask to move it. The image and the content always agree, because the crosshairs are drawn from the content:

- A point with no `position` (the writer does not see the image): the media agent gives it one looking at the image, with
  `--set "<point>=x,y"` (in % from the top left corner), which writes it in the content and draws the crosshair.
- To move a point, the same `--set`; to move a hotspot, its `area` in the content, then `anchors` again.
- `coursekit verify` fails when the content moved or added a point and the image was not drawn again, and warns of a point with
  no position. An `uploaded` image whose crosshairs change goes back to `produced`, to upload it again; an SVG for creator is
  exported to PNG after its crosshairs (`coursekit media render`).

## Job aids

A **job aid** (`job_aid`) is a checklist or a quick guide the learner downloads as a PDF to use at work, when the procedure
of a section is something they will do again. The design proposes the ones a unit needs; the writer writes its text in the
body of its placeholder (after the four fields, on lines that start with `>`: `##` headings, numbered steps, `- [ ]` checks),
so it is reviewed with the unit; the media agent never writes it.

Every job aid of a project comes out of one **template**: `theme/templates/job-aid.html` of the course, else of the project,
else the one of coursekit (neutral, with the tokens and the fonts of the brand). Its values in double braces are `lang`,
`title`, `subtitle` (the course and the unit), `content` (the text as HTML; a list whose items all start with `[ ]` comes out
as a checklist), `page`, `margins`, `tokens_css`, `fonts_css` and `style_css`.

The job aids have a **style of their own**, because paper is not a screen: `media › job_aid` (see
[`media`](04-configuration.md#media-production-options)) gives the page (`page`, `orientation`, `margins`), the typography of each
part (`text`: `kicker`, `title`, `heading`, `subheading`, `body`, `quote`, with a family of the fonts of the brand, the size in
pt and the colour of a role of the theme) and the shapes (`shapes`). `/define-theme` sets it from the brand as it sets the style
of the videos, and the template reads it as CSS variables (`--ja-<role>-<key>`), falling back to the theme for what it leaves
empty. The template is changed only for a layout the style cannot give (a logo, a footer).

- While the theme is defined, [`coursekit theme sample`](03-commands.md#coursekit-theme) prints a job aid with sample text to
  `theme/branding/samples/job-aid.pdf`: the person opens it and asks for changes until it looks right.
- The template is signed with the [style guide of the media](#the-style-guide-of-the-media): a change to it asks for a new signature.
- `coursekit media render CODE ID` prints each job aid to `media/<id>.pdf` with the Chrome, Chromium or Edge of the machine.
  The PDF is tagged (headings, lists, tables, the language and the title) and has the outline of its headings, so a screen
  reader follows it; keep the template semantic for that.
- In the course it is a download in place of its placeholder: an `ATTACHMENT` in creator (uploaded with
  `request_asset_upload` of kind `attachment`) and a link in the html package.

## Upload to creator

With the creator backend the assets are uploaded to the content of their unit, which the assembly creates, and the course is assembled again so that they replace their placeholders (the handoff does it by itself: [Handoff mode](02-workflow.md#handoff-mode)). The agent asks creator for an upload address (`request_asset_upload`, or `request_embed_upload` for packages) and sends the file with `coursekit media upload CODE --file F --url "<uploadUrl>" --content-type MIME`; then it records the path with `coursekit media set CODE ID --status uploaded --asset-path <path>`.

Creator takes only PNG, JPEG, WebP and GIF as an image, so an SVG cannot be an image block:

- A static infographic or diagram: the agent keeps the SVG as the source and uploads a PNG exported from it.
- An animated SVG (`agent-svg-animated`): `coursekit media embed CODE ID` wraps the SVG in `media/src/<id>/index.html`, with creator's manifest `slxd-embed.json` (it takes the height of the drawing), the agent uploads both files as an EMBED package, and the assembly puts an EMBED block where the asset's file is an `.svg`. The animation is kept.

## Voice providers

A course uses **one** voice for all its narration, so a course never mixes voices. The choice is stored in `course.yaml › media.voice`.

| Provider | Needs (in `.env`) | Default voice | Notes |
|---|---|---|---|
| `elevenlabs` | `ELEVENLABS_API_KEY`; a voice in `ELEVENLABS_VOICE_ID` or `--voice` | none | Best quality; writes exact captions from its timestamps |
| `azure` | `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` | `es-ES-ElviraNeural` / `en-GB-SoniaNeural`; `AZURE_SPEECH_VOICE` overrides | Neural voices |
| `google` | `GOOGLE_TTS_API_KEY` | `es-ES-Chirp3-HD-Aoede` / `en-GB-Chirp3-HD-Aoede`; `GOOGLE_TTS_VOICE` overrides | Chirp 3 HD voices |
| `gemini` | `GEMINI_API_KEY` (Gemini API, from Google AI Studio) | `Aoede` in both languages; `GEMINI_TTS_VOICE` overrides | Gemini TTS voices, with a style instruction ([The Gemini voice](#the-gemini-voice)) |
| `piper` | `PIPER_VOICE` (path to a `.onnx` voice) and the `piper` command; `PIPER_SPEAKER` for multi-speaker voices | the file in `PIPER_VOICE` | Local draft voice |

The default voice depends on the course language (`es` or `en`). In `media plan` and `media providers` the voice options are named `elevenlabs-api`, `azure-api`, `google-api`, `gemini-api` and `piper` (the providers above), plus `elevenlabs-mcp`, the agent using the ElevenLabs connector directly (without `coursekit tts`); that one is always listed, because only the agent can tell whether it has the connector. The subtitle options are `elevenlabs-timestamps` and `stable-ts`.

```bash
coursekit voice set gemini                 # the voice of the project: every course without its own inherits it
coursekit voice list PWD                   # providers, availability and the voice of the course
coursekit voice set PWD azure              # fixes the provider (and its default voice)
coursekit voice set PWD piper --speaker 1  # a speaker of a multi-speaker Piper voice
coursekit voice set PWD elevenlabs --voice <voice-id>
```

**Voices of the characters.** The characters of the dialogues and the simulations can have their own voice, of the same provider: `coursekit voice set PWD azure --voice es-ES-AlvaroNeural --character Daniel` stores it in `course.yaml › media.voices`, and `coursekit tts --course PWD --character Daniel …` uses it. With Piper, a character without a voice of its own takes a speaker of the voice in turns, in the order of the cast of the story bible: enough for drafts.

`voice set <provider>`, without a course, fixes the voice of the project (`project.yaml › media.voice`), and every course without a voice of its own uses it; `voice set <CODE> <provider>` gives one course its own, and `voice unset <CODE>` takes it away so the course inherits the project's again. A change of the voice of the project reaches every course that inherits it, also the narration still to produce of a course half done. If the provider is not configured on this machine it warns (other people on the team may have it) but still saves it. With several providers available and none chosen, `tts` stops and asks you to run `voice set`; with none available it says which keys to set.

### The Gemini voice

The `gemini` provider uses the text-to-speech models of the Gemini API. They take a **style instruction** besides the text: how to say it (emotions, delivery, pace, volume), sent with every piece of the script so that the tone does not change between them. Its settings are in `media.yaml › gemini` ([Configuration](04-configuration.md#media-production-options)), and a course changes them in `course.yaml › media › gemini`:

```yaml
# course.yaml
media:
  gemini:
    style: "calm, warm and clear, like a teacher explaining"
```

| Key | Default | Meaning |
|---|---|---|
| `model` | `gemini-3.8-flash-tts` | Model of the Gemini API. `gemini-3.8-flash-lite-tts` costs less; `gemini-3.1-flash-tts-preview` is the earlier preview model |
| `style` | empty | How to say it. Empty: the voice as it is |
| `chunk_bytes` | `4500` | Longest piece of a script per request, in UTF-8 bytes. The model returns at most about ten minutes of audio per request |
| `tier` | `flex` | `flex`: half the price, the same request, and the answer in minutes instead of seconds (up to 15); when Google has no capacity it answers 429 or 503 and coursekit tries again a few times. `standard`: the full price and the quickest answer |
| `flex_fallback` | `true` | When `flex` still has no capacity after the attempts, the request goes in the standard tier. `false`: it fails instead (exit code 1), and nothing is paid at the full price |

`coursekit voice set PWD gemini` writes the model in force in the course (`course.yaml › media.voice.model`; `voice set gemini`, in the project's voice): the course keeps the model it started with when the default changes, so its narration never changes voice halfway. To move a course to another model, change that key and produce its narration again. The voices are the Gemini ones (`Aoede`, `Kore`, `Charon`, `Puck`…), without a language: the language is the course's. The Gemini API marks all the audio it generates with an inaudible SynthID watermark. On its free tier, Google may use what is sent to improve its products: for the content of a client, use a key with billing.

### The batch of the Gemini voice

Besides `flex`, the Gemini API has a **batch**: the requests of a whole course are sent together in one job and Google answers them within 24 hours (often within minutes), at the same half price. Nothing waits for the answer: the narrations are queued, the job is sent and they are collected later. A course keeps its queue in `media/tts-batch.yaml` (versioned: what was sent, with which model, voice and style, and how it went). It exists only with the Gemini voice.

Three commands put narrations in the queue with `--batch`, instead of voicing them:

| Command | What goes in the queue | What `collect` does with it |
|---|---|---|
| `coursekit video voice CODE ID --batch` | The scenes of a montage whose text or voice changed | Writes their audio, aligns their words (`stable-ts`) and records their length: `coursekit video render` goes on |
| `coursekit media narrate CODE --batch` | The scenes of the simulations still to narrate | Writes `media/files/<id>.mp3` and marks the asset `produced` |
| `coursekit tts --course CODE --in … --out … --batch` | A script | Writes the `--out` file |

Then [`coursekit tts-batch`](03-commands.md#coursekit-tts-batch) `send CODE` uploads the queue (a long script is several requests, joined again when collected) and creates the job; `status CODE` says how it goes; `collect CODE` writes what arrived and leaves in the queue what failed, to be sent again. A job that does not finish in 48 hours expires with no results and everything goes back to the queue. Creating a job is not idempotent (sending again would be paid twice), so a second `send` is refused while one is under way. The assets of the queue are neither pending for the media agent nor produced: `media plan` and the handoff leave them be until they are collected.

In [handoff mode](02-workflow.md#handoff-mode), when the media agent leaves narrations in the queue, the handoff sends them and stops, saying that they are on their way; `coursekit handoff CODE` later collects them (if the job has finished; otherwise it stops again) and carries on with what depended on them.

## `coursekit tts`

Reads a script and writes the voice-over:

```bash
coursekit tts --course PWD --in courses/PWD/media/scripts/U1-S2-M1.md --out courses/PWD/media/files/U1-S2-M1.mp3
```

| Option | Meaning |
|---|---|
| `--in FILE`, `--out FILE` | Script (whitespace is collapsed) and output audio; both required |
| `--course CODE` | Use the voice of that course and its language. Without it, the language is `es` |
| `--engine elevenlabs\|azure\|google\|gemini\|piper` | Force a provider instead of the course's |
| `--voice V` | Force a voice. Otherwise: the course voice (if same provider), then the provider's environment variable, then the default for the language |
| `--speaker N` | Speaker of a multi-speaker Piper voice |

The provider is `--engine`, else the course's `media.voice.provider`, else the only provider available. Long scripts are split at sentence ends (Azure 4,000 bytes, Google 4,500, Gemini `media.yaml › gemini.chunk_bytes`); the pieces are asked for as uncompressed audio, joined one after the other and encoded to MP3 once with `ffmpeg`, so there are no gaps between them and no second pass of compression; Piper also needs `ffmpeg` to write MP3 (an `--out` ending in `.wav` keeps the WAV). ElevenLabs also writes `<out>.vtt` (same name, `.vtt`) with captions from its timestamps, grouped at sentence ends or about 84 characters.

## `coursekit subtitles`

Aligns a known script with its audio, word by word, with `stable-ts` and writes a WebVTT file whose cues end at sentence ends or after about 84 characters:

```bash
coursekit subtitles --course PWD --audio courses/PWD/media/files/U1-S2-M1.mp3 \
  --text courses/PWD/media/scripts/U1-S2-M1.md --out courses/PWD/media/files/U1-S2-M1.vtt
```

`--course` takes the language of the course; without it the language is `--language` (default `es`). `--model` is the model name passed to `stable-ts` (default `base`). Use it for audio from Azure, Google or Piper; ElevenLabs already writes its own `.vtt`. Captions are always required for video.

## Draft voice (Piper) and stable-ts

Both are installed by `coursekit setup --media` as separate `uv` tools (Python 3.12), because they are heavy and only needed for media. They are installed once per machine and every project uses them:

- **Piper** is a local text-to-speech engine for quick drafts, free and offline. `setup --media` also downloads a voice for the project's content language into `~/.local/share/piper` (`%LOCALAPPDATA%\piper` on Windows) and sets `PIPER_VOICE` in `.env` if it is empty: `es_ES-sharvard-medium` for Spanish (speakers 0 and 1) and `en_GB-alba-medium` for English.
- **stable-ts** aligns scripts with audio to produce captions (`coursekit subtitles`).

Both count as installed when their command (`piper`, `stable-ts`) is on your `PATH`.

## `coursekit setup --media`

Run by a person, never by an agent (agents are told to ask you to run it). An interactive `coursekit setup` also offers it.

| Step | macOS | Windows | Linux |
|---|---|---|---|
| System tools | `brew install` for the missing ones of `ffmpeg`, `node`, `vhs`, `asciinema` (needs Homebrew) | `winget install` for `ffmpeg` (`Gyan.FFmpeg`), `node` (`OpenJS.NodeJS.LTS`), `vhs` (`charmbracelet.vhs`); `asciinema` has no Windows build, terminal demos use VHS | Installs nothing: prints `sudo apt install …` for the missing ones of `ffmpeg nodejs npm asciinema`, and the address of `vhs` |
| `piper`, `stable-ts` | `uv tool install --python 3.12 piper-tts` and `stable-ts` (needs `uv`) | same | same |
| Draft voice | Downloaded, `PIPER_VOICE` set | same | same |
| Remotion | Copies the template to `tools/remotion` (if missing), installs its dependencies once in the coursekit store and links `tools/remotion/node_modules` to them ([Where the tools live](#where-the-tools-live)) | same | same |
| API keys | Asked only in an interactive terminal | same | same |

The keys are asked one by one with hidden input (press Enter to skip). Those already set are not asked again. When one is saved, its companion values are asked too:

| Service | Key | Also asked |
|---|---|---|
| ElevenLabs | `ELEVENLABS_API_KEY` | `ELEVENLABS_VOICE_ID` |
| Azure Speech | `AZURE_SPEECH_KEY` | `AZURE_SPEECH_REGION` (required, `doctor` warns without it), `AZURE_SPEECH_VOICE` |
| Google TTS | `GOOGLE_TTS_API_KEY` | `GOOGLE_TTS_VOICE` |
| Gemini TTS | `GEMINI_API_KEY` | `GEMINI_TTS_VOICE` |
| Magnific | `MAGNIFIC_API_KEY` | — |

All of them go to `.env`, which is never committed. `coursekit doctor` shows the Media section: `ffmpeg`, `vhs`, `asciinema`, `piper`, `stable-ts`, the coursekit store (path and size), `Remotion dependencies (tools/remotion/node_modules)` when the project has a Remotion workspace, `PIPER_VOICE` and which keys are set.

## Where the tools live

Nothing heavy is installed inside a project. The tools are installed once per machine and every project uses the same copy:

| Tool | Where | Shared by the projects |
|---|---|---|
| `ffmpeg`, `node` (with `npm`), `vhs`, `asciinema` | System packages (Homebrew, winget or your package manager) | Yes |
| `piper`, `stable-ts` | `uv` tools, in the tool folder of `uv` | Yes |
| Piper draft voice | `~/.local/share/piper`, or `%LOCALAPPDATA%\piper` on Windows | Yes |
| Remotion dependencies (`node_modules`) | The coursekit store, in `workspaces/remotion-<hash>/`; each project links to it | Yes |
| Builder of the html backend (`@studiolxd/scorm`, `esbuild`) | The coursekit store, in `workspaces/html-builder-<hash>/` (installed by `coursekit setup` or the first `coursekit assemble build`) | Yes |
| Remotion sources (`src/`, `package.json`, `tsconfig.json`) | `tools/remotion/` in the project | No: they are the project's and versioned with it |
| API keys and `PIPER_VOICE` | `.env` of the project | No: personal and never committed |
| The record of what `setup` installed | `installed.json` in the coursekit store | Yes, one per machine |

### The coursekit store

The store is `COURSEKIT_HOME` if you define it, else the data folder of your user:

| System | Store |
|---|---|
| macOS | `~/Library/Application Support/coursekit` |
| Linux | `~/.local/share/coursekit` (`$XDG_DATA_HOME/coursekit` if that variable is set) |
| Windows | `%LOCALAPPDATA%\coursekit` |

`coursekit doctor` shows its path and size in the Media section. To move it, see [Troubleshooting](09-troubleshooting.md#the-coursekit-store-takes-a-lot-of-space).

### Remotion is installed once

Remotion with its dependencies is about 230 MB, and the browser it downloads the first time it renders takes about 600 MB more, kept inside the same `node_modules`. Installing that in every project would waste a lot of disk and time, so `coursekit setup --media`:

1. Copies the template to `tools/remotion/` (only `src/`, `package.json` and `tsconfig.json`) if the project does not have it.
2. Runs `npm install` in the store, in `workspaces/remotion-<hash>/`, only if that folder does not exist yet.
3. Makes `tools/remotion/node_modules` a link to the `node_modules` of that folder: a symbolic link, or a junction on Windows.

The second project that runs `coursekit setup --media` downloads nothing: it only makes the link. The project `.gitignore` ignores `node_modules/`, so the link is never committed.

The `<hash>` is that of the `package.json` of the project (and of its `package-lock.json`, if there is one). Projects with the same dependencies share the install; a project that changes its dependencies gets its own install in the store, next to the other. If the link cannot be made, the project installs its own `node_modules` in `tools/remotion/`, as any Node project does; and a project that already has a real `node_modules` folder there keeps it. See [Troubleshooting](09-troubleshooting.md#the-remotion-link-cannot-be-made).

To remove everything that `setup` installed outside the projects, run `coursekit uninstall` (see [Commands](03-commands.md#coursekit-uninstall) and [Getting started](01-getting-started.md#uninstall)).

## Theme tokens

Infographics, diagrams, GIFs, simulations and videos use the colours and fonts of the course theme so they look like the course. Those values are the design tokens: `tokens.json` (the values) and `tokens.css` (the same values as CSS custom properties, plus base classes for simulations). Nobody writes them by hand: coursekit derives them from the theme of the assembly platform (slxd creator backend) or from the stylesheet of the project (html backend) and records where they come from, so the media and the assembled course share the same colours and fonts.

### Define the theme

The `/define-theme [CODE]` command (design agent; `coursekit run define-theme [CODE]` from a terminal) does the whole flow, and `/new-course` reminds the person to run it when the project has no tokens yet. When the theme is already defined (tokens derived and a style guide of the media), it **completes** it: what exists stays as it is and is not proposed again, the agent adds only what is missing (a block of the style still with the defaults of coursekit, such as `media › job_aid`, or a section of the guide) and says what it added; the guide then asks for a new signature because of those sections. To redo a part, say so: `/define-theme redo the style of the videos`. The first time:

1. `coursekit theme show` tells whether tokens already exist and where they come from.
2. The agent lists the themes of the platform (`list_themes`) and, with the person, picks one, creates one (from scratch, from a preset or as a copy of another) or adapts one with `update_theme` using the colours and fonts of the client's brand. A theme change in the platform changes every content that uses it, so a course that needs its own look gets a copy of the theme.
3. The agent saves the whole result of `get_theme` to `.cache/theme/get_theme.json` (a cache folder, not committed).
4. `coursekit theme import .cache/theme/get_theme.json` converts it into `tokens.json` and `tokens.css`, and prints the notes and the contrast of each pair. If a pair fails, the colour is fixed in the platform (`update_theme`), `get_theme` is saved again and the import is repeated. The tokens are never edited by hand.
5. The agent links the theme to the contents with `set_content_theme`, using the id that `coursekit theme show --course <CODE>` prints; contents created later get it when they are assembled ([08-assembly-and-delivery.md](08-assembly-and-delivery.md)). The person validates the theme the way they validate the design.

The platform theme can be redone at any time: importing again overwrites the tokens, and `coursekit media plan` then warns about the assets made with the previous ones.

With the html backend there is no platform theme and steps 2, 3 and 5 do not apply: the agent writes or adapts `theme/maqueta.css` (or `courses/<CODE>/theme/maqueta.css` for one course) with the brand in the CSS variables, and runs `coursekit theme import theme/maqueta.css` (add `--course CODE` for the own theme of a course). The package already uses the stylesheet without the import; the import is what gives the media the same tokens and satisfies the guard ([The media guard](#the-media-guard)).

### The tokens file

`theme/tokens.json` for a theme named "ACME training" (version 3), shortened:

```json
{
  "origin": {"source": "creator", "theme_id": "11111111-2222-4333-8444-555555555555", "name": "ACME training",
             "version": 3, "imported_at": "2026-10-09T10:14:30+02:00",
             "derived": ["accent-ink", "border", "correct-ink", "surface", "surface-highlight", "text-muted", "wrong-ink"],
             "defaults": ["radius", "space", "shadow"], "notes": []},
  "color": {"background": "#FFFFFF", "text": "#000000", "headings": "#1B365D", "accent": "#0A58CA",
            "on-accent": "#FFFFFF", "link": "#0A58CA", "correct": "#14733A", "on-correct": "#000000",
            "wrong": "#B3261E", "on-wrong": "#000000", "text-muted": "#595959", "surface": "#F5F5F5",
            "surface-highlight": "#E2EBF9", "border": "#CCCCCC", "accent-ink": "#0A58CA", "correct-ink": "#14733A",
            "wrong-ink": "#B3261E"},
  "font": {"family": "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
           "headings": "'ACME Sans', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
           "ui": "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
           "size-base": "17px", "line-height": "1.5"},
  "radius": "8px",
  "shadow": {"soft": "0 2px 8px rgba(0, 0, 0, 0.12)"},
  "space": {"xs": "4px", "sm": "8px", "md": "16px", "lg": "24px", "xl": "32px"}
}
```

`origin` says where the file comes from: `source` (`creator`), the id, name and version of the platform theme, the date of the import, the tokens that were `derived` (not in the platform) and the groups that are package `defaults`, and the `notes` printed by the import. A `tokens.json` whose `origin.source` is neither `creator` nor `css` counts as written by hand.

Derived from a stylesheet, the `origin` is different (the values, shortened, are those of the stylesheet):

```json
{
  "origin": {"source": "css", "file": "maqueta.css", "sha256": "3f9a1c07be52",
             "imported_at": "2026-10-09T10:14:30+02:00", "notes": []},
  "color": {"background": "#FFFFFF", "text": "#1A1A1A", "headings": "#1A1A1A", "accent": "#7A1FA2"},
  "font": {"family": "'ACME Sans', sans-serif", "headings": "'ACME Sans', sans-serif", "size-base": "16px", "line-height": "1.6"},
  "radius": "8px"
}
```

`file` is the name of the stylesheet and `sha256` the first 12 characters of the hash of its content; `coursekit theme show` prints them as `origin: CSS variables of maqueta.css (fingerprint 3f9a1c07be52), imported on 2026-10-09`. There are no `derived` and `defaults` lists: the base layout of the package declares every token, so the stylesheet only changes the ones it wants.

`coursekit theme tokens` rewrites `tokens.css` from `tokens.json`: `:root` custom properties (`--color-<name>`, `--font-family`, `--font-family-headings`, `--font-family-ui`, `--font-size-base`, `--line-height`, `--radius`, `--shadow-<name>`, `--space-<name>`; `font.google`, if present, becomes an `@import`) and the base classes for simulations (`.btn`, `.card`, `.is-correct`, `.is-wrong`, `.note`). Do not edit the CSS by hand either.

### One theme per project, one per course

A project has one theme, in `theme/`, which every course inherits. A course that needs its own look defines it with `/define-theme <CODE>` (`coursekit theme import FILE --course CODE`), which writes `courses/<CODE>/theme/tokens.json` and `tokens.css` and records `slxd.theme_id` in the `course.yaml`. From then on that course uses its own tokens: a course uses the tokens of `courses/<CODE>/theme/` when `tokens.json` exists there, and the project's otherwise. `coursekit theme show CODE` says which ones apply to a course. The project-level accent still paints the catalog Excel (see below).

### What is derived and what comes from the platform

| Tokens | Origin |
|---|---|
| `background`, `text`, `headings`, `accent`, `on-accent` (the `accentText` role), `link`, `correct`, `on-correct`, `wrong`, `on-wrong` | The semantic colour roles of the platform theme, with palette references resolved. A text role the theme does not set inherits the text colour. |
| `text-muted`, `surface`, `surface-highlight`, `border`, `accent-ink`, `correct-ink`, `wrong-ink` | Derived by coursekit from the colours above (mixes of text, background and accent); the muted text is kept at least 4.5:1 on the background. `accent-ink`, `correct-ink` and `wrong-ink` are the accent and the colours of state as ink (a line, a mark, a word on the background): the colour itself when it reads there, darkened towards the text until it does. Listed in `origin.derived`; a role the project fixes (`theme.roles`) takes its colour instead and goes to `origin.set`. |
| `palette.<id>` | The named colours of the platform theme (`emerald`, `cayenne`, `prussian`…), imported with their ids, to draw with: portraits, illustrations. They are not roles and they do not change the fingerprint of the tokens. In `tokens.css` they are `--palette-<id>`. |
| `font.family`, `font.headings`, `font.ui` | The font assignments of the theme: the system font stack, an uploaded font by its name (followed by the system stack as fallback), or a font included in the platform by its id, with a note because the name may not match its CSS family. |
| `font.size-base`, `font.line-height` | The base font size and line height of the theme. |
| `radius`, `space`, `shadow` | Package defaults: the platform has no such values. Listed in `origin.defaults`; the project can fix the radius and the shadow (`theme.radius`, `theme.shadow`). |

With the html backend the tokens come from the CSS variables of the base layout of the package with the stylesheet over it (`coursekit theme import FILE.css`); a `var(--x)` reference is resolved, the last declaration of a variable wins, and nothing is derived by coursekit:

| CSS variable | Token |
|---|---|
| `--color-<name>` | `color.<name>`: `background`, `text`, `text-muted`, `headings`, `accent`, `accent-ink`, `on-accent`, `link`, `surface`, `surface-highlight`, `border`, `correct`, `wrong`, `correct-ink`, `wrong-ink` (the base layout declares them all; add others if you need them). A value that is not a plain colour (a gradient, `color-mix()`) is kept as written and left out of the contrast check, with a note. |
| `--font-family`, `--font-family-headings`, `--font-family-ui` | `font.family`, `font.headings`, `font.ui` |
| `--font-size-base`, `--line-height` | `font.size-base`, `font.line-height` |
| `--radius` | `radius` |
| `--space-<name>` | `space.<name>` (`xs`, `sm`, `md`, `lg`, `xl`) |
| `--shadow-<name>` | `shadow.<name>` (`soft`) |

### Limits

- The tokens are the light mode. When the platform theme has a dark mode, the import leaves a note saying so; the media are produced in light mode.
- A colour role that cannot be resolved falls back to a default and leaves a note.
- With the html backend, only the variables above are read: the rest of `theme/maqueta.css` (selectors, layout rules) restyles the package but does not reach the tokens. The reading is textual: every `--name: value` declaration of the file counts wherever it is (also inside a selector other than `:root`) and the last one wins; the blocks of at-rules (`@media`, `@supports`...) are skipped, so the variables of a dark mode or of a print layout never reach the tokens.

### The media guard

The asset types that use the tokens are listed in `uses_theme` of the media configuration (`infographic`, `diagram`, `animated_gif`, `simulation`, `video`, `terminal_demo` and `job_aid` by default; see [04-configuration.md](04-configuration.md)). For them:

- `coursekit media plan` warns when the course has assets of those types and its tokens are missing or were written by hand (neither `creator` nor `css` origin), and for each produced or uploaded asset that was made with other tokens than the current ones (produce it again).
- `coursekit media set CODE ID --status produced` (or `uploaded`) is refused until the tokens are derived: from the platform theme (creator backend) or from the stylesheet of the project (html backend, `coursekit theme import FILE.css`). `--force` skips the check, for the rare case of a course that deliberately does not follow the theme.
- When it goes through, the asset stores a fingerprint of the tokens (`theme`, in `media/manifest.yaml`). If the theme changes and is imported again, the fingerprint no longer matches and `plan` warns. The fingerprint covers the colours, fonts, radius, spacing and shadows, not the origin or the date, so importing the same theme again does not raise warnings.

The media agent stops and asks the person to run `/define-theme` when the tokens are missing, instead of inventing colours.

### The brand material

The theme of the platform gives the colours and the fonts of the course; the brand says how they are used. You leave the brand material in `theme/branding/` (or, for a course with a brand of its own, in `courses/<CODE>/theme/branding/`, which wins as a whole over the project's) as you leave the reference material in `brief/`, and [`coursekit brand`](03-commands.md#coursekit-brand) converts it for the agents:

```
theme/branding/
  sources/      ← what you leave: brand book, token files, fonts, logos, images
  links.md      ← two parts: the brand material read whole (a Storybook, a brand website, a documentation)
                  and "# Websites to infer the style from" (the website of the company, observed in a browser)
  notes.md      ← your indications ("lavender only as a fill", "no logo in the videos"…)
  index.md      ← written by coursekit brand: what there is and where; the agents read it first
  text/         ← written by coursekit brand: the material as Markdown, what was observed
  fonts/        ← fonts/fonts.css and the font files (yours, or Google Fonts with an open licence)
  logo/, tokens/, style/
  media-style.md  ← the style guide of the media, written by the agent from all of this and signed by you
```

A brand kit (`.zip`) or the package of a design system (`.tgz`) left in `sources/`, or the page of that package on npm in `links.md` (it is downloaded from the registry), is opened and only its fonts, icons, logos and token files are taken; the icons go to `icons/`, to be used as they are. A Storybook is read whole: every page of documentation and every component, with its props, its stories and its page, from the manifests it publishes. A website under the second heading is not read but looked at: its CSS variables, the styles of its headings, links, buttons and cards, its colours weighted by the area they cover, its fonts, its logo and a screenshot. What is observed is a clue for the agent, never a rule: when it contradicts the brand material, the brand wins. The fonts of `fonts/fonts.css` go inside the videos and the SVGs exported as PNG (`media › fonts`), so they look the same on any machine; a font the brand uses with no usable files (a font served by a website is not licensed to copy) is listed in the index for you to provide.

### Colours of the brand for the roles

Some colour roles of the tokens do not exist in the platform and coursekit derives them (`text-muted`, `surface`, `surface-highlight`, `border`, `accent-ink`, `correct-ink`, `wrong-ink`, mixed from the text, the background and the accent), and the radius and the shadow are package defaults. A brand usually has its own colour for those uses. The project fixes them in `project.yaml › theme` (a course with its own tokens, in `course.yaml › theme`), without touching the platform theme:

```yaml
theme:
  source: tenant_default
  roles: {surface: grey-lightest, border: grey-light, text-muted: grey-darkest, accent-ink: text}
  radius: 0
  shadow: none
```

`border` (px; the colour of the borders is the role `border` of `roles`) and `weights` (`{normal: 300, strong: 500}`) fix the width of the borders and the two weights of the text the same way. Any role can be fixed, also one the platform gives when the brand says otherwise (the text on a fill of state, for example); the course in the platform keeps the platform's. A role takes the name of a colour of the palette of the theme (`coursekit theme roles` lists it), another role, or a hex when the brand defines it and the palette lacks it. `coursekit theme import` applies them instead of deriving, records them in `origin.set` and, if a name is not in the palette, stops with the list. `coursekit theme roles` shows each role, its value, where it comes from and where it is seen in the media (the background of the cards of a comparison, the source under a figure…), which is how a person chooses, and what the agent of `/define-theme` quotes when it proposes a colour. The radius and the shadow of the theme also reach the videos.

### Illustration sources

The illustrations of a brand look alike: one hand, one line, one palette. When a studio's illustrations fit the brand, its page on Magnific goes under `# Illustration sources` in `theme/branding/links.md` (`https://www.magnific.com/author/<name>`). With `MAGNIFIC_API_KEY`, [`coursekit brand`](03-commands.md#coursekit-brand) finds the id of that author, keeps a few previews of its work in `style/` (references of the style; a preview costs no download) and writes the source to `theme/branding/illustration-sources.json`.

The media agent then looks there first for a **concept illustration**, one that goes with a concept of the content and reinforces it: [`coursekit media stock CODE ID --find "…"`](03-commands.md#coursekit-media) lists the illustrations of the sources that match (in English, the language of the catalog) and come as SVG, and `--take` downloads the chosen one, recolours it to the ink and the paper of the brand (`media › stock`) and records in the manifest where it comes from and its licence. A studio usually publishes each illustration in several versions; with `stock.color: black` only the line versions are searched and a colour one is refused. What the script asks for on top (the accent on one element) is added by hand, and when nothing fits the agent combines elements of several or generates one in the same style, with the previews as reference.

A download through the API of a plan with stock downloads costs no credits, within its daily limit; a premium plan needs no attribution. The option is `magnific-stock` in `media.yaml › types.image` (`only: illustration`), offered when there are sources and a key.

The kinds of illustration are those the style guide describes: a **diagram** (a type of its own, drawn as SVG with the tokens), a **concept illustration** (from the sources, in the colours of the guide) and a **scene** with characters (the simulations, a story), which a course can draw in a style of its own in its guide. The script of each resource says which kind it is.

### The style guide of the media

`theme/branding/media-style.md` (or, for one course, `courses/<CODE>/theme/branding/media-style.md`, which wins) is an optional file in which you write, in plain Markdown, how the media of your courses must look: the exact composition of a video cover, colours by token name, typography, and above all what must **not** appear. The media agent reads it before producing anything and it overrides coursekit's defaults for the types it covers; it can be as narrow (only the cover of videos) or as wide as you want, and you add a section per type as you need it. Be exact: sizes in pixels and the position of each element make every cover come out the same. Colours are best named by their token (`--palette-<id>` and `--color-<role>` of `theme/tokens.css`), which are already in the project; what the file mentions from outside the project (a logo, a font file) must be copied into `theme/branding/`, because the headless session of the agent only reads the project. `coursekit agents` is not needed after editing it: it is read as it is. If an instruction cannot be followed the agent says so and does the closest thing without adding elements.

With brand material, the agent of `/define-theme` writes the guide from it ([The brand material](#the-brand-material)): colour, data graphics, typography, shape, icons, motion, videos, images, logo and what never appears, each rule with the place of the brand it comes from in brackets; what the brand does not state goes as a question, not as a rule. A person reads it and signs it: the guide of the project once for every course that uses it, `coursekit approve media-style`, and a course's own guide with its code, `coursekit approve media-style CODE`: while it is not signed, or after it changes, no visual resource is marked produced (`rules › review › media_style: none` turns the signature off; the handoff signs it itself). In a session with no one to ask, the agent applies only what the brand says in so many words and lists the rest in `theme/branding/brand-report.md`.

The guide ends with a table of the indications of `theme/branding/notes.md` (the answers of the person, one per line): each one copied as it is, with the section of the guide where it applies or why it does not apply to the media. That table is how coursekit knows that every indication reached the guide: `coursekit approve media-style` lists, before asking, the lines of `notes.md` the guide does not quote, and `coursekit media plan` warns of them. The media agent reads `notes.md` too, and where it and the guide differ, the notes win and the agent says so in its report, so that the guide is written again. An icon the library of the brand lacks is drawn with the rules of the guide for icons (grid, stroke, joins, live area), measured on the icons of the library, saved in `media/files/icons/` and listed in the report of the agent, for a person to add it to the library.

The visual style of the scenes, characters, objects and illustrations is chosen with `media › visual › style` (`flat`, `pixel-art`, `3d`, `isometric`, `illustration` or `photo`; see [`media`](04-configuration.md#media-production-options)); `media-style.md` adds the details. Reference images of the style go in `theme/branding/style/` (or the course's `theme/branding/style/`). Reference scenes, the result the scenes of the courses aim at (inside and outside, with and without people, adults and children), go in `style/scenes/`, with example model sheets of characters: the agent passes the closest one as the style reference of each new scene, builds a model sheet per character and checks the hands before an image is produced. Without an image generator the style is `visual.fallback` (`flat`), drawn as SVG.

### Change the theme after producing the media

If the theme was wrong (for example the default theme of the tenant) the media made with it carries the wrong look. To redo it:

1. Fix the theme in the platform (or choose another one) and import it again. If the wrong theme was the project's, `coursekit run define-theme` (without a code) overwrites `theme/tokens.json`, which every course without its own theme inherits. `coursekit run define-theme CODE` writes the theme of that one course in `courses/<CODE>/theme/` instead and leaves the project's alone ([One theme per project, one per course](#one-theme-per-project-one-per-course)).
2. `coursekit media redo CODE` marks the assets that use the theme and were made with other tokens (`--all` marks every one that uses the theme; `coursekit media redo CODE ID [ID ...]` the ones you name, for assets that carry the theme without being of those types, such as an image with the accent colour painted on it). They go back to `scripted`.
3. `coursekit handoff CODE` carries on (or, by hand, `/produce-media`, `/assemble`, and again `/produce-media` and `/assemble`): it produces them again, uploads them to the content of their unit, links the contents to the theme again (`set_content_theme` runs on every assembly) and assembles the course again, so the new media replace the old ones. With the html backend the course is built again instead. The old uploads stay in the platform until its storage cleanup.

A course already `delivered` is not carried on by the handoff: redo the media and the assembly by hand and deliver a new version.

### Contrast check

`coursekit theme check` reports the WCAG contrast of the colour pairs the media and components use; exit code 1 if any fails. Without tokens, it stops with `missing theme/tokens.json: derive it from the theme of the assembly platform` (with the html backend, import `theme/maqueta.css`). The pairs checked (those whose two colours exist):

| Pair (text on background) | Use | Minimum ratio |
|---|---|---|
| `text` on `background` | Body text | 4.5 |
| `text-muted` on `background` | Secondary text | 4.5 |
| `on-accent` on `accent` | Button text on the accent | 4.5 |
| `accent` on `background` | Accent elements and large text | 3.0 |
| `text` on `surface` | Text on cards | 4.5 |
| `text` on `surface-highlight` | Text on highlights | 4.5 |
| `on-correct` on `correct` | Text on the fill of what is right | 4.5 |
| `correct-ink` on `background` | What is right as ink (borders, marks, text) | 4.5 |
| `on-wrong` on `wrong` | Text on the fill of what is wrong | 4.5 |
| `wrong-ink` on `background` | What is wrong as ink (borders, marks, text) | 4.5 |

```text
  ok   text on background (body text): 21.00:1, needs 4.5:1
  FAIL on-accent on accent (button text on the accent): 4.00:1, needs 4.5:1
```

The import prints the same lines. A failing pair does not stop it: fix the colour in the platform theme (or in the CSS variable of the stylesheet) and import again.

The accent colour of the project tokens (`accent-ink`, else `accent`) also paints the header of the catalog Excel ([08-assembly-and-delivery.md](08-assembly-and-delivery.md)).

## Remotion workspace

Videos (`video`) and some GIFs are programmed with [Remotion](https://www.remotion.dev). `coursekit setup --media` copies a template to `tools/remotion/` and links its dependencies:

```text
tools/remotion/
├── package.json        scripts: studio (preview) and render
├── tsconfig.json
├── node_modules        link to the coursekit store (not committed)
└── src/
    ├── index.ts        registers the root
    ├── Root.tsx        example composition "title-card" (1920×1080, 30 fps, 120 frames)
    ├── Screencast.tsx  a real screen recording with zooms that follow the narration
    └── theme.ts        imports theme/tokens.json: color, font
```

`theme.ts` reads the project tokens; for a course with its own theme, point the composition at `courses/<CODE>/theme/tokens.json`. The media agent adds one composition per video asset in `src/videos/<asset-id>.tsx` and registers it in `Root.tsx`. From `tools/remotion/`, `npm run studio` opens the preview and `npm run render -- <composition-id> <output>` renders it. The project keeps only the sources: the dependencies are in the coursekit store and shared by every project ([Remotion is installed once](#remotion-is-installed-once)). The `remotion` option is available only when `node` is installed and `tools/remotion/node_modules` exists; a link that points at nothing does not count (`coursekit setup --media` repairs it). Remotion is free for small teams; larger companies need a licence (remotion.dev/license). `coursekit setup --media` also adds to an existing `tools/remotion/` the files the template gained since (such as `Screencast.tsx`), never over the ones the project has.

### The Screencast component

`Screencast` is the composition of a tutorial over a real recording (recipe `screen-recording`): the recording is not redrawn, and its zooms are computed from data, not baked into the video, so a zoom is changed by changing a number and rendering again. It uses the events of the recording (`media/recordings/<id>.events.json`, written by `coursekit capture replay` or by a terminal session) and the words of the narration (`<audio>.words.json`, written by `coursekit subtitles` or by the ElevenLabs voice). A zoom is for a detail that does not read at full size (a word, an indicator, one line of a change), not for every sentence or every click: a focus starts going in a moment before its words are said (`lead`), stays at least `min_hold` seconds or until the end of its sentence (or `hold` seconds), and goes back to the whole screen; two focuses close in time move from one to the other without zooming out. When the event (or the focus) has the box of what it shows (`box`: left, top, width and height as fractions of the screen, which `mark` and `point_text` of a capture session write), the zoom goes only as close as that box fits with `margin` around it, places it in the middle of the frame as far as the edges of the screen allow (so the start of a line is never cut off), and draws a mark around all of it: a rectangle (`rect`), a rounded one (`round`) or an ellipse wide enough to hold it (`ellipse`), with a line that keeps its width at any zoom and a tone that reads on its background (white with a dark halo on a dark one, the accent ink with a light halo on a light one; the event says which, `tone`). Without a box it zooms on its point and draws no mark. The numbers come from `config/video.yaml › screencast` ([`video`](04-configuration.md#video-the-style-of-the-videos-made-as-a-montage)); `coursekit video check` warns of more than one zoom in a scene, of zooms too close and of too many a minute. Without focuses, the clicks close in time and space are joined into one sustained zoom. The edges of the screen never show.

```tsx
import { Screencast } from "../Screencast";
import events from "../../../../courses/PWD/media/recordings/U1-S2-M1.events.json";
import words from "../../../../courses/PWD/media/files/u1-s2-m1.words.json";

<Screencast src={staticFile("U1-S2-M1.mp4")} events={events} words={words}
  focus={[{ word: "minimum length", event: "the minimum length" }]} zooming={{ scale: 1.4 }} />
```

| Prop | Meaning |
|---|---|
| `src` | The recording. |
| `events`, `words` | The two files above. |
| `focus` | The zooms: `word` (the words of the narration it enters with, the first time they are said after the previous focus) or `at` (a second); where: `event` (the label or the note of an event), `box` (fractions of the screen) or `fx`/`fy`; `shape` of its mark; `scale` (at most) and `hold`. A focus whose words are not said makes no zoom. |
| `auto` | Zoom on the groups of clicks when there is no focus (default `true`). |
| `startFrom`, `zooming`, `ring` | Second of the recording it starts from; the values of `config/video.yaml › screencast` (`scale`, `ease`, `lead`, `minHold`, `margin`, `mark`); the mark around what each focus shows when its box is known (default `true`). |

## Tools required per type

| Type (id) | Tools |
|---|---|
| `image` | The creator stock tools (agent MCP) for decorative images; `MAGNIFIC_API_KEY`, or the Magnific connector, to generate the rest (without them, drawn as SVG) |
| `infographic`, `diagram` | None (SVG by the agent with the theme tokens); `MAGNIFIC_API_KEY` for generated illustrations |
| `animated_gif` | `vhs` (terminal), or none (animated SVG), or `node` + Remotion |
| `terminal_demo` | `asciinema` (not on Windows) or `vhs` |
| `video` | `node` + Remotion (`tools/remotion`), `ffmpeg`, a voice provider and `stable-ts` or ElevenLabs for captions; `vhs` for terminal videos. Also the theme tokens |
| `audio` | A voice provider (`ffmpeg` for MP3 joining and Piper) |
| `simulation` | None (HTML/JS by the agent with `tokens.css`) |
| `job_aid` | A Chrome, Chromium or Edge (headless) |

The types `infographic`, `diagram`, `animated_gif`, `simulation`, `video` and `terminal_demo` also need the theme tokens derived from the platform theme, or from the stylesheet with the html backend ([Theme tokens](#theme-tokens)).

## Worked example

Produce the infographic of the course `PWD`:

```bash
coursekit media extract PWD
coursekit media plan PWD
```

```text
manifest: 3 assets (pending 3)
U1-S2-M2 [infographic] Anatomy of a strong password
  - agent-svg (yes): SVG written by the agent with the theme tokens (coursekit theme show); icons with search_stock_icons
```

The media agent (`/produce-media PWD`, or `coursekit run produce-media PWD`) writes the SVG with the tokens, saves it as `media/files/U1-S2-M2.svg` and records it:

```bash
coursekit media set PWD U1-S2-M2 --status produced --recipe agent-svg \
  --file media/files/U1-S2-M2.svg --alt "Diagram of length, variety and uniqueness"
# U1-S2-M2: produced
```

The command is refused if the course tokens are missing or were written by hand ([The media guard](#the-media-guard)): run `/define-theme` first. After uploading it to the platform, the agent records `coursekit media set PWD U1-S2-M2 --status uploaded --asset-path <path>`. The next `coursekit assemble plan` then replaces the placeholder with the image. With the html backend there is no upload: the `produced` status with its `--file` is final, and `coursekit assemble build PWD --unit 1` copies the SVG into the package ([Media for the html backend](#media-for-the-html-backend)). For a video, the same flow adds the steps `scripted` (script in `media/scripts/`), `coursekit voice set PWD <provider>`, `coursekit tts --course PWD …` and `coursekit subtitles …`.

Next: [08-assembly-and-delivery.md](08-assembly-and-delivery.md)
