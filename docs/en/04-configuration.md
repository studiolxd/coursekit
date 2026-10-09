# Configuration

Where every setting of a coursekit project lives, the order in which they combine, and how to see and change the value in force.

The examples use a generic project: client "ACME", a course on strong passwords with code `PWD`.

## Where each value lives

| Place | Committed | Who edits it | What it holds |
|---|---|---|---|
| Package defaults (inside coursekit) | no (ships with the tool) | nobody | The default production rules, directives, media options and delivery settings, and the default tool and model of each role. |
| `config/<name>.yaml` | yes | the team | Overrides of one of the four configurations: `rules`, `directives`, `media`, `delivery`. |
| `project.yaml` | yes | the team | Project identity, languages, assembly backend, slxd server, mirror folder, network. It can also carry `rules:`, `directives:`, `media:` and `delivery:` sections. |
| `course.yaml` | yes | commands and people | The record of one course. It can carry `rules:`, `directives:`, `media:` and `delivery:` sections that apply to that course only. |
| `theme/` and `courses/<CODE>/theme/` | yes | `coursekit theme import` (tokens); the team (`maqueta.css`) | Design tokens of the theme, derived from the theme of the assembly platform or, with the html backend, from the stylesheet (see [Theme tokens and cache folders](#theme-tokens-and-cache-folders)). Not a configuration layer: nobody edits the tokens by hand. With the html backend, `maqueta.css` is the stylesheet that restyles the package and is edited by hand (see [Files of the html backend](#files-of-the-html-backend)). |
| Per-machine store (outside every project) | no | `coursekit setup` and `coursekit uninstall` | Node dependencies shared by the projects and the record of what `coursekit setup` installed (see [The per-machine store](#the-per-machine-store)). Not a configuration layer. |
| `.env` (and the real environment) | no (git-ignored) | each person | Personal data: signing identity, interface language, local paths, tool and model of each role, API keys. |
| Command options | no | the person running it | `--agent` and `--model` for one launch. |

Rule of thumb: what must be the same for the whole team goes in versioned files (`project.yaml`, `config/`); what is personal or secret goes in `.env`. Production rules are never read from `.env`.

## How values combine

### The four production configurations

`rules`, `directives`, `media` and `delivery` are built by merging, in this order (the last one wins):

1. Package defaults.
2. `config/<name>.yaml`, if it exists.
3. The `<name>:` section of `project.yaml`, if it exists.
4. The `<name>:` section of the course's `course.yaml`, when a course is involved.

Merging rules:

- A mapping merges key by key: you write only the keys you change.
- Anything else replaces the previous value. **Lists are replaced whole**, not appended to: to change one item of a list you must write the complete list.
- Setting a key to a new value never removes sibling keys.

### Personal settings

- A variable already set in the real environment (your shell) wins over the same variable in `.env`. An empty value in `.env` counts as not set.
- `--agent` and `--model` on a command win over `<ROLE>_AGENT` and `<ROLE>_MODEL` for that launch only. `--agent` without `--model` uses that tool's default model (it does not reuse the model from `.env`).

### Interface language

`coursekit` picks the language of its messages (`es` or `en`) in this order:

1. The language chosen in the `coursekit init` wizard, during that run.
2. `COURSEKIT_LANG` (real environment or `.env`).
3. `ui_language` in `project.yaml` (if missing, `content_language`).
4. The system language (`LC_ALL`, `LC_MESSAGES`, `LANG`).
5. English.

Every text, `--help` included, follows `COURSEKIT_LANG` (the shell variable, or the one in the `.env` of the project you are in), else `ui_language`, else the system language.

## See the value in force

```bash
coursekit config                     # the four configurations, every value with its origin
coursekit config rules               # only one: rules | directives | media | delivery
coursekit config rules --changed     # only what differs from the package defaults
coursekit config rules --course PWD  # include the overrides in courses/PWD/course.yaml
coursekit config delivery --json     # merged values as JSON
coursekit rules                      # shortcut for `coursekit config rules`
coursekit rules PWD --changed        # shortcut with a course and --changed
```

Each line is `key  value  (origin)`, where the origin is the layer that set the value: `package`, `config` (`config/<name>.yaml`), `project` (a section of `project.yaml`) or `course`. Nested keys are shown with dots, for example `defaults.grading.passing_score`.

Skills and commands receive the rules as numbers rendered when `coursekit agents` runs, using the project-level values (package, `config/`, `project.yaml`). After changing a rule, run `coursekit agents` (it also runs on `coursekit setup`, and after every `git pull` or checkout through the project's git hooks once `coursekit setup` has enabled them). Course-level overrides apply to the checks (`coursekit verify`, `coursekit sync`) but are not written into the skill texts.

## `project.yaml`

Created by `coursekit init` and then owned by the project: `coursekit init --update` never rewrites it. Edit it by hand.

| Key | Default | Allowed values | Meaning |
|---|---|---|---|
| `name` | folder name | free text | Project name. Shown to the agents as the name of the team. |
| `client` | empty | free text | Client name (for example `ACME`). Copied into the `course.yaml` of every new course. |
| `content_language` | `es` | `es`, `en` | Language of the course content. It selects the content format tokens (section heading word, objective tag, placeholder label), the default `language` of new courses and the default narration voices. A course can differ: `coursekit new --language`. |
| `ui_language` | same as `content_language` | `es`, `en` | Language of coursekit messages, of the catalog spreadsheet and of what agents say to people. A person can override the messages with `COURSEKIT_LANG`. |
| `tone` | empty | free text | Tone of the courses (for example "close and practical"). Copied into `design.tone` of new courses. When empty, agents are told to use the tone in `course.yaml`. |
| `address` | `tu` for `es`, `you` for `en` | `tu`, `usted` (Spanish); `you` (English) | How learners are addressed. Given to the agents as a writing rule. `coursekit init` rejects a value that does not fit the language. |
| `assembly.backend` | `creator` | `creator`, `html` | Where the courses are assembled. With `creator` the units are loaded into slxd creator (`coursekit assemble plan`, `diff`, `applied`, `link`) and `coursekit verify` also checks that the content can be turned into creator bricks. With `html` coursekit builds each unit as a SCORM package (`coursekit assemble build`) and `coursekit verify` also checks that every component can be rendered. The instructional design is always done in creator, so `platform.slxd.mcp_url` is needed with either backend. A course can use the other backend: `assembly.backend` in its `course.yaml` (see below). `coursekit init --backend` sets it. |
| `theme.source` | `tenant_default` | `tenant_default`, `branding` | Creator backend only: where the theme of the courses comes from. `tenant_default` uses the default theme of the organization in creator; `branding` makes `/define-theme` create one from the material in `theme/branding/` (without material, the tenant's default is used). With the html backend it is not used. The handoff reads it so it never has to ask. |
| `platform.slxd.mcp_name` | `slxd-creator` | free text without spaces | Name of the slxd MCP server in `.mcp.json`, `opencode.json` and `.codex/config.toml`. |
| `platform.slxd.mcp_url` | empty | URL starting with `http://` or `https://` | Address of the slxd MCP server (for example `https://acme.example.com/mcp/creator`). Needed with either backend, because the instructional design is done in creator. When empty, no server is configured in any tool, `coursekit doctor` says so and `coursekit init` warns at the end. |
| `platform.slxd.connector` | empty | free text | The creator connector you logged in at account level, by the name your AI tool lists it (for example `SLXD Creator Studio LXD`; the `claude.ai ` prefix is optional). When set, the sessions without an interface that coursekit starts (the handoff, `--headless`) may use its tools, in addition to the server of `mcp_name`. Claude Code names those tools `mcp__claude_ai_<name with underscores>__<tool>`. Without it only the project server is allowed. See [MCP server problems](09-troubleshooting.md#mcp-server-problems). |
| `platform.slxd.organization_id` | empty | free text | Reserved. coursekit does not read it today. |
| `mirror.provider` | `none` | `sharepoint`, `onedrive`, `google-drive`, `nextcloud`, `folder`, `none` | Kind of shared folder that mirrors the courses. `none` disables `coursekit publish`. |
| `mirror.url` | empty | URL (or, for `folder`, text with `{code}`) | Web address of the mirror folder, used to build the per-course links in the catalog. For `folder`, a `{code}` in the text is replaced by the course code. A SharePoint or OneDrive sharing link (`/:f:/s/...`) has no folder path, so per-course links cannot be built from it. `coursekit publish --check` tells you what link form is in use. |
| `network.ca_bundles` | `[]` | list of file paths | Extra CA certificates for networks that inspect TLS. Environment variables and `~` are expanded; the first file that exists is used. See `NODE_EXTRA_CA_CERTS` below. |

Minimal example:

```yaml
name: Strong passwords
client: ACME
content_language: en
ui_language: en
tone: close and practical
address: you

assembly:
  backend: creator   # creator | html

platform:
  slxd:
    mcp_name: slxd-creator
    mcp_url: https://acme.example.com/mcp/creator

mirror:
  provider: sharepoint
  url: https://acme.example.com/sites/training/Shared%20Documents/Courses

network:
  ca_bundles:
    - ~/certs/acme-proxy.pem
```

The local path of the mirror folder is personal and does not go here: it is `MIRROR_DIR` in `.env`.

Besides these keys, `project.yaml` accepts the sections `rules:`, `directives:`, `media:` and `delivery:` (see below).

## `.env`

`coursekit init` and `coursekit setup` create `.env` from `.env.example` when it is missing. `.env` is git-ignored; `.env.example` is generated by coursekit and refreshed by `coursekit init --update`.

File format: one `KEY=value` per line; lines starting with `#` are comments; `export KEY=value` is accepted; a value with spaces or `#` goes between quotes; an unquoted ` # comment` after a value is ignored.

### Identity and language

| Variable | Default | Meaning |
|---|---|---|
| `COURSEKIT_USER_NAME` | empty | Name that signs approvals (`coursekit approve`) and appears in the history of the course. |
| `COURSEKIT_USER_EMAIL` | empty | Email that goes with the name. Both are required to sign. `coursekit setup` asks for them (suggesting your git identity); `coursekit setup --identity` changes them, optionally with `--name` and `--email`. |
| `COURSEKIT_LANG` | `ui_language` of the project (written by `coursekit init`) | `es` or `en`. Language of coursekit messages for you. |

### Mirror folder

| Variable | Default | Meaning |
|---|---|---|
| `MIRROR_DIR` | empty | Local path of the mirror folder (`project.yaml` › `mirror`), the one your desktop sync client keeps in sync. Needed by `coursekit publish` and `coursekit doctor`. |

### Roles: tool and model

Five roles, two variables each. Full details in [Agents](05-agents.md).

| Variable | Default after `coursekit setup` | Meaning |
|---|---|---|
| `DESIGN_AGENT` / `DESIGN_MODEL` | `claude` / `opus` | Instructional design. |
| `WRITER_AGENT` / `WRITER_MODEL` | `claude` / `sonnet` | Writing units. |
| `REVIEWER_AGENT` / `REVIEWER_MODEL` | `claude` / `opus` | AI review of units. |
| `MEDIA_AGENT` / `MEDIA_MODEL` | `claude` / `opus` | Media production. |
| `ASSEMBLY_AGENT` / `ASSEMBLY_MODEL` | `claude` / `sonnet` | Assembly, delivery and directive sync. |

- `<ROLE>_AGENT` is `claude`, `opencode` or `codex`. If unset or empty, `claude`. Any other value is an error when the role is launched.
- `<ROLE>_MODEL` is an id that the tool understands (Claude Code: an alias such as `opus` or an id; opencode: `provider/model`). Empty means the tool's own default model.
- `.env.example` ships with empty models; `coursekit setup` fills in the proposed ones (see [Agents](05-agents.md)).

### Voice, subtitles and image providers (optional)

A provider is used only if its key is set. See [Media](07-media.md) for how coursekit chooses between them.

| Variable | Default | Meaning |
|---|---|---|
| `ELEVENLABS_API_KEY` | empty | ElevenLabs key. Enables narration with exact subtitles from character timestamps. |
| `ELEVENLABS_VOICE_ID` | empty | ElevenLabs voice. Required together with the key (there is no default voice). |
| `AZURE_SPEECH_KEY` | empty | Azure AI Speech key. |
| `AZURE_SPEECH_REGION` | empty | Azure region of that key. Required together with the key. |
| `AZURE_SPEECH_VOICE` | empty | Azure voice. Empty: `es-ES-ElviraNeural` (Spanish) or `en-GB-SoniaNeural` (English). |
| `GOOGLE_TTS_API_KEY` | empty | Google Cloud Text-to-Speech key. |
| `GOOGLE_TTS_VOICE` | empty | Google voice. Empty: `es-ES-Chirp3-HD-Aoede` (Spanish) or `en-GB-Chirp3-HD-Aoede` (English). |
| `MAGNIFIC_API_KEY` | empty | Magnific key, for generated images. coursekit checks that it is set; the media agent uses it. |
| `PIPER_VOICE` | empty | Path to a Piper voice model (`.onnx`) for local draft narration. `coursekit setup --media` downloads one and fills this in. |
| `PIPER_SPEAKER` | `0` in `.env.example` | Speaker number of the Piper voice. |

### Variables outside `.env`

| Variable | Meaning |
|---|---|
| `COURSEKIT_PROJECT` | Real environment variable: path of the project root. When set, coursekit uses it instead of looking for `project.yaml` upwards from the current folder. |
| `COURSEKIT_HOME` | Real environment variable: folder of the per-machine store. When set, it replaces the default folder of the user's data (see [The per-machine store](#the-per-machine-store)). It is read by `coursekit setup`, `coursekit doctor` and `coursekit uninstall`: set it the same way for the three. |
| `NODE_EXTRA_CA_CERTS` | Path of the corporate CA certificate for Node tools (Claude Code, opencode, npm). If `network.ca_bundles` lists a file that exists, `coursekit setup` offers to set it (and `UV_NATIVE_TLS=1` for uv) permanently for your user, and `coursekit doctor` reports whether it is set. |
| `UV_NATIVE_TLS` | `1` makes uv use the system certificate store. `coursekit setup` sets it for its own run when a CA bundle is found. |
| `LC_ALL`, `LC_MESSAGES`, `LANG` | System language, used for the messages when nothing else says otherwise. |

## The `config/` files

The four configurations are `rules`, `directives`, `media` and `delivery`. Every project gets `config/<name>.example.yaml` with the complete package defaults (a reference, never read). To change something, create `config/<name>.yaml` with **only the keys you change**; `coursekit init --update` refreshes the examples without touching your overrides.

The same keys can be written in a `<name>:` section of `project.yaml` (wins over `config/`) or of a course's `course.yaml` (wins over both, for that course only).

### `rules`: production rules

Structure (units, sections, objectives, hours) is not set here: it comes from each course's approved instructional design. These are the checks applied on top of it.

| Key | Default | Meaning |
|---|---|---|
| `pages_per_hour` | `10` | Pages of learner-facing text per hour of study. |
| `words_per_page` | `500` | Words per page. Minimum words of a section = pages (rounded up) × `words_per_page`; the minimum is stored in `course.yaml` by `coursekit sync`. |
| `defaults.intro_section` | `true` | New courses start with an introduction-and-objectives section in every unit. |
| `defaults.summary_section` | `true` | New courses end every unit with a summary section. |
| `defaults.structure` | `sin_modulos` | Structure of new courses: `sin_modulos` or `con_modulos` (slxd structural pattern). |
| `defaults.grading.passing_score` | `50` | Passing score of a test, when the design does not give that assessment activity its own (`notaAprobado`). |
| `defaults.grading.attempts` | `2` | Attempts allowed per test, when the design does not give that assessment activity its own (`intentosMax`; `0` is unlimited). |
| `design.competencies_per_course` | `"2–4"` | Guidance given to the design agent: competencies per course. |
| `design.objectives_per_unit` | `"2–4"` | Guidance: objectives per unit. |
| `design.intro_summary_hours` | `"0.2–0.3"` | Guidance: hours for the introduction and the summary. |
| `review.ai` | `required` | `required` or `skip`. `required`: an AI review comes before each unit's sign-off. `skip`: a unit that passes `coursekit verify` counts as reviewed and the person's sign-off is the review. Either way a person can record their own review of a unit with `coursekit reviewed --by`. |
| `handoff.rounds` | `2` | Attempts per step of `coursekit handoff` (writing a unit, its review with its fixes, the design sign-off, media, assembly, delivery) before it stops. `--rounds` changes it for one run. |
| `handoff.media_tools` | `[]` | Programs the media agent may run when nobody can approve them (the handoff, `--headless`). Without this rule it may run `coursekit`, `npx`, Python and every program the recipes of the media configuration declare in `needs` (`bin`, `media`: `vhs`, `piper`, `stable-ts`…, also those of your own `config/media.yaml`). Add the rest here, for example `[blender, gs]`. `bash`, `sh` and `node` let the agent run any command and are never taken from the recipes: add them only if you accept that. The agent may also read the folder of the store where the Remotion workspace lives. |
| `content.word_margin` | `0.05` | Recommended margin over the minimum words (`0.05` = 5 %). Below it, `coursekit verify` warns; below the minimum itself it is an error. |
| `content.placeholders_per_hour` | `2.5` | Media placeholders required per unit hour (rounded up). |
| `content.min_placeholder_types` | `4` | Distinct placeholder types required per unit (capped by the number of placeholders required). |
| `content.interactive_per_hour` | `4` | Distinct interactive directives required per hour of a content section. |
| `content.min_interactive_per_content_section` | `1` | Floor for the previous rule: every content section needs at least this many. |
| `content.questions_per_objective` | `5` | Question bank size per objective of the unit (a shortfall is a warning). |
| `content.placeholder_types` | `image`, `video`, `animated_gif`, `infographic`, `diagram`, `simulation`, `terminal_demo`, `audio` | Placeholder types allowed in the content, by **id**. The author writes the word of the course language in the placeholder (`Infographic`, `Infografía`…) and `verify` maps it to the id; a type that is not in the list is an error. A list you write replaces the whole list, and the ids must match the keys of `types` in the `media` configuration. The table of ids and words is in [Resource types and directive keys by language](06-content.md#resource-types-and-directive-keys-by-language). |
| `content.allowed_symbols` | `★✔✘·—‹›` | The only pictographic symbols allowed in the text; any other is an error. |

`defaults.*` only seeds **new** courses: it is copied into `course.yaml` by `coursekit new`. For an existing course, edit its `course.yaml` (see below).

### `directives`: directives and creator bricks

Registry of the `:::name` directives of the content format and the creator brick each one becomes.

| Key | Meaning |
|---|---|
| `synced_with_creator` | Date the registry was last compared with the creator brick catalog (`/sync-directives` updates it). |
| `directives.<name>.brick` | Creator brick type the directive becomes (for example `ACCORDION`). |
| `directives.<name>.role` | `interactive` (counts towards the interactive minimum), `question` (practice or assessment question) or `static` (highlighted text, does not count as interactive). |
| `directives.<name>.use` | One-line guidance on when to use it (written in English in the defaults). |
| `not_directives.<BRICK>` | Creator bricks that are not directives (plain Markdown, placeholders, unused), with a note. |
| `component_equivalents.<component>` | What to use instead of a common e-learning component that has no brick (shown as a hint when a writer uses it). The defaults cover `stepper`, `hotspots`, `reveal`, `toggle-compare`, `checklist`, `tooltips`, `modal`, `branching-scenario` and `simulated-terminal`. |

The default directives are, by role: `interactive` (`accordion`, `tabs`, `carousel`, `carousel-quotes`, `flashcards`, `flashcard-gallery`, `labelled-graphic`, `timeline`, `dialog` and the games `word-search`, `wordle`, `hangman`, `pasapalabra`, `memory`, `trivial`), `question` (`single-choice`, `multi-select`, `true-false`, `sorting`, `match`, `sorting-groups`, `fill-in-the-blank`, `order-words`, `short-answer`) and `static` (`note`, `highlight`, `quote`). Because mappings merge, you can add a directive or change the `role` of one by writing just that entry. `coursekit directives check FILE` compares the registry with a saved `list_brick_types` result.

### `media`: production options

For each placeholder type, an ordered list of options; `coursekit media plan` keeps, for each asset, the options whose requirements are met.

| Key | Meaning |
|---|---|
| `voice` | Options for narration (Video and Audio). A course uses one provider for all its narration. |
| `subtitles` | Options for subtitles. |
| `types.<id>` | Options for each placeholder type, keyed by its id: `image`, `infographic`, `diagram`, `animated_gif`, `terminal_demo`, `video`, `audio`, `simulation`. A project override of `types` uses the same ids (not the words of the content); mappings merge, so `types: {image: [...]}` replaces only the options of `image`. |
| `statuses` | Life cycle of an asset: `pending`, `scripted`, `produced`, `uploaded`. |
| `uses_theme` | Placeholder types whose production uses the theme tokens. Type ids; default: `infographic`, `diagram`, `animated_gif`, `simulation`, `video`, `terminal_demo`. For these types `coursekit media plan` warns when the tokens (the course's own, else the project's) are missing or were written by hand, and when an asset was made with other tokens; `coursekit media set --status produced` or `uploaded` is refused when the tokens are missing or were written by hand unless `--force` is given, and records the tokens the asset was made with. It is a list, so a list you write replaces the whole list. See [Theme tokens](07-media.md#theme-tokens). |

```yaml
# config/media.yaml: only licensed stock for images (the key is the id, not the word `Image`)
types:
  image:
    - {id: creator-stock, needs: {mcp: search_stock_images}, how: "Licensed stock only"}
```

Each option has `id`, `how` (description), `needs` (requirements) and optionally `only` (restricts the option to some content, for example `terminal`). `needs` can combine:

| Requirement | Met when |
|---|---|
| `env: VAR` | the variable is set (`.env` or shell); a list `[A, B]` needs all of them |
| `bin: CMD` | the command is installed |
| `mcp: TOOL` | the agent has that MCP tool (only the agent can check it) |
| `media: X` | the command `X` is on the `PATH` (`coursekit setup --media` installs `piper` and `stable-ts`) |
| `path: P` | the path exists inside the project (for example `tools/remotion/node_modules`) |
| `none` | always |

The default voice chain is `elevenlabs-api`, `azure-api`, `google-api`, `elevenlabs-mcp`, `piper`; subtitles: `elevenlabs-timestamps`, `stable-ts`. Remember that lists are replaced whole: to remove one voice option, write the complete `voice` list without it.

### `delivery`: SCORM export and client review

With the creator backend the `export.*` keys go to the creator export. With the html backend coursekit builds the package itself and reads only `export.standard` (the SCORM version of `imsmanifest.xml` and of the player) and `file_name` (the name of the zip); `deliveryType`, `reporting` and `scoreSource` do not apply.

| Key | Default | Meaning |
|---|---|---|
| `export.deliveryType` | `lms` | Delivery type passed to the creator export. |
| `export.standard` | `scorm_1_2` | `scorm_1_2` or `scorm_2004`. Both backends use it. |
| `export.reporting` | `passed_incomplete` | `passed_incomplete` or `completed_incomplete`. |
| `export.scoreSource` | `quiz` | `quiz` or `lessonProgress`. |
| `file_name` | `{code}-U{unit:02d}-v{version}-{standard}.zip` | Name of each package inside `courses/<CODE>/delivery/`. `{standard}` is the standard without underscores (`scorm12`, `scorm2004`). `coursekit delivery name CODE --unit N --version V` prints the expected name. |
| `client_review.required` | `false` | Whether the client must review the assembled course before it is delivered. With `true`, the delivery commands (`coursekit delivery check`, `name` and `add`, that is, `/deliver`) are refused until the last round of `coursekit client` is `approved` or `skipped` (`coursekit client CODE skip --reason "..."`). With `false`, delivering needs no round, and you can still open one. |

The client review is the optional stage between `assembly` and `delivered`; see [Workflow](02-workflow.md#client-review-optional). Like every key of `delivery`, `client_review.required` can be overridden per project (`config/delivery.yaml` or the `delivery:` section of `project.yaml`) and per course, so one course can require the review in a project that does not:

```yaml
# courses/PWD/course.yaml
delivery:
  client_review:
    required: true
```

## `course.yaml`: what a person may set per course

`course.yaml` is the record of a course and is mostly maintained by commands. These are the keys that a person may edit by hand:

| Key | Meaning |
|---|---|
| `language` | Language of this course (`es` or `en`); by default the project's `content_language`. |
| `assembly.backend` | `creator` or `html`: the backend that assembles this course, instead of the project's (`project.yaml › assembly.backend`). The key is absent by default, so the course follows the project; add it only for a course that needs the other backend. `coursekit status CODE` prints the one in force. |
| `client` | Client of the course. |
| `design.hours` | Total hours. `coursekit sync` reports a mismatch with the sum of the unit hours of the approved design. |
| `design.structure` | `sin_modulos` or `con_modulos`. |
| `design.intro_section`, `design.summary_section` | Whether every unit opens with an introduction and closes with a summary. |
| `design.audience`, `design.level`, `design.prerequisites` | Free text for the design agent. |
| `design.tone`, `design.notes` | Tone and extra instructions for this course. |
| `design.grading.passing_score`, `attempts` | Grading of this course: the pass mark and the attempts a test has when the design does not set them for its assessment activity. See [Grading of a test](08-assembly-and-delivery.md#grading-of-a-test). |
| `owners.*` | Who leads each stage (`instructional_design`, `writing`, `review`, `media`, `assembly`); shown in the catalog. |
| `rules:`, `directives:`, `media:`, `delivery:` | Overrides for this course only, with the same keys as the `config/` files. For example `delivery › client_review › required` makes the client review mandatory for this course (see above). |

Do not edit by hand: `units` (written by `coursekit sync`), `approvals` (written only by `coursekit approve`), `deliveries`, `history`, `client_review` and `hold`. The `slxd` block (`matrix_id`, `folder_id`, `theme_id`, `organization_id`) is filled in by the agents as they work; `theme_id` is also written by `coursekit theme import --course`.

Fields written by commands, which you can read but should not edit:

| Key | Written by | Content |
|---|---|---|
| `status` | the commands of each phase | Course status. `client_review` and `on_hold` are set by `coursekit client` and `coursekit hold` |
| `client_review` | `coursekit client` | List of rounds of review by the client. Each one has `round`, `sent_at`, `sent_by`, `to`, `links` (the review links sent), `outcome` (empty while open, then `changes`, `approved` or `skipped`), `closed_at`, `by` (who approved on behalf of the client) and `note`. Not to be confused with the setting `delivery › client_review` above |
| `slxd.theme_id` | `coursekit theme import --course` | Id of the platform theme the course's own tokens were derived from. The assembly links the theme to the contents with it |
| `hold` | `coursekit hold` | Only while the course is `on_hold`: `previous` (status before the pause), `reason`, `by` and `at`. `coursekit resume` removes it |
| `units[].links.preview` | `coursekit assemble link --preview` | Live preview of the unit, without comments |
| `units[].links.review` | `coursekit assemble link --review` | Review link of the unit, where the client comments |

The links are per unit because each unit is its own content in creator. There is no course-level `links` block.

One thing to know about `media:` in `course.yaml`: its `voice` key is where `coursekit voice set` stores the voice chosen for the course. See [Media](07-media.md).

## Theme tokens and cache folders

The design tokens of the theme are data derived from the platform, not configuration. They are versioned with the project.

| Path | Written by | Content |
|---|---|---|
| `theme/tokens.json` | `coursekit theme import FILE` | Tokens of the project theme: `color`, `font`, `radius`, `space`, `shadow`, and `origin` |
| `theme/tokens.css` | `coursekit theme import`, `coursekit theme tokens` | The same tokens as CSS custom properties, plus base classes for simulations |
| `courses/<CODE>/theme/tokens.json`, `tokens.css` | `coursekit theme import FILE --course CODE` | The own tokens of a course. A course uses them when they exist; otherwise it uses the project's |
| `.cache/theme/get_theme.json` | the design agent | Saved result of the platform tool `get_theme`, the input of the import with the creator backend. `.cache/` is git-ignored |
| `theme/maqueta.css`, `courses/<CODE>/theme/maqueta.css` | the team | The stylesheet of the html backend, the input of the import with that backend (see [Files of the html backend](#files-of-the-html-backend)). Written by hand, unlike the tokens |

`origin` in `tokens.json` records where the tokens come from:

| Key | Content |
|---|---|
| `source` | `creator` when derived from the theme of the platform; `css` when derived from the stylesheet of the html backend. A file with neither counts as written by hand: `coursekit doctor` and `coursekit media` treat it as not derived |
| `theme_id`, `name`, `version` | Id, name and version of the platform theme (`creator` only) |
| `file`, `sha256` | The name of the stylesheet and the first 12 characters of the hash of its content (`css` only). `coursekit theme show` prints them as the fingerprint |
| `imported_at` | Date and time of the import |
| `derived` | Tokens that the platform does not have and coursekit derived from its colours (`text-soft`, `surface`, `highlight`, `line`, `accent-strong`) (`creator` only) |
| `defaults` | Groups that are package defaults, because the platform has none (`radius`, `space`, `shadow`) (`creator` only) |
| `notes` | Notes of the import, for example that the theme has a dark mode and the tokens are the light mode, or (`css`) a colour variable that is not a plain value |

Do not edit these files: to change a colour or a font, change the theme in the platform (or, with the html backend, `theme/maqueta.css`) and import it again. See [Theme tokens](07-media.md#theme-tokens) for the flow and `coursekit theme` in [03-commands.md](03-commands.md#coursekit-theme).

## Files of the html backend

With the html backend (`project.yaml › assembly.backend: html`, or `assembly.backend: html` in one `course.yaml`) `coursekit assemble build` builds each unit as a SCORM package. These are the files of the project that shape it, and what it generates:

| Path | Versioned | What it is |
|---|---|---|
| `theme/maqueta.css` | yes | The stylesheet of the project ("maqueta" is the Spanish word for layout). It restyles the package and, through the CSS variables it declares (`--color-accent`, `--font-family`, `--radius`…), is the theme: `coursekit theme import theme/maqueta.css` derives the tokens from it. The variables you can change are the `:root` of the base layout of the package, listed in [Theme tokens](07-media.md#theme-tokens). |
| `courses/<CODE>/theme/maqueta.css` | yes | The same for one course: it is added after the project's, only in the packages of that course. `coursekit theme import courses/<CODE>/theme/maqueta.css --course CODE` derives that course's own tokens. |
| `components/*.css` | yes | Extra styles, added to the package after the stylesheets above, in alphabetical order. |
| `components/*.js` | yes | Extra behaviour, bundled with esbuild into the player (`assets/player.js`) of every package, before the code of the player. |
| `courses/<CODE>/assembly/html/unit-NN/` | no (`.gitignore`) | The package of a unit, rebuilt by `coursekit assemble build` and openable from the disk. |
| `courses/<CODE>/delivery/<name>.zip` | no (`.gitignore`) | The zip of a unit, written by `coursekit assemble build --version X.Y`. |

The styles of a package (`assets/styles.css`) are put together in this order, so each layer wins over the previous ones: the base layout of the package; the `tokens.css` that applies to the course (if the course has tokens); `theme/maqueta.css`; `courses/<CODE>/theme/maqueta.css`; `components/*.css`.

`coursekit theme import` derives the tokens from the one file you give it, over the base layout of the package, not over the other layers. Edit `maqueta.css`, import it again, and the tokens (and the media guard) follow; the package already uses the stylesheet itself without importing it. See [`coursekit theme`](03-commands.md#coursekit-theme) and, for what the build does, [`coursekit assemble`](03-commands.md#coursekit-assemble) and [08-assembly-and-delivery.md](08-assembly-and-delivery.md).

The builder that bundles the player (`@studiolxd/scorm` and `esbuild`) is not in the project: it lives in the [per-machine store](#the-per-machine-store).

## The per-machine store

Some things are installed once per machine, not per project, so that ten projects do not download the same dependencies ten times. They live in the store: a folder outside every project that coursekit creates when it first needs it.

Where it is, in order of precedence:

| Where | Path |
|---|---|
| `COURSEKIT_HOME` is set | That folder. |
| macOS | `~/Library/Application Support/coursekit` |
| Linux | `$XDG_DATA_HOME/coursekit`, or `~/.local/share/coursekit` when `XDG_DATA_HOME` is not set |
| Windows | `%LOCALAPPDATA%\coursekit` |

What it holds:

| Path (inside the store) | Written by | Content |
|---|---|---|
| `workspaces/<name>-<hash>/` | `coursekit setup --media` (Remotion); `coursekit setup` and `coursekit assemble build` (html builder) | A Node workspace installed once with `npm install`: the Remotion one (`workspaces/remotion-<hash>/`) and the builder of the html backend (`workspaces/html-builder-<hash>/`, with `@studiolxd/scorm` and `esbuild`). `<hash>` is computed from its `package.json` and `package-lock.json`: projects with the same dependencies share the folder, and a project that edits its `package.json` gets another one. The html builder takes its `package.json` from coursekit, so every project of the same version shares it. |
| `installed.json` | `coursekit setup`, `coursekit assemble build` | The record of what coursekit installed outside the projects, so that `coursekit uninstall` can take it away. |

`installed.json` is a JSON file with one list per kind of thing:

| Key | Holds |
|---|---|
| `uv_tools` | Names of the `uv` tools `setup` installed (`piper-tts`, `stable-ts`). |
| `files` | Paths of the voice files `setup` downloaded (`.onnx` and `.onnx.json`). |
| `shell_lines` | The lines `setup` added to `~/.zshrc` or `~/.bashrc` (file and variable name): the certificate variables for a TLS-inspecting proxy, preceded by the comment `# coursekit (TLS-inspecting proxy)`. |
| `windows_env` | Names of the user variables `setup` defined on Windows. |
| `system` | Packages `setup` installed with Homebrew or winget (`manager` and `packages`). `coursekit uninstall` never removes them: it lists them. |
| `workspaces` | Names of the folders of `workspaces/` that coursekit installed (`remotion-<hash>`, `html-builder-<hash>`), whether `setup` or the first `coursekit assemble build` did it. |

Do not edit it by hand. It is only a record: if it is lost, the shell-file lines, the `uv` tools of coursekit and the folders of `workspaces/` are still recognised by `coursekit uninstall`, but the voice files, the Windows variables and the system packages are not.

### What is per machine and what is per project

| Per machine (outside the project) | Per project |
|---|---|
| The store: `workspaces/` and `installed.json`. | `tools/remotion/`: the sources of the Remotion workspace (`package.json`, compositions), versioned with the project. |
| The `uv` tools (`piper-tts`, `stable-ts`), in the folders of `uv`. | `tools/remotion/node_modules`: a link to `workspaces/remotion-<hash>/node_modules` in the store (a symbolic link; a junction on Windows). It is not versioned. |
| The Piper voice files, in `~/.local/share/piper` (`%LOCALAPPDATA%\piper` on Windows). | `.env`: `PIPER_VOICE` points at the voice file. |
| The lines in the shell files and the user variables of Windows. | `project.yaml › network`: which CA certificate to use. |
| The system packages (`ffmpeg`, `node`, `vhs`, `asciinema`). | |
| `workspaces/html-builder-<hash>/`: the builder of the html backend (`@studiolxd/scorm`, `esbuild`). | Nothing: the project keeps no copy or link; `coursekit assemble build` uses the one in the store. |

The `.gitignore` that `coursekit init` writes ignores `node_modules/` (`coursekit init --update` refreshes the `.gitignore` unless you edited it by hand), so the link is never committed. If the link cannot be made, or `tools/remotion/` already has a real `node_modules` folder, that folder is used as it is.

`coursekit doctor` shows the path and size of the store and whether the Remotion dependencies are reachable; `coursekit uninstall` takes the store apart. See [`coursekit setup`](03-commands.md#coursekit-setup), [`coursekit doctor`](03-commands.md#coursekit-doctor) and [`coursekit uninstall`](03-commands.md#coursekit-uninstall).

## Worked examples

### Change the passing score

For new courses, in `config/rules.yaml`:

```yaml
defaults:
  grading:
    passing_score: 70
```

```bash
coursekit rules --changed
# defaults.grading.passing_score  70  (config)
```

Courses that already exist keep the value they were created with. To change `PWD`, edit `courses/PWD/course.yaml`:

```yaml
design:
  grading:
    passing_score: 70
```

and reassemble so that the quizzes in creator get the new value.

### Change the SCORM standard

In `config/delivery.yaml`:

```yaml
export:
  standard: scorm_2004
```

```bash
coursekit config delivery --changed
# export.standard  scorm_2004  (config)
coursekit delivery name PWD --unit 1 --version 2
# PWD-U01-v2-scorm2004.zip
```

For a single course, put the same two lines in a `delivery:` section of `courses/PWD/course.yaml`.

### Change words per page

In `config/rules.yaml`:

```yaml
words_per_page: 450
```

The minimums are stored in each course, so refresh them:

```bash
coursekit agents              # skills show the new number
coursekit sync PWD --check    # preview
coursekit sync PWD            # write the new minimums into course.yaml
```

### Require the client's review

For every course of the project, in `config/delivery.yaml`:

```yaml
client_review:
  required: true
```

```bash
coursekit config delivery --changed
# client_review.required  true  (config)
coursekit delivery check PWD
# PWD needs the client's review before it is delivered (delivery.yaml › client_review.required): `coursekit client PWD send`
```

For a single course, use the `delivery:` section of its `course.yaml` (see above). `coursekit config delivery --course PWD` shows the value in force with its origin.

### Make one course stricter

In `courses/PWD/course.yaml`:

```yaml
rules:
  content:
    questions_per_objective: 8
```

```bash
coursekit rules PWD --changed
# content.questions_per_objective  8  (course)
```

Next: [Agents](05-agents.md)
