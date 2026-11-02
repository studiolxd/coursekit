# Assembly

How an approved course is assembled: loaded into the assembly platform, or built as a web package by coursekit. The client's review is in [Client review](10-client-review.md); the export of the SCORM packages, their record, the shared folder and the catalog are in [Delivery and publishing](09-delivery.md).

```text
creator backend:  units approved ─► media uploaded ─► assemble (plan · diff · apply · record) ─► preview and review links
html backend:     units approved ─► media produced ─► assemble build (page · player · manifest) ─► preview folder and zip
                                                                                      │
                                                         client review (optional) ◄───┘
                                                                  │
                  catalog ◄─ publish (mirror folder) ◄─ delivery add (record packages) ◄─ SCORM package (export or zip)
```

## Assembly backends

The backend is chosen when the project is created (`coursekit init --backend creator|html`) and stored in `project.yaml › assembly.backend` (`creator` by default). A course can use the other one: `course.yaml › assembly.backend` overrides the project's. `coursekit status PWD` prints the one in force (`Assembly: html backend`).

| Backend | What it does | Where the unit ends up |
|---|---|---|
| `creator` | Converts `content.md` and `assessment.md` into creator bricks (`coursekit assemble plan`, `diff`, `applied`, `link`), loads them incrementally through the slxd MCP server, and exports the SCORM package from the platform | A content in creator, with preview and review links |
| `html` | Builds each unit as a web page with its own player (`coursekit assemble build`) and packages it as SCORM 1.2 or 2004 by itself. Same directives and same format as `creator` | A folder `courses/PWD/assembly/html/unit-01/` that opens in a browser, and a zip in `delivery/` |

Each backend refuses the commands of the other for a course: `plan`, `diff`, `applied` and `link` fail for an html course (they point to `build`), and `build` fails for a creator course. `coursekit verify` converts the content in both cases: with `html` it also reports the directives that are not available yet.

The instructional design is made in slxd (the design agent saves the matrix from the slxd MCP server) or in the project (`design/design.yaml`, [`coursekit design`](03-commands.md#coursekit-design)), with either backend. The MCP server (`project.yaml › platform.slxd.mcp_url` and `mcp_name`, default `slxd-creator`) is needed with the creator backend or a design made in slxd; with the html backend and a local design, nothing goes through slxd. The `coursekit init` wizard asks for the URL only when it is needed. `coursekit agents` writes the server into `.mcp.json`, `opencode.json` and `.codex/config.toml` (see [05-agents.md](05-agents.md)).

The sections [The assembly flow](#the-assembly-flow) to [Directive registry](#directive-registry-directives-check-and-sync-directives) describe the **creator backend**. The html backend has its own section, [The html backend](#the-html-backend). [Client review](10-client-review.md#client-review) and [Delivery](09-delivery.md#delivery) apply to both, with the differences noted there.

## The assembly flow

This and the next sections are about the creator backend. Never edit content directly in creator: if something is wrong, fix the `.md` and load it again. The conversion is deterministic (the same Markdown always gives the same bricks), so later edits become small update operations instead of a rebuild.

**Requirements.** The design is signed, every unit to assemble is `approved` (unsigned units only if you explicitly want a preview), and `course.yaml` has `slxd.matrix_id` (and `slxd.theme_id`, if the course has a theme of its own: `coursekit theme import --course` writes it). To have the contents themed, the design tokens must be derived from the platform first (`/define-theme`): see [The theme of the course](#the-theme-of-the-course).

| Step | Who | Command or tool |
|---|---|---|
| 1. Skeleton, first time only | assembly agent | Generates one content per unit with one lesson per section in creator; then `coursekit assemble link PWD --unit 1 --content-id <id>` stores `units[].content_id`. It also applies the theme of the course to each content (see below) |
| 2. Plan | `coursekit` | `coursekit assemble plan PWD --unit 1` writes `assembly/unit-01.plan.json` |
| 3. Differences | `coursekit` | `coursekit assemble diff PWD --unit 1` prints the operations to bring creator in line with the plan |
| 4. Apply | assembly agent | Applies the operations with the creator tools (`create_lesson`, `add_brick`, `update_brick`, `delete_brick`, `update_quiz_settings`…) |
| 5. Record | assembly agent | `coursekit assemble applied PWD --unit 1 --lesson U1-S1 --lesson-id <id> --brick-ids id1,id2,…` after each lesson; `--content` after renaming the content |
| 6. Repeat | | `diff` until the content and every lesson are `unchanged` |
| 7. Checks | assembly agent | Accessibility audit, text comparison with the `.md`, a snapshot named `assembly-YYYY-MM-DD`, and the two links of each unit (live preview and client review) saved with `coursekit assemble link --preview URL --review URL`. The links (and a new review version) are created only when no asset is left that is not `uploaded`: with creator the first assembly still shows placeholders, so the links wait for the assembly that follows the upload |

You launch the agent with `/assemble PWD 1` in Claude Code or opencode, or with `coursekit run assemble PWD 1` from a terminal; without a unit number it processes every unit in order. Run `plan` again after `link`, so the plan carries the `content_id`.

### The theme of the course

The colours and fonts of the contents in creator come from a theme of the platform, and the graphics, simulations and videos of the media were made with the design tokens derived from that same theme (`/define-theme`, see [Theme and design tokens](02-workflow.md#theme-and-design-tokens)). So the assembly does not take the theme id from a hand-filled field. The agent runs `coursekit theme show --course PWD`:

```text
project tokens: theme/tokens.json
origin: platform theme 'ACME corporate' (th_8c41, version 3), imported on 2026-10-09
```

and applies the id in the `origin:` line with `set_content_theme` to each content of the course. The theme of a course is its own one when it has it (`courses/PWD/theme/`, recorded in `slxd.theme_id`) and otherwise the one of the project. When there are no tokens derived from the platform (`coursekit theme show` says they are missing or were written by hand) there is no theme to apply: the contents keep the default theme of the platform and the agent tells you about `/define-theme`. A theme that is changed in the platform afterwards changes every content that uses it. The html backend does not use a platform theme: it styles the package with its own base layout and the tokens of the project (see [Styles](#styles)).

### `coursekit assemble`

| Action | Options | Result |
|---|---|---|
| `plan` | `--unit N` | Writes the plan and prints warnings; exit code 1 and no plan if there are errors |
| `diff` | `--unit N` | Prints JSON with the operations (needs the plan) |
| `applied` | `--unit N --lesson KEY --lesson-id ID --brick-ids ID1,ID2,…` | Records a lesson as applied; the number of ids must equal the bricks of the lesson in the plan |
| `applied` | `--unit N --content` | Records the content title as applied (after renaming it) |
| `link` | `--unit N --content-id ID` | Stores the creator content id of the unit |
| `link` | `--unit N --preview URL` and/or `--review URL` | Stores the live preview link and/or the client review link of the unit. At least one of `--content-id`, `--preview` and `--review` is required, and they can be combined |
| `build` | `[--unit N] [--version X.Y]` | Html backend only: builds the package of the unit (see [`coursekit assemble build`](#coursekit-assemble-build)) |

`plan`, `diff`, `applied` and `link` are for the creator backend and need `--unit` (without it: exit code 2). For a course assembled with the html backend they are refused.

```text
$ coursekit assemble plan PWD --unit 1
plan assembly/unit-01.plan.json: 4 lessons, 16 bricks (ACCORDION 1, NOTE 3, SINGLE_CHOICE 6, TABS 1, TEXT 4, TIMELINE 1)
```

### Files it writes

| File | Written by | Content |
|---|---|---|
| `assembly/unit-NN.plan.json` | `assemble plan` | `course`, `unit`, `content_id`, `content_title` and the lessons with their bricks (`type`, `data`, `meta`, `hash`) |
| `assembly/unit-NN.applied.json` | `assemble applied` | Per lesson: `lessonId`, `title` and its bricks (`brickId`, `type`, `hash`); plus `content_title` |
| `course.yaml › units[].content_id` | `assemble link` | The creator content of the unit |
| `course.yaml › units[].links.preview` | `assemble link --preview` | Live preview of the unit: it follows the content, without comments |
| `course.yaml › units[].links.review` | `assemble link --review` | Review link of the unit, where the client comments (see [Client review](10-client-review.md#client-review)) |
| `course.yaml › status` | `assemble applied` | Moves from `media` to `assembly` by itself when every unit is in creator exactly as planned |

Both JSON files are versioned with the course: they are what lets coursekit reload only what changed. Do not edit them by hand.

The links are **per unit**, not per course, because each unit is its own content in creator. There is no course-level `links` block. A command that changes the course (including `assemble`) is refused while the course is on hold: [`coursekit resume`](03-commands.md#coursekit-resume) first.

### What the plan contains

The html backend builds its pages from this same plan. Lesson keys are `U<unit>-S<section>` for content lessons and `U<unit>-E<N.M>` for assessment activities. The content is titled with the course title when it has a single unit, otherwise `Unit N. <unit title>`. Assessment lessons carry the settings of their quiz in the plan (see [Grading of a test](#grading-of-a-test)).

| Markdown | Brick |
|---|---|
| Consecutive paragraphs | `TEXT` (merged into one) |
| `###` to `######` | `HEADING` |
| Lists | `LIST` (bulleted or numbered) |
| Tables | `TABLE` |
| Code fences | `CODE` (the language if known, otherwise automatic) |
| Plain blockquote `> …` | `HIGHLIGHT` |
| `:::name` directive | The brick of the registry (table in [06-content.md](06-content.md)) |
| Media placeholder not uploaded | `NOTE` titled `Media asset — <type>: <title>` (the first words are those of the course language, and the type is written as in the content, for example `Infographic`), with description and specifications |
| Media placeholder uploaded | By type id: `image`, `infographic`, `diagram` and `animated_gif` become `IMAGE`; `video` becomes `VIDEO` (with captions and transcript if registered); `audio` becomes `AUDIO`; `simulation` and `terminal_demo` become `EMBED`; `job_aid` becomes an `ATTACHMENT` (the PDF). Plus an `ATTACHMENT` per uploaded download |
| Objective tags, `---`, HTML comments | Not published |

Only the **Instructions for the learner** and **Question bank** subsections of an activity of `assessment.md` go into its assessment lesson.

`plan` prints warnings for a `labelled-graphic` whose image is not produced yet and for a lesson without content. It fails (and `verify` reports it as `assembly: …`) when a directive is unknown or does not follow its structure: `single-choice` without exactly one correct option, `true-false` without `answer: true|false`, `fill-in-the-blank` without blanks written as `{answer}` in the `question:` line, a panel directive without `#### Title` panels, a `pasapalabra` item that does not match `- A (starts): definition :: ANSWER`, a key of the directive written in the other language, or a section that is not in the design.

The keys of the directive lines (`question:`, `answer:`, `answers:`, `feedback:`, `feedback-correct:`, `feedback-incorrect:`, `image:`, `position:`, `title:` and the objective key) and the words some of them take (`true`/`false`; `starts`/`contains`) are those of the course language. A Spanish course writes `pregunta:`, `respuesta: verdadero`, `(empieza)`, `(contiene)`… The tables with the keys and the words of each language are in [06-content.md](06-content.md#directives). A key of the other language is not ignored: `plan` fails, and `verify` reports it as `assembly: …`, naming the language the key belongs to and the valid keys:

```text
U1-S2: the key 'pregunta:' belongs to the language 'es'; this course uses: answer, answers, feedback, feedback-correct, feedback-incorrect, image, objective, position, question, title
```

### Grading of a test

Each assessment activity of the design has its own grading in creator (`design_matrix_ae_create` and `design_matrix_ae_update`): its weight (`peso`), its pass mark (`notaAprobado`, 0 to 100) and its attempts (`intentosMax`, `0` is unlimited). `coursekit sync` reads them into `course.yaml › units[].activities.assessment`, and the plan gives the quiz of each assessment lesson:

| Plan field (`quiz`) | From the design | When the design leaves it empty |
|---|---|---|
| `passingGrade` | `notaAprobado` | `design.grading.passing_score` of `course.yaml` (default `50`) |
| `maxAttempts` | `intentosMax` | `design.grading.attempts` (default `2`; `0` is unlimited) |
| `courseWeight` | `peso` | `1` |

The activity of a lesson is the one with the same title in the design, else the one in the same position of the unit (`U1-E1.2` is the second). With the creator backend the assembly agent passes the three values to `update_quiz_settings`. `courseWeight` is the weight of the quiz among the quizzes of the same unit, normalised (60 and 40 weigh like 3 and 2), and `0` leaves it out of the score. Each unit is its own course and its own package, so the weights never compare tests of different units: combining units into one grade is for the LMS.

A change only in the grading of a test (after signing the design again and running `plan`) shows in `diff` as an `update_quiz` operation of that lesson, and the course is not `assembly` again until it is applied. With the html backend the three values are written in the settings of each test, but the package reports one score for the unit (the best of its tests), so the weight does not change it.

### Where the tests go

The tests are written in the `assessment.md` of their unit, and the writing, the review and `verify` see them there. Where they end up is decided at assembly and delivery by `delivery › assessment` (a course may set its own in `course.yaml › delivery › assessment`):

| `placement` | What is assembled and delivered |
|---|---|
| `unit` (default) | Each unit carries its tests as evaluation lessons, and its package reports their score. |
| `separate` | The units carry no tests and report the learner's progress (`lessonProgress`), completed or incomplete (`completed_incomplete`). All the tests of the course go in one package of their own, one more unit after the last one (`coursekit status` gives its number), titled with the course title and «Assessment» («Evaluación» in Spanish); it reports the score (`quiz`). The plan of each unit says which in `score_source` (and `reporting: completed_incomplete` in a unit without tests), and the delivery agent passes them to the creator export. With the creator backend and a design made in slxd, the generator makes it (`design_matrix_generate_course` with `leccionesEvaluacion: "separadas"`: a content «Evaluaciones — …» after the units, with the grading of the course) and the agent links it; with a local design it is created with `create_content`. It is recorded in `course.yaml › assessment_unit`. |

| `format` | The questions of the tests |
|---|---|
| `platform` (default) | Evaluation lessons of the packages, in creator or in the html package. |
| `aiken`, `gift`, `moodle-xml`, `qti` | A question bank the LMS imports, recorded by `coursekit delivery questions` in `delivery/`. With the creator backend (`gift`, `moodle-xml`, `qti`) the questions of every test go in a content of their own in creator, the bank content (one more unit after the others, never delivered as a package, recorded in `course.yaml › bank_unit`), and creator exports the bank (`create_export` with `deliveryType: question_bank`; `qti` is an IMS QTI 2.1 zip); `delivery questions --url` saves it. With html, or in `aiken`, `delivery questions` writes it from the `assessment.md`. The questions leave the packages; an activity with a scored simulation keeps the simulation in its package (its unit's, or the package of the tests with `separate`), and an activity with only questions has no lesson. A package left without tests reports the learner's progress, completed or incomplete (`score_source: lessonProgress` and `reporting: completed_incomplete` in its plan), whatever `export` says. |

Each bank format takes some question types: `verify` refuses the others in `assessment.md` while the unit is written, and `delivery questions` refuses them too.

| Directive | `aiken` | `gift` | `moodle-xml` | `qti` (creator) |
|---|---|---|---|---|
| `single-choice` | ✔ | ✔ | ✔ (`multichoice`, one answer) | ✔ |
| `multi-select` | ✘ | ✔ (each right answer 100/n %, each wrong one negative) | ✔ (`multichoice`, several answers) | ✔ |
| `true-false` | ✘ | ✔ | ✔ | ✔ |
| `match` | ✘ | ✔ | ✔ (`matching`) | ✔ |
| `sorting-groups` | ✘ | ✔ (as matching: each item to its group) | ✔ (`matching`) | ✔ |
| `short-answer` | ✘ | ✔ | ✔ | ✔ |
| `fill-in-the-blank` | ✘ | ✔ (one blank per question) | ✔ (`cloze`, several blanks) | ✔ |
| `sorting`, `order-words` | ✘ | ✘ | `sorting` ✔ (core `ordering` type, Moodle 4.4 or later), `order-words` ✘ | `sorting` ✔, `order-words` ✘ |

The table is what coursekit asks for; creator's export may leave out more (images in GIFT, a type a format cannot carry) and lists it in the `warnings` of `get_export_status`, which the delivery agent shows. What each file coursekit writes keeps: the text of the question, its options, the right answers and the feedback (right, wrong and general; Aiken has no feedback), with the HTML of the texts (plain text in Aiken). Each question is named after its activity and position, with its objective (`U1-E1.1-q3 · U1.2`). The id of the common error a distractor represents is never written. Moodle XML says whether the options of each question are shuffled (`shuffleanswers`, from `delivery › shuffle_options › assessment` or the `shuffle:` of the question; a matching always); GIFT and Aiken cannot, and the quiz of Moodle decides. Moodle XML says whether the options of each question are shuffled (`shuffleanswers`, from `delivery › shuffle_options › assessment` or the `shuffle:` of the question; a matching always); GIFT and Aiken cannot, and the quiz of Moodle decides. GIFT and Moodle XML put each activity in its own category (`<CODE>/U1 E1.1 <title>`); Aiken has none, so it is one file per activity. Pass marks, attempts and weights are not part of these formats: they are set on the quiz of the LMS.

### Simulations in creator

Creator has no brick for a simulation and does not share state between bricks, so in its plan:

- A **simulation** is an `EMBED` of its own package: `coursekit media extract` adds the asset `SIM-<ID>` (kind `package`), `coursekit media embed <CODE> SIM-<ID>` builds `media/src/SIM-<ID>/` (`index.html` with the player of the simulations, the skins, the styles and the theme, and the produced images in `media/`, plus creator's manifest `slxd-embed.json`), and the media agent uploads that folder with `request_embed_upload` and records it (`media set … --status uploaded --asset-path <embedFolderPrefix>`). Until then a note stands for it and `plan` warns. The simulation plays inside the embed, and creator keeps its state, counts its grade and records its decisions (below).
- The package speaks creator's `slxd-embed` protocol (version 1) and declares `complete`, `resize`, `state`, `result` and `interaction` in `slxd-embed.json` (creator reads it when the folder is written in the brick and shows what it understood in `properties.embedPackage`; a wrapped SVG declares only `resize`):
  - when it loads it says `ready` and creator answers with the last state it kept, so the learner finds it where it was (in the SCORM export, between sessions; in the previews, for the session);
  - after each step it sends its state (scene, variables, points, attempt, decisions; well under the 1,024 characters creator keeps) and, after each decision, an `interaction` (`<simulationId>-<attempt>-<n>` in `cmi.interactions`, the letter of the option, its text as the description, correct, incorrect or neutral, its points as the weight);
  - at an ending it sends its `result` (points, maximum, grade 0–100, ending and its kind), then its state with `done` and `complete`: creator closes the simulation with that grade and completes the brick;
  - when the test opens a new attempt, creator sends `reset` and the simulation starts again (a new attempt for the interactions); the height of its content goes in `resize`, which the iframe takes without a scroll bar of its own.
- The EMBED carries `simulationId` (the id of the simulation), `scored` and `weight`. A scored simulation in a test counts with the formula of the html backend (`100 × (questions right + Σ weight · grade / 100) / (questions + Σ weights)`, where creator weighs each question with its own weight); a test made only of simulations is graded by itself when the last one ends; in a content without tests, its scored simulations give the score of the content. Scored simulations outside the tests of a content that has them do not count (`verify` warns of them).
- In a decision-based course, the EMBED of the simulation that opens each content section carries `blocker_enabled`: the lesson does not let the learner go on until the simulation reaches an ending, so they decide before reading the explanation. The other simulations (a second one in the section, those of the tests) do not block.
- An **adaptive block** is assembled with its neutral branch (`:::else`), and `plan` warns.

The adaptive block is the next phase of creator's protocol (see [Known limits of the creator backend](#known-limits-of-the-creator-backend)).

### `diff`

For every lesson, `diff` gives an action and its operations; the `data` of each operation is the payload for the creator tool:

| Action | Meaning |
|---|---|
| `create` | The lesson is not in `applied.json`: one `add` operation per brick |
| `update` | Operations `update`, `delete`, `add` (with `position`), `rename_lesson` and `update_quiz` (the grading of a test changed), computed from the brick hashes and the quiz settings |
| `unchanged` | Nothing to do |
| `delete` | The lesson is in `applied.json` but no longer in the plan; the agent asks you before deleting it |

The content itself has `action: rename` when its title differs from the applied one, otherwise `unchanged`.

## Directive registry: `directives check` and `/sync-directives`

Both backends read the registry of directives, which is kept in line with the bricks of creator. The registry (`defaults/directives.yaml`, overridable in `config/directives.yaml`) must list every brick type of creator, either as a directive or under `not_directives`. When creator adds or removes bricks:

```bash
coursekit run sync-directives
```

or `/sync-directives` in your agent. The agent saves the result of the creator tool `list_brick_types` as `.cache/list_brick_types.json` and runs:

```bash
coursekit directives check .cache/list_brick_types.json
```

| Output | Meaning |
|---|---|
| `NEW <BRICK> [category] when to use` | A creator brick that is neither a directive nor in `not_directives` |
| `REMOVED <BRICK> (in directive 'name')` or `(in not_directives)` | The registry names a brick that no longer exists |
| `ok: the directive registry matches creator (N bricks)` | Nothing to do; exit code 0 (1 if there is any line above) |

For each `NEW`, the agent checks the brick schema and either adds a directive (kebab-case name, `brick`, `role`, `use`) or lists it under `not_directives` with a reason. For each `REMOVED`, it removes the entry and lists the content files that used it (it does not change them). It edits `config/directives.yaml`, updates `synced_with_creator` with today's date and repeats `check` until it says `ok`. It does not commit.

## The html backend

With `assembly.backend: html` nothing is loaded into a platform. `coursekit assemble build` turns each unit into a SCORM package of its own: a web page with all its lessons, a player, styles, the produced media and the manifest. It reads the same `content.md`, `assessment.md` and produced media as the creator backend, and it reuses its plan (same directives, same format, same errors). Never edit the package: if something is wrong, fix the `.md` and build again.

### Requirements and builder

- The design is signed and the units are `approved` before you build the package you will deliver (a preview of an unsigned unit is possible; `build` does not check the status of the unit). A course on hold is refused: [`coursekit resume`](03-commands.md#coursekit-resume) first.
- The player is bundled at each build from two npm packages, `@studiolxd/scorm` (the SCORM runtime) and `esbuild`. They are installed once per machine in the coursekit store (see [04-configuration.md](04-configuration.md#the-per-machine-store)), not in the project. `coursekit setup` prepares them when the project uses the html backend, `coursekit assemble build` tries again if they are missing, and `coursekit doctor` reports whether they are there. It needs Node and npm, and network access the first time.
- Produced media with their files (see [Media](#media)), if the unit has placeholders.

### `coursekit assemble build`

```bash
coursekit assemble build PWD                          # every unit: preview folder
coursekit assemble build PWD --unit 1                 # one unit
coursekit assemble build PWD --unit 1 --version 1.0   # also the zip, ready for `delivery add`
```

| Option | Meaning |
|---|---|
| `--unit N` | Build only that unit; without it, every unit of the course |
| `--version X.Y` | Also write the zip `courses/PWD/delivery/<file_name of delivery.yaml>` (by default `{code}-U{unit:02d}-v{version}-{standard}.zip`, for example `PWD-U01-v1.0-scorm12.zip`) |

```text
$ coursekit assemble build PWD --unit 1 --version 1.0
unit 1: 5 files in courses/PWD/assembly/html/unit-01
package PWD-U01-v1.0-scorm12.zip (212.4 KB)
```

Without `--version` the last line is `preview: coursekit preview PWD (with a simulated LMS), or open courses/PWD/assembly/html/unit-01/index.html in the browser` (see [Preview with a simulated LMS](#preview-with-a-simulated-lms)). Warnings are printed first (`WARNING …`): a `labelled-graphic` whose image is not produced yet, and a produced asset whose file does not exist.

Each build starts from scratch: the unit's folder is deleted and written again. The standard (SCORM 1.2 or 2004 4th edition) is `export.standard` of the delivery configuration ([SCORM export settings](09-delivery.md#scorm-export-settings)). The command fails, with exit code 1 and the list of problems, when:

- the plan has errors (an unknown directive, a question without its correct option, a key written in the other language…: the same messages as `verify`);
- the unit uses a directive of the project's registry that the backend cannot render;
- the package does not carry every word of the content (see [The check of the words](#the-check-of-the-words));
- the builder cannot be prepared (Node, npm or the install failed: `coursekit doctor`).

Nothing is written to `assembly/unit-NN.plan.json`: the plan is built in memory and `assemble plan`, `diff`, `applied` and `link` do not apply. When every unit has its package built and the course was in `media`, `build` moves it to `assembly` (the history records `Every unit built`).

### The package

```text
courses/PWD/assembly/html/unit-01/
├── index.html          every lesson of the unit in one page
├── imsmanifest.xml     one SCO; SCORM 1.2 or 2004 4th edition
├── assets/
│   ├── styles.css      layout, tokens, maqueta and components, in that order
│   └── player.js       SCORM runtime and behaviour of the components (bundled)
└── media/              produced media, downloads and subtitles
```

The folder is generated and git-ignored (`courses/*/assembly/html/`). It opens straight from the disk in a browser (open `index.html`): without an LMS the SCORM runtime is an in-memory mock, so the package works the same and nothing is sent anywhere. The zip has the same files, with `imsmanifest.xml` first at its root, which is what `coursekit delivery add` checks.

The page is built with progressive enhancement. The lessons (one per section of `content.md`, then one per activity of `assessment.md`) are sections of one page and the page is complete and readable without JavaScript: every lesson one after another, the panels open, and the text of every answer in the markup. The player then shows one lesson at a time. Content HTML is sanitized with an allow-list of tags and attributes: no scripts, no event handlers, no `javascript:` links (a removed link keeps its text).

### Components

| Directive or Markdown | Brick | In the package |
|---|---|---|
| Paragraphs, `###`–`######`, lists, tables, code fences | `TEXT`, `HEADING`, `LIST`, `TABLE`, `CODE` | Text, headings (level 3 to 6; the lesson title is the level 2), lists, tables in a scrollable box, code blocks. Every block says its language, never creator's automatic detection: the language of the fence or its alias if creator has it (`bash`, `python`, `yaml`, `powershell`, `diff`…); `shell` ("Terminal") for a `text` or unlabelled block that is a terminal session or only commands, and for `console`, `terminal` and `cmd`; `plaintext` for any other text and for a language creator lacks (see `rules › assembly › code_languages` in [Configuration](04-configuration.md)) |
| `note`, `highlight`, plain blockquote, `quote` | `NOTE`, `HIGHLIGHT`, `QUOTE` | A note with a title, a highlighted block, a quote with its attribution |
| `accordion` | `ACCORDION` | Native `details` elements (they work without JavaScript) |
| `tabs` | `TABS` | Tab list with arrow, Home and End keys; every panel is in the markup |
| `carousel`, `carousel-quotes` | `CAROUSEL`, `CAROUSEL_QUOTES` | One slide at a time with previous and next buttons and a "Slide n of N" status |
| `timeline` | `TIMELINE` | Ordered list with the date and title of each milestone |
| `flashcards`, `flashcard-gallery` | `FLASHCARD_CAROUSEL`, `FLASHCARD_GALLERY` | Cards that flip (click, Enter or Space), one at a time or in a grid |
| `labelled-graphic` | `LABELLED_GRAPHIC` | The image with numbered hotspots that open their explanation (Escape or Close to dismiss). Without a produced image: a plain list of the points |
| `dialog` | `DIALOG` | The lines of the conversation with the name of each speaker |
| `scenario`, `conversation` | `SIMULATION` | The simulation played scene by scene: the background with its layers and the areas that can be clicked (focusable buttons with the label as their name), the portraits of the characters, the text with the variants that hold, the choices as buttons, the feedback of a decision before going on, and at the end the ending, the debriefing, the decisions taken, the score (scored ones) and the buttons to go back to the last checkpoint (`decision_based.rewind`) and to start again. With a `skin`, the application ([Skins](06-content.md#skins)) takes the place of the background. A `conversation` shows the exchange as a chat. Without JavaScript: the opening situation and its options. Images not produced yet are left out (initials stand for the portraits) |
| `:::if` / `:::else` | `CONDITIONAL` | Both branches are in the page; the player shows the `:::if` one when every simulation it reads has been played and its condition holds, else the neutral one (also without JavaScript) |
| Image, infographic, diagram, animated GIF placeholder (produced) | `IMAGE` | Figure with alt text and caption |
| Video placeholder (produced) | `VIDEO` | Video with controls, captions track (if there is a `.vtt`) and the transcript in a `details` |
| Audio placeholder (produced) | `AUDIO` | Audio with controls and the transcript |
| Simulation and terminal demo placeholder (produced) | `EMBED` | An `iframe` of the package folder (`media/<id>/index.html`) |
| Download of an asset, job aid | `ATTACHMENT` | A download link |
| `single-choice`, `multi-select`, `true-false` | `SINGLE_CHOICE`, `MULTI_SELECT`, `TRUE_FALSE` | Radio buttons or checkboxes, in a new order on every try when the plan shuffles them (`delivery › shuffle_options`); true-false offers True and False |
| `sorting` | `SORTING` | The items shuffled, with move up and move down buttons |
| `match` | `MATCH` | One drop-down per term on the left, with the terms on the right shuffled |
| `sorting-groups` | `SORTING_GROUPS` | One drop-down per item with the categories; the items shuffled when the plan says so |
| `fill-in-the-blank` | `FILL_IN_THE_BLANK` | A text box in each blank of the sentence (`{a/b}` accepts several answers) |
| `order-words` | `ORDER_WORDS` | Word buttons that are clicked into the sentence in order, one line per sentence |
| `short-answer` | `SHORT_ANSWER` | A text box compared with the accepted answers |

Text answers (`fill-in-the-blank`, `short-answer`) are compared ignoring case, accents and extra spaces. A multiple-selection question is right only when every option is as the key says. Feedback follows the directive: `feedback-correct:` after a right answer, `feedback-incorrect:` after a wrong one, `feedback:` always. Directives are explained in [06-content.md](06-content.md#directives); the games are below, in [Games](#games).

### The player

With JavaScript the page becomes a small course player:

- One lesson is shown at a time. The lesson list (the "Lessons" navigation) marks the current and the visited lessons; **Previous** and **Next** move between them; the progress bar shows the percentage of lessons visited; a **skip to content** link is the first element of the page. When the lesson changes, the page scrolls to the top and focus moves to the lesson title.
- The unit reopens in the lesson where the learner left it.
- **Practice questions** (in content lessons) have a **Check** button. It does nothing until the question is answered; then it locks the answers, marks them and shows the feedback, and the button becomes **Try again**, which clears the answer and shuffles again.
- **The assessment lessons** (`assessment.md`) are graded together with one **Submit answers** button. Unanswered questions block the submit ("Answer every question before submitting."). The score is the percentage of questions fully right, rounded; the learner passes when it reaches `the pass mark of the test (see [Grading of a test](#grading-of-a-test)). The attempts of the test limit them (empty or 0: unlimited). After submitting, each question shows its mark and feedback and the report says the score and whether the learner passed; if not, **Try again** appears while attempts are left (the report says how many) and "No attempts left." when none are. The attempts used and the best score are kept in the suspend data, so reopening the unit does not give new attempts.
- **Simulations** keep their state (the scene, the variables, the points and whether they ended) when the learner moves between lessons and when the unit is reopened, and every decision updates the adaptive blocks of the unit. A **scored** simulation inside an assessment lesson counts in its test: it weighs `weight` questions and adds its grade (the points of its path over the maximum reachable); the test cannot be submitted until those simulations have ended, and **Try again** restarts them too. A test made only of scored simulations has no **Submit answers** button: it is graded by itself when they all reach an ending, and starting them again opens a new attempt while there are attempts left (after that they can be played, without a grade). In a unit without a test, the score is the weighted grade of its scored simulations once all of them have ended; in a unit with a test, the scored simulations of the content are practice.
- **The simulation that opens a section** of a decision-based course holds the rest of the lesson until it reaches an ending: what follows it is hidden, with a line that says so, and **Next** is off. The learner decides before reading the explanation, as in creator, where its EMBED blocks the lesson. A learner who comes back to a simulation already ended finds the lesson open.
- The interface texts (button labels and messages) are in the language of the course.
- The page is responsive (the lesson list is a side column on wide screens), respects reduced motion and forced colours, and prints with every lesson.

### Games

The games are practice: nothing is graded nor sent to the LMS. They work with the keyboard and a screen reader (what happens
is said in a live region under the game), and the order of letters and cards depends only on the id of the game, so every
learner sees the same board. Without JavaScript the page lists what each game is about.

| Directive | In the player |
|---|---|
| `word-search` | A grid with the words placed across, down or diagonally: press the first letter of a word and then the last one; the arrow keys move across the grid; the words found are crossed out |
| `wordle` | One word after another: six tries; each letter says whether it is in place, elsewhere or not in the word (in colour and in words) |
| `hangman` | One word after another: a key per letter (Ñ included); six misses at most |
| `pasapalabra` | The letters of the wheel; for each, its definition ("Starts with" or "Contains"), an answer field and **Pass**; alternatives with `/` count, and accents and case do not |
| `memory` | Each line is a pair of cards; turn them two at a time; it counts pairs and moves |
| `trivial` | The learner chooses a category and answers one of its questions; a category is won with a right answer |

### SCORM tracking

The runtime is `@studiolxd/scorm`, bundled into `assets/player.js`.

| What | How it is reported |
|---|---|
| Location | The key of the current lesson (`U1-S2`, `U1-E1.1`); the unit reopens there |
| Suspend data | The visited lessons, the attempts used, the best score, the number of interactions recorded and, of each simulation, its scene, variables, points, whether it ended, its attempt and how many decisions it has taken (no more, to stay within the 4,096 characters of SCORM 1.2) |
| Progress | Lessons visited divided by lessons of the unit (progress measure, SCORM 2004) |
| Completion | Without a test: completed when every lesson has been visited, incomplete until then. With a test, in SCORM 2004: completed when every lesson has been visited, and passed or failed when the test is submitted. With a test, in SCORM 1.2, which has a single status: passed or failed when the test is submitted |
| Score | Raw (percentage), minimum 0 and maximum 100; also scaled in SCORM 2004 |
| Interactions | One per question of the test: its id, the type (choice for single and multiple choice, fill-in for the rest), the response (in a choice, the letters of the options chosen: `a,c` in SCORM 1.2, `a[,]c` in 2004; in the rest, the learner's answer cut at 250 characters), correct or wrong (`wrong` in 1.2, `incorrect` in 2004), weight 1. And one per decision in a simulation: `<simulation>-<attempt>-<n>` (each start from the beginning is a new attempt, so ids are never repeated), choice, the letter of the decision among those of its scene (`a`, `b`…), its text as the description (SCORM 2004 only: 1.2 has no description), correct when it earned points, wrong when it lost them and neutral otherwise, weighted by its points. Every value is one the standard admits: a strict LMS refuses the rest and they are lost |
| Session | Session time and exit `suspend`; the data is committed after every change and the session is terminated when the page is hidden or closed |

### Preview with a simulated LMS

The folder of a unit opens from the disk, but then the package has no LMS: its tracking stays in memory and is lost on
closing. [`coursekit preview`](03-commands.md#coursekit-preview) plays it as a platform would:

```bash
coursekit preview PWD            # opens http://127.0.0.1:8765/ in the browser
```

- A local server shows a page that holds the SCORM 1.2 and 2004 APIs, with the unit inside: the package finds its LMS
  and sends what it would send on a platform. Nothing leaves the machine. The simulated LMS is as strict as a platform:
  a value the standard does not admit (a result, a response, a score out of range, a saved state too long) is refused
  with its error code and listed in red in the panel, under **Values an LMS would refuse**.
- What the unit sends is kept in the browser, per course and unit: **Exit and reopen** closes the session (exit and
  finish) and opens it again, so you see whether it resumes where it was (`entry: resume`, the location, the state of
  each simulation). **Clear the tracking** starts the unit from scratch.
- A side panel shows the tracking live: completion, success, score, location, entry and exit; the saved state
  (`suspend_data`) with its size against the limit of the standard (4,096 characters in SCORM 1.2); every interaction
  (id, response, result and weight: one per question of a test and one per decision of a simulation); and the calls to
  the API.
- When a unit is built again (`coursekit assemble build` in another terminal), it reopens by itself.
- A selector changes unit. A unit that is not built shows the command that builds it.

It is a check of the package, not a replacement for a test on the real platform (SCORM Cloud or the client's LMS)
before delivering.

### Checking the package

Before delivering, [`coursekit assemble check`](03-commands.md#coursekit-assemble) plays each unit as a learner would,
and `coursekit assemble build --version` does it by itself before writing the zip (`--no-check` skips it):

```bash
coursekit assemble check PWD            # every unit
coursekit assemble check PWD --unit 2
```

| What it checks | An error when |
|---|---|
| Files | The page or its styles point to a file that is not in the package |
| Console and loading | The player writes an error in the console, or a file does not load |
| Accessibility | axe finds a `critical` or `serious` violation in a lesson (`moderate` and `minor` are warnings); a contrast problem shows its ratio and colours |
| Tests | Answered right, after the best path of its scored simulations, a test does not send the score it should |
| Unit score | In a unit without a test, its scored simulations (by their best path) do not give the score they should |
| Simulations | A path of [`coursekit paths`](03-commands.md#coursekit-paths) cannot be played, or ends at another scene or with other points |
| Adaptive blocks | After a path, a `:::if` block shows a branch other than the one its condition asks for |
| SCORM | The LMS would refuse a value; the saved state does not fit in the standard (a warning from 80 % of it) |
| Resuming | On exiting and coming back, the unit is not where it was |

It needs Node and a browser: the installed Google Chrome or, else, Microsoft Edge (`--browser PATH` for another one),
driven without a window by Playwright. The first run prepares the checker in the store (`npm install` of
`playwright-core` and `axe-core`; no browser is downloaded). Without a browser only the files are checked, with a
warning. A unit with many paths takes some seconds: every path of every simulation is played.

### Styles

`assets/styles.css` is built in layers, each one over the previous:

1. **The base layout** of the package: neutral, accessible, driven by CSS variables (`--color-background`, `--color-text`, `--color-accent`, `--color-surface`, `--color-border`, `--color-correct`, `--color-wrong`, `--font-family`, `--font-size-base`, `--radius`, `--space-*`…). Its classes start with `ck-`.
2. **The tokens** of the course: `courses/PWD/theme/tokens.css` if the course has its own theme, else `theme/tokens.css` of the project. If there are no tokens, this layer is empty and the base layout shows as it is.
3. **`theme/maqueta.css`** of the project, then **`courses/PWD/theme/maqueta.css`**: the stylesheet that restyles anything (the "maqueta").
4. **Every `components/*.css`** of the project, in file-name order.

`coursekit theme import theme/maqueta.css` derives the design tokens from the CSS variables of the stylesheet over the base layout and records where they come from, so the graphics, simulations and videos of the media are made with the same colours and fonts (see [Theme and design tokens](02-workflow.md#theme-and-design-tokens)).

The `*.js` files of the project's `components/` folder are bundled into the player, before it starts, in file-name order. They are plain ES modules that can use the DOM, for behaviour the package does not have. A project without a `components/` folder just has the layers above.

### Media

There is no upload to a platform: the media are files that travel inside the package. An asset with status `produced` or `uploaded` and `--file` pointing at a local file is copied to `media/` and used by the matching component; for a simulation or a demo, `--file` is the folder of the package or its `index.html`, and the whole folder is copied. The path is read relative to the course folder or to its `media/` folder (or absolute). See [07-media.md](07-media.md).

- `--subtitles-path` points at a local `.vtt` of a video; it is copied to `media/` and added as the captions track. A value that is not an existing local file (for example, a path from another platform) is ignored.
- The transcript, if registered with `--transcript`, goes in a collapsible block under the video or the audio.
- Downloads registered for the asset (`--download`) are copied to `media/files/` and linked.
- An asset that is not produced stays as a visible note with its description and specifications, so the package never has a hole. A produced asset whose file does not exist is a warning and also stays as that note.

### The check of the words

The build compares the words of `content.md` and `assessment.md` that the learner reads with the words of the page. From `assessment.md` only the text under **Instructions for the learner** and **Question bank** counts, because only that reaches the package (the other subsections document the activity for the team). It leaves out what is not text for the learner: the syntax of the format (`:::` lines, the `question:` and `answer:` keys, list markers), metadata (objective tags, the objective key, comments, `image:` and `position:`), the media placeholders (their box is replaced by the asset or by its note) and the targets of links. If a word is missing, the build fails with `the package does not contain N word(s) of the content: …` and the first twenty words.

The typical cause is a line that the format does not render, for example a question without its `question:` key (written as a plain line inside the directive). Fix it in the `.md` and build again. The comparison is by sets of words, so it does not depend on how a component lays the text out.

### Limits

- **It has not been tested in a real LMS.** Try the package in the target LMS (or in SCORM Cloud) before you deliver it: check that the location is resumed, the score and the status are recorded, and the test behaves as you expect.
- The package is one SCO per unit. A course of several units gives several packages.
- `export.reporting` and `export.scoreSource` do not apply: the status and the score are those of [SCORM tracking](#scorm-tracking).

## Known limits of the creator backend

These are gaps of the authoring platform, not of coursekit. The pipeline works around them or warns instead of failing, and each one disappears when creator closes it. The list is kept up to date with each version of coursekit; the preview of the assembled course is where to check whether one still applies.

- **Theme.** Creator does not publish through MCP which fields of the theme each block accepts, their type, their default or what they paint, and `update_theme` does not say which fields it discarded or why. After importing a theme, look at the result in creator.
- **Embeds in the shared view.** An EMBED (a simulation, a terminal demo) can show blank in the shared view of a content, because the platform refuses to frame it (`X-Frame-Options: DENY`). In the learner's view and in the exported package it works.
- **Fields of one line.** The options of a question (`single-choice`, `multi-select`, `sorting`, `order-words`, the two sides of a `match`, the items and groups of a `sorting-groups`), the lines of a `dialog` and the titles of panels, slides, hotspots and timeline events take one paragraph with bold, italic, subscript and superscript only. The plan sends them without inline code, links or line breaks (their text stays) and the question without links, so creator accepts them; `assemble plan` and `verify` warn of each field changed.
- **Code block.** Long lines are cut (coursekit never leaves a block to its automatic detection: it always sends a language of its list, see `assembly.code_languages` in [Configuration](04-configuration.md)). Inline code, code blocks inside tabs or accordions, and long alternative texts are not handled well either.
- **Flashcards.** Some theme fields leave the front face blank, and the "Flip" label shows under the card.
- **Theme fonts.** A font of the theme may not load in the player (CORS).
- **Adaptive blocks (`:::if`).** Creator has the `CONDITIONAL` brick, but coursekit still assembles the neutral branch (`:::else`) and `plan` warns, until the learner's player shows the branches. Simulations do report their state, score and every decision to the SCORM of the content (the `slxd-embed` protocol, see [Simulations in creator](#simulations-in-creator)).

Next: [Delivery and publishing](09-delivery.md)
