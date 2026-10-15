# Workflow

The whole production process of a course, from the brief to the delivery: who does what, which statuses exist and what moves them.

## The process at a glance

```text
 brief -> design -> [SIGN DESIGN] -> writing -> AI review -> editorial review -> [SIGN EACH UNIT]
         \                                                                              |
          +-> theme (once per project, before media) ----+                              |
                                                         v                              |
 delivered <- [client review: optional] <- assembly <- media <--------------------------+
```

At any point a person can pause the course (`on_hold`) and resume it later. See [Pause a course](#pause-a-course).

There is an alternative path for courses that nobody has to review: [handoff mode](#handoff-mode) runs phases 2 to 9 by itself (without the client review), and coursekit signs in place of a person, marked as Coursekit Handoff.

| # | Phase | Who | Main commands | Result |
|---|---|---|---|---|
| 1 | Brief | person | `coursekit brief [CODE]` | reference material converted in `brief/` |
| 2 | Instructional design | design agent, then person | `/new-course`, `/design-change`, `/approve-design` | proposal in SLXD Creator, exported to `courses/<CODE>/design/` |
| 2b | Design sign-off | **person** | `coursekit approve design <CODE>` | units and sections written into `course.yaml` |
| 2c | Theme and design tokens | design agent, then **person** validates | `/define-theme [CODE]`, `coursekit theme show` | theme in the platform; `theme/tokens.json` and `tokens.css` derived from it. Once per project, before media: see [Theme and design tokens](#theme-and-design-tokens) |
| 3 | Writing | writer agent | `coursekit write <CODE> [N]`, `/write-unit`, `coursekit verify` | `content.md` and `assessment.md` per unit |
| 4 | AI review | reviewer agent | `coursekit review <CODE> [N]`, `/review-unit` | `reviews/unit-NN-ai-review.md` |
| 5 | Editorial review and sign-off | **person** | `/approve-unit`, `coursekit approve content <CODE> --unit N` | unit `approved` |
| 6 | Media | media agent | `coursekit media ...`, `/produce-media` | assets produced and uploaded |
| 7 | Assembly | assembly agent | `coursekit assemble ...`, `/assemble` | creator backend: content loaded into SLXD Creator. html backend: a SCORM package built per unit by coursekit (`coursekit assemble build`). See [Assembly and delivery by backend](#assembly-and-delivery-by-backend) |
| 8 | Client review (optional) | **person**, then assembly agent | [`coursekit client`](03-commands.md#coursekit-client), `/client-feedback` | rounds recorded in `course.yaml`; the client's comments applied to the Markdown and answered |
| 9 | Delivery | assembly agent | `coursekit delivery ...`, `/deliver` | SCORM packages (exported from creator, or built by coursekit with the html backend) recorded and published |

The Markdown of each unit is the source of truth. Anything wrong in Creator (or in an html package) is fixed in the `.md` and loaded or built again, never edited in the output.

## Who does what

| | Person | Agent |
|---|---|---|
| Brief | gathers the material | converts it (`coursekit brief`) and reads it |
| Design | reviews the proposal, asks for changes, **signs** | proposes and changes it in SLXD Creator |
| Writing | starts it, reads the result | writes and runs `coursekit verify` |
| AI review | starts it | reviews with another tool or model, writes the report, runs `coursekit reviewed` |
| Editorial review | reads and edits each unit, **signs** | prepares the sign-off (`/approve-unit`) |
| Theme | chooses or approves the theme, validates it like the design | defines it in the platform with the brand colours and fonts and derives the tokens (`/define-theme`) |
| Media, assembly, delivery | decides, checks the result | produces, loads, exports |
| Client review | opens and closes each round and records what the client decided | reads the client's comments, applies the agreed ones to the Markdown and answers them (`/client-feedback`) |
| Pause and resume | decides (`coursekit hold`, `coursekit resume`) | cannot do it |
| Handoff (alternative path) | starts it and accepts the result without reviewing it | runs every step; coursekit signs as Coursekit Handoff |
| Commits and pushes | does them | does not, unless asked |

Each agent runs on one of six **roles**: `design`, `writer`, `reviewer`, `media`, `illustration` and `assembly`. Each role has a tool (`claude`, `opencode`, `codex`) and a model, kept in `.env` (`DESIGN_AGENT`, `DESIGN_MODEL`, and so on). `coursekit roles` shows them. A review is best done by a different model than the writer: coursekit warns when both are the same. See [Agents](05-agents.md).

**Only a person signs.** `coursekit approve` records your name, the time and a fingerprint of what you approved, and commits it with you as author. The agent settings of Claude Code and opencode deny agents to run it, and also `coursekit client`, `coursekit hold`, `coursekit resume`, `coursekit handoff` and `coursekit reviewed --by`, which record decisions of people or sign in their place; Codex has no such denial in its configuration and relies on the `AGENTS.md` instructions (see [Agents](05-agents.md#permissions-what-agents-may-not-do)). The one exception is [handoff mode](#handoff-mode), where coursekit itself signs, marked, as Coursekit Handoff. From an agent chat you can run it yourself by prefixing the line with `!`:

```text
! coursekit approve design PWD --yes
```

In your own terminal, without `--yes`, it asks for confirmation first. Without a terminal and without `--yes` it refuses. `--no-commit` records the approval without committing.

## Handoff mode

`coursekit handoff "<title>" <hours>` takes a course from its title to its delivery **by itself**: nobody reviews the design, the units or the media on the way, and there is no client review. It is meant for courses whose quality you accept without a person's reading; use the normal flow when someone has to review.

```bash
coursekit handoff "Strong passwords" 2 --code PWD   # a new course, from its title and hours
coursekit handoff PWD                               # carry on a course that stopped
```

`--rounds` sets the attempts. `--code`, `--no-intro`, `--no-summary` and `--notes` create the course the way [`coursekit new`](03-commands.md#coursekit-new) does; they and `--no-pause` only make sense when creating it, and when carrying on coursekit refuses them (exit code 2).

The only pause is at the start: once the course folders exist, in a terminal, it waits for you to drop the reference material of the course (`courses/<CODE>/brief/`) and press Enter. `--no-pause` skips it; without a terminal it never waits. When the look of the project comes from brand material that is not there yet (html backend, or creator with `theme.source: branding`), the pause also tells you to drop it in `theme/branding/`. After that it goes on by itself, and it never asks about the theme: it follows `theme.source`.

| Status of the course | What handoff does |
|---|---|
| (new) | coursekit creates the course folders and waits for the reference material (see above); then the design agent proposes the design (`/new-course` on the existing course; it does not ask for material). |
| `design` | If `design/matrix.json` does not exist yet, the design agent exports the proposal (`/design-change`; with a local design, `coursekit design`). Then it refreshes and validates the export (`/approve-design`); coursekit signs the design as **Coursekit Handoff**. If it cannot be signed, the design agent fixes it and it tries again. |
| `design_approved`, `writing` | The writer agent writes each unit until it verifies. When an attempt leaves errors, the next one gets them in `reviews/unit-NN-fix.md` (see *Fix only this* below). |
| `ai_review` | The reviewer agent reviews each unit. If the `<!-- result: ... -->` line of its report says `not_ready` (see [AI review](#4-ai-review)), the writer fixes only what `reviews/unit-NN-fix.md` lists (the errors of `verify` and the blocking findings the review did not apply) and it is reviewed again. With `review.ai: skip` this stage does not happen: the units are already `reviewed`. |
| `editorial_review` | coursekit signs each unit as Coursekit Handoff. |
| `media` | coursekit extracts the media manifest. If a pending asset is of a type that uses the theme (`uses_theme`) and the design tokens are not derived (missing or written by hand), the design agent defines the theme (`/define-theme`) following `project.yaml › theme.source` and the material in `theme/branding/`, without asking; the media agent produces the assets (`/produce-media`); the assembly agent assembles (`/assemble`). |
| `assembly` | With the creator backend, if produced assets are not uploaded yet (they can only be uploaded to the content of their unit, which the assembly creates), the media agent uploads them and the assembly agent assembles again so they replace their placeholders; it stops if they stay unuploaded or the course is not in creator as planned. With the html backend coursekit first plays every package (`coursekit assemble check`) and, if it finds errors, writes them to `reviews/package-check.md` and stops. Then the assembly agent delivers (`/deliver`). |

- **Signatures.** Every approval it gives is by `Coursekit Handoff <handoff@coursekit.local>` and carries `via: handoff` in `course.yaml › approvals`, and the commit has that author, so it is never mistaken for a person's. The agents still cannot sign nor run `coursekit handoff`: the signature is given by coursekit, not by them.
- **Attempts.** Each step is tried `rules › handoff › rounds` times (`--rounds`). If it still fails (a unit that does not verify, an AI review that stays `not_ready`, media assets left to produce, a course that does not assemble or deliver) it stops, with exit code 1, and the message says what failed and where the agent session is logged (`.cache/logs/`). It also stops, with a pointer to `coursekit status`, when a step changes nothing (neither the course status, nor the units, nor the approvals). If the cause is a refusal that another attempt would meet again (a program or a server that a session without an interface is not allowed to use), it does not repeat the step: it stops and names it.
- **Fix only this.** When a unit fails (it does not verify, or the review says `not_ready`), coursekit writes `reviews/unit-NN-fix.md`: the errors of `coursekit verify` with the place they point at, and the blocking findings of the AI review that were not applied, with their section and criterion (the review writes the severity `blocking` and the action `applied` or `proposed` untranslated, so they can be read). The writer is told to fix that list and nothing else. Each report keeps the fingerprint of its findings: if a round ends with the same findings as the round before (even if their line numbers moved), the handoff stops there instead of spending another round, and the report says what is left. The report is deleted when the unit passes.
- **A new version of a delivered course.** After editing the content of a `delivered` course, `coursekit handoff <CODE> --new-version` verifies every unit again and puts the course back in the status they imply (the edited units fall back to `verified`, so the AI review looks at the parts that changed and coursekit signs them again; if none fell back, it goes on from `media`). It then runs the usual stages: media marked to be produced again (`coursekit media redo`) is produced, the assembly applies only the differences, and the delivery makes the next version (`1.1`, `1.2`…). The reopening is recorded in the `history` of the `course.yaml`.
- **Carry on.** `coursekit handoff <CODE>` continues from the current status, without repeating what is signed. If the course is `on_hold` (the message says to run `coursekit resume <CODE>` first) or in `client_review` it stops: handoff does not handle either. `coursekit handoff "<title>" <hours>` refuses a course code that already exists and points to `coursekit handoff <CODE>`.
- **What it refuses.** If the project requires the client review (`delivery › client_review › required`) it refuses to start, before creating the course, and to carry on while that review is not approved or skipped: handoff does not do it. Both end with exit code 1.
- **How it runs.** Every agent runs headless, with the limits in [Agents](05-agents.md#headless---headless). The sessions are logged in `.cache/logs/` (`<CODE>-<step>-handoff-<date>-<time>.log`, and `<CODE>-uNN-write-…` or `-review-…` for the units). After each step the mirror folder and the catalog are refreshed, if the project has them. At the end it prints `handoff finished`, with the status of the course.
- **What it needs.** The roles of the `.env` and, when the course uses slxd (creator backend, or a design made in slxd), the slxd MCP URL, like the normal flow, with creator already authorized (a session without an interface cannot sign in; see [MCP server problems](09-troubleshooting.md#mcp-server-problems)), and the providers of the media you want produced. It cannot ask: doubts are left written in the units (`<!-- VERIFICAR -->`) and in the reports.

## Statuses

### Course

A course has one status in `course.yaml › status`:

| Status | Meaning | What moves it here |
|---|---|---|
| `design` | design proposal in progress | `coursekit new` creates the course in this status |
| `design_approved` | design signed, writing not started | `coursekit approve design` |
| `writing` | at least one unit is started | derived from the units |
| `ai_review` | every unit passes verification | derived from the units |
| `editorial_review` | every unit is AI-reviewed | derived from the units |
| `media` | every unit is signed | derived from the units |
| `assembly` | every unit is loaded in Creator exactly as planned (creator backend) | `coursekit assemble applied`, automatically, only from `media`. `coursekit assemble build` (html backend), automatically, when every unit has its package built and the course was in `media` |
| `client_review` | a round of client review is open (optional stage) | [`coursekit client`](03-commands.md#coursekit-client) `CODE send`, only from `assembly` |
| `delivered` | every unit has a package of the same version | `coursekit delivery add`, automatically, only from `assembly` or `client_review` |
| `on_hold` | paused by a person | [`coursekit hold`](03-commands.md#coursekit-hold) `CODE --reason "..."`; [`coursekit resume`](03-commands.md#coursekit-resume) `CODE` brings it back |

From `design_approved` to `media`, the status is **derived** from the least advanced unit and recalculated every time a unit changes status. So it can also go back when a unit does. Signing a changed design again keeps the progress of the units, and the status is derived from them again. From `assembly` onwards it is not recalculated.

`client_review` and `on_hold` are not derived from the units: they are set by the commands below.

#### Client review (optional)

The client reviews the assembled course before delivery. It is **off by default**: `client_review.required` is `false` in the delivery configuration, so the flow `assembly` -> delivery works as always, and you may still open a round if you want one. When a project sets `client_review.required: true`, the delivery is refused until the last round is approved or skipped. The setting can be overridden per project (`config/delivery.yaml`) and per course (`course.yaml › delivery › client_review`); see [Configuration](04-configuration.md#delivery-scorm-export-and-client-review).

```text
 assembly --send--> client_review --approve--> (deliver)
    ^                    |
    +------changes-------+          skip: deliver without the client's approval, with a reason
```

| Command (people only) | Effect |
|---|---|
| `coursekit client CODE send [--to WHO] [--where URL]` | Opens round N. The course moves from `assembly` to `client_review` and the review links of the units are recorded in the round |
| `coursekit client CODE changes [--note TEXT]` | The client asked for changes: the round closes with outcome `changes` and the course goes back to `assembly` |
| `coursekit client CODE approve --by "Name" [--note TEXT]` | The client approved: the round closes with outcome `approved`, with the client's name and the date. The course stays in `client_review` and can be delivered |
| `coursekit client CODE skip --reason TEXT` | You decide to deliver without the client's approval. It records a round with outcome `skipped` and the reason, which unlocks the delivery (then `/deliver`); it does not deliver nor change the status. Allowed from `assembly` or `client_review`, and refused while a round is open |

A round in a normal flow:

1. The assembly agent has recorded a preview link and a review link per unit (`coursekit assemble link`). With the html backend there are no platform links: you host the zip or the preview folder yourself and send one link with `--where URL`.
2. You send the links to the client and open the round: `coursekit client PWD send --to "ACME training team"`.
3. The client comments on the review links, without an account.
4. `/client-feedback PWD` (assembly agent, creator backend only: it reads the comments of the review links): reads the comments, applies the agreed ones in the `.md`, reloads the changes, publishes a new review version for the client and answers each comment. Comments that change objectives, hours, activities or structure are a design change and are left to you (`/design-change`).
5. You close the round: `coursekit client PWD changes --note "..."` if the client wants more; then apply, reassemble and `send` again (round 2). If the client agrees, `coursekit client PWD approve --by "..."`.
6. Deliver with `/deliver`.

A unit edited after its signature goes back to `verified`: it needs a new AI review and signature before delivery, as in [Changes after approval](#changes-after-approval). See [Assembly and delivery](08-assembly-and-delivery.md#client-review) for the review links and the creator tools involved.

#### Pause a course

`coursekit hold CODE --reason "..."` puts the course in `on_hold`; `coursekit resume CODE` brings it back. Only a person runs them. Pausing stores the previous status, the reason, who and when in `course.yaml › hold` and adds an entry to `history`.

While a course is on hold, the commands that change it are refused: `write`, `review`, `reviewed`, `approve`, `assemble` (every action, including `plan` and `diff`), `sync` (without `--check`), `media set`, `run` (with the code of a course, except `new-course` and `course-status`), `client` and the delivery commands (`delivery check`, `name` and `add`). The commands that read or check still work (`status`, `verify`, `outline`, `config`, `sync --check`, `catalog`...). `coursekit status CODE` shows who paused it, when, why and where it was. The message of a refused command ends with the way back: `coursekit resume CODE`.

`resume` restores the previous status and removes the `hold` block. If the course was being written (`design_approved` to `media`), the status is calculated again from its units.

### Unit

Each unit has its own status in `course.yaml › units[].status`:

```text
pending -> writing -> verified -> reviewed -> approved
```

| Status | Meaning | What moves it here |
|---|---|---|
| `pending` | no content yet | `coursekit approve design` (units are created from the design) |
| `writing` | content started but it does not pass `coursekit verify` | `verify` finds errors in a unit with words, or in a unit that was further ahead |
| `verified` | passes every check of `coursekit verify` | `verify` without errors |
| `reviewed` | the AI review report exists (or a person recorded their review, or the project skips the AI review) and the unit still verifies | `coursekit reviewed <CODE> <N>` (run by the reviewer agent), `coursekit reviewed <CODE> <N> --by NAME`, or `coursekit verify` with `review.ai: skip` |
| `approved` | signed by a person | `coursekit approve content <CODE> --unit N` |

Rules that decide the course status: any unit past `pending` makes it `writing`; every unit `verified` or beyond makes it `ai_review`; every unit `reviewed` or beyond, `editorial_review`; every unit `approved`, `media`.

### What `coursekit status` shows

```bash
coursekit status           # one line per course
coursekit status PWD       # detail and next step
```

```text
PWD — Strong passwords (2 h)
Status: design_approved
Assembly: creator backend
Design: signed by Ana Ruiz <ana@acme.example> on 2026-10-09T01:18:52+02:00
  U1 Strong passwords · 2 h · 3 sections · 2 objectives · min. 10,000 words · pending
Next step: write the units with `coursekit write PWD <N>`
```

The detail lists each unit with its status and, if known, the tool that wrote it. If the course is on hold it adds who paused it, when, why and the status it had; if there is a client review it adds the last round and its outcome (`open`, `asked for changes`, `approved` or `skipped`). The last line is the next step for the current status. If the design changed after being signed, the "Design" line says so and the next step is to sign it again.

### What is recorded in `course.yaml`

| Key | Content |
|---|---|
| `status` | the course status |
| `units[].status` | the unit status |
| `units[].written_with`, `reviewed_with` | tool and model of the writer and of the reviewer |
| `units[].review` | how the unit was reviewed: `kind` (`ai`, `human` with `by`, `at`, `note`, `report`, or `skipped`) |
| `units[].reviewed_parts` | fingerprint of every section and activity at the time of the AI review |
| `approvals` | every sign-off: gate (`design` or `content`), who, when and the hashes of what was approved |
| `units[].links.preview`, `units[].links.review` | live preview of the unit (no comments) and its client review link, written by `coursekit assemble link` |
| `client_review` | the rounds of client review: `round`, `sent_at`, `sent_by`, `to`, `links`, `outcome`, `closed_at`, `by`, `note` |
| `hold` | present only while `on_hold`: `previous` status, `reason`, `by` and `at` |
| `deliveries` | every recorded SCORM package: version, unit, date, file and hash |
| `history` | one entry per course status change and per approval: `date`, `status`, `by`, `note` |
| `assembly.backend` | optional: the backend of this course (`creator` or `html`) when it differs from the project's |

Do not edit `status`, `units`, `client_review` or `hold` by hand: the commands write them. Approvals are written only by `coursekit approve`.

## Phase by phase

### 1. Brief

Drop documents in `brief/sources/`, URLs in `brief/links.md` and general indications in `brief/notes.md`. A course has its own `brief/` with the same layout, and its notes win over the project ones. Then:

```bash
coursekit brief            # project brief
coursekit brief PWD        # brief of one course (includes the project one)
coursekit brief --refresh  # download the URLs again
```

This writes `brief/index.md` and the converted text in `brief/text/`, which is what the agents read. Only new or changed files are converted.

### Import from eXeLearning

A course that already exists as eXeLearning packages (`.elp`, eXeLearning 2 and 3) is not written again from scratch: its content is converted to Markdown, keeping its structure and its kind of interactivity, and the agents work from it. Drop the `.elp` files in `brief/sources/` and `coursekit brief` converts them like any other document, or create whole courses with [`coursekit import`](03-commands.md#coursekit-import).

What the conversion does:

| In the package | In the Markdown |
|---|---|
| Tree of pages | A heading per page (`##`, `###`…); pages with no content are left out |
| Text, lists, tables, images | Markdown; the images are copied to `brief/text/media/<package>/` |
| `exe-accordion`, `exe-tabs`, `exe-carousel` (in any iDevice) | `:::accordion`, `:::tabs`, `:::carousel`, one `#### Title` per panel (a slide without a title gets its number) |
| Flip cards, relate game, map | `:::flashcards`, `:::match`, `:::labelled-graphic` (with the position of each point) |
| Multiple choice, multi-select, true or false | `:::single-choice`, `:::multi-select`, `:::true-false`, with the feedback of the options; the questions come without objective, which the design assigns |
| Generic iDevices (warning, definition, example, "did you know", reflection) | `:::note`, `:::highlight`, `:::reflection`, by the rules of [`import`](04-configuration.md#import-exelearning-packages) |
| The prompt before an interactive ("Click on the arrows…") and the instructions of the games | Left out: the interactives of coursekit bring their own |
| Videos and other embedded content | A `> **[Video]** address` line, counted by host in the report |

Nothing is dropped silently. `brief/import-report.md` lists, per package, what the rules left out (with its text and how many times), the iDevices with no rule (imported as text), the embedded content by host, the pages left out, and a **word-by-word check**: every word of the text of the source must be in the Markdown, and the report names the ones that are not. `coursekit brief` flags the packages with something to look at in `brief/index.md`. Only the `.elp` of eXeLearning 2 and 3 are read; a package of eXeLearning 4 (`.elpx`) must be exported again as `.elp`.

Courses from a folder: a folder with `.elp` files is a course and each package a unit; a parent folder with one subfolder per course creates all of them. The hours (and the title) are not in the packages, so they come from the plan (`coursekit import <folder> --plan` writes `import.yaml` to fill in and review), from an Excel or CSV with the folder and the hours (`--hours-file`) or from one value for all of them (`--default-hours`). The units are ordered by the number in the name of each package, and a course with two versions of the same unit waits until the plan says which one to use. With `--handoff` each course goes on to delivery by itself.

A course created by `coursekit import` has `design.origin: import`, and the agents work on it as a **migration**: the design proposes the units and sections from the structure of the packages (one unit per package, one section per page), keeps each interactive as it is, uses the hours you gave, and proposes the objectives and the learning and assessment activities the packages lack, marking what is new; the writing reuses the client's text without rewriting it (the skeleton of each unit shows, instead of a minimum of words, the page of the package each section comes from and its words, and `coursekit verify` fails if the unit grows beyond [`content.import_max_growth`](04-configuration.md#rules-production-rules) times its package), registers the images of the packages instead of making them again (`coursekit media adopt`) and replaces embedded video on a forbidden host with a video placeholder; the AI review adds a criterion of **fidelity to the package** (nothing lost, nothing reworded without a reason, every interactive of the same kind). In this kind of course `coursekit verify` only warns when a section falls short of its words, interactives or placeholders, and names the units that fall short of or run over the words of their hours.

Videos hosted on a site you forbid (YouTube, Vimeo…) can stay when they come from an **official channel**: list the channels in `rules › forbidden › allow_channels` and `coursekit videos check` approves those videos. For the rest the writing agent searches the web for an equivalent video on an official channel and registers it with its evidence (`coursekit videos propose`); `reviews/external-videos.md` lists those proposals for a person to check (`coursekit videos approve` or `reject`), and `coursekit verify` warns while one is unchecked. The handoff cannot ask you, so it stops before the content goes into creator while a proposal is unchecked (`handoff.stop_on_unchecked_videos`) and carries on with `coursekit handoff CODE` once you have settled it; a channel you list in `allow_channels` never waits. With no official equivalent the video becomes a media placeholder.

A migrated course is **corrected, not expanded**: the hours are the ones you gave, the content keeps the size of the packages (a unit that falls short of the words its hours ask for is a warning of `coursekit verify`, never a reason to write more), and only what is out of date, wrong or forbidden is changed.

To make the migration follow the client's wishes, write them in `brief/notes.md` (for example "remove every reference to a region" or "do not keep videos hosted on other sites") and list what must not remain in `rules › forbidden`: addresses of sites (`hosts`, subdomains included) and words or phrases (`terms`). The agents apply the notes, the import report counts what the packages contain of it, and `coursekit verify` rejects every occurrence that is left. If a course is about an application or a regulation, the design agent also proposes its official documentation or text for `brief/links.md` ([`brief.reference_sources_max`](04-configuration.md#rules-production-rules)), so the reviewer can check the content against it.

### 2. Instructional design

```text
/new-course "Strong passwords" 2 --code PWD
```

The design agent creates the course, reads the brief and builds a **proposal**: competencies, units, objectives, sections, activities and hours. Where depends on `course.yaml › design.tool`: in the design matrix of SLXD Creator (`slxd`) or in `courses/PWD/design/design.yaml` (`local`, see [Local design](#local-design)). Either way it exports the design to `courses/PWD/design/` (`matrix.json`, `validation.json` and the Excel you review) and ends with a summary. Review it, then ask for changes in plain words:

```text
/design-change PWD Add a unit on password managers and move 0.5 hours to it
```

When you are happy:

```text
/approve-design PWD
```

The agent refreshes the export if you edited in Creator (or in `design.yaml`), validates the design, runs `coursekit sync PWD --check` and summarises what you are about to sign. It cannot sign. Then you do:

```bash
coursekit approve design PWD
```

The sign-off requires `design/matrix.json` and no validation errors in `design/validation.json` (and, in a decision-based course, the [story bible](06-content.md#story-bible)). It writes the units and their sections into `course.yaml` (progress already recorded is kept: status, review record and links), creates a skeleton `content.md` and `assessment.md` per unit in `content/unit-NN/`, records the approval, sets the course to `design_approved` and commits.

#### Local design

A course with `design.tool: local` (the choice of `coursekit init`, `rules › defaults.design_tool` or `coursekit new --design-tool local`) needs no slxd: its design is `courses/<CODE>/design/design.yaml`, which the design agent writes (`coursekit new` leaves a commented template) and you may edit too. Keys in English, texts in the language of the course:

```yaml
profile: {audience: Office staff, level: Basic, prerequisites: "", context: "", tone: ""}
passing: all_tests                  # or course_score, with course_passing_score: 0-100
competencies:
  - {id: C1, text: Protect the work accounts in daily office work}
objectives:                         # the course's, in order
  - {id: O1, text: Apply the criteria of a strong password to a new account, bloom: apply, competencies: [C1]}
  - {id: O2, text: Analyse why a password is weak, bloom: analyze, competencies: [C1]}
units:                              # with design.structure con_modulos: modules: [{title, hours, general_objective, units}]
  - title: Passwords that protect
    sections:
      - {title: Introduction and objectives, hours: 0.2}
      - {title: What a strong password looks like, hours: 0.6, objectives: [O1, O2]}
      - {title: Summary, hours: 0.2}
    learning_activities:
      - {title: Sort the passwords, type: classification, objectives: [O1, O2]}
    assessment_activities:
      - {title: Unit test, instrument: case_study, criterion: Half right, weight: 1, passing_score: 50,
         attempts: 2, objectives: [O1, O2]}
```

- `bloom`: `remember`, `understand`, `apply`, `analyze`, `evaluate`, `create`. Learning activity `type`: `self_assessed`, `classification`, `interactive_decision`, `branching_scenario`, `hotspot_analysis`, `guided_simulation`, `template_practice`. Assessment `instrument`: `quiz`, `case_study`, `portfolio`, `rubric`. `weight`, `passing_score` and `attempts` are optional (the course's `design.grading` applies).
- A section may be split into `subsections` (each with its hours and objectives); a unit or a module without `hours` takes the sum of its parts, and with them they must add up. The total is `course.yaml › design.hours`.
- The ids of objectives and competencies are free and unique (`O1`, `C1`...). The content names the objectives of each unit `U1.1`, `U1.2`... as `coursekit sync --check` prints them. Give a unit or a section an `id` of its own if you move it around a design that was already synced.

[`coursekit design PWD`](03-commands.md#coursekit-design) checks it with the rules of a design matrix (coverage, evidence, practice before assessment, instrument and Bloom level, hours, verbs, progression) and exports `matrix.json`, `validation.json` and `PWD-instructional-design.xlsx`; from there the flow is the same as with slxd. The sign-off refuses a `design.yaml` that was not exported, and a later export that changes the design invalidates the signature (exporting again without changes does not).

### 3. Writing

```bash
coursekit write PWD 1      # unit 1
coursekit write PWD        # every unit still to do, in order
```

Or `/write-unit PWD 1` in your AI tool (`/write-unit PWD`, without a number, writes every unit still to write, in order, in the same session and stops at the first that does not verify; `coursekit write` instead opens one session per unit). The writer agent works on one unit at a time, section by section, and runs `coursekit verify` after each one. Add `--headless` to run without the tool's interface (the session goes to `.cache/logs/`; then it stops at the first unit that does not end `verified`), and `--agent`/`--model` to use another tool or model for this launch.

```bash
coursekit verify PWD --unit 1
```

`verify` checks the content against the production rules (word minimums, objective tags, interactive directives, placeholders, forbidden symbols...) and moves the unit status. It refuses to run if the design is not signed or changed after signing. See [Content](06-content.md).

### 4. AI review

```bash
coursekit review PWD 1
```

Or `/review-unit PWD 1`. The reviewer agent writes `reviews/unit-01-ai-review.md` (findings, changes applied, proposals awaiting your decision) and runs `coursekit reviewed PWD 1`, which checks again that the unit verifies and marks it `reviewed`. Reviewing a unit that was already reviewed is partial: only the sections and activities changed since the last review. Use `--full` to review everything, or `--parts "section 4, activity 1.2"` to choose.

The report opens with its **Result** (ready, ready with changes or not ready), repeated in a comment that tools read: `<!-- result: ready | ready_with_changes | not_ready -->` (one value, with underscores). The rest is a summary, a table of findings (each one blocking, improvement or minor), the changes applied and the proposals awaiting your decision. A partial review appends its own section to the same report and updates the Result if it changes. In [handoff mode](#handoff-mode) a `not_ready` result sends the unit back to the writer.

#### Without AI review

Two ways, and a person signs in both:

- **One unit, reviewed by a person.** After reading it, run `coursekit reviewed PWD 1 --by "Ana Pérez" [--note "..."] [--report reviews/notes.md]`. The unit becomes `reviewed` without the AI report, and `course.yaml › units[].review` and the history record who reviewed it. Content edited after that goes back to `verified`, as with the AI review. `--note` and `--report` need `--by`, and the report must be a file inside the course folder. The record `units[].review` is removed if the unit goes back below `reviewed`. Agents are denied `--by`.
- **The whole project (or one course), no AI review at all.** Set `review.ai: skip` in `rules` (`config/rules.yaml`, `project.yaml › rules` or `course.yaml › rules`). A unit that passes `coursekit verify` is `reviewed` straight away (`review.kind: skipped`), the course goes from `writing` to `editorial_review` without the `ai_review` phase, and your sign-off is the review. `coursekit review` still works if you want an AI review of a unit anyway.

#### Update out-of-date content (optional)

Courses age: products change name and interface, versions and prices move, regulations are replaced. `/update-unit PWD 1` (or `coursekit run update-unit PWD 1`) asks the reviewer agent to check the unit against current official sources: first the documentation the brief downloaded, then the web. It writes `reviews/unit-01-currency.md` with each finding (what the unit says, what is true now with its source, the text it proposes) and the claims it could not verify, and **changes nothing** unless you add `--apply`. Even then it writes only plain facts that have an official source (a name, a version, a figure, a date, an interface path, a link); anything that changes what the unit teaches stays as a proposal for you. A unit whose content changed goes back to `verified` and needs the AI review again.

The `update.mode` rule (`config/rules.yaml`, `project.yaml` or one course's `course.yaml › rules`) makes the handoff run it before the AI review of each unit: `off` (default; it does not run by itself), `propose` (report only) or `apply`. See [`rules`](04-configuration.md#rules-production-rules).

### 5. Editorial review and sign-off

Read the unit in `courses/PWD/content/unit-01/`, resolve the proposals in the AI review report and edit the Markdown as needed. After editing, run `coursekit verify PWD --unit 1`: if the edit touched parts the AI reviewed, the unit goes back to `verified` and needs another (partial) review before it can be signed. Then:

```text
/approve-unit PWD 1
```

The agent checks that the unit verifies and the report exists, and tells you to sign:

```bash
coursekit approve content PWD --unit 1
```

Signing requires: the design still signed and unchanged, no verification errors, the unit `reviewed` (or `approved`) and its AI review report (not needed when a person recorded their review with `coursekit reviewed --by`, nor with `review.ai: skip`). It records the hashes of `content.md` and `assessment.md` and commits the unit, the report and `course.yaml`. When the last unit is signed, the course moves to `media`.

### 6. Media

```text
/produce-media PWD
```

The media agent extracts the placeholders of the content into a manifest (`coursekit media extract`), shows the plan (`coursekit media plan`, which names each type by its English id: `image`, `infographic`, `video`…) and tells you what it will produce and with what before spending credits of paid APIs. Infographics, diagrams, animated GIFs, simulations and videos are made with the design tokens of the theme, so they need `/define-theme` first: see [Theme and design tokens](#theme-and-design-tokens). See [Media](07-media.md).

### 7. Assembly

```text
/assemble PWD
```

`/assemble` loads the skill of the backend of the course: `creator-assembly` or `html-assembly` (`coursekit status PWD` shows it: `Assembly: creator backend` or `Assembly: html backend`).

**Creator backend.** The assembly agent builds a plan per unit (`coursekit assemble plan`), compares it with what is already in Creator (`coursekit assemble diff`), applies only the differences and records every lesson (`coursekit assemble applied`). When every unit is in Creator exactly as planned, the course moves from `media` to `assembly`. The agent creates the links of each unit (each unit is its own content in creator): a live preview, without comments, and a review link where the client comments; it records them with `coursekit assemble link` and gives them to you. It also applies the theme of the course to each content (`set_content_theme`, with the id that `coursekit theme show --course PWD` gives).

**html backend.** The agent runs `coursekit assemble build PWD --unit N` for each unit (without `--unit`, every unit). It writes a preview folder, `courses/PWD/assembly/html/unit-NN/`, that opens from the disk in a browser, and refuses the content that cannot be rendered (a key in the wrong language, a question without its options...); the folder is generated and is not versioned. With `--version X.Y` it also writes the zip of the unit in `courses/PWD/delivery/`. The agent tells you what to check in the preview (navigation, one component of each kind, the questions and the test).

See [Assembly and delivery](08-assembly-and-delivery.md).

### 8. Client review

Optional. A round is opened and closed by a person with [`coursekit client`](03-commands.md#coursekit-client) (see [Client review (optional)](#client-review-optional) above); the agent only handles the comments with `/client-feedback PWD`. With the html backend there is no review link from a platform: you host the zip or the preview folder and give the link yourself, with `coursekit client PWD send --where URL`. `/client-feedback` works with the creator backend only; with html the comments reach you your own way, you apply them by editing the `.md` and `/assemble PWD` builds again. If a unit goes back after editing, run `coursekit verify`, review and sign again where needed, and `/assemble PWD` loads only what changed.

### 9. Delivery

```text
/deliver PWD 1.0
```

The agent starts with `coursekit delivery check PWD`: it refuses while the course is on hold and, if the project requires the client's review, until the last round is approved or skipped. Then it exports one SCORM package per unit, downloads it to `courses/PWD/delivery/` and records it with `coursekit delivery add`. When every unit has a package of the same version, the course becomes `delivered` (only from `assembly` or `client_review`; in another status the package is recorded with a warning). Each `coursekit delivery add` also copies the course to the mirror folder and refreshes the catalog (when the project has one). See [Assembly and delivery](08-assembly-and-delivery.md).

With the html backend nothing is exported from a platform: for each unit the agent runs `coursekit assemble build PWD --unit N --version 1.0` (it writes the zip in `courses/PWD/delivery/`) and then `coursekit delivery add` without `--job` or `--snapshot`. The check at the start, the record and the publication are the same.

### At any point

Two commands do not belong to a phase:

- `/course-status [CODE]` (design role) runs `coursekit status` and explains the result and the next step in two or three lines.
- `/sync-directives` (assembly role) keeps the directive registry in step with the creator brick catalog. Run it when the catalog changes, not once per course. It saves `list_brick_types` in `.cache/list_brick_types.json`, checks it with `coursekit directives check` and, for each new brick type, decides whether it becomes a directive in `config/directives.yaml` (or goes to `not_directives` with the reason). It removes the types that disappeared, listing the content that used them without changing it, and updates `synced_with_creator`.

## Assembly and delivery by backend

A course is assembled either in **slxd creator** or with the **html backend**. The choice is made once per project in `project.yaml › assembly.backend` (the `init` wizard asks for it; the default is `creator`) and a course can override it in `course.yaml › assembly › backend`. `coursekit status CODE` shows `Assembly: <backend> backend`. Everything before the assembly (brief, design, writing, review, media) is the same, and the instructional design is done in creator with either backend.

| | creator backend | html backend |
|---|---|---|
| Where it is assembled | in SLXD Creator, through the slxd MCP server | in your project: coursekit renders each unit as a page with its navigation, progress, components and SCORM tracking |
| What builds the package | the platform exports the SCORM (`/deliver`, with the export tools) | coursekit (`coursekit assemble build CODE [--unit N] [--version X.Y]`, with @studiolxd/scorm and esbuild from the coursekit store) |
| Output | content in creator; the zip is downloaded to `delivery/` | preview folder `assembly/html/unit-NN/`; with a version, the zip in `delivery/` |
| Agent skill | `creator-assembly` | `html-assembly` |
| How the client reviews | preview and review links of creator, recorded with `coursekit assemble link`; comments on the link | you host the zip or the preview and send the link with `coursekit client CODE send --where URL`; the comments reach you your own way |
| What registers the delivery | `coursekit delivery add` with `--job` and `--snapshot` of the export | `coursekit delivery add` without them |
| Theme | a theme of the platform, tokens derived with `coursekit theme import <get_theme.json>` | the stylesheet `theme/maqueta.css`, tokens derived with `coursekit theme import theme/maqueta.css` |

Commands of one backend are refused in the other, with a message that points to the right one (see [Troubleshooting](09-troubleshooting.md#the-html-backend)). The html backend does not need the platform to assemble, but the package must be tried in the LMS it will be delivered to (or in SCORM Cloud) before it is handed over. The details are in [Assembly and delivery](08-assembly-and-delivery.md).

## Theme and design tokens

The graphics, simulations and videos of a course use the colours and fonts of its theme, so they look like the course. The theme lives in the assembly platform (creator). coursekit never takes the colours and fonts from a hand-written file: it **derives** the design tokens from the theme of the platform and records where they come from.

```text
/define-theme            # the theme of the project, which every course inherits
/define-theme PWD        # the own theme of one course
```

What `/define-theme [CODE]` does (design role, skill `theme-definition`):

1. Looks at `coursekit theme show` to see whether the tokens already come from a platform theme (if so, it asks before redoing them) and reads the brand material for colours, fonts and logos: `theme/branding/` (logos, font files, guidelines, colour lists) and `brief/`. The choice made when the project was created is `project.yaml › theme.source`.
2. With `tenant_default` it takes the theme the platform marks as default (`isDefault`) and does not create or change anything. With `branding` it makes the theme from `theme/branding/` (without material, it uses the default one and says so). In a session with a person, or when the person asks for something else, it lists the themes of the platform and you choose one or create a new one: from nothing, from a preset or as a copy of an existing one. A change to a theme changes every content that uses it, so to change only one course the agent copies the theme and links the copy.
3. Adapts it with the brand colours and fonts (`update_theme`) and reports the platform's warnings.
4. Saves the result of `get_theme` to `.cache/theme/get_theme.json` and runs `coursekit theme import .cache/theme/get_theme.json`. That writes `theme/tokens.json` and `theme/tokens.css` with an `origin`: theme id, name, version and date. It prints the notes and the contrast of each colour pair; if a pair is below the minimum the colour is fixed in the platform and imported again, never edited in the tokens.
5. Summarises the result for you. **You validate the theme as you validate the design.**

Where the tokens live:

| Scope | Files | How |
|---|---|---|
| Project (every course inherits it) | `theme/tokens.json`, `theme/tokens.css` | `/define-theme` |
| One course (wins for that course) | `courses/<CODE>/theme/tokens.json`, `tokens.css`; the theme id is recorded in `course.yaml › slxd.theme_id` | `/define-theme <CODE>` |

`coursekit theme show` prints which tokens apply (`coursekit theme show --course PWD` for a course) and where they come from: the project's or the course's, the theme of the platform with its id and version, and when they were imported. `coursekit theme tokens` rewrites the CSS, `coursekit theme check` measures the contrast and `coursekit theme import FILE [--course CODE]` derives the tokens; the options are in [`coursekit theme`](03-commands.md#coursekit-theme).

Where it sits in the flow: once the project exists and before producing media, ideally right after `/new-course` (which tells you in its summary when the project has no tokens). The assembly uses the same theme (see [Assembly and delivery](08-assembly-and-delivery.md#the-theme-of-the-course)).

The guard. The design tokens are only trusted when they come from the platform:

- `coursekit media plan` warns when a course has infographics, diagrams, animated GIFs, simulations or videos and the tokens are missing or were written by hand.
- `coursekit media set CODE ID --status produced` (or `uploaded`) for those five types is **refused** unless the tokens are derived from the platform. `--force` skips the guard when you accept the risk.
- The asset remembers which tokens it was made with. If you import the theme again and the colours or fonts change, `coursekit media plan` says which assets must be produced again.
- `coursekit doctor` has a "Project theme" section that tells you whether the project's tokens are derived, missing or written by hand.

The list of types that need tokens is `uses_theme` in the `media` configuration ([Configuration](04-configuration.md#media-production-options)).

Notes: if the platform theme has a dark mode, the tokens are those of the light mode. Softer text, surfaces, line, radius, spacing and shadow do not exist in the platform theme; coursekit derives them and the import lists them.

With the `html` assembly backend there is no platform theme. The tokens are derived from the CSS variables of the stylesheet `theme/maqueta.css` laid over the base layout of the package (`--color-accent`, `--color-text`, `--font-family`, `--radius`...). `/define-theme` writes or adapts that stylesheet from the material in `theme/branding/` and runs `coursekit theme import theme/maqueta.css` (with no stylesheet and no material, `coursekit theme import` without a file derives the tokens from the base layout); the tokens carry as origin the stylesheet and its fingerprint. The package is styled with the base layout, then the tokens, then `theme/maqueta.css` of the project and `courses/<CODE>/theme/maqueta.css` of the course if it exists, which may restyle anything.

## Changes after approval

coursekit compares what is on disk with the fingerprints taken at each step, so a change never goes unnoticed.

| What changes | What happens |
|---|---|
| The design is exported again with different content after being signed | `status` shows "the design must be approved again". `verify`, `approve content` and the writing skill stop until you sign again with `coursekit approve design`. Units keep their progress (status, who wrote and reviewed them, review record and links; they are matched by their SLXD id) and new units start `pending`. Until assembly the course status is derived from the units again (it does not go back to `design_approved` if they are further ahead); from `assembly` onwards it stays as it is |
| A reviewed unit is edited | the next `verify` sends it back to `verified` and lists the changed parts; `coursekit review` then reviews only those parts |
| An approved unit is edited | the next `verify` sends it back to `verified` (or `writing` if it no longer passes, or `reviewed` if no reviewed part changed). The old approval stays in `approvals` as history; you sign again |
| A unit no longer passes `verify` | it goes back to `writing` |
| A unit goes back while the course is between `design_approved` and `media` | the course status goes back with it |
| A unit goes back while the course is in `assembly` or later | the unit goes back, but the course status stays; sign the unit again and reassemble |
| A media placeholder changes | its asset returns to `pending` the next time you run `coursekit media extract` |
| The client asks for changes (`coursekit client CODE changes`) | the round closes and the course goes back to `assembly`; apply the changes, reassemble and open the next round with `send` |
| You sign a unit whose content changed after its AI review | `coursekit approve content` refuses and names the parts; review again, or `--force` to sign anyway |

Rule of thumb: after changing anything by hand, run `coursekit verify <CODE>`. `verify` is what sends a unit back; as a safety net, `coursekit approve content` also refuses a unit that changed after its AI review (it names the parts) unless you add `--force`.

## Worked example

A two-hour course on strong passwords for the client ACME, code `PWD`. Commands starting with `/` are typed in the AI tool, opened with `claude` (or `opencode`, `codex`) in the project folder.

```bash
coursekit init acme-courses
cd acme-courses
```

Reference material first (optional), then design:

```bash
cp ~/Documents/password-policy.pdf brief/sources/
coursekit brief
```

```text
/new-course "Strong passwords" 2 --code PWD
/design-change PWD Add a unit on password managers
/approve-design PWD
```

Define the theme once, any time before producing media (the agent proposes it from the brand material; you validate it):

```text
/define-theme
```

Sign the design yourself, in a terminal or from the chat:

```bash
coursekit approve design PWD
coursekit status PWD
```

Write and review, unit by unit or all at once:

```bash
coursekit write PWD 1
coursekit verify PWD --unit 1
coursekit review PWD 1
```

Read the unit and the AI review, edit what you want, check, and sign:

```bash
coursekit verify PWD --unit 1
coursekit approve content PWD --unit 1
```

With every unit signed (`coursekit status PWD` shows `media`), produce and assemble:

```text
/produce-media PWD
/assemble PWD
```

If the client reviews the course, open a round, let the agent process the comments and close the round (an optional step, required only if the project says so):

```bash
coursekit client PWD send --to "ACME training team"
```

```text
/client-feedback PWD
```

```bash
coursekit client PWD changes --note "Two wording changes in unit 1"
coursekit client PWD send --to "ACME training team"
coursekit client PWD approve --by "ACME training lead"
```

Then deliver:

```text
/deliver PWD 1.0
```

```bash
coursekit status
```

Next: [Commands](03-commands.md)
