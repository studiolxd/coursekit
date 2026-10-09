# Media production

How media placeholders become produced assets: the manifest, the production options, voice-over and captions, the theme tokens and the tools each type needs.

## Placeholders and types

A media placeholder is written in `content.md` (format in [06-content.md](06-content.md#media-placeholders)). Its type is one of eight resource types. Each type has an English **id**, the same in every course, which is what the configuration (`config/media.yaml › types` and `uses_theme`, `config/rules.yaml › content.placeholder_types`), the media manifest (`media/manifest.yaml › assets[].type`), the output of `coursekit media plan` and the theme guard use. What the author **writes** in the placeholder is the word of the course language for that type (for example `Infographic` in an English course and `Infografía` in a Spanish one); the table that maps each id to its words is in [06-content.md](06-content.md#media-placeholders). The word of the other language is a `coursekit verify` error that lists the valid words.

| Id | Meaning | Options, in order of preference (what each one needs) |
|---|---|---|
| `image` | Image | `magnific-api` (`MAGNIFIC_API_KEY`) · `magnific-mcp` (agent MCP tool `images_generate`) · `creator-stock` (agent MCP tool `search_stock_images`) |
| `infographic` | Infographic | `agent-svg` (nothing) · `magnific-api` |
| `diagram` | Diagram | `agent-svg` |
| `animated_gif` | Animated GIF | `vhs` (command `vhs`; terminal content only) · `agent-svg-animated` (nothing) · `remotion-gif` (`node` and `tools/remotion/node_modules`) |
| `terminal_demo` | Interactive terminal demo | `asciinema` (command `asciinema`; terminal content only) · `vhs` (video alternative; terminal content only) |
| `video` | Video | `remotion` (`node` and `tools/remotion/node_modules`) · `vhs` (terminal content only) |
| `audio` | Audio | `voice` (nothing): the voice chain below |
| `simulation` | Interactive simulation | `agent-html` (nothing): self-contained HTML/JS that uses `tokens.css` |

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
| `asset_path` | The path of the asset in the platform once uploaded (`--asset-path`) |
| `downloads` | The downloadable files: `file`, `title`, `asset_path` and `size` of each one |
| `theme` | The fingerprint of the theme tokens the asset was made with ([The media guard](#the-media-guard)) |

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

An option with several `needs:` must meet all of them. `only: terminal` limits an option to assets that show a terminal; the agent decides from the placeholder's description. If nothing is available, `media plan` prints `no option available: install a tool or set a key (coursekit config media)`.

```text
U1-S1-M1 [image] Sticky note on a monitor
  - magnific-mcp (if the agent has the MCP tool): Claude's Magnific connector
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

## Voice providers

A course uses **one** voice for all its narration, so a course never mixes voices. The choice is stored in `course.yaml › media.voice`.

| Provider | Needs (in `.env`) | Default voice | Notes |
|---|---|---|---|
| `elevenlabs` | `ELEVENLABS_API_KEY`; a voice in `ELEVENLABS_VOICE_ID` or `--voice` | none | Best quality; writes exact captions from its timestamps |
| `azure` | `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` | `es-ES-ElviraNeural` / `en-GB-SoniaNeural`; `AZURE_SPEECH_VOICE` overrides | Neural voices |
| `google` | `GOOGLE_TTS_API_KEY` | `es-ES-Chirp3-HD-Aoede` / `en-GB-Chirp3-HD-Aoede`; `GOOGLE_TTS_VOICE` overrides | Chirp 3 HD voices |
| `piper` | `PIPER_VOICE` (path to a `.onnx` voice) and the `piper` command; `PIPER_SPEAKER` for multi-speaker voices | the file in `PIPER_VOICE` | Local draft voice |

The default voice depends on the course language (`es` or `en`). In `media plan` and `media providers` the voice options are named `elevenlabs-api`, `azure-api`, `google-api` and `piper` (the providers above), plus `elevenlabs-mcp`, the agent using the ElevenLabs connector directly (without `coursekit tts`); that one is always listed, because only the agent can tell whether it has the connector. The subtitle options are `elevenlabs-timestamps` and `stable-ts`.

```bash
coursekit voice list PWD                   # providers, availability and the voice of the course
coursekit voice set PWD azure              # fixes the provider (and its default voice)
coursekit voice set PWD piper --speaker 1  # a speaker of a multi-speaker Piper voice
coursekit voice set PWD elevenlabs --voice <voice-id>
```

`voice set` needs both the course code and the provider. If the provider is not configured on this machine it warns (other people on the team may have it) but still saves it. With several providers available and none chosen, `tts` stops and asks you to run `voice set`; with none available it says which keys to set.

## `coursekit tts`

Reads a script and writes the voice-over:

```bash
coursekit tts --course PWD --in courses/PWD/media/scripts/U1-S2-M1.md --out courses/PWD/media/files/U1-S2-M1.mp3
```

| Option | Meaning |
|---|---|
| `--in FILE`, `--out FILE` | Script (whitespace is collapsed) and output audio; both required |
| `--course CODE` | Use the voice of that course and its language. Without it, the language is `es` |
| `--engine elevenlabs\|azure\|google\|piper` | Force a provider instead of the course's |
| `--voice V` | Force a voice. Otherwise: the course voice (if same provider), then the provider's environment variable, then the default for the language |
| `--speaker N` | Speaker of a multi-speaker Piper voice |

The provider is `--engine`, else the course's `media.voice.provider`, else the only provider available. Long scripts are split at sentence ends (Azure 4,000 bytes, Google 4,500) and joined with `ffmpeg`; Piper also needs `ffmpeg` to write MP3 (an `--out` ending in `.wav` keeps the WAV). ElevenLabs also writes `<out>.vtt` (same name, `.vtt`) with captions from its timestamps, grouped at sentence ends or about 84 characters.

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

The `/define-theme [CODE]` command (design agent; `coursekit run define-theme [CODE]` from a terminal) does the whole flow, and `/new-course` reminds the person to run it when the project has no tokens yet:

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
             "derived": ["accent-strong", "highlight", "line", "surface", "text-soft"],
             "defaults": ["radius", "space", "shadow"], "notes": []},
  "color": {"background": "#FFFFFF", "text": "#000000", "headings": "#1B365D", "accent": "#0A58CA",
            "on-accent": "#FFFFFF", "link": "#0A58CA", "correct": "#14733A", "on-correct": "#000000",
            "wrong": "#B3261E", "on-wrong": "#000000", "text-soft": "#595959", "surface": "#F5F5F5",
            "highlight": "#E2EBF9", "line": "#CCCCCC", "accent-strong": "#0A58CA"},
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
| `text-soft`, `surface`, `highlight`, `line`, `accent-strong` | Derived by coursekit from the colours above (mixes of text, background and accent); the soft text is kept at least 4.5:1 on the background. `accent-strong` equals `accent`. Listed in `origin.derived`. |
| `font.family`, `font.headings`, `font.ui` | The font assignments of the theme: the system font stack, an uploaded font by its name (followed by the system stack as fallback), or a font included in the platform by its id, with a note because the name may not match its CSS family. |
| `font.size-base`, `font.line-height` | The base font size and line height of the theme. |
| `radius`, `space`, `shadow` | Package defaults: the platform has no such values. Listed in `origin.defaults`. |

With the html backend the tokens come from the CSS variables of the base layout of the package with the stylesheet over it (`coursekit theme import FILE.css`); a `var(--x)` reference is resolved, the last declaration of a variable wins, and nothing is derived by coursekit:

| CSS variable | Token |
|---|---|
| `--color-<name>` | `color.<name>`: `background`, `text`, `text-soft`, `headings`, `accent`, `accent-strong`, `on-accent`, `link`, `surface`, `highlight`, `line`, `correct`, `wrong` (the base layout declares them all; add others if you need them). A value that is not a plain colour (a gradient, `color-mix()`) is kept as written and left out of the contrast check, with a note. |
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

The asset types that use the tokens are listed in `uses_theme` of the media configuration (`infographic`, `diagram`, `animated_gif`, `simulation` and `video` by default; see [04-configuration.md](04-configuration.md)). For them:

- `coursekit media plan` warns when the course has assets of those types and its tokens are missing or were written by hand (neither `creator` nor `css` origin), and for each produced or uploaded asset that was made with other tokens than the current ones (produce it again).
- `coursekit media set CODE ID --status produced` (or `uploaded`) is refused until the tokens are derived: from the platform theme (creator backend) or from the stylesheet of the project (html backend, `coursekit theme import FILE.css`). `--force` skips the check, for the rare case of a course that deliberately does not follow the theme.
- When it goes through, the asset stores a fingerprint of the tokens (`theme`, in `media/manifest.yaml`). If the theme changes and is imported again, the fingerprint no longer matches and `plan` warns. The fingerprint covers the colours, fonts, radius, spacing and shadows, not the origin or the date, so importing the same theme again does not raise warnings.

The media agent stops and asks the person to run `/define-theme` when the tokens are missing, instead of inventing colours.

### Contrast check

`coursekit theme check` reports the WCAG contrast of the colour pairs the media and components use; exit code 1 if any fails. Without tokens, it stops with `missing theme/tokens.json: derive it from the theme of the assembly platform` (with the html backend, import `theme/maqueta.css`). The pairs checked (those whose two colours exist):

| Pair (text on background) | Use | Minimum ratio |
|---|---|---|
| `text` on `background` | Body text | 4.5 |
| `text-soft` on `background` | Secondary text | 4.5 |
| `on-accent` on `accent` | Button text on the accent | 4.5 |
| `accent` on `background` | Accent elements and large text | 3.0 |
| `text` on `surface` | Text on cards | 4.5 |
| `text` on `highlight` | Text on highlights | 4.5 |
| `correct` on `background` | Correct feedback | 4.5 |
| `wrong` on `background` | Wrong feedback | 4.5 |

```text
  ok   text on background (body text): 21.00:1, needs 4.5:1
  FAIL on-accent on accent (button text on the accent): 4.00:1, needs 4.5:1
```

The import prints the same lines. A failing pair does not stop it: fix the colour in the platform theme (or in the CSS variable of the stylesheet) and import again.

The accent colour of the project tokens (`accent-strong`, else `accent`) also paints the header of the catalog Excel ([08-assembly-and-delivery.md](08-assembly-and-delivery.md)).

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
    └── theme.ts        imports theme/tokens.json: color, font
```

`theme.ts` reads the project tokens; for a course with its own theme, point the composition at `courses/<CODE>/theme/tokens.json`. The media agent adds one composition per video asset in `src/videos/<asset-id>.tsx` and registers it in `Root.tsx`. From `tools/remotion/`, `npm run studio` opens the preview and `npm run render -- <composition-id> <output>` renders it. The project keeps only the sources: the dependencies are in the coursekit store and shared by every project ([Remotion is installed once](#remotion-is-installed-once)). The `remotion` option is available only when `node` is installed and `tools/remotion/node_modules` exists; a link that points at nothing does not count (`coursekit setup --media` repairs it). Remotion is free for small teams; larger companies need a licence (remotion.dev/license).

## Tools required per type

| Type (id) | Tools |
|---|---|
| `image` | `MAGNIFIC_API_KEY`, or the Magnific connector, or the creator stock tools (agent MCP) |
| `infographic`, `diagram` | None (SVG by the agent with the theme tokens); `MAGNIFIC_API_KEY` for generated illustrations |
| `animated_gif` | `vhs` (terminal), or none (animated SVG), or `node` + Remotion |
| `terminal_demo` | `asciinema` (not on Windows) or `vhs` |
| `video` | `node` + Remotion (`tools/remotion`), `ffmpeg`, a voice provider and `stable-ts` or ElevenLabs for captions; `vhs` for terminal videos. Also the theme tokens |
| `audio` | A voice provider (`ffmpeg` for MP3 joining and Piper) |
| `simulation` | None (HTML/JS by the agent with `tokens.css`) |

The types `infographic`, `diagram`, `animated_gif`, `simulation` and `video` also need the theme tokens derived from the platform theme, or from the stylesheet with the html backend ([Theme tokens](#theme-tokens)).

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
