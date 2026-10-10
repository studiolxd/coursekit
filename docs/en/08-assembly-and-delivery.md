# Assembly and delivery

How an approved course is assembled (loaded into the assembly platform, or built as a web package), exported as SCORM packages, recorded, published to the shared folder and tracked in the catalog.

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
| `html` | Builds each unit as a web page with its own player (`coursekit assemble build`) and packages it as SCORM 1.2 or 2004 by itself. Same directives and same format as `creator`; the games are not available yet (see [Limits](#limits)) | A folder `courses/PWD/assembly/html/unit-01/` that opens in a browser, and a zip in `delivery/` |

Each backend refuses the commands of the other for a course: `plan`, `diff`, `applied` and `link` fail for an html course (they point to `build`), and `build` fails for a creator course. `coursekit verify` converts the content in both cases: with `html` it also reports the directives that are not available yet.

The instructional design is done in creator with either backend (the design agent saves the matrix from the slxd MCP server), so the project always needs the MCP server: `project.yaml › platform.slxd.mcp_url` and `mcp_name` (default `slxd-creator`). The `coursekit init` wizard asks for the URL in both cases. `coursekit agents` writes the server into `.mcp.json`, `opencode.json` and `.codex/config.toml` (see [05-agents.md](05-agents.md)).

The sections [The assembly flow](#the-assembly-flow) to [Directive registry](#directive-registry-directives-check-and-sync-directives) describe the **creator backend**. The html backend has its own section, [The html backend](#the-html-backend). [Client review](#client-review) and [Delivery](#delivery) apply to both, with the differences noted there.

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
| `course.yaml › units[].links.review` | `assemble link --review` | Review link of the unit, where the client comments (see [Client review](#client-review)) |
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
| Media placeholder uploaded | By type id: `image`, `infographic`, `diagram` and `animated_gif` become `IMAGE`; `video` becomes `VIDEO` (with captions and transcript if registered); `audio` becomes `AUDIO`; `simulation` and `terminal_demo` become `EMBED`. Plus an `ATTACHMENT` per uploaded download |
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

Without `--version` the last line is `preview: open courses/PWD/assembly/html/unit-01/index.html in the browser`. Warnings are printed first (`WARNING …`): a `labelled-graphic` whose image is not produced yet, and a produced asset whose file does not exist.

Each build starts from scratch: the unit's folder is deleted and written again. The standard (SCORM 1.2 or 2004 4th edition) is `export.standard` of the delivery configuration ([SCORM export settings](#scorm-export-settings)). The command fails, with exit code 1 and the list of problems, when:

- the plan has errors (an unknown directive, a question without its correct option, a key written in the other language…: the same messages as `verify`);
- the unit uses a directive that is not available yet (the games);
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
| Paragraphs, `###`–`######`, lists, tables, code fences | `TEXT`, `HEADING`, `LIST`, `TABLE`, `CODE` | Text, headings (level 3 to 6; the lesson title is the level 2), lists, tables in a scrollable box, code blocks. The language of the fence is used if creator knows it (`bash`, `python`, `yaml`…; `powershell`, `pwsh`, `cmd` and `terminal` become `bash`); a `text` or unlabelled block made only of commands becomes `bash`, and any other uses creator's automatic detection, because creator has no plain-text language (when it adds `plaintext`, `shell`, `powershell`, `diff`, `dockerfile` and `http`, list them in `rules › assembly › code_languages`: [Configuration](04-configuration.md)) |
| `note`, `highlight`, plain blockquote, `quote` | `NOTE`, `HIGHLIGHT`, `QUOTE` | A note with a title, a highlighted block, a quote with its attribution |
| `accordion` | `ACCORDION` | Native `details` elements (they work without JavaScript) |
| `tabs` | `TABS` | Tab list with arrow, Home and End keys; every panel is in the markup |
| `carousel`, `carousel-quotes` | `CAROUSEL`, `CAROUSEL_QUOTES` | One slide at a time with previous and next buttons and a "Slide n of N" status |
| `timeline` | `TIMELINE` | Ordered list with the date and title of each milestone |
| `flashcards`, `flashcard-gallery` | `FLASHCARD_CAROUSEL`, `FLASHCARD_GALLERY` | Cards that flip (click, Enter or Space), one at a time or in a grid |
| `labelled-graphic` | `LABELLED_GRAPHIC` | The image with numbered hotspots that open their explanation (Escape or Close to dismiss). Without a produced image: a plain list of the points |
| `dialog` | `DIALOG` | The lines of the conversation with the name of each speaker |
| Image, infographic, diagram, animated GIF placeholder (produced) | `IMAGE` | Figure with alt text and caption |
| Video placeholder (produced) | `VIDEO` | Video with controls, captions track (if there is a `.vtt`) and the transcript in a `details` |
| Audio placeholder (produced) | `AUDIO` | Audio with controls and the transcript |
| Simulation and terminal demo placeholder (produced) | `EMBED` | An `iframe` of the package folder (`media/<id>/index.html`) |
| Download of an asset | `ATTACHMENT` | A download link |
| `single-choice`, `multi-select`, `true-false` | `SINGLE_CHOICE`, `MULTI_SELECT`, `TRUE_FALSE` | Radio buttons or checkboxes; true-false offers True and False |
| `sorting` | `SORTING` | The items shuffled, with move up and move down buttons |
| `match` | `MATCH` | One drop-down per term on the left, with the terms on the right shuffled |
| `sorting-groups` | `SORTING_GROUPS` | One drop-down per item with the categories |
| `fill-in-the-blank` | `FILL_IN_THE_BLANK` | A text box in each blank of the sentence (`{a/b}` accepts several answers) |
| `order-words` | `ORDER_WORDS` | Word buttons that are clicked into the sentence in order, one line per sentence |
| `short-answer` | `SHORT_ANSWER` | A text box compared with the accepted answers |

Text answers (`fill-in-the-blank`, `short-answer`) are compared ignoring case, accents and extra spaces. A multiple-selection question is right only when every option is as the key says. Feedback follows the directive: `feedback-correct:` after a right answer, `feedback-incorrect:` after a wrong one, `feedback:` always. Directives are explained in [06-content.md](06-content.md#directives); the games are not in this table because they are not available yet.

### The player

With JavaScript the page becomes a small course player:

- One lesson is shown at a time. The lesson list (the "Lessons" navigation) marks the current and the visited lessons; **Previous** and **Next** move between them; the progress bar shows the percentage of lessons visited; a **skip to content** link is the first element of the page. When the lesson changes, the page scrolls to the top and focus moves to the lesson title.
- The unit reopens in the lesson where the learner left it.
- **Practice questions** (in content lessons) have a **Check** button. It does nothing until the question is answered; then it locks the answers, marks them and shows the feedback, and the button becomes **Try again**, which clears the answer and shuffles again.
- **The assessment lessons** (`assessment.md`) are graded together with one **Submit answers** button. Unanswered questions block the submit ("Answer every question before submitting."). The score is the percentage of questions fully right, rounded; the learner passes when it reaches `the pass mark of the test (see [Grading of a test](#grading-of-a-test)). The attempts of the test limit them (empty or 0: unlimited). After submitting, each question shows its mark and feedback and the report says the score and whether the learner passed; if not, **Try again** appears while attempts are left (the report says how many) and "No attempts left." when none are. The attempts used and the best score are kept in the suspend data, so reopening the unit does not give new attempts.
- The interface texts (button labels and messages) are in the language of the course.
- The page is responsive (the lesson list is a side column on wide screens), respects reduced motion and forced colours, and prints with every lesson.

### SCORM tracking

The runtime is `@studiolxd/scorm`, bundled into `assets/player.js`.

| What | How it is reported |
|---|---|
| Location | The key of the current lesson (`U1-S2`, `U1-E1.1`); the unit reopens there |
| Suspend data | The visited lessons, the attempts used and the best score |
| Progress | Lessons visited divided by lessons of the unit (progress measure, SCORM 2004) |
| Completion | Without a test: completed when every lesson has been visited, incomplete until then. With a test, in SCORM 2004: completed when every lesson has been visited, and passed or failed when the test is submitted. With a test, in SCORM 1.2, which has a single status: passed or failed when the test is submitted |
| Score | Raw (percentage), minimum 0 and maximum 100; also scaled in SCORM 2004 |
| Interactions | One per question of the test: its id, the type (choice for single and multiple choice, fill-in for the rest), the learner's response (cut at 250 characters), correct or incorrect, weight 1 |
| Session | Session time and exit `suspend`; the data is committed after every change and the session is terminated when the page is hidden or closed |

### Styles

`assets/styles.css` is built in layers, each one over the previous:

1. **The base layout** of the package: neutral, accessible, driven by CSS variables (`--color-background`, `--color-text`, `--color-accent`, `--color-surface`, `--color-line`, `--color-correct`, `--color-wrong`, `--font-family`, `--font-size-base`, `--radius`, `--space-*`…). Its classes start with `ck-`.
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

- **The games are not available yet**: `word-search`, `wordle`, `hangman`, `pasapalabra`, `memory` and `trivial`. `coursekit assemble build` refuses a unit that uses them (`MEMORY: this component is not available in the html backend yet…`) and `coursekit verify` reports them as `assembly: …`. Use another directive, or the creator backend.
- **It has not been tested in a real LMS.** Try the package in the target LMS (or in SCORM Cloud) before you deliver it: check that the location is resumed, the score and the status are recorded, and the test behaves as you expect.
- The package is one SCO per unit. A course of several units gives several packages.
- `export.reporting` and `export.scoreSource` do not apply: the status and the score are those of [SCORM tracking](#scorm-tracking).

## Client review

Optional: the client reviews the assembled course and comments before it is delivered. Whether it is mandatory is a setting, `client_review.required` in the delivery configuration (default `false`; per project in `config/delivery.yaml`, per course in `course.yaml › delivery › client_review`: see [04-configuration.md](04-configuration.md#delivery-scorm-export-and-client-review)). The process and its statuses are in [02-workflow.md](02-workflow.md#client-review-optional).

With the html backend there are no platform links to create or record: the person hosts the package (the zip in a test LMS, or the preview folder on a web server) and gives the link when the round is opened: `coursekit client PWD send --where URL`. The rounds, `changes`, `approve` and `skip` work as described below; to apply the client's comments, edit the `.md`, run `coursekit verify` and build again (`coursekit assemble build`), then host the new package.

### The links of each unit

This subsection is about the creator backend. At the end of `/assemble` the assembly agent creates, for each unit (each is its own creator content), two links and records them with `coursekit assemble link`:

| Link | Creator tool | For whom |
|---|---|---|
| Live preview (`links.preview`) | `share_content` (enabled, with live updates) | The team. It shows the content as it is, with no comments |
| Review (`links.review`) | `enable_review` (no password unless you ask for one) | The client. It publishes version `v1` of the review and lets the client comment without an account. `get_review` reads it again |

```bash
coursekit assemble link PWD --unit 1 --preview https://acme.example.com/p/abc --review https://acme.example.com/r/xyz
# unit 1 -> preview https://acme.example.com/p/abc; review link https://acme.example.com/r/xyz
```

### Rounds

A round is the cycle "send to the client, the client answers". Only a person runs `coursekit client`; agents are denied it.

```bash
coursekit client PWD send --to "ACME training team"     # round 1: the course goes to client_review
```

`send` needs the course in `assembly`, no round open and the review links of the units recorded (or one link given with `--where URL`, which replaces them). It records in `course.yaml › client_review` the round number, who sent it and when, `--to`, and the links. Send those links to the client yourself.

While the client comments, the assembly agent handles the comments with `/client-feedback PWD` (or `/client-feedback PWD 2` for one unit). It uses the `client-review` skill and these creator tools:

| Step | Creator tool |
|---|---|
| Read the state and the pending threads | `get_review`, `list_review_comments` (status `pending`; `since` to read only what is new). Each thread says the lesson, the text and, if any, a screenshot |
| Apply what was agreed | edits the `.md` (never creator), `coursekit verify`, then `assemble plan`, `diff` and apply as in [the assembly flow](#the-assembly-flow) |
| Publish what changed | `publish_review_version` with a label (`v1.1`, `v1.2`...). Only the latest version accepts comments |
| Answer | `reply_review_comment` on each thread, then `set_review_comment_status` with `resolved`. `verified` is the client's to set |

Before changing anything the agent shows a table with each comment, the section it refers to and what it proposes (apply, do not apply and why, or needs you), and waits for your decision; without an interface it applies only clear text corrections that fit the design. A comment that changes objectives, hours, activities or structure is a design change (`/design-change`), not a content edit. A unit edited after its signature goes back to `verified` and needs a new AI review and signature.

Then you close the round:

| Command | When |
|---|---|
| `coursekit client PWD changes --note "..."` | The client wants changes. The round closes (outcome `changes`) and the course goes back to `assembly`. Apply, reassemble and run `send` again: that is round 2 |
| `coursekit client PWD approve --by "Name" --note "..."` | The client agrees. The round closes (outcome `approved`) with the client's name and date, and the course can be delivered |
| `coursekit client PWD skip --reason "..."` | You deliver without the client's approval. It records a round with outcome `skipped` and the reason; it needs the course in `assembly` or `client_review` with no open round |

When you close a round, the agent can export the comments of the round with `export_review_comments`: it returns a CSV through a signed link that is valid for 24 hours, and the file is saved as `.cache/client-review/PWD-round-N.csv`, which git ignores and `coursekit publish` never copies. The CSV contains the e-mail addresses of the guests who commented: do not paste it anywhere nor move it into the course.

`coursekit status PWD` shows the last round and its outcome (`open`, `asked for changes`, `approved` or `skipped`), and the next step for `client_review` is to record the client's answer.

## Delivery

Each unit is one SCORM package: with the creator backend, one creator content exported from the platform; with the html backend, the zip that `coursekit assemble build --version` writes.

### Before exporting: `delivery check`

```bash
coursekit delivery check PWD
# PWD: it can be delivered
```

`/deliver` starts with this command, and `delivery name` and `delivery add` apply the same rules. It refuses (exit code 1, with a message) when:

| Case | The message says | What to do |
|---|---|---|
| The course is on hold | "PWD has been on hold since ..." | `coursekit resume PWD` |
| `client_review.required` is `true` and no round exists | "PWD needs the client's review before it is delivered ..." | Open a round (`send`), or skip it with a reason (`skip`) |
| The last round asked for changes | "the client asked for changes in PWD ..." | Apply the changes, reassemble and open the next round (`send`) |
| The last round is still open | "PWD is waiting for the client's answer (round N, sent to ...)" | Record the answer: `approve` or `changes` |

The exact texts are in [Troubleshooting](09-troubleshooting.md#the-course-is-on-hold-or-the-clients-review-blocks-the-delivery).

When it is only a matter of status, it prints a warning instead of refusing: `warning: PWD is in '<status>', not in a delivery status (assembly, client_review): the package is recorded, but the course is not marked as delivered`. Without the requirement (`required: false`) the rounds do not matter: a course in `assembly` can always be delivered.

### SCORM export settings

From `src/coursekit/defaults/delivery.yaml`; override them in `config/delivery.yaml`, `project.yaml › delivery` or `course.yaml › delivery` ([04-configuration.md](04-configuration.md)).

| Key | Default | Values |
|---|---|---|
| `export.deliveryType` | `lms` | |
| `export.standard` | `scorm_1_2` | `scorm_1_2`, `scorm_2004` |
| `export.reporting` | `passed_incomplete` | `passed_incomplete`, `completed_incomplete` |
| `export.scoreSource` | `quiz` | `quiz`, `lessonProgress` |
| `file_name` | `{code}-U{unit:02d}-v{version}-{standard}.zip` | File name pattern |

With the creator backend, the agent calls the creator export tool with the `export` values, waits for the job to finish and downloads the package. With the html backend only `export.standard` and `file_name` are used: the standard decides the manifest and the tracking of the package, and `reporting` and `scoreSource` do not apply (see [SCORM tracking](#scorm-tracking)).

### File naming and recording

```bash
coursekit delivery name PWD --unit 1 --version 1.0
# PWD-U01-v1.0-scorm12.zip
```

`{standard}` loses its underscores (`scorm_1_2` becomes `scorm12`, `scorm_2004` becomes `scorm2004`). The package is downloaded to `courses/PWD/delivery/` with that name and recorded:

```bash
coursekit delivery add PWD --unit 1 --version 1.0 \
  --file courses/PWD/delivery/PWD-U01-v1.0-scorm12.zip --job <export-job-id> --snapshot <snapshot-id>
# recorded PWD-U01-v1.0-scorm12.zip · course delivered
```

With the html backend the zip is written by `build` straight into `courses/PWD/delivery/` with that name, so there is nothing to download and no export job or snapshot:

```bash
coursekit assemble build PWD --unit 1 --version 1.0
coursekit delivery add PWD --unit 1 --version 1.0 --file courses/PWD/delivery/PWD-U01-v1.0-scorm12.zip
# recorded PWD-U01-v1.0-scorm12.zip · course delivered
```

`delivery add` checks that the file is a valid zip with `imsmanifest.xml` at its root, that it is directly inside `courses/PWD/delivery/` and that the unit exists. It then appends an entry to `course.yaml › deliveries` with `version`, `unit`, `date`, `by` (the signing identity of `.env`), `standard`, `file`, `sha256`, `export_job` and `snapshot` (empty for an html package). When every unit has a package of the same version **and the course is in `assembly` or `client_review`**, the course status becomes `delivered` and a history entry is added. In any other status the package is recorded with the warning above and the course status does not change. While some unit has no package of the version, it prints `recorded <file> · pending units for v<version>: [2, 3]`. `courses/*/delivery/` is in the project `.gitignore`: the zips are not versioned, `course.yaml` is.

## Publishing to the mirror folder

The mirror folder is a read-only copy of the courses in a folder synced by your provider's desktop client (or any folder). Anything edited there is overwritten on the next publication.

| Setting | Where | Meaning |
|---|---|---|
| `mirror.provider` | `project.yaml` | `sharepoint`, `onedrive`, `google-drive`, `nextcloud`, `folder` or `none` |
| `MIRROR_DIR` | `.env` (personal) | Local path of the synced folder. `coursekit init --mirror-dir PATH` writes it |
| `mirror.url` | `project.yaml` (shared) | Web address of the mirror folder, used for the course links of the catalog. `coursekit init --mirror-url URL` writes it |

`mirror.url` by provider, and the link written in the catalog for course `PWD`:

| Provider | What to paste in `mirror.url` | Link for `PWD` |
|---|---|---|
| `sharepoint`, `onedrive` | The folder address from the address bar of the library (`…/Forms/AllItems.aspx?id=<folder path>`), a "copy link" address (`…/:f:/r/<path>`) or a plain path (`/sites/<site>/<library>/<folder>`) | From the library address: the same address with `/courses/PWD` added to the `id` path. From a copy link: `https://<host>/<folder path>/courses/PWD` (the `/:f:/r` prefix and the query are dropped). From a plain path: the path with `/courses/PWD` added. A sharing link (`/:f:/s/<token>`) has no path, so no links are written (the check warns) |
| `nextcloud` | The address of the Files app with `?dir=/Folder` | The same address with `dir=/Folder/courses/PWD` |
| `google-drive` | The folder address | The same address for every course (folder ids are not in the path) |
| `folder` | Any base address; `{code}` is replaced by the course code | The address with `{code}` replaced; without `{code}`, the same address |

```bash
coursekit publish --check    # reports the configuration; writes nothing
coursekit publish            # every course
coursekit publish PWD        # one course
```

`--check` prints one of `info: no mirror folder (project.yaml › mirror.provider: none)`, `warning: MIRROR_DIR is not set in .env; nothing will be published`, `warning: MIRROR_DIR does not exist: …` or `ok: <provider> mirror in <path>`, followed by a line about the links (`ok: course folder links like …`, `info: no mirror.url…` or the sharing-link warning). `--only-if-configured` makes `publish` do nothing, silently, when there is no mirror; the `post-merge` git hook uses it to publish after every pull.

### Automatic publication

You rarely run `coursekit publish` yourself. When the project has a mirror folder, these commands publish the course they changed as soon as they finish: `coursekit new`, `sync` (without `--check`), `verify` (without `--no-update`), `reviewed`, `approve`, `assemble applied`, `assemble link`, `assemble build`, `media set`, `delivery add`, `hold`, `resume`, `client` and `handoff` (after each step). That is why the preview and review links, the status and the packages reach the mirror and the catalog without anyone asking.

- The catalog of the project (`courses/course-catalog.xlsx`) is always refreshed, silently.
- Without a mirror (`mirror.provider: none`, or no `MIRROR_DIR`) nothing else happens and nothing is printed.
- If the mirror cannot be updated (the folder does not exist, the Excel is open), the command prints a warning on the error output and keeps its own exit code: its work is done and `coursekit publish` tries again.
- The only publication an agent runs is the one after exporting the instructional design: downloading the Excel is not a `coursekit` command that could do it.

What `publish` does:

- For each course it copies `course.yaml`, `design/`, `content/` and `reviews/` into `<MIRROR_DIR>/courses/PWD/`, only the files whose content changed. `brief/`, `media/` and `assembly/` are not mirrored.
- Files it published before that no longer exist in the course are removed from the mirror (tracked in `courses/PWD/.published.json`, inside the mirror), together with the folders left empty. Files it never published are not touched.
- `delivery/` is append-only: a package is copied once and never overwritten or deleted in the mirror, even if it is removed locally. A new version has a new file name.
- It writes the catalog to `<MIRROR_DIR>/<catalog file>`, with links to the course folders. If the Excel is open, it fails with `cannot replace … (is it open in Excel?)`.
- It first refreshes the catalog in `courses/` and prints `wrote <path> (N courses, M units)` (not with `--only-if-configured`). Then it prints one line per course that changed (`published PWD: 5 copied, 0 removed, 0 unchanged`) and one for the catalog of the mirror. With `mirror.provider: none` it prints the first line and says there is nothing to publish (exit code 0). With a provider and no `MIRROR_DIR`, it fails with `no mirror folder configured (project.yaml › mirror and MIRROR_DIR in .env)`.

## The tracking catalog

`coursekit catalog` builds the tracking Excel from every `courses/*/course.yaml`. It is generated: never edit it (changes go in each `course.yaml`). It is written next to the courses, in `courses/` (`--output PATH` to change it; git ignores it), and, by `publish`, to the mirror folder. The copy in `courses/` is refreshed by the same commands that publish, with or without a mirror, and has no folder links. The file name and every label follow the project's `ui_language`: `course-catalog.xlsx` in English, `catalogo-cursos.xlsx` in Spanish. The header colour is the `accent-strong` (else `accent`) token of `theme/tokens.json`, or dark grey; the `Courses` and `Units` sheets have a frozen header and filters. `coursekit catalog` alone leaves the **Folder** column empty: the links are written by `publish`.

Sheets, in the language of the catalog (English / Spanish): `Courses` / `Cursos`, `Units` / `Unidades` and `About` / `Información`.

**Courses sheet** (one row per course)

| Column (English) | Columna (español) | Value |
|---|---|---|
| Code | Código | `code` |
| Title | Título | `title` |
| Status | Estado | Course status, translated |
| Hours | Horas | `design.hours` |
| Units | Unidades | Number of units |
| Minimum words | Palabras mínimas | Sum of the minimum words of the sections |
| Current words | Palabras actuales | Learner-facing words written in each `content.md` (the same count as `verify`) |
| % words | % palabras | Current divided by minimum, as a percentage (it can exceed 100 %) |
| Media assets | Recursos multimedia | The larger of the placeholders in the content and the assets in the manifest |
| Assets produced | Recursos producidos | Manifest assets that are `produced` or `uploaded` |
| Folder | Carpeta | Link to the course folder in the mirror (hyperlink; written only by `publish`, and only with a usable `mirror.url`) |
| Design approved by | DI aprobado por | Who signed the design |
| Design approved on | DI aprobado el | Date and time of that signature |
| Design lead · Writing lead · Review lead · Media lead · Assembly lead | Resp. DI · Resp. redacción · Resp. revisión · Resp. multimedia · Resp. montaje | `owners` (`instructional_design`, `writing`, `review`, `media`, `assembly`) |
| Last update | Última actualización | Date of the last `history` entry |
| Last note | Última nota | Note of that entry |

**Units sheet** (one row per unit)

| Column (English) | Columna (español) | Value |
|---|---|---|
| Code | Código | Course code |
| Unit | Unidad | Unit number |
| Title | Título | Unit title |
| Status | Estado | Unit status as is: `pending`, `writing`, `verified`, `reviewed` or `approved` |
| Hours | Horas | Unit hours |
| Minimum words · Current words | Palabras mínimas · Palabras actuales | As above, for the unit |
| Media assets | Recursos multimedia | Placeholders in the unit's `content.md` |
| Editorial approval | Aprobación editorial | Who signed the unit |
| Approved on | Aprobada el | Date and time of that signature |
| Content ID | ID de contenido | `units[].content_id` |
| Preview | Preview | `units[].links.preview` (hyperlink): live preview of the unit |
| Review | Review | `units[].links.review` (hyperlink): client review link of the unit |

**About sheet**: when it was generated, the source (`courses/*/course.yaml`), branch and commit, the git user who generated it and a notice that the file is generated and must not be edited.

## Delivery checklist

Before exporting:

- [ ] Design signed and unchanged, and every unit `approved` (`coursekit status PWD`).
- [ ] Every media asset `uploaded` and validated in the preview (no asset of `media/manifest.yaml` is `pending`, `scripted` or `produced`, and `coursekit media plan PWD` shows no warnings: `plan` lists only `pending` and `scripted` assets). With the html backend: every asset `produced` with its file, which `build` copies into the package.
- [ ] Every unit assembled. Creator: `content_id` set and `coursekit assemble diff` reports `unchanged` for the content and every lesson. Html: `coursekit assemble build PWD` finishes without errors and you have read its warnings. The course status is `assembly` (or `client_review`, if you opened a round).
- [ ] Creator: preview and review links of every unit recorded (`units[].links`). Html: the preview opened in a browser (`courses/PWD/assembly/html/unit-01/index.html`) and the lessons, one component of each kind and the test checked.
- [ ] Course not on hold, and `coursekit delivery check PWD` passes.
- [ ] Client review, if the project requires it (`client_review.required`) or you want it: the last round `approved` (`coursekit client PWD approve --by "..."`) or skipped with a reason (`coursekit client PWD skip --reason "..."`).
- [ ] Version decided: `1.0` the first time, then `1.1`, `1.2`… according to `course.yaml › deliveries`.
- [ ] Export settings checked (`coursekit config delivery`).

For each unit, with the creator backend:

- [ ] Snapshot of the content named `v<version>`.
- [ ] Export with the `export` settings and wait for `COMPLETE` (on `FAILED`, stop and read the error).
- [ ] File name from `coursekit delivery name`, downloaded to `courses/PWD/delivery/`.
- [ ] `coursekit delivery add` (it checks the zip and records it).

For each unit, with the html backend:

- [ ] `coursekit assemble build PWD --unit N --version <version>` (the zip is written to `courses/PWD/delivery/` with the name from `coursekit delivery name`).
- [ ] `coursekit delivery add` without `--job` or `--snapshot` (it checks the zip and records it).

At the end:

- [ ] Course status `delivered` (`coursekit status PWD`).
- [ ] Packages and catalog in the mirror folder (`coursekit delivery add` publishes them; `coursekit publish PWD` if you had no mirror at that moment).
- [ ] At least one unit tested in the target LMS (or in SCORM Cloud). With the html backend this is a must: the packages have not been tested in a real LMS by coursekit.
- [ ] `course.yaml` committed (the zips are not versioned); commits are made only when you ask for them.

The agent does the export steps (creator) or the build and record steps (html) with `/deliver PWD 1.0` or `coursekit run deliver PWD 1.0`.

## Worked example

Course `PWD`, one unit, client ACME, mirror provider `folder`, creator backend:

```bash
coursekit assemble link PWD --unit 1 --content-id c-123
coursekit assemble plan PWD --unit 1
coursekit assemble diff PWD --unit 1        # content: rename; lessons: create…
# the agent applies the operations and records each lesson:
coursekit assemble applied PWD --unit 1 --lesson U1-S1 --lesson-id l-1 --brick-ids a,b
coursekit assemble applied PWD --unit 1 --content
coursekit assemble diff PWD --unit 1        # until everything is "unchanged"
```

The agent records the links of the unit:

```bash
coursekit assemble link PWD --unit 1 --preview https://acme.example.com/p/abc --review https://acme.example.com/r/xyz
```

The client reviews (optional); you open and close the round, and the agent processes the comments:

```bash
coursekit client PWD send --to "ACME training team"
# round 1 opened; the course moves to client_review. Links: ...
# /client-feedback PWD   (in the agent)
coursekit client PWD approve --by "ACME training lead"
# round 1 approved by ACME training lead: it can be delivered
```

Deliver version 1.0:

```bash
coursekit delivery check PWD
# PWD: it can be delivered
coursekit delivery name PWD --unit 1 --version 1.0
# PWD-U01-v1.0-scorm12.zip  (the agent exports and downloads it to courses/PWD/delivery/)
coursekit delivery add PWD --unit 1 --version 1.0 --file courses/PWD/delivery/PWD-U01-v1.0-scorm12.zip \
  --job job-1 --snapshot snap-1
# recorded PWD-U01-v1.0-scorm12.zip · course delivered
coursekit publish --check
# ok: folder mirror in /path/to/MIRROR_DIR
# info: no mirror.url in project.yaml; the catalog will have no folder links
coursekit publish PWD
# wrote /path/to/project/courses/course-catalog.xlsx (1 courses, 1 units)
# published PWD: 5 copied, 0 removed, 0 unchanged
# wrote /path/to/MIRROR_DIR/course-catalog.xlsx (1 courses, 1 units)
```

The same course with the html backend (`assembly.backend: html`) skips the links, the loading and the export; the review link is the one of the package you host:

```bash
coursekit assemble build PWD --unit 1
# unit 1: 5 files in courses/PWD/assembly/html/unit-01
# preview: open courses/PWD/assembly/html/unit-01/index.html in the browser
coursekit assemble build PWD --unit 1 --version 1.0
# package PWD-U01-v1.0-scorm12.zip (212.4 KB)
# (try the zip in the target LMS or SCORM Cloud, and host it for the client if there is a review)
coursekit client PWD send --to "ACME training team" --where https://lms.acme.example.com/courses/pwd
coursekit client PWD approve --by "ACME training lead"
coursekit delivery add PWD --unit 1 --version 1.0 --file courses/PWD/delivery/PWD-U01-v1.0-scorm12.zip
# recorded PWD-U01-v1.0-scorm12.zip · course delivered
```

Next: [09-troubleshooting.md](09-troubleshooting.md)
