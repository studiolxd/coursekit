# Content format — `content.md` and `assessment.md`

Canonical format of a unit's content. The writing agent writes it, `coursekit verify` checks it
and the assembly turns it into the platform's blocks. Course language: {{language_name}}; the
format words below (section heading, objective tag, media placeholder) are in that language.

## 1. Structure of `content.md`

```markdown
# {{t_unit}} N — <unit title>

> unit header: duration, minimum pages and words, unit objectives (UN.1, UN.2…)

---

## {{t_section}} 1 — {{t_intro_title}} *(…)*
### Subsection
…
## {{t_section}} 2 — <title> *(…)*
…
*[{{t_objective}} UN.1 — Verb]*
…
## {{t_section}} N — {{t_summary_title}} *(…)*
```

- Each section opens with `## {{t_section}} N — <title> *(minimum)*`. Number, order, title and
  minimum come from the approved instructional design (`course.yaml › units › sections`): the
  minimum is {{words_per_hour}} words per hour of the section ({{pages_per_hour}} pages of
  {{words_per_page}} words).
- Each section becomes one lesson.
- Subsections with `###`. Prose, lists, Markdown tables and code blocks are converted as they are.
- The tag `*[{{t_objective}} UN.M — Verb]*`, one per line, closes each content section. It is
  editorial metadata: it is not published.

**Word count:** only text the learner reads counts. Media placeholders, objective tags, HTML
comments and the `:::` lines of directives do not count (the text inside a directive does).

Writing rules: {{language_name}}, {{address_rule}}, complete prose (no bare lists or unexpanded
outlines), **no emojis** (only `{{allowed_symbols}}` are allowed).

## 2. Interactive component directives

A component is written as a `:::name` … `:::` block and becomes one block of the assembly
platform. The full registry of directives, their block and when to use each one is
`coursekit config directives` (`directives` and `use`): it is the only valid list. Common
components that are not directives have their equivalent in `component_equivalents`.

Each content section includes **distinct** interactive directives in proportion to its hours
({{interactive_per_hour}} per hour, at least {{min_interactive_per_content_section}}). `note`,
`highlight` and `quote` do not count as interactive.

Internal structure (anything else fails at assembly):

| Directive | Internal structure |
|---|---|
| `accordion`, `tabs`, `carousel` | one `#### Title` per panel, tab or slide + Markdown text |
| `timeline` | `#### <date> — <title>` per milestone (without " — ", all of it is the title) + text |
| `flashcards`, `flashcard-gallery` | `#### Front` + text of the back |
| `labelled-graphic` | `imagen: <exact title of the placeholder>` + `#### Point` + text; optional `posición: x,y` (0–100) under each point |
| `dialog` | `**Character:** line`, one per line |
| `carousel-quotes` | one quote per paragraph, with `— author` on its last line |
| `note` | optional `título: …` + text |
| `highlight` | text |
| `quote` | quote + `— author` on the last line |
| `word-search`, `wordle`, `hangman` | `- WORD` per line |
| `memory` | `- card content` per line |
| `pasapalabra` | `- A (empieza): definition :: ANSWER` or `(contiene)`; alternatives with `/` |
| `trivial` | `#### Category` + `pregunta: …` blocks with `- [x]` / `- [ ]` options, separated by a blank line |

A plain blockquote (`> text`) becomes a highlight.

## 3. Question directives (practice activities and tests)

The directives with `role: question`: `single-choice`, `multi-select`, `true-false`, `sorting`,
`match`, `sorting-groups`, `fill-in-the-blank`, `order-words`, `short-answer`.

```markdown
:::single-choice
{{t_question_key}} U1.2
pregunta: <question>
- [ ] <distractor>
- [x] <correct answer>
- [ ] <distractor>
feedback-correcto: <why it is right>
feedback-incorrecto: <which section to review>
:::
```

- `single-choice` (exactly one `- [x]`) and `multi-select`: options `- [x]` / `- [ ]`.
- `match`: lines `- term :: definition`. `sorting`: list in the right order. `order-words`:
  `- full sentence` per sentence. `sorting-groups`: `#### Category` + list of items.
  `true-false`: `respuesta: verdadero|falso`. `fill-in-the-blank`: blanks in `pregunta:` as
  `{answer}` (several accepted: `{a/b}`). `short-answer`: `respuestas: a | b | c`.
- Common keys: `{{t_question_key}}`, `pregunta:`, `feedback-correcto:`, `feedback-incorrecto:`,
  `feedback:`. Each key on one line. Every question carries `{{t_question_key}}` and feedback.

## 4. Media placeholders

Exact format (shown as a visible box until the asset is produced):

```markdown
> **[{{t_placeholder}} — <type>]**
{{placeholder_field_lines}}
```

Allowed types: {{placeholder_types}}. Per unit: {{placeholders_per_hour}} placeholders per hour
of the unit and at least {{min_placeholder_types}} different types.

## 5. `assessment.md`

The summative activities of the unit, in order:

```markdown
## {{t_assessment}} N.M — <name>
### (objectives assessed · instructions for the learner · development · automatic marking and
###  scoring · attempts and feedback · question bank)
:::single-choice
…
:::
```

The unit test bank has {{questions_per_objective}} questions per objective assessed by
questionnaire.
