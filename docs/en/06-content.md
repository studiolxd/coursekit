# Course content

How a course folder is laid out, the format of `content.md` and `assessment.md`, the interactive directives, and the rules `coursekit verify` enforces.

## Course folder

`coursekit new` creates the folder; every other file appears as the course moves through the workflow (see [02-workflow.md](02-workflow.md)).

```text
courses/PWD/
├── course.yaml                  record of the course: units, status, approvals, deliveries, history
├── brief/                       reference material (links.md, notes.md, sources/; text/ and index.md after `coursekit brief`)
├── design/
│   ├── matrix.json              instructional design, exactly as exported from the platform
│   ├── PWD-instructional-design.xlsx   the file people review
│   ├── proposal-notes.md        notes of the design agent
│   └── validation.json          validation findings (optional)
├── content/
│   └── unit-01/
│       ├── content.md           the lessons of the unit
│       └── assessment.md        summative activities and question bank
├── reviews/
│   └── unit-01-ai-review.md     report of the AI review
├── media/
│   ├── manifest.yaml            one entry per media placeholder
│   ├── scripts/ · src/ · files/ scripts, sources and produced files (see 07-media.md)
├── theme/                       own theme of the course (optional): tokens.json, tokens.css, maqueta.css (html backend)
├── assembly/
│   ├── unit-01.plan.json        generated plan, creator backend (see 08-assembly-and-delivery.md)
│   ├── unit-01.applied.json     what is loaded in the platform, creator backend
│   └── html/unit-01/            package built by the html backend (generated, not versioned)
└── delivery/
    └── PWD-U01-v1.0-scorm12.zip SCORM packages
```

`coursekit new` creates `brief/`, `design/`, `content/`, `media/` (with an empty `manifest.yaml`), `reviews/` and `course.yaml`. `assembly/` appears with the first `coursekit assemble plan` (creator backend) or `coursekit assemble build` (html backend) and `delivery/` with the first package. `theme/` exists only if the course has a theme of its own (`/define-theme PWD`); without it the course uses the project's `theme/` (next to `courses/`), which holds the design tokens every course inherits.

Two more folders of the project matter to the html backend, both next to `courses/` and both written by people:

| Path | What it is |
|---|---|
| `theme/maqueta.css` | The stylesheet that restyles the package of the html backend (the "maqueta"). A course can have its own in `courses/PWD/theme/maqueta.css`; it goes over the project's. `coursekit theme import theme/maqueta.css` derives the design tokens from its CSS variables |
| `components/` | Extra `*.css` (styles added to every package) and `*.js` (behaviour bundled into the player) of the project. Optional |

Both are explained in [Styles](08-assembly-and-delivery.md#styles).

### Who writes what

| Path | Created by | Changed by |
|---|---|---|
| `course.yaml` | `coursekit new` | coursekit commands write `units`, `status`, `history`, `approvals` and `deliveries`; people and agents fill `owners`, `links`, `design` and `slxd`. Do not edit `units` or `approvals` by hand |
| `design/*` | design agent | design agent. `matrix.json` is never edited by hand: signing the design records its hash |
| `content/unit-NN/*.md` | `coursekit sync` (skeleton, only when missing) | writer agent; people for editorial changes |
| `reviews/unit-NN-ai-review.md` | reviewer agent | reviewer agent |
| `media/manifest.yaml` | `coursekit media extract` | `coursekit media extract` and `coursekit media set` |
| `media/scripts`, `src`, `files` | media agent | media agent |
| `theme/{tokens.json,tokens.css}` (project) and `courses/<CODE>/theme/{tokens.json,tokens.css}` (course) | `coursekit theme import` (run by `/define-theme`) | `coursekit theme import` again, `coursekit theme tokens` for the CSS. Never by hand: they are derived from the theme of the platform and carry its `origin` (theme id, name, version, date). `course.yaml › slxd.theme_id` is written by the import for a course with its own theme |
| `theme/maqueta.css` and `courses/<CODE>/theme/maqueta.css`, `components/*` (html backend) | People | People. They are the one place where the look of the html package is written; the package itself is never edited |
| `assembly/*.json` | `coursekit assemble` (creator backend) | `coursekit assemble` (never by hand) |
| `assembly/html/` | `coursekit assemble build` (html backend) | `coursekit assemble build` rebuilds it from scratch; it is generated and git-ignored |
| `delivery/*.zip` | assembly agent (download, creator backend) or `coursekit assemble build --version` (html backend) | recorded with `coursekit delivery add` |
| `brief/` | `coursekit new` | people drop material in it; `coursekit brief` converts it |

Approvals (`approvals` in `course.yaml`) are written only by `coursekit approve`, and only a person runs it.

## Content language and UI language

| | Setting | What it controls |
|---|---|---|
| Content language | `content_language` in `project.yaml` (`language` in `course.yaml` overrides it per course; `coursekit new --language`) | The words of the content format (section heading, objective tag, placeholder, field names), the skeleton templates, the number format (`5,000` in English, `5.000` in Spanish), the language the agents write in and the form of address (`tu` / `usted` / `you`) |
| UI language | `ui_language` in `project.yaml`; `COURSEKIT_LANG` in `.env` overrides it for one person | Messages of coursekit (including the findings of `verify`), review reports, design notes and the language of the catalog Excel |

Both take `es` or `en`. If `ui_language` is not set, `content_language` is used. A course language such as `es-ES` is read as `es`.

## Format of `content.md`

The format words below come from `src/coursekit/lang/en.yaml` and `es.yaml`. `verify`, `outline`, `media` and `assemble` all read them, so the headings must be typed exactly as shown. The words of the content are the ones of the course language: do not mix them (see [Resource types and directive keys by language](#resource-types-and-directive-keys-by-language)).

| Element | English content | Spanish content |
|---|---|---|
| Unit title | `# Unit N — <title>` | `# Unidad N — <título>` |
| Section heading | `## Section N — <title> *(min. 1,000 words)*` | `## Apartado N — <título> *(mín. 1.000 palabras)*` |
| Objective tag | `*[Objective U1.2 — Verb]*` | `*[Objetivo U1.2 — Verbo]*` |
| Media placeholder | `> **[MEDIA ASSET — <type>]**` (`<type>`: `Image`, `Infographic`…) | `> **[RECURSO MULTIMEDIA — <tipo>]**` (`<tipo>`: `Imagen`, `Infografía`…) |
| Placeholder fields | `Title`, `Description`, `How it is made`, `Specifications` | `Título`, `Descripción`, `Cómo se elabora`, `Especificaciones` |
| Assessment activity heading | `## ASSESSMENT ACTIVITY N.M — <name>` | `## ACTIVIDAD DE EVALUACIÓN N.M — <nombre>` |
| Question objective key | `objective:` | `objetivo:` |
| Other directive keys and words | `question:`, `answer:`, `feedback-correct:`, `true`/`false`, `(starts)` | `pregunta:`, `respuesta:`, `feedback-correcto:`, `verdadero`/`falso`, `(empieza)` |
| Introduction title (default) | `Introduction and objectives` | `Introducción y objetivos` |
| Summary title (default) | `Summary` | `Resumen` |

### Unit header and sections

`coursekit sync` writes the skeleton. Replace each `<!-- kind … -->` comment with the content of that section:

```markdown
# Unit 1 — Passwords that protect

> **Duration:** 1 hours · **Minimum pages:** 10 · **Minimum words:** 5,000
> **Unit objectives:**
> - **U1.1** — Create strong passwords
> - **U1.2** — Identify weak passwords

---

## Section 1 — Introduction and objectives *(min. 1,000 words)*

<!-- kind: intro -->

## Section 2 — What makes a password strong *(min. 3,000 words)*

<!-- kind: content · objectives: U1.1, U1.2 -->
```

- The number, order and title of each section come from the approved design. The `*(min. …)*` part is optional and informative. The dash can be `—` or `-`.
- Each section becomes one lesson. Use `###` for subsections; prose, lists, Markdown tables and code blocks are converted as they are.
- Every section has a `kind`: `intro` (first section, when `design.intro_section` is `true`), `summary` (last section, when `design.summary_section` is `true`), `content` (it develops objectives) or `activities` (no objectives: learning activities).
- Complete prose, no bare lists, **no emojis** (see the allowed symbols below). Only the emoji rule is checked by `verify`; the quality of the prose is an editorial rule.

### Objective tags

Every `content` section ends with one tag per objective it covers, one per line:

```markdown
*[Objective U1.1 — Create]*
*[Objective U1.2 — Identify]*
```

The tag is editorial metadata: it is not published. `verify` reads the ids (`U1.1`) to check that each objective of the unit is covered at least once. It only requires one tag per `content` section (tags in other kinds of section are not read) and every unit objective tagged somewhere: it does not compare the tags with the objectives the design gives to that section, nor check that an id exists.

### Media placeholders

A placeholder reserves the place of an image, video or other resource until it is produced:

```markdown
> **[MEDIA ASSET — Image]**
> **Title:** Sticky note on a monitor
> **Description:** A password written on a note stuck to a screen.
> **How it is made:** Licensed stock photo.
> **Specifications:** 1280x720 px, alt text required.
```

The four fields are mandatory. The `<type>` is one of eight resource types, written with the word of the course language (in English: `Image`, `Video`, `Animated GIF`, `Infographic`, `Diagram`, `Interactive simulation`, `Interactive terminal demo`, `Audio`; the Spanish words are in the table below). Each type also has an id (`image`, `video`, `animated_gif`, `infographic`, `diagram`, `simulation`, `terminal_demo`, `audio`) used in the configuration and the manifest. Production is explained in [07-media.md](07-media.md).

### What counts as a word

Only text the learner reads counts: the placeholder box (its `>` lines, up to the first line that does not start with `>`), objective tags (each on a line of its own), HTML comments and the `:::` lines of directives are left out. The text *inside* a directive does count, and so does a plain blockquote (`> text`). Words are the whitespace-separated tokens of what is left, so a list marker, a `####` or the pipes of a table count as one each. They are counted per section; the unit header is not counted.

`coursekit outline` shows a different, approximate figure: it counts every word of the section without comments, including placeholder boxes, tags and directive names, so it is higher than the figure of `verify`. The number that counts is the one `verify` prints.

### Resource types and directive keys by language

Some words of the format are written in the language of the course, but the configuration and the manifest must not depend on that language. So a resource type has an **id** (always in English, the same in every course) and a **word** per content language (`media_types` in `src/coursekit/lang/<code>.yaml`):

| Id | Spanish content | English content |
|---|---|---|
| `image` | `Imagen` | `Image` |
| `video` | `Vídeo` | `Video` |
| `animated_gif` | `GIF animado` | `Animated GIF` |
| `infographic` | `Infografía` | `Infographic` |
| `diagram` | `Esquema/Diagrama` | `Diagram` |
| `simulation` | `Simulación interactiva` | `Interactive simulation` |
| `terminal_demo` | `Demo interactiva en terminal` | `Interactive terminal demo` |
| `audio` | `Audio` | `Audio` |

- In `content.md` you write the **word** of the course language in the placeholder (`> **[MEDIA ASSET — Infographic]**`). Case and surrounding spaces do not matter, but accents do: in a Spanish course `Video` and `Infografia` are errors, only `Vídeo` and `Infografía` are accepted. The dash of the placeholder heading can be `—` or `-`.
- Everywhere else the **id** is used: `content.placeholder_types` in `config/rules.yaml`, the keys of `types` and the `uses_theme` list in `config/media.yaml` (see [04-configuration.md](04-configuration.md)), and `type` in `media/manifest.yaml › assets`. `coursekit media extract` converts the word to the id, so the manifest is the same whatever the language of the course.
- A word of the other language is an error: in an English course, `Infografía` fails with `unknown or not allowed placeholder type 'Infografía' (use: Image, Video, Animated GIF, …)`.

The keys of the `key: value` lines inside directives, and the few words some of them take, follow the content language too (`directive_keys` and `directive_words` in the same file; the objective key is `question_objective_key`):

| Used for | English content | Spanish content |
|---|---|---|
| Question text | `question:` | `pregunta:` |
| Answer of `true-false` | `answer:` | `respuesta:` |
| Accepted answers of `short-answer` | `answers:` | `respuestas:` |
| General, correct and incorrect feedback | `feedback:` · `feedback-correct:` · `feedback-incorrect:` | `feedback:` · `feedback-correcto:` · `feedback-incorrecto:` |
| Image of `labelled-graphic` | `image:` | `imagen:` |
| Position of a point | `position:` | `posición:` |
| Title of `note` | `title:` | `título:` |
| Objective of a question | `objective:` | `objetivo:` |
| Value of `true-false` | `true` · `false` | `verdadero` · `falso` |
| Mode of a `pasapalabra` item | `(starts)` · `(contains)` | `(empieza)` · `(contiene)` |

The directive **names** (`:::single-choice`, `:::tabs`…) are the same in both languages. A key that belongs to the other language is not ignored: `coursekit assemble plan` and `coursekit verify` fail with `the key 'pregunta:' belongs to the language 'es'; this course uses: …` and list the valid ones. The format reference that the agents read (`.coursekit/docs/content-format.md`) shows the words of the course language. A new language needs `media_types`, `directive_keys` and `directive_words` in its `lang/<code>.yaml` (see `CONTRIBUTING.md`).

### Doubts and VERIFICAR markers

When the writer cannot confirm a fact (a version, a command, an option, a product name) from the reference material in `brief/`, it does not invent it: it leaves `<!-- VERIFICAR: what to check -->` next to the text. It is an HTML comment, so it is not counted as words and is not published. `coursekit verify` does not look for these markers, and a unit passes with them still in: they are a convention between the writer and the reviewer. The reviewer finds each one, resolves it with the material (a claim that contradicts the material is a blocking finding) and removes it. In [handoff mode](02-workflow.md#handoff-mode), where nobody can be asked, the doubts stay written in the units and in the reports. The improvements that change the approach are not applied by the reviewer: they go under "Proposals awaiting a human decision" in `reviews/unit-NN-ai-review.md`, for the person to resolve before signing.

## Format of `assessment.md`

The summative activities of the unit, in the order they are done. One `##` heading per activity of the design, with these `###` subsections:

```markdown
# Unit 1 — Assessment activities

## ASSESSMENT ACTIVITY 1.1 — Unit test
### Objectives assessed
### Instructions for the learner
### Development and implementation
### Automatic marking and scoring
### Attempts and feedback
### Question bank
```

| English | Spanish |
|---|---|
| `Objectives assessed` | `Objetivos que evalúa` |
| `Instructions for the learner` | `Instrucciones para el alumno` |
| `Development and implementation` | `Desarrollo e implementación` |
| `Automatic marking and scoring` | `Corrección automática y puntuación` |
| `Attempts and feedback` | `Intentos y retroalimentación` |
| `Question bank` | `Banco de preguntas` |

The assembly loads only what is under **Instructions for the learner** and **Question bank** (text and directives) into the platform's assessment lesson; the other subsections document the activity for the team. Put the question directives (see below) in the bank. Every question carries the objective key and feedback.

- `verify` does not check the headings of `assessment.md`, but the assembly matches them exactly, with the words of the course language: a misspelled `### Question bank` loads no questions. One assessment lesson is built per `## ASSESSMENT ACTIVITY` heading.
- `verify` counts every question directive of the file, wherever it is. One placed in another subsection counts for `verify` but never reaches the learner.
- The pass mark and the attempts are not read from the Markdown: they come from `course.yaml › design.grading` (`passing_score` and `attempts`; see [04-configuration.md](04-configuration.md)). The subsections `Automatic marking and scoring` and `Attempts and feedback` only document the activity. The weights (`unit_tests_weight`, `final_test_weight`) are not read by the assembly either.

## Directives

A directive is a block that becomes one interactive element of the course:

```markdown
:::tabs
#### Length
Length matters more than complexity.
#### Uniqueness
Never reuse a password.
:::
```

`:::name` opens the block and a line with only `:::` closes it. Directives cannot be nested, and lines inside code fences are ignored. The registry lives in `src/coursekit/defaults/directives.yaml`; a project can change it in `config/directives.yaml` (its complete copy is in `config/directives.example.yaml`).

### Roles

| Role | Meaning |
|---|---|
| `interactive` | Counts towards the interactive minimum of a `content` section |
| `question` | Practice or assessment question; needs the objective key |
| `static` | Highlighted text; does **not** count as interactive |

### Directive table

| Directive | Creator brick | Role | Use | Html backend |
|---|---|---|---|---|
| `accordion` | `ACCORDION` | interactive | Long content split into collapsible sections opened on demand | ✔ |
| `tabs` | `TABS` | interactive | Alternative views of related content in tabs | ✔ |
| `carousel` | `CAROUSEL` | interactive | Step-by-step slides, with optional cover and summary | ✔ |
| `carousel-quotes` | `CAROUSEL_QUOTES` | interactive | Rotating set of quotes or testimonials | ✔ |
| `flashcards` | `FLASHCARD_CAROUSEL` | interactive | Memorise and recall, one card at a time (term ↔ definition) | ✔ |
| `flashcard-gallery` | `FLASHCARD_GALLERY` | interactive | Grid of cards to self-assess recall | ✔ |
| `labelled-graphic` | `LABELLED_GRAPHIC` | interactive | Image with hotspots that explain its parts (diagrams) | ✔ |
| `timeline` | `TIMELINE` | interactive | Chronological or sequential facts or steps | ✔ |
| `dialog` | `DIALOG` | interactive | Scripted conversation between characters (role play, worked examples) | ✔ |
| `word-search` | `WORD_SEARCH` | interactive | Word search; vocabulary reinforcement | not available yet |
| `wordle` | `WORDLE` | interactive | Guess the word; vocabulary | not available yet |
| `hangman` | `HANGMAN` | interactive | Hangman; vocabulary | not available yet |
| `pasapalabra` | `PASAPALABRA` | interactive | Letter wheel with one clue per letter; broad review of a topic | not available yet |
| `memory` | `MEMORY` | interactive | Matching pairs; recall and association | not available yet |
| `trivial` | `TRIVIAL` | interactive | Trivia by category; gamified review | not available yet |
| `single-choice` | `SINGLE_CHOICE` | question | Check understanding with a single correct option | ✔ |
| `multi-select` | `MULTI_SELECT` | question | Assess when several options can be correct | ✔ |
| `true-false` | `TRUE_FALSE` | question | Quick check of a statement | ✔ |
| `sorting` | `SORTING` | question | Put items in the correct sequence | ✔ |
| `match` | `MATCH` | question | Pair items on the left with items on the right | ✔ |
| `sorting-groups` | `SORTING_GROUPS` | question | Classify items into their categories | ✔ |
| `fill-in-the-blank` | `FILL_IN_THE_BLANK` | question | Recall specific words inside a sentence (blanks) | ✔ |
| `order-words` | `ORDER_WORDS` | question | Rebuild sentences from scrambled words | ✔ |
| `short-answer` | `SHORT_ANSWER` | question | Free answer compared with a list of accepted answers | ✔ |
| `note` | `NOTE` | static | Note, tip or warning set apart from the main text | ✔ |
| `highlight` | `HIGHLIGHT` | static | Highlight a key idea | ✔ |
| `quote` | `QUOTE` | static | Quote from an expert or source, with attribution | ✔ |

The games (`word-search` to `trivial`) count as interactive; use them sparingly, for review or reward. They are the only directives the html backend does not render yet (last column): `coursekit assemble build` refuses a unit that uses one, and `coursekit verify` reports it with the html backend (`MEMORY: this component is not available in the html backend yet…`). Everything else is built as described in [Components](08-assembly-and-delivery.md#components). A plain blockquote (`> text`) that is not a placeholder becomes a `HIGHLIGHT` brick.

Everything else in Markdown maps to a brick without a directive: paragraphs to `TEXT`, `###`–`######` headings to `HEADING`, lists to `LIST`, tables to `TABLE`, code fences to `CODE`. Media placeholders are explained in [07-media.md](07-media.md).

### Internal structure

Anything that does not follow these shapes fails when the unit is converted (`verify` reports it).

| Directive | Internal structure |
|---|---|
| `accordion`, `tabs`, `carousel` | One `#### Title` per panel, tab or slide, followed by Markdown text |
| `timeline` | `#### <date> — <title>` per milestone (without ` — `, the whole line is the title) + text |
| `flashcards`, `flashcard-gallery` | `#### Front` + text of the back |
| `labelled-graphic` | `image: <exact title of the image placeholder>`, then `#### Point` + text; optional `position: x,y` (0–100) under each point |
| `dialog` | `**Character:** line`, one per line |
| `carousel-quotes` | One quote per paragraph, with `— author` on its last line |
| `note` | Optional `title: …` line (default title: `Note`) + text |
| `highlight` | Text |
| `quote` | Quote + `— author` on the last line |
| `word-search`, `wordle`, `hangman` | `- WORD` per line |
| `memory` | `- card content` per line |
| `pasapalabra` | `- A (starts): definition :: ANSWER` (or `(contains)`) per line |
| `trivial` | `#### Category`, then blocks with `question: …` and `- [x]` / `- [ ]` options, separated by a blank line |

The `image:` of a `labelled-graphic` is matched against the title of a resource in `media/manifest.yaml`, so the placeholder must exist in the manifest (run `coursekit media extract` first) and be produced. Otherwise `assemble` only warns (`labelled-graphic: image 'X' not produced yet`) and the graphic has no image. Only the lines before the first `####` are keys of the graphic itself; a `position:` goes under the point it belongs to.

Inside a directive, a line that starts with a lowercase word and a colon (`tip: …`) is read as a key, not as text. In `note`, `highlight`, `quote` and `carousel-quotes` it is silently removed from the published text; in the other directives a key of the other language raises the error described above. Write `Tip:` with a capital or reword the sentence. Keys go on a line of their own, not after a list marker.

### Question directives

```markdown
:::single-choice
objective: U1.1
question: Which password is the strongest?
- [ ] Summer2024!
- [x] correct horse battery staple river
- [ ] P@ssw0rd
feedback-correct: Length and randomness win.
feedback-incorrect: Review the section on length.
:::
```

| Directive | Body |
|---|---|
| `single-choice` | Options `- [x]` / `- [ ]`; exactly one `- [x]` |
| `multi-select` | Options `- [x]` / `- [ ]` |
| `true-false` | `answer: true` or `answer: false` |
| `sorting` | A list in the right order |
| `match` | Lines `- term :: definition` |
| `sorting-groups` | `#### Category` + list of its items |
| `fill-in-the-blank` | Blanks written in `question:` with the correct word in braces, as `{long}` (several accepted answers: `{a/b}`); there is no `answer:` line |
| `order-words` | One `- full sentence` per sentence |
| `short-answer` | `answers: a \| b \| c` |

Each key goes on one line. The key names inside directives (`question:`, `answer:`, `answers:`, `feedback-correct:`, `feedback-incorrect:`, `feedback:`, `title:`, `image:`, `position:`) and the objective key (`objective:`) are the ones of the content language shown here; a Spanish course writes `pregunta:`, `respuesta:`, `objetivo:`… (see [Resource types and directive keys by language](#resource-types-and-directive-keys-by-language)). Mixing languages is an error.

`question:` is required, but `verify` only warns when `objective:` is missing. A question without `question:`, a `multi-select` with no `- [x]`, a `match` with no `::` pair or a `short-answer` without `answers:` passes `verify` and is published empty or broken, so check them by hand. `objective:` takes a unit objective id (`U1.1`); its value is not validated. Every question should also carry feedback (`feedback-correct:`, `feedback-incorrect:` or `feedback:`); that is an editorial rule that `verify` does not check.

### Components that are not directives

If a directive name is not in the registry, `verify` fails and suggests the equivalent:

| Common component | Use instead |
|---|---|
| stepper | `carousel` (or `timeline` for a time sequence) |
| hotspots | `labelled-graphic` |
| reveal | `accordion` or `flashcards` |
| toggle-compare | `tabs` |
| checklist | `multi-select` (as self-assessment) |
| tooltips | `note`, or a glossary in an `accordion` |
| modal | `accordion` |
| branching-scenario | `dialog` (complex branches: `Interactive simulation` placeholder) |
| simulated-terminal | `Interactive terminal demo` placeholder |

## `coursekit sync` and `coursekit outline`

### `coursekit sync CODE [--check]`

Reads `design/matrix.json` and rewrites the `units` of `course.yaml`: title, hours, objectives (relabelled `U1.1`, `U1.2`… in order of appearance), sections (`kind`, `title`, `hours`, `min_words`, objectives, subsections) and activities. Then, for each unit that has no `content.md`, it writes the skeleton of `content.md` and `assessment.md` in the content language.

- Existing content is never overwritten. `content.md` is regenerated only while it is still the untouched skeleton of a previous design, and `assessment.md` is written only when it is missing or still the blank template. If the headings of `content.md` differ from the design, sync warns and you update them by hand.
- Progress fields (`content_id`, `status`, `written_with`, `reviewed_with`, `reviewed_parts`, `review`, `links`) are kept, matched by the platform id of the unit.
- `--check` only reports what would be synced and writes nothing.
- It warns when a section has no hours, when unit hours do not add up to the section hours, when units do not add up to the course hours, or when the first/last section is not an introduction/summary while `intro_section`/`summary_section` is on (the title must match `^\s*introduction` and `^\s*(summary|wrap-up|conclusion)`; in Spanish `introducci[oó]n` and `resumen|síntesis|conclusión`).
- Minimum words of a section: `ceil(hours × 10)` pages × 500 words (1 hour = 5,000 words; 0.2 h = 1,000; 0.6 h = 3,000).

`coursekit approve design` runs `sync` itself when you sign. Editing `matrix.json` after the signature makes `verify` refuse to run until the design is approved again.

### `coursekit outline CODE [--section U.S]`

A compact map for agents and people: every unit with status, objectives, and each section with its objectives, minimum words and how much is written. `--section 1.2` prints only the text of section 2 of unit 1 (comments removed) so you can check what an earlier unit says without reading it whole. A bad value (`x`) exits with code 2; a section that is not written prints `section 1.2: not written`.

```text
U1 Passwords that protect · 1 h · pending
  U1.1 (apply): Create strong passwords
  1.2 What makes a password strong [U1.1, U1.2] · min. 3,000 · 3,200 words written
```

## `coursekit verify`

```bash
coursekit verify PWD              # every unit
coursekit verify PWD --unit 1     # one unit
coursekit verify PWD --no-update  # do not move unit and course status
```

The exit code is 1 if any unit has errors; warnings never fail. The design must be approved and unchanged first; otherwise the command stops with `PWD: the instructional design is not approved yet (coursekit approve design PWD)` or `design/matrix.json changed after the approval: the design must be approved again`.

### Rules and real numbers

The numbers are the package defaults (`src/coursekit/defaults/rules.yaml`). A project overrides them in `config/rules.yaml` or `project.yaml › rules`, and a course in `course.yaml › rules` (see [04-configuration.md](04-configuration.md)).

| Check | Rule | Default | Severity |
|---|---|---|---|
| Sections | Section numbers in `content.md` equal the design's | — | error |
| Section title | Same title as the design | — | warning |
| Minimum words | `ceil(hours × pages_per_hour)` pages of `words_per_page` words per section | 10 pages/hour, 500 words/page (5,000 words per hour) | error |
| Word margin | Recommended margin over the minimum (`word_margin`) | 5 % | warning |
| Objective tag | Each `content` section has at least one tag; each unit objective is tagged somewhere | — | error |
| Interactive minimum | Distinct interactive directives per `content` section: `max(min_interactive_per_content_section, ceil(hours × interactive_per_hour))` | 4 per hour, at least 1 (0.6 h needs 3) | error |
| Placeholders | At least `ceil(unit hours × placeholders_per_hour)` in the unit | 2.5 per hour (1 h needs 3) | error |
| Placeholder types | At least `min(min_placeholder_types, placeholders required)` different types | 4 (1 h needs 3) | error |
| Placeholder form | Known type (a word of the course language) and the four fields present | 8 types | error |
| Directives | Known name, closed, not nested | — | error |
| Question objective | Every question directive has the objective key (`objective:` / `objetivo:`) | — | warning |
| Question bank | `questions_per_objective` × number of distinct objectives assessed by an activity whose instrument is `cuestionario` (the value of the instrument field of the design, whatever the course language) | 5 per objective | warning |
| Symbols | No emoji or pictograph outside `allowed_symbols` | `★ ✔ ✘ · — ‹ ›` | error |
| Assembly | The Markdown converts to bricks (same parse as `assemble plan`). With the html backend it also reports the directives that are not available yet | — | error |
| Files | `content.md` and `assessment.md` exist | — | error |

Notes: the interactive minimum counts **distinct** directive names, so repeating `tabs` three times counts once; `note`, `highlight`, `quote` and question directives do not count. Only `content` sections need tags and interactive directives; `intro`, `summary` and `activities` sections only need their words. Questions are counted in `content.md` (formative questions) and `assessment.md` (bank); only the bank is compared with the expected number, and only as a total: `verify` does not check how the questions are spread among the objectives, nor the value of their `objective:`.

The symbols check reads `content.md` and `assessment.md` in full, comments and code blocks included. It rejects emoji and the symbol blocks U+2300–23FF, U+2600–27BF and U+2B00–2BFF, so a check mark such as U+2713 or a warning sign such as U+26A0 fails: use `✔` or `✘`. Arrows are not affected.

### Reading the messages

```text
[FAIL] PWD · U1 — Passwords that protect
  words 0/5,000 · placeholders 0 (0 types) · formative questions 0 · bank questions 0
  ERROR   content.md › Section 1: 0 words < minimum 1,000
  ERROR   content.md › Section 2: 0 words < minimum 3,000
  ERROR   content.md › Section 2: missing objective tag *[Objective UN.M — …]*
  ERROR   content.md › Section 2: 0 distinct interactive directives < 3
  ERROR   content.md › Section 3: 0 words < minimum 1,000
  ERROR   content.md: objective U1.1 is not tagged in any content section
  ERROR   content.md: objective U1.2 is not tagged in any content section
  ERROR   content.md: 0 placeholders < 3
  ERROR   content.md: 0 placeholder types < 3
  WARNING assessment.md: 0 questions in the bank, expected 5 (5 per objective assessed by questionnaire)
```

This is the output for the untouched skeleton of the worked example below.

The header says `[OK]` or `[FAIL]`. The second line gives words (written/minimum), placeholders (and distinct types), formative questions and bank questions. Then one line per finding: `ERROR` fails the unit, `WARNING` does not. A finding about a section is labelled `content.md › Section N`; syntax findings carry `file:line`.

| Message | What to do |
|---|---|
| `Section N: X words < minimum Y` | Write more; placeholders, tags, comments and `:::` lines do not count |
| `Section N: X words, below the recommended 5 % margin` | Aim a little above the minimum (warning) |
| `Section N: missing objective tag *[Objective UN.M — …]*` | Add the tag line at the end of the section |
| `objective U1.1 is not tagged in any content section` | Cover that objective in a `content` section and tag it |
| `Section N: X distinct interactive directives < Y` | Add directives of other kinds |
| `X placeholders < Y` · `X placeholder types < Y` | Add placeholders, or vary their type |
| `unknown or not allowed placeholder type 'Imagen' (use: Image, Video, …)` | Use one of the words listed, which are those of the course language (in an English course `Image`, not `Imagen`) |
| `placeholder missing fields: …` | Add the missing `> **Field:** …` lines |
| `unknown directive ':::name'` (`use: …`) | Use a registry directive; the hint names the equivalent |
| `nested directive inside ':::tabs'` · `directive ':::tabs' is not closed` | One directive at a time; close it with `:::` |
| `question without 'objective:'` | Add `objective: U1.1` as the first line of the question |
| `assembly: U1-S2: the key 'pregunta:' belongs to the language 'es'; this course uses: …` | A key of the other language: write the one of the course language (`question:`) |
| `emoji/pictograph not allowed (U+…)` | Remove it, or use one of the allowed symbols |
| `sections [1, 2] do not match the design [1, 2, 3]` | Restore the missing or extra `## Section N` heading |
| `title 'X' differs from the design 'Y'` | Warning: align the heading with the design |
| `assembly: …` | The Markdown does not convert (for example `:::single-choice needs exactly one correct option`); fix it in the `.md` |
| `missing …/content.md` · `missing assessment.md` | Run `coursekit sync` or create the file |

### What `verify` does to the unit status

Unless you pass `--no-update`, `verify` also moves the unit. A unit with no errors becomes `verified`; the exception is a project with `review.ai: skip` (see [04-configuration.md](04-configuration.md)), where it becomes `reviewed` straight away (`review.kind: skipped`) and your sign-off is the review. A unit with errors goes back to `writing` if it was `verified` or later, or if it was `pending` and already has words; a `pending` unit with no words stays `pending`. It prints a line such as `status: unit pending -> verified · course design_approved -> ai_review`. Statuses are explained in [02-workflow.md](02-workflow.md).

### What changed since the AI review

When the AI review is required, `coursekit reviewed` stores a fingerprint of every part of the unit in `course.yaml › units[N].reviewed_parts`: each section of `content.md` (`section 2`) and each activity of `assessment.md` (`activity 1.1`), from its `##` heading to the next one, comments included. Text before the first `##` heading (the unit header, the title of `assessment.md`) belongs to no part. A part counts as changed when its text differs in any way, even a space or a `VERIFICAR` comment, or when it is added or removed.

| After an edit, `verify` finds | The unit goes to |
|---|---|
| Errors | `writing` |
| `reviewed` unit, no errors, a part changed | `verified`, with `changed after the AI review: section 2 (coursekit review: partial review)`; the next `coursekit review` covers only those parts |
| `approved` unit, no errors, a part changed | `verified`; the earlier approval stays in the history and you sign again |
| `approved` unit, no errors, a file changed but no part (for example the unit header) | `reviewed` |
| Any passing unit with `review.ai: skip` | `reviewed` |

## Worked example

A one-hour course on strong passwords (code `PWD`, client ACME) whose design has been exported to `courses/PWD/design/matrix.json` and signed.

```bash
coursekit new "Strong passwords" 1 --code PWD
# the design agent saves design/matrix.json; a person signs it:
coursekit sync PWD
```

```text
1 unit, 3 sections, 5,000 minimum words · synced into course.yaml
  written: content/unit-01/content.md
```

The writer agent fills `content/unit-01/content.md`. Section 2 (0.6 h) needs at least 3,000 words, 3 distinct interactive directives and both objective tags; the unit needs 3 placeholders of 3 different types and a bank of 5 questions per objective assessed by the unit test (5 here, because the design's test assesses one objective; 10 if it assessed both). The excerpt below shows only part of what `verify` counts:

```markdown
## Section 2 — What makes a password strong *(min. 3,000 words)*

Length matters more than complexity. A long passphrase is easier to remember and much harder to guess…

:::tabs
#### Length
Every extra character multiplies the work of a guessing attack.
#### Uniqueness
Never reuse a password.
:::

> **[MEDIA ASSET — Infographic]**
> **Title:** Anatomy of a strong password
> **Description:** Diagram of length, variety and uniqueness.
> **How it is made:** SVG with theme tokens.
> **Specifications:** 1280 px wide, alt text.

*[Objective U1.1 — Create]*
*[Objective U1.2 — Identify]*
```

```bash
coursekit verify PWD --unit 1
```

```text
[OK] PWD · U1 — Passwords that protect
  words 5,947/5,000 · placeholders 3 (3 types) · formative questions 1 · bank questions 5
```

The unit is now `verified`. Next come the AI review and the signature (see [02-workflow.md](02-workflow.md)), then media ([07-media.md](07-media.md)).

Next: [07-media.md](07-media.md)
