# Troubleshooting

Find out what is missing with `coursekit doctor`, fix it with `coursekit setup`, and look up the common problems.

## coursekit doctor

```bash
coursekit doctor
```

It prints what is installed and configured on this machine for the current project. It changes nothing and always ends normally. Every line has a mark and, when something is missing, the command that fixes it after an arrow:

| Mark | Meaning |
|---|---|
| `ok` | fine |
| `missing` | needed and not found; the line suggests the fix |
| `info` | for your information, or optional |

### Base

| Check | Meaning and fix |
|---|---|
| `coursekit <version> (Python <x.y>)` | `missing` if Python is older than 3.12. Reinstall with uv, which brings a valid Python: `uv tool install --force git+https://github.com/studiolxd/coursekit` |
| `.env` | your personal settings file. Fix: `coursekit setup` |
| `signing identity` | the name and email that sign approvals. Fix: `coursekit setup --identity` |
| `git hooks` / `not a git repository` | `info` when the folder is not a git repository. Otherwise the hooks (`.githooks`) are not active. Fix: `coursekit setup` |
| `MarkItDown (coursekit brief)` | the library that converts the brief documents. Fix: reinstall coursekit |
| `Node (web links of brief/links.md)` | needed only to download the URLs of the brief. Fix: `coursekit setup --media` |
| `html backend builder (@studiolxd/scorm and esbuild)` | shown only when the project assembles with the html backend. `ok` when the builder is installed in the coursekit store; `info`, with the fix after the arrow, when it is not. Fix: `coursekit setup` (it needs Node and npm). See [The html backend](#the-html-backend) |

### Agent tools

| Check | Meaning and fix |
|---|---|
| `slxd MCP server 'slxd-creator'` | `info` with "no mcp_url" when `project.yaml › platform.slxd.mcp_url` is empty. Fix: set it, then `coursekit agents` |
| `<tool>: not installed` | `info`: that AI tool is not on this machine. Harmless if you use another one |
| `<tool>: skills and commands` | the tool does not see the generated skills and commands. Fix: `coursekit agents` |
| `<tool>: MCP slxd-creator` | the MCP server is not in the tool's configuration (shown only when the URL is set). Fix: `coursekit agents` |
| `<role>: <tool> · <model>` | the tool of that role is not installed. Install it or change `<ROLE>_AGENT` in `.env`. `default model` means the tool's own default |
| `writer and reviewer use the same tool and model` | `info`: another model for the review catches more. Change `REVIEWER_AGENT` / `REVIEWER_MODEL` |

### Network

| Check | Meaning and fix |
|---|---|
| `corporate CA certificate: NODE_EXTRA_CA_CERTS` | a certificate listed in `project.yaml › network › ca_bundles` exists but `NODE_EXTRA_CA_CERTS` is not set. Fix: `coursekit setup` |
| `no corporate CA certificate configured or found` | `info`: nothing to do unless you are behind a TLS-inspecting proxy (see below) |

### Mirror folder

| Check | Meaning and fix |
|---|---|
| `no mirror folder` | `info`: `mirror.provider` is `none` |
| `<provider>: MIRROR_DIR` | `MIRROR_DIR` is empty or the folder does not exist. Fix: set it in `.env` to the local path of the synced folder |

### Project theme

| Check | Meaning and fix |
|---|---|
| `tokens derived from the theme of the platform` | `ok`: `theme/tokens.json` exists and carries the `origin` of a platform theme (imported with `coursekit theme import`) |
| `no design tokens (theme/tokens.json)` | `info`: the project has no tokens yet. Fix: `/define-theme` before producing media |
| `tokens written by hand, not derived from the platform` | `info`: `theme/tokens.json` exists but has no platform origin. Fix: `/define-theme` before producing media |

The check looks at the project's tokens (`theme/`); a course with its own theme is checked with `coursekit theme show --course CODE`. See [Theme and design tokens](02-workflow.md#theme-and-design-tokens).

### Media

Optional. Install what is missing with `coursekit setup --media`: `ffmpeg`, `vhs`, `asciinema` (not available on Windows; terminal demos use VHS), `piper`, `stable-ts`, and `PIPER_VOICE` (path to the draft voice). The four API keys (`ELEVENLABS_API_KEY`, `AZURE_SPEECH_KEY`, `GOOGLE_TTS_API_KEY`, `MAGNIFIC_API_KEY`) show `ok` when set and `info` when not. It also shows two lines about what is installed once per machine ([Where the tools live](07-media.md#where-the-tools-live)):

| Check | Meaning and fix |
|---|---|
| `coursekit store <path> (<size>)` | `info`, shown when the store exists: where it is and how much it takes. See [The coursekit store takes a lot of space](#the-coursekit-store-takes-a-lot-of-space) |
| `Remotion dependencies (tools/remotion/node_modules)` | Shown when the project has `tools/remotion`. `missing` when `node_modules` is not there, or is a link that points at nothing (the store was removed or moved). Fix: `coursekit setup --media`. See [Remotion dependencies are missing](#remotion-dependencies-are-missing) |

See [Media](07-media.md).

## coursekit setup

`setup` prepares this machine for the project and can be repeated at any time. See [Getting started](01-getting-started.md) for the full list of steps.

| Option | What it does |
|---|---|
| (none) | `.env`, identity, network, hooks, roles, skills and commands, the html backend builder (only for html projects), offer of media tools, doctor report |
| `--identity` | only sets or changes the signing identity |
| `--name NAME`, `--email EMAIL` | the identity, without asking. Changing only one keeps the other |
| `--roles` | choose again the tool and model of each role |
| `--media` | also install the media tools, without asking |
| `--yes`, `-y` | ask nothing; take the defaults |

Without a terminal, `setup` never asks. Questions are skipped and the missing pieces are reported.

## Common problems

### "no signing identity" / signing identity missing

Approvals need your name and email. Run `coursekit setup --identity`, or give them directly:

```bash
coursekit setup --identity --name "Ana Ruiz" --email ana@acme.example
```

They are saved in `.env` as `COURSEKIT_USER_NAME` and `COURSEKIT_USER_EMAIL`. The git identity is only a suggestion; signatures never use it.

### "no project.yaml found in ... or any parent folder"

You are outside a project. `cd` into the project folder (any subfolder works), or point to it:

```bash
COURSEKIT_PROJECT=/path/to/acme-courses coursekit status
```

On Windows PowerShell: `$env:COURSEKIT_PROJECT = "C:\path\to\acme-courses"`.

### "coursekit: ... already a project; use `coursekit init --update`"

`init` never overwrites a project. Use `coursekit init --update` to refresh the generated files.

### `coursekit` is not found after installing

Run `uv tool update-shell` and open a new terminal.

### "<tool> is not installed on this machine"

A command tried to launch an AI tool that is not installed. `coursekit roles` shows the tool of every role and marks the missing ones `(not installed)`. Install the tool, or change the role in `.env` (`WRITER_AGENT=opencode`), or choose again with `coursekit setup --roles`. For a single launch use `--agent` and `--model`. `<ROLE>_AGENT` accepts only `claude`, `opencode` and `codex`.

### MCP URL missing

Without `platform.slxd.mcp_url`, the agents cannot reach SLXD Creator. The instructional design is done in creator with either backend, so the URL is needed with the html backend too (the end of `init` warns when it is missing, whichever backend you chose); with the creator backend, assembly and delivery run on it as well. Put the URL (`https://<tenant>.slxd.app/mcp/creator`) in `project.yaml` and run `coursekit agents`: it adds the server to `.mcp.json`, `opencode.json` and `.codex/config.toml`. If it reports that a JSON file is not valid, fix that file and run it again.

### Corporate proxy and certificates

A proxy that inspects TLS makes Claude Code, opencode, npm and uv fail with certificate errors. List the certificate in `project.yaml`:

```yaml
network:
  ca_bundles:
    - /etc/ssl/certs/acme-ca.pem
```

Paths may use `~` and environment variables; the first one that exists on the machine is used. Then run `coursekit setup`: it offers to set `NODE_EXTRA_CA_CERTS` and `UV_NATIVE_TLS=1` for your user (the Windows user environment, or a line in `~/.zshrc`, or `~/.bashrc` if your shell is bash). Open new terminals and restart the AI tools afterwards. To do it by hand, set both variables yourself.

### Mirror folder problems

`coursekit publish --check` reports the configuration without publishing:

| Message | Fix |
|---|---|
| `no mirror folder configured` | the provider is set but `MIRROR_DIR` is not: set it in `.env` (with `mirror.provider: none`, `publish` just says there is nothing to publish) |
| `MIRROR_DIR is not set in .env` | add it: the local path of the folder synced by the desktop client |
| `MIRROR_DIR does not exist` | check the path; the desktop client must have synced the folder |
| `mirror.url is a sharing link without a folder path` | copy the address from the browser bar of the folder instead |
| `cannot replace ... (is it open in Excel?)` | close the catalog spreadsheet and publish again |

Put paths with spaces between quotes in `.env`. The mirror is a read-only copy: anything edited there is overwritten on the next publication. The commands that change a course publish it by themselves when there is a mirror folder; if the folder cannot be written they only print a warning (`the mirror folder could not be updated`) and the course is not affected: fix the cause and run `coursekit publish`.

### Theme tokens: missing, written by hand or out of date

The design tokens of the media (colours and fonts) must be derived from the theme of the platform with `/define-theme` (see [Theme and design tokens](02-workflow.md#theme-and-design-tokens)). `coursekit theme show --course CODE` says which tokens a course uses and where they come from. These are the messages and what to do; `<CODE>` stands for the course code.

| Message | Meaning and fix |
|---|---|
| `<CODE> has no theme tokens: define the theme with /define-theme before producing infographics, diagrams, simulations or videos (--force to skip it)` | Shown by `coursekit media plan` as a warning and by `coursekit media set CODE ID --status produced` as a refusal, for infographics, diagrams, animated GIFs, simulations and videos. Neither the project nor the course has tokens. Run `/define-theme` (the theme of the project) or `/define-theme <CODE>` (a theme of its own for the course), validate the theme and repeat. `--force` marks the asset anyway; use it only if the asset does not depend on the look of the course |
| ``<path> does not exist: define the theme with /define-theme (or `coursekit theme import`)`` | The same situation, as `coursekit theme show` reports it |
| `the tokens of <CODE> do not come from the theme of the platform (written by hand): import them with /define-theme (--force to skip it)` | `tokens.json` exists but has no platform origin, because it was written by hand. Run `/define-theme`: the import replaces the file with tokens derived from the theme of the platform. If you had adjusted values on purpose, make that change in the platform theme instead. `coursekit theme show` words it as `the tokens do not come from the theme of the platform (written by hand): import them with /define-theme` |
| `<asset> was produced with other theme tokens: produce it again` | The asset was marked `produced` with some tokens and the theme was imported again with different colours or fonts. `coursekit media plan` lists it. Produce it again (`/produce-media <CODE> <asset>`) and mark it with `coursekit media set`. Assets marked before coursekit recorded the tokens are not reported |
| `the file does not look like a get_theme result (no theme.config.colors)` | `coursekit theme import FILE` received a file that is not the complete result of `get_theme` (or is not JSON). Call `get_theme` again and save the whole result, unchanged, to `.cache/theme/get_theme.json` |
| `the file <path> does not exist` / `coursekit: theme import needs the file with the get_theme result` | The path of the file is wrong or missing: `coursekit theme import .cache/theme/get_theme.json [--course CODE]` |
| `some pair is below the minimum contrast: fix it in the theme of the platform (update_theme) and import it again; do not edit the tokens by hand` | After the import, a line `FAIL <foreground> on <background> (<use>): <ratio>:1, needs <minimum>:1` shows a colour pair under its minimum (4.5:1 for text, 3.0:1 for the accent on the background). Correct the colour in the theme of the platform (`/define-theme` does it with `update_theme`) and import again. `coursekit theme check` exits with 1 until every pair passes |
| `some pair is below the minimum contrast: fix the colour in the stylesheet and import it again; do not edit the tokens by hand` | The same as above, for the html backend: the tokens come from `theme/maqueta.css`. Correct the colour variable in that file and run `coursekit theme import theme/maqueta.css` again |
| `missing <path>: derive it from the theme of the assembly platform` | `coursekit theme tokens` or `check` found no `tokens.json`. Run `/define-theme` |
| `<path> is not a valid tokens JSON` | `tokens.json` is damaged. Do not repair it by hand: run `/define-theme` (or `coursekit theme import`) again |
| `WARNING the font '<font>' is a font included in the platform: its name is used as the CSS family; adjust it if it differs` | Not an error: a note printed by the import. The CSS family is the font's name; check that it is right for the media |
| `WARNING the colour role '<role>' could not be resolved; the default is used` and `WARNING the theme has a dark mode: the tokens are those of the light mode` | Notes of the import, not errors. Review the role in the platform theme if the default is not what you want; the media follow the light mode |

### The html backend

The html backend builds one SCORM package per unit with `coursekit assemble build` (see [Workflow](02-workflow.md#assembly-and-delivery-by-backend) and [Assembly and delivery](08-assembly-and-delivery.md)). These are its messages and what to do; `<CODE>` stands for the course code.

| Message | Meaning and fix |
|---|---|
| ``<CODE> is assembled with the html backend: `<action>` is for the creator backend; use `coursekit assemble build` `` | You ran `assemble plan`, `diff`, `applied` or `link` on a course of the html backend. They are for creator. Build with `coursekit assemble build <CODE> --unit N` |
| ``<CODE> is assembled with the '<backend>' backend: `build` is for the html backend (project.yaml › assembly.backend or course.yaml › assembly.backend)`` | You ran `assemble build` on a course of the creator backend. If you want this course in html, set `assembly.backend: html` in its `course.yaml` (or in `project.yaml` for every course) and run `coursekit setup` to prepare the builder |
| `coursekit: assemble <action> needs --unit` | `plan`, `diff`, `applied` and `link` (creator backend) work on one unit: add `--unit N`. Only `build` can run without `--unit` (every unit) |
| `<lesson>: <BRICK>: this component is not available in the html backend yet (the games come in a later delivery)` | The unit uses a game (`word-search`, `wordle`, `hangman`, `pasapalabra`, `memory` or `trivial`), for example `U1-S3: MEMORY: ...`. `assemble build` refuses it, and `coursekit verify` reports it as `assembly: ...`. Replace it in the `.md` with another activity (a question or an interactive directive) or assemble that course in creator |
| `the package does not contain N word(s) of the content: …` | The build checks that every word the learner should read in `content.md` and `assessment.md` is in the page, and lists the first ones missing. The usual cause is a line the format does not render: for example a question without its key (`question:`), a line of a directive in the wrong place or an unknown key. Find those words in the unit, correct the `.md` as [Content](06-content.md) describes and build again. Never edit the output |
| `the builder could not be prepared (npm install of @studiolxd/scorm and esbuild): check Node and npm with coursekit doctor` | The builder (the SCORM runtime and esbuild) is installed once per machine in the coursekit store, with `npm`, and the install failed or `npm` is missing. Install Node (`coursekit setup --media` can), check the network, and behind a proxy see [Corporate proxy and certificates](#corporate-proxy-and-certificates); then run `coursekit setup` or build again |
| `esbuild failed to bundle the player: …` | The bundle of the player did not finish; the message ends with what esbuild said. A broken script in `components/*.js` of the project is the usual cause: fix or remove it. If the message is about the install, repeat `coursekit setup` to repair the builder |
| `the asset X is produced but its file does not exist (coursekit media set … --file): the placeholder stays` | Shown as a warning. The asset is marked `produced` but its file is missing, so the package keeps the placeholder with its description. Register the file with `coursekit media set CODE X --status produced --file media/files/X.<ext>` and build again |
| `html backend builder (@studiolxd/scorm and esbuild)` in `coursekit doctor` | Not a failure: the line is `info` until the builder exists. Run `coursekit setup` |

The packages must be tried in the LMS they will be delivered to (or in SCORM Cloud) before delivering: the build checks the content, not how a particular LMS records the tracking. The preview folder opened from the disk, without an LMS, keeps its state only in memory.

### Content words of the other language, true-false and fill-in-the-blank

The resource types, the keys of the directives (`question:`, `answer:`…) and a few words (`true`/`false`, `(starts)`/`(contains)`) are written in the language of the course; see [Resource types and directive keys by language](06-content.md#resource-types-and-directive-keys-by-language). `coursekit verify` and `coursekit assemble plan` reject what does not match. In `verify` the messages of the assembler start with `assembly:`; the label that follows says where: `U1-S2` is section 2 of unit 1 and `U1-E1.1` is assessment activity 1.1.

| Message | Meaning and fix |
|---|---|
| `content.md:LINE: unknown or not allowed placeholder type 'Infografía' (use: Image, Video, Animated GIF, Infographic, Diagram, Interactive simulation, Interactive terminal demo, Audio)` | The word in `> **[MEDIA ASSET — …]**` is not one of the course language (here an English course with a Spanish word), or its type is not in `content.placeholder_types` of `config/rules.yaml`. Write one of the words listed after `use:` (case and spaces do not matter). In the configuration the types are ids (`infographic`, not the word), see [Configuration](04-configuration.md) |
| `the key 'pregunta:' belongs to the language 'es'; this course uses: answer, answers, feedback, feedback-correct, feedback-incorrect, image, objective, position, question, title` | A `key: value` line of a directive uses a key of the other language (`pregunta:` in an English course, `question:` in a Spanish one). It is not ignored: replace it with the key of the course language from the list (`question:`). The directive names (`:::single-choice`) do not change. If the whole course is in the wrong language, check `language` in `course.yaml` and `content_language` in `project.yaml` |
| `:::true-false needs 'answer: true\|false'` | The question has no `answer:` line, or its value is not one of the two words of the course language (`true` / `false` in English; `verdadero` / `falso` in Spanish). Write `answer: true` or `answer: false` |
| `:::fill-in-the-blank needs blanks written as {answer} in 'question:'` | The `question:` line has no blank. Write each blank between braces inside the sentence: `question: A strong password is {long}.` (several accepted answers: `{long/lengthy}`). The key is the one of the course language |
| `:::pasapalabra items: '- A (starts\|contains): definition :: ANSWER'` | An item of the letter wheel does not follow the form letter, mode in parentheses, definition, `::`, answer. The mode is `(starts)` or `(contains)` in English and `(empieza)` or `(contiene)` in Spanish |

### Missing media tools

Run `coursekit setup --media`. On macOS it needs [Homebrew](https://brew.sh); on Windows it needs `winget`; on Linux it only prints what to install (`sudo apt install ffmpeg nodejs npm asciinema`, plus [vhs](https://github.com/charmbracelet/vhs)). It also needs `uv` to install `piper` and `stable-ts`, and `npm` for the Remotion workspace. If the voice download fails, run it again when you are online.

### The Remotion link cannot be made

`coursekit setup --media` installs the dependencies of Remotion once in the coursekit store and links `tools/remotion/node_modules` to them. If it cannot make the link (Windows without permission to create junctions, or a file system without links, such as some network or removable drives), it does not fail: it runs `npm install` inside `tools/remotion/` and the project keeps its own copy, as any Node project does. You see `ok: Remotion dependencies` instead of `ok: Remotion dependencies shared from <path>`. Everything works the same; the only cost is the disk space of one more copy (about 230 MB, plus the browser Remotion downloads on its first render, about 600 MB).

The same happens if `npm install` fails in the store. To get the shared copy, fix the cause (network, proxy, permissions) and run `coursekit setup --media` again. If the project already has a real `node_modules` folder, setup keeps it and says so; to share instead, delete `tools/remotion/node_modules` and repeat.

### Remotion dependencies are missing

`coursekit doctor` shows `missing  Remotion dependencies (tools/remotion/node_modules)` when the folder does not exist or when it is a link to a store that is no longer there: the store was removed (for example with `coursekit uninstall`), moved, or `COURSEKIT_HOME` points somewhere else than when you installed. Run `coursekit setup --media`: it installs them again in the store if needed and repairs the link, without touching the sources of `tools/remotion`. If you changed `COURSEKIT_HOME` on purpose, make sure it is set in the shell before running it.

### The coursekit store takes a lot of space

The store holds the dependencies of Remotion and the browser it downloads (about 230 MB plus about 600 MB), once for all your projects. Where it is:

| System | Store |
|---|---|
| macOS | `~/Library/Application Support/coursekit` |
| Linux | `~/.local/share/coursekit` |
| Windows | `%LOCALAPPDATA%\coursekit` |

`coursekit doctor` prints its path and size. To keep it somewhere else (another disk), set `COURSEKIT_HOME` **in the shell, before running `coursekit setup`**, and keep it set in every later session (for example in your shell profile, or with `setx COURSEKIT_HOME "D:\coursekit"` on Windows), because `doctor`, `setup` and `uninstall` look for the store where the variable says; a value in the `.env` of a project would apply only to that project:

```bash
export COURSEKIT_HOME=/Volumes/Big/coursekit     # PowerShell: $env:COURSEKIT_HOME = "D:\coursekit"
coursekit setup --media
```

With the variable set, `setup --media` installs there and relinks the projects it runs in; run it once in each project that had a link to the old store. To bring the existing install along, move the contents of the old folder to the new one before running it. Then delete the old store, or let `coursekit uninstall` do it before you change the variable. To free the space without changing anything else, run `coursekit uninstall`: it asks per group and removes the dependency folders; the projects keep their sources, and `coursekit setup --media` installs them again when you need them. Details in [Commands](03-commands.md) and [Configuration](04-configuration.md#the-per-machine-store).

### Another install after editing package.json

The store folder of Remotion is named after a hash of the `package.json` of the project (and its `package-lock.json`). A project that adds or updates a dependency in `tools/remotion/package.json` no longer matches the shared install: the next `coursekit setup --media` makes a second install, `workspaces/remotion-<other-hash>/`, and links the project to it. It is normal and expected; the other projects keep using the first one. It costs the disk space of one more install. The folders of installs that no project uses any more stay in the store until `coursekit uninstall` removes them (or you delete them by hand). If you do not need your change, restore the `package.json` of the template and repeat `coursekit setup --media`.

### Windows

- Messages show paths with forward slashes (`courses/PWD/course.yaml`).
- `setup` sets `core.autocrlf input` in the project when it enables the hooks.
- `asciinema` does not exist on Windows; terminal demos use VHS.
- Proxy variables are stored in the Windows user environment through PowerShell.
- Put paths with spaces, such as `MIRROR_DIR`, between quotes in `.env`.
- Piper voices are stored in `%LOCALAPPDATA%\piper`, and the coursekit store (the shared Remotion dependencies) in `%LOCALAPPDATA%\coursekit`. In `tools/remotion/` the `node_modules` link is a junction; if Windows or the drive does not allow it, the project installs its own copy ([The Remotion link cannot be made](#the-remotion-link-cannot-be-made)).

### Signing problems

| Message | Fix |
|---|---|
| `no interactive terminal` | sign in your own terminal, or in the agent chat as `! coursekit approve ... --yes` |
| `the design must be approved again` | the design changed after your signature: review it and run `coursekit approve design <CODE>` |
| `design/matrix.json is missing` | ask the design agent to export the design first (`/approve-design <CODE>`) |
| `the design has N validation errors` | fix them in SLXD Creator, export again, then sign |
| `unit N is 'verified': it needs its review first` | run `coursekit review <CODE> N`, or record your own review with `coursekit reviewed <CODE> N --by "Name"`, or set `review.ai: skip` in `rules` if the project has no AI review |
| `missing AI review ...` | the report `reviews/unit-NN-ai-review.md` does not exist: run the review, or record a person's review with `coursekit reviewed <CODE> N --by "Name"` |
| `unit N changed after its AI review (...)` | the unit was edited after the review and the message names the parts. Review it again with `coursekit review <CODE> N` (only those parts), or sign anyway with `--force` if you accept it |
| `unit N does not pass verification` | run `coursekit verify <CODE> --unit N` and fix the errors |
| `recorded, not committed` | the approval is saved in `course.yaml` but git could not commit it (for example, the folder is not a git repository). Commit it yourself or fix git |
| `<CODE> has been on hold since ...` | the course is paused: see the next section |

### The course is on hold or the client's review blocks the delivery

A course on hold refuses the commands that change it (`write`, `review`, `reviewed`, `approve`, `assemble`, `sync` without `--check`, `media set`, `client` and the delivery commands); reading commands such as `status` still work. The client review (when the project requires it) refuses the delivery. These are the messages and what to do; `<CODE>` stands for the course code (for example `PWD`).

| Message | Meaning and fix |
|---|---|
| ``<CODE> has been on hold since <date> (<reason>); it was in '<status>'. Resume it with `coursekit resume <CODE>` `` | The course is paused. Check the reason with `coursekit status <CODE>`; if it can continue, run `coursekit resume <CODE>` (it goes back to the status it had). Agents cannot do this: it is a person's command |
| `<CODE> is already on hold` | `coursekit hold` on a course that is already paused. Nothing to do |
| `<CODE> is not on hold (status: <status>)` | `coursekit resume` on a course that is not paused. Nothing to do |
| ``<CODE> needs the client's review before it is delivered (delivery.yaml › client_review.required): `coursekit client <CODE> send` `` | The project (or the course) requires the client's review and there is no round yet. Open one with `coursekit client <CODE> send`, or, if the client will not review it, record the reason with `coursekit client <CODE> skip --reason "..."` |
| `<CODE> is waiting for the client's answer (round N, sent to ...)` | A round is open. When the client answers, record it: `coursekit client <CODE> approve --by "Name"` or `coursekit client <CODE> changes --note "..."` |
| `the client asked for changes in <CODE>: apply them, assemble again and open another round ...` | The last round closed with `changes`. Apply the changes (`/client-feedback <CODE>` handles the comments), run `/assemble <CODE>`, sign again the units that went back, and open the next round with `coursekit client <CODE> send` |
| ``round N is still open: close it with `approve` or `changes` `` | You tried `send` or `skip` with a round open. Close it first |
| `<CODE> is in '<status>': the client's review starts with the course assembled (status 'assembly')` | `send` (or `skip`) needs the course in `assembly`. Finish the assembly first, or, after `changes`, wait for the course to be back in `assembly` |
| `the units have no review links: run /assemble (it creates the link of each unit) or pass --where with the link` | `send` has no link to record. Run `/assemble <CODE>` (it creates the review link of each unit), or record them yourself with `coursekit assemble link <CODE> --unit N --review URL`, or send one link with `--where URL` |
| `<CODE> has no round open with the client` | `approve` or `changes` with no open round. `coursekit status <CODE>` shows the last round |
| `coursekit: approve needs --by with the name of who approves` | Add `--by "Name"`: the name of the person who approves on behalf of the client |
| `coursekit: skip needs --reason` | Add `--reason "..."` |
| `warning: <CODE> is in '<status>', not in a delivery status (assembly, client_review): the package is recorded, but the course is not marked as delivered` | Not an error: `delivery add` recorded the package, but the course only becomes `delivered` from `assembly` or `client_review`. Usually the course was not assembled or went back to an earlier status. Fix the cause, then record the packages again with `delivery add` (or check that `coursekit status <CODE>` shows what you expect). With the html backend, `assemble build` does not move the course to `assembly`, so this warning appears for a course still in `media` |

If the client review is not mandatory and you do not want it, there is nothing to do: with `client_review.required: false` the course can be delivered from `assembly`. See [Configuration](04-configuration.md#delivery-scorm-export-and-client-review).

## Change the language

There are two languages. The **course language** (`content_language` in `project.yaml`, and `language` in each `course.yaml`) is the language of the content. The **interface language** is the one of coursekit messages and of what the agents tell you. coursekit picks the interface language in this order:

1. the language chosen in `init` (while it runs);
2. `COURSEKIT_LANG` (`es` or `en`) from the environment or from your `.env`;
3. `ui_language` in `project.yaml` (shared by the team; falls back to `content_language`);
4. the language of the system (`LC_ALL`, `LC_MESSAGES`, `LANG`);
5. English.

To change it for you only, set `COURSEKIT_LANG=en` in `.env`. For the whole team, change `ui_language` in `project.yaml`, then run `coursekit agents` so the generated commands pick it up. The `--help` texts follow it too.

The interface language does not touch the content. The words of `content.md` (headings, placeholder types, directive keys) follow the **course language**; if you change it for a course that is already written, `coursekit verify` rejects the old words until you rewrite them (see [Content words of the other language, true-false and fill-in-the-blank](#content-words-of-the-other-language-true-false-and-fill-in-the-blank)).

## Refresh generated files

| Command | Refreshes |
|---|---|
| `coursekit agents` | skills, commands, agents, docs and tool settings (`.claude/`, `.opencode/`, `.coursekit/`, `.mcp.json`, `opencode.json`, `.codex/config.toml`). Needed after changing `project.yaml`, `.agents/` or the role models in `.env`, after updating coursekit, and after a pull (the git hooks do it for you) |
| `coursekit init --update` | `AGENTS.md`, `CLAUDE.md`, `.env.example`, `.gitignore`, `config/*.example.yaml` and the hooks. Never `project.yaml` |

`init --update` keeps any generated file you edited by hand and says so. To take the new template, delete that file and run it again. `coursekit agents` only overwrites files it generated (they carry a marker) and leaves yours alone, reporting them as kept.

## FAQ

**Can an agent sign for me?** No. `coursekit approve` is denied in the generated settings of Claude Code and opencode, and the project instructions forbid it for every tool. Use `!` in the chat if you want to sign without leaving it. The same applies to `coursekit client` (rounds of client review), `coursekit hold` and `coursekit resume`.

**Can the whole process run without me?** Yes: `coursekit handoff "<title>" <hours>`. It signs as Coursekit Handoff and nobody reviews the course; see [Workflow](02-workflow.md#handoff-mode). If it stops, it says why; fix it and run `coursekit handoff <CODE>` to carry on.

**Is the client review mandatory?** Not by default. It is if the project says so (`client_review.required: true` in `config/delivery.yaml`) or the course does (`delivery › client_review › required` in its `course.yaml`). See [Workflow](02-workflow.md#client-review-optional).

**How do I pause a course?** `coursekit hold <CODE> --reason "..."`, and `coursekit resume <CODE>` to continue. See [Workflow](02-workflow.md#pause-a-course).

**Do I need to know git?** Little. coursekit commits signatures for you; agents do not commit or push unless you ask.

**Which backend should I use?** With `creator`, the platform hosts the content and exports the SCORM packages, and the client reviews on creator's links. With `html`, coursekit builds the package of each unit itself (`coursekit assemble build`): no platform is needed for the assembly, you host the zip or preview for the client, and the package must be tried in your LMS. The html backend does not have the games yet (`word-search`, `wordle`, `hangman`, `pasapalabra`, `memory`, `trivial`); if a course needs them, assemble it in creator. The instructional design is done in creator with either one. Set it in `project.yaml › assembly.backend` (the `init` wizard asks) and, for one course, in `course.yaml › assembly › backend`. See [Workflow](02-workflow.md#assembly-and-delivery-by-backend).

**Can two people work on the same project?** Yes: `project.yaml`, `courses/` and `config/` are versioned, and each person has their own `.env`, identity, tools and models. After a pull the hooks refresh the generated files.

**Where are the logs of headless runs?** In `.cache/logs/`, one file per session. The folder is not versioned.

**Where do the colours and fonts of the media come from?** From the theme of the assembly platform, never from a hand-written file: `/define-theme` derives `theme/tokens.json` and `tokens.css` from it (see [Theme and design tokens](02-workflow.md#theme-and-design-tokens)). With the `html` backend they come from the CSS variables of `theme/maqueta.css` over the base layout of the package (`coursekit theme import theme/maqueta.css`).

**Where do I change a production rule?** Not in a skill and not in `.env`: create `config/rules.yaml` with only the values you change (see [Configuration](04-configuration.md)).

**I changed a skill and it was overwritten.** Skills are generated. Put your version in `.agents/skills/<name>/SKILL.md` instead (see [Agents](05-agents.md)).

**How do I remove everything coursekit installed?** Before removing the package, run `coursekit uninstall --dry-run` to see the list and `coursekit uninstall` to remove it: it asks for each group (the shared Node dependencies, the media tools installed with uv, the downloaded voices, the lines added to your shell files and, on Windows, the user variables) and, if the coursekit store ends up empty, deletes it. System packages (`ffmpeg`, `node`, `vhs`, `asciinema`) are only listed, with the command to remove them yourself. Then run `uv tool uninstall slxd-coursekit`. The projects are never touched: delete their folders, or their `.claude/`, `.opencode/`, `.codex/`, `.coursekit/` and `tools/`, by hand. If you removed the package first, `uv tool install git+https://github.com/studiolxd/coursekit` brings the command back so you can run `coursekit uninstall`. See [Getting started](01-getting-started.md#uninstall).

**Which Python do I need?** 3.12 or 3.13. uv installs it for you.

Back to the [index](index.md).
