# Agents

How coursekit uses AI coding tools: which tools and roles exist, what `coursekit agents` generates for each tool, and how to launch, restrict and customise the agents.

## Tools and roles

coursekit works with three tools. It does not install them: they must be on your `PATH` (`coursekit doctor` tells you which are missing).

| Tool | Value in `.env` | How you use it |
|---|---|---|
| Claude Code | `claude` | Open `claude` in the project folder and type slash commands such as `/write-unit PWD 1`. |
| opencode | `opencode` | Open `opencode` in the project folder and type the same slash commands. |
| Codex | `codex` | Open `codex` in the project folder and ask for the command (for example "run /write-unit PWD 1"). Codex has no project slash commands: it reads the command file `.coursekit/agents/commands/write-unit.md` and follows it. |

Any of them can also be launched for you with `coursekit write`, `coursekit review` and `coursekit run` (see below).

The work is split into five roles. Each role has a tool and a model.

| Role | Does | Slash commands it runs | Default tool | Default model (Claude Code) | Default model (opencode) |
|---|---|---|---|---|---|
| `design` | Instructional design proposal and changes; the theme and design tokens | `/new-course`, `/design-change`, `/approve-design`, `/define-theme`, `/course-status` | `claude` | `opus` | `anthropic/claude-opus-5-5` |
| `writer` | Writes the content of a unit | `/write-unit` | `claude` | `sonnet` | `anthropic/claude-sonnet-5-5` |
| `reviewer` | AI review of a written unit | `/review-unit`, `/approve-unit` | `claude` | `opus` | `anthropic/claude-opus-5-5` |
| `media` | Produces and uploads media assets | `/produce-media` | `claude` | `opus` | `anthropic/claude-opus-5-5` |
| `assembly` | Loads content into creator or builds the html packages, processes the client's review comments, exports or records packages, syncs directives | `/assemble`, `/client-feedback`, `/deliver`, `/sync-directives` | `claude` | `sonnet` | `anthropic/claude-sonnet-5-5` |

Codex has no proposed model: with `codex`, the model is Codex's own default unless you set one. The reviewer defaults to a different model than the writer on purpose: another model catches more.

## Choose the tool and model of each role

Three ways, from lasting to one-off:

1. **Guided**: `coursekit setup --roles` shows the proposal, asks you to confirm it and, if you decline, asks the tool and model of each role. With `--yes` (or without a terminal) it keeps what is already in `.env` and fills in the defaults above.
2. **By hand in `.env`** (personal, not committed):

   ```bash
   WRITER_AGENT=opencode
   WRITER_MODEL=anthropic/claude-sonnet-5-5
   REVIEWER_AGENT=claude
   REVIEWER_MODEL=opus
   ```

   `<ROLE>_AGENT` is `claude`, `opencode` or `codex` (default `claude` if unset). `<ROLE>_MODEL` is an id that tool understands; empty means the tool's default model. See [Configuration](04-configuration.md).
3. **For one launch**: `--agent TOOL` and `--model MODEL` on `coursekit write`, `coursekit review` and `coursekit run`. `--agent` alone uses that tool's default model, not the one in `.env`.

```bash
coursekit roles      # tool and model of each role in force (and whether the tool is installed)
coursekit doctor     # also checks that each role's tool is installed
```

In the opencode interface the model comes from the generated `writer` and `reviewer` agents (see below), which take it from `WRITER_MODEL` and `REVIEWER_MODEL` when that role uses opencode; coursekit regenerates them when it launches an opencode role, or run `coursekit agents` yourself. In that interface `--model` is not applied, and the other roles (`design`, `media`, `assembly`) use opencode's own default model. With `--headless`, `--model` is always passed to the tool.

## What `coursekit agents` generates

```bash
coursekit agents
# agents: 4 written, 51 unchanged, 0 removed
```

The source is the package plus your overrides in `.agents/` (see below). Each file is rendered with the project values and copied to where each tool reads it. It also runs inside `coursekit setup`, and from the project's git hooks after every pull and checkout (once `coursekit setup` has enabled them).

| Content | Claude Code | opencode | Codex and any other tool |
|---|---|---|---|
| Skills | `.claude/skills/<name>/SKILL.md` | `.opencode/skill/<name>/SKILL.md` | `.coursekit/agents/skills/<name>/SKILL.md` |
| Slash commands | `.claude/commands/<name>.md` | `.opencode/command/<name>.md` | `.coursekit/agents/commands/<name>.md` |
| Agents | none | `.opencode/agent/writer.md`, `.opencode/agent/reviewer.md` | none |
| Reference docs | `.coursekit/docs/content-format.md` and `.coursekit/docs/slxd-mcp.md` (shared by all tools) | | |
| Instructions | `CLAUDE.md` (imports `AGENTS.md`) | `AGENTS.md`, listed in `opencode.json` | `AGENTS.md` |
| slxd MCP server | `.mcp.json` | `opencode.json` | `.codex/config.toml` |
| Deny rules | `.claude/settings.json` | `opencode.json` | none |

`AGENTS.md` and `CLAUDE.md` are created by `coursekit init` and refreshed by `coursekit init --update`; the rest is produced by `coursekit agents`. The skills, commands, agents and docs under `.claude/`, `.opencode/` and `.coursekit/` are git-ignored: they are regenerated, never edited by hand. The MCP and permission files (`.mcp.json`, `opencode.json`, `.claude/settings.json`, `.codex/config.toml`) are not ignored, so they can be committed with the project.

How coursekit treats files:

- Every generated file carries a comment `generated by coursekit agents` and the place to edit it. Files with that marker are overwritten when the source changes and removed when the source disappears.
- A file in those folders **without** the marker (one you wrote yourself) is never overwritten or removed; `coursekit agents` lists it as kept.
- `.mcp.json`, `opencode.json`, `.claude/settings.json` and `.codex/config.toml` are merged, never replaced: your other entries stay.
- Other files in a skill folder (examples, assets) are copied unchanged next to its `SKILL.md`.

### Skills

| Skill | Used when |
|---|---|
| `instructional-design` | Proposing and changing a course's instructional design in slxd (`/new-course`, `/design-change`, `/approve-design`). |
| `content-writing` | Writing a unit's `content.md` and `assessment.md` (`/write-unit`). |
| `content-review` | Reviewing a unit written by another model and writing the report in `reviews/` (`/review-unit`). |
| `theme-definition` | Choosing or creating the theme of the project (or of one course) in slxd creator, adapting it to the brand and deriving the design tokens from it with `coursekit theme import` (`/define-theme`). |
| `media-production` | Producing and uploading the media assets, using the design tokens of the theme (`/produce-media`). |
| `creator-assembly` | Loading and reloading content into slxd creator, and the preview and review links of each unit (`/assemble`, creator backend). |
| `html-assembly` | Building the SCORM package of each unit with `coursekit assemble build`, looking at the preview and packaging a version (`/assemble`, html backend). It reads the same `.md` and the same produced media; the output is never edited by hand. |
| `client-review` | Reading the client's comments on the review links, applying the agreed ones to the `.md`, publishing a new review version and answering each comment (`/client-feedback`, creator backend only: the html backend has no review links). |
| `delivery` | Exporting (creator) or building (html), recording and publishing the SCORM packages (`/deliver`). |

Which of the two assembly skills applies depends on the backend of the course (`assembly.backend` in `project.yaml`, or in `course.yaml`; `coursekit status CODE` shows it). The `theme-definition` skill also covers both backends.

Skills and commands read the production numbers from your configuration: words per hour, directives per hour, questions per objective and so on are rendered from [Configuration](04-configuration.md); no number is written in a skill by hand.

### Slash commands

| Command | Arguments | What it does |
|---|---|---|
| `/new-course` | `"<title>" <hours> [--code ABC101] [--no-intro] [--no-summary] [--no-material] [indications]` | Creates the course and builds the instructional design proposal in slxd for human review. It runs `coursekit theme show` and, if the project has no design tokens, tells you in its summary to run `/define-theme` before producing media. If there is no material the agent asks before designing (unless `--no-material`) and, if you go on without it, marks the syllabus as an assumption. |
| `/design-change` | `<CODE> <changes>` | Applies in slxd the changes you ask for on the design proposal. |
| `/approve-design` | `<CODE>` | Prepares the sign-off of the design and tells you how to sign it. |
| `/define-theme` | `[CODE]` | Defines the theme in slxd creator and derives the design tokens of the media from it. With the html backend there is no platform theme: it writes or adapts the stylesheet `theme/maqueta.css` with the brand in its CSS variables and runs `coursekit theme import theme/maqueta.css`. Without a code it works on the theme of the project, which every course inherits; with a code, on the own theme of that course (`courses/<CODE>/theme/`, recorded in `slxd.theme_id`), which wins for it. It lists the platform's themes, you choose or create one (from nothing, from a preset or as a copy), it adapts it with the brand colours and fonts, saves the `get_theme` result to `.cache/theme/get_theme.json` and runs `coursekit theme import`. It never writes `tokens.json` by hand. You validate the theme as you validate the design. See [Theme and design tokens](02-workflow.md#theme-and-design-tokens). |
| `/course-status` | `[CODE]` | Runs `coursekit status` and explains the state of the courses (or of one) and the next step in two or three lines. Not tied to a phase: use it at any point. |
| `/write-unit` | `<CODE> [N]` | Writes a unit of a course whose design is signed. Without `N`, it writes every unit still to write, in order, in the same session (it stops at the first one that does not verify). `coursekit write` launches it with a number: one session per unit. |
| `/review-unit` | `<CODE> <N>` | AI review of a written unit, with a report in `reviews/` whose Result is repeated in a `<!-- result: ... -->` comment (`ready`, `ready_with_changes` or `not_ready`); it finishes with `coursekit reviewed`. See [AI review](02-workflow.md#4-ai-review). |
| `/approve-unit` | `<CODE> <N>` | Checks that a unit is ready for editorial sign-off and tells you how to sign it. |
| `/produce-media` | `<CODE> [asset id]` | Produces the pending media assets and uploads them. |
| `/assemble` | `<CODE> [N]` | Loads the skill of the backend of the course. Creator: loads the content of a course or unit into creator (only what changed) and applies the theme of the course to each content (`set_content_theme`, with the id from `coursekit theme show --course CODE`); without tokens derived from the platform it leaves the default theme and tells you about `/define-theme`. Html: builds the package of each unit with `coursekit assemble build CODE --unit N` and tells you what to check in the preview. Without a unit number it processes every unit in order. |
| `/client-feedback` | `<CODE> [N]` | Creator backend only (it needs the review links, which the html backend does not have). Reads the client's comments on the review links of a course (or of one unit), applies the agreed ones to the `.md`, reloads, publishes a new review version and answers each comment. It never opens or closes a round: you do that with `coursekit client`. |
| `/deliver` | `<CODE> [version]` | Starts with `coursekit delivery check`, then exports the SCORM packages, records them and publishes them in the mirror folder. With the html backend there is no export from a platform: for each unit it runs `coursekit assemble build CODE --unit N --version X.Y` and records the zip with `coursekit delivery add` without `--job` or `--snapshot`. |
| `/sync-directives` | none | Syncs the directive registry (`config/directives.yaml`) with the creator brick catalog. Not tied to a course or a phase: run it when the catalog changes. See [At any point](02-workflow.md#at-any-point). |

When you type a slash command in an already open session, that session's tool and model apply. The roles in `.env` apply when coursekit launches the tool for you. In opencode, `/write-unit` and `/review-unit` select the `writer` and `reviewer` agents.

For Codex, the same commands are plain files. Ask Codex for the command ("run /assemble PWD") and it follows `.coursekit/agents/commands/assemble.md`; the skills are in `.coursekit/agents/skills/<name>/SKILL.md`. When coursekit launches Codex it passes that instruction itself.

## The slxd MCP server

Agents talk to slxd creator through an MCP server configured in `project.yaml`. It is needed with both assembly backends, because the instructional design (matrix, Excel) is always done in creator; with the html backend the assembly itself does not use it:

```yaml
platform:
  slxd:
    mcp_name: slxd-creator
    mcp_url: https://acme.example.com/mcp/creator
```

`coursekit agents` writes it into each tool, only when `mcp_url` is set:

| Tool | File | Entry |
|---|---|---|
| Claude Code | `.mcp.json` | `mcpServers.<mcp_name>` with `type: http` and the URL |
| opencode | `opencode.json` | `mcp.<mcp_name>` with `type: remote`, the URL and `enabled: true` |
| Codex | `.codex/config.toml` | `[mcp_servers."<mcp_name>"]` with `url` |

Each person authenticates with their slxd account (OAuth) the first time a tool uses the server. A session without an interface (the handoff, `--headless`) cannot do that: authorize the server once with `/mcp` in your AI tool, or log in to the creator connector of your account and name it in `platform.slxd.connector`, which also lets those sessions use its tools. `.codex/config.toml` is generated only if it does not exist or still has the `generated by coursekit agents` line; remove that line to manage the file by hand. With no `mcp_url`, `coursekit doctor` reports it and the design role (and, with the creator backend, the media and assembly roles) cannot reach slxd. The skills explain how to call the tools that are not listed directly (`find_tools`, `tool_schema`, `run_tool`); the reference is `.coursekit/docs/slxd-mcp.md`.

## Permissions: what agents may not do

Agents must never sign anything. Approvals are recorded only by `coursekit approve`, which only a person runs; agents tell you what to type. The same goes for the decisions of people that other commands record: `coursekit client` (rounds of client review and what the client decided) and `coursekit hold` / `coursekit resume` (pausing a course) and `coursekit reviewed --by` (the review of a person). `coursekit handoff` is denied too: it signs by itself, so an agent that could start it would be signing. The project's `AGENTS.md` also tells every tool not to commit or push unless you ask, not to write credentials in versioned files and not to install software (they ask you to run `coursekit setup` instead).

coursekit enforces the essentials in each tool:

| Tool | Denied by configuration | Where |
|---|---|---|
| Claude Code | `coursekit approve`, `coursekit client`, `coursekit hold`, `coursekit resume`, `coursekit handoff`, `coursekit reviewed ... --by`, `git push`, and editing `courses/*/assembly/*.json` | `permissions.deny` in `.claude/settings.json` |
| opencode | `coursekit approve`, `coursekit client`, `coursekit hold`, `coursekit resume`, `coursekit handoff`, `coursekit reviewed ... --by`, `git push` | `permission.bash` in `opencode.json` |
| opencode `writer` and `reviewer` agents | the `writer`: `coursekit approve`, `client`, `hold` and `resume`, also `git commit` and `git push`; the `reviewer`: those plus `coursekit handoff` and `coursekit reviewed ... --by` (the `opencode.json` rules above apply to both); any other shell command asks first; `coursekit verify`, `status`, `brief`, `outline`, `config`, `git status` and `git diff` are allowed (the reviewer may also run `coursekit reviewed`) | `.opencode/agent/*.md` |
| Codex | nothing in configuration: it relies on the `AGENTS.md` instructions | |

Headless launches add their own limits (see below). The rules you have to apply yourself: review `git diff` before committing, and run `coursekit approve` only in your own terminal.

## Launch an agent

### `write` and `review`: unit by unit

```bash
coursekit write PWD 1                 # write unit 1 with the writer role
coursekit write PWD                   # every unit still to do, in order
coursekit review PWD 1                # review unit 1 with the reviewer role
coursekit review PWD 1 --full         # whole unit, even if reviewed before
coursekit review PWD 1 --parts "section 4"   # only those parts
coursekit write PWD 2 --agent opencode --model anthropic/claude-sonnet-5-5
```

| Option | Meaning |
|---|---|
| `CODE` `[N]` | Course code and unit number. Without `N`, every unit still to do: for `write`, units pending or being written; for `review`, units already verified. |
| `--agent`, `--model` | Tool and model for this launch (override `.env`). |
| `--headless` | Run without the tool's interface (see below). |
| `--full`, `--parts` | Review only. By default, a unit already reviewed is reviewed again only in the parts that changed since; `--full` reviews the whole unit and `--parts` names the parts. `write` does not accept them. |

What coursekit does on each launch:

- It records the writer in `units[N].written_with` and the reviewer in `reviewed_with` of `course.yaml`, as `tool · model` (for example `claude · sonnet`, or `claude · default model`).
- It starts the tool with `/write-unit CODE N` or `/review-unit CODE N` (for Codex, with the instruction to follow the command file).
- With several units, it goes on to the next one when the tool ends cleanly (interactive) or when the unit reached the expected status (headless), and stops at the first one that does not: "stopped at unit N: fix it and launch the command again".

### A reviewer different from the writer

The review is worth most when it is done by another model. If the reviewer's tool and model are the same as the unit's writer, coursekit warns and goes on:

```text
warning: unit 1 was written with claude · sonnet, the same tool and model as this review; another model catches more (REVIEWER_AGENT / REVIEWER_MODEL in .env)
```

If `course.yaml` does not say who wrote the unit, the warning asks you to check it was not the same model. The review command also tells the reviewer agent to mention it at the start of the report, and `coursekit doctor` flags a project whose writer and reviewer roles are the same tool and model.

### `run`: any other command

```bash
coursekit run new-course "Strong passwords" 2 --code PWD
coursekit run define-theme
coursekit run assemble PWD
coursekit run deliver PWD 1
coursekit run course-status
coursekit run produce-media PWD --agent opencode --model anthropic/claude-opus-5-5
coursekit run assemble PWD --role design     # run it with another role's agent
```

`coursekit run NAME [ARGS]` launches any command with the agent of its role (table above). `--role` chooses another role (`design`, `writer`, `reviewer`, `media`, `assembly`); for a command that is not in the table the default role is `design`. `--headless`, `--agent`, `--model` and `--role` may come after the command name.

### Headless (`--headless`)

Headless runs the tool without its interface so another agent or a scheduled task can launch it:

- The agent is told nobody can answer: it must not ask questions, decide with what it has, leave doubts noted in the content or in its report, and finish with a short summary of what it did and what is pending.
- The full session goes to `.cache/logs/` (git-ignored): `<CODE>-uNN-write-<date>-<time>.log` or `...-review-...` for units, `<command>-<role>-<date>-<time>.log` for `run`. For Codex there is also a `.last.txt` with its final message.
- coursekit prints the final message of the session and where the log is: `unit 1: reviewed · session in .cache/logs/PWD-u01-review-20261009-101500.log`. If the tool failed it adds `· exit N`.
- For `write` and `review`, the exit code is 0 only if the unit reached the expected status (written: `verified` or later; reviewed: `reviewed` or `approved`); otherwise it is the tool's exit code, or 1.
- The tool runs from the project folder in a clean session: environment variables starting with `CLAUDE` are not passed on.

How each tool is called, and its limits:

| Tool | Command (simplified) | Limits |
|---|---|---|
| Claude Code | `claude -p ... --permission-mode acceptEdits --allowedTools ... --disallowedTools ...` | Allowed: read, edit and write files, skills, and only these shell commands: `coursekit verify`, `brief`, `status`, `outline`, `config`, `git status`, `git diff` (the reviewer also `coursekit reviewed`). The `design`, `media` and `assembly` roles also get the slxd MCP server (and, when `platform.slxd.connector` names one, that connector of your account), any `coursekit` command and web fetch. Always denied: `git commit`, `git push`, `coursekit approve`, `coursekit client`, `coursekit hold`, `coursekit resume`, `coursekit handoff`, `coursekit reviewed ... --by`. |
| opencode | `opencode run [--agent writer\|reviewer] --auto --format json ...` | Writer and reviewer run as the generated agents with their permissions; the instruction points at the command file because `run` has no slash commands. |
| Codex | `codex exec --sandbox workspace-write --json -o <log>.last.txt ...` | Workspace-write sandbox. |

## Customise with `.agents/`

To change what coursekit generates, add files under `.agents/` in the project, with the same layout as the package:

```text
.agents/
  skills/<name>/SKILL.md
  commands/<name>.md
  agents/<name>.md
  docs/<name>.md
```

- A file with the same name **replaces** the package's one; a new name **adds** one.
- Files starting with `_` (for example `.agents/skills/_house-rules.md`) are partials: include them in any file with `{{> _house-rules}}` (the name includes the underscore).
- Texts can use `{{token}}` values. An unknown token or partial stops `coursekit agents` with an error that names the file.
- Run `coursekit agents` afterwards. Generated files say at the top where to edit them.

```bash
mkdir -p .agents/skills/content-writing
# write your own SKILL.md there, then:
coursekit agents
```

Available tokens:

| Token | Value |
|---|---|
| `{{project_name}}`, `{{client}}`, `{{tone}}` | `name`, `client` and `tone` of `project.yaml` |
| `{{language_name}}`, `{{ui_language_name}}` | Name of the content language and of the interface language |
| `{{address_rule}}` | The rule for addressing learners, from `address` |
| `{{backend}}`, `{{mcp_name}}` | `assembly.backend` and `platform.slxd.mcp_name` |
| `{{t_section}}`, `{{t_objective}}`, `{{t_placeholder}}`, `{{t_assessment}}`, `{{t_intro_title}}`, `{{t_summary_title}}`, `{{t_unit}}`, `{{t_question_key}}`, `{{placeholder_field_lines}}` | Content format words for the content language (heading word, objective tag, placeholder label...) |
| `{{k_question}}`, `{{k_answer}}`, `{{k_answers}}`, `{{k_feedback}}`, `{{k_feedback_correct}}`, `{{k_feedback_incorrect}}`, `{{k_image}}`, `{{k_position}}`, `{{k_title}}`, `{{k_objective}}` | Keys of the directive lines in the content language (`question`, `feedback-correct`… in English; `pregunta`, `feedback-correcto`… in Spanish) |
| `{{w_true}}`, `{{w_false}}`, `{{w_starts}}`, `{{w_contains}}` | Words that some keys take in the content language (`true`/`false` in `true-false`; `starts`/`contains` in `pasapalabra`) |
| `{{pages_per_hour}}`, `{{words_per_page}}`, `{{words_per_hour}}`, `{{word_margin_pct}}` | Word rules from `rules` |
| `{{questions_per_objective}}`, `{{placeholders_per_hour}}`, `{{min_placeholder_types}}`, `{{placeholder_types}}`, `{{interactive_per_hour}}`, `{{min_interactive_per_content_section}}`, `{{allowed_symbols}}` | Content rules from `rules`. `{{placeholder_types}}` lists each allowed type as the word written in the content followed by its id in parentheses |
| `{{competencies_per_course}}`, `{{objectives_per_unit}}`, `{{intro_summary_hours}}` | Design guidance from `rules` |
| `{{model}}` | Only in files of `agents/`: the role's model when the role uses opencode; the line is dropped otherwise |

Next: [Content](06-content.md)
