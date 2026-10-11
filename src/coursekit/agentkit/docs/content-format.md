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
- Code blocks: write ```` ```bash ```` for commands (also PowerShell and `cmd`) and ```` ```text ```` for what a program prints or a
  conversation. Creator has no plain-text language, so a `text` block made only of commands is shown as `bash` and the rest
  uses the platform's automatic detection, which guesses badly with short code: keep outputs in `text` and commands in `bash`.
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
| `labelled-graphic` | `{{k_image}}: <exact title of the placeholder, as in `media/manifest.yaml`>` + `#### Point` + text; optional `{{k_position}}: x,y` (0–100) under each point |
| `dialog` | `**Character:** line`, one per line |
| `carousel-quotes` | one quote per paragraph, with `— author` on its last line |
| `note` | optional `{{k_title}}: …` + text |
| `highlight` | text |
| `quote` | quote + `— author` on the last line |
| `word-search`, `wordle`, `hangman` | `- WORD` per line |
| `memory` | `- card content` per line |
| `pasapalabra` | `- A ({{w_starts}}): definition :: ANSWER` or `({{w_contains}})`; alternatives with `/` |
| `trivial` | `#### Category` + `{{k_question}}: …` blocks with `- [x]` / `- [ ]` options, separated by a blank line |

A plain blockquote (`> text`) becomes a highlight.

## 2.1 Simulations (`scenario`, `conversation`)

Decision-based courses (`course.yaml › design.approach: decision-based`) open every content section with a simulation; any
course may use them. The body is **YAML with a fixed schema in English**; only the texts are in {{language_name}}. It is not
counted as text: what is read on its longest path counts as words of its section, plus `decision_based.decision_seconds`
per decision (`coursekit config rules`); scored simulations of `assessment.md` count in the activities section of the unit.

```markdown
:::scenario
id: call
title: The support call
skin: phone
objective: [U1.1, U1.2]
scored: true
state: {risk: 0, trust: 2, called: false}
scenes:
  begin:
    background: Marta's desk at ACME
    characters: [{name: Technician, expression: hurried}]
    text: |
      It is 9:10 and your phone rings. Someone from support needs your password
      "to migrate your mailbox before 10".
    checkpoint: true
    choices:
      - {text: I give it to him, goto: leak, effects: {risk: 3}, score: -2}
      - {text: I ask for his extension and call him back, goto: safe, set: {called: true}, score: 2}
      - {text: I check with my manager first, goto: safe, if: "trust >= 2 && !called", score: 1}
    hotspots:
      - {label: Sticky note on the monitor, area: [62, 30, 8, 6], goto: note, effects: {risk: 1}}
  note:
    text: Your password is written on the sticky note.
    next: [{if: "risk >= 1", goto: leak}, {goto: safe}]
  safe:
    text: The "technician" hangs up.
    ending: good
    debriefing: Checking through another channel breaks the trick.
  leak:
    text: Three days later your account sends 400 emails to customers.
    variants: [{if: "risk >= 4", text: "And the sticky note was still on the monitor."}]
    ending: bad
    debriefing: Urgency is the usual lever of social engineering.
:::
```

| Key | Value |
|---|---|
| `id` | unique in the course: lower case, digits and `_` (no `-`); the content reads its state as `id.variable` |
| `title` | title shown to the learner |
| `skin` | optional: `mail-desktop`, `mail-web`, `chat-workspace`, `messenger`, `phone`, `browser` |
| `screen` | with a `skin`, what the application shows (each scene may add its own `screen`); keys per skin below |
| `character` | `conversation` only, required: the person the learner talks to |
| `objective` | `U1.2` or a list: the objectives it practises (every objective of the unit, in decision-based courses) |
| `scored`, `weight` | counts for the grade (default `false`), and its weight among the scored ones (default 1) |
| `pass_requires` | scored only: the condition every passing path meets (the key behaviour, e.g. `"reported"`); verify fails otherwise and warns when a good ending fails or a bad one passes |
| `state` | variables and their initial value (numbers, `true`, `false`) |
| `start` | first scene (default: the first one) |
| `scenes.<id>` | `skin` (optional: the scene happens in another application, e.g. from the chat to the email; it shows only its own `screen`; a scene with `background` happens in that place instead of on the screen), `text` (required), `background`, `layers` (`image`, `area`, `if`), `characters` (`name`, `expression`, `position`: `left`, `right` or `center`), `variants` (`if`, `text`: extra text when the condition holds), `checkpoint`, and **one** way out: `choices`, `hotspots`, `next` or `ending` |
| choice / hotspot | `text` (choice) or `label` + `area` `[x, y]` or `[x, y, w, h]` in % (hotspot); `goto`; optional `if`, `effects` (adds to variables), `set` (gives them a value), `score` (points, `+` or `-`), `feedback` |
| hotspot `target` | instead of `area`, a part of the screen of the skin (keys per skin below) |
| `next` | moves on without a decision: list of `{if, goto}`, the first that holds |
| `ending` | `good`, `mixed` or `bad`, with its `debriefing` (required) |

- **Quote the texts** that hold `#` (a YAML comment after a space: the rest of the text is lost), `: ` or a comma inside
  `{…}`; `coursekit verify` fails on a `#` without quotes.
- **Conditions** use code syntax, the same in every language: `risk >= 3 && !called || trust < 2`; numbers, `true`, `false`,
  `+`, `-`, `==`, `!=`, `<`, `<=`, `>`, `>=`, `!`, `&&`, `||` and parentheses. Quote them in YAML.
- **Points:** each decision adds or subtracts `score`; the grade of a scored simulation is the points of the path over the
  maximum reachable, which `coursekit verify` computes. A scored simulation needs some path that earns points.
- **Consequences:** a decision changes the state; later scenes show it with `variants`, `layers` with `if`, conditional
  choices and `next`. Make the bad consequence appear later, as in real life, and give paths to recover.
- **Realism:** every option is something a real person would do; none is obviously right; the feedback explains, it does not
  preach. The debriefing says what happened, what an expert would have done and why.
- `background` and `layers.image` describe the image (one image per description in the whole course: repeat the same
  text to reuse it); portraits come from the cast of the story bible with the `expression` of each scene. They are not
  media placeholders.
- `coursekit verify` walks every path: unknown scenes, unreachable scenes, dead ends (a state with no option left), endings
  without debriefing, undeclared variables, ids repeated in the course.

### Skins

The application is drawn in HTML with real text; it recalls the everyday ones but never write their brand names. `body` and
`text` are Markdown.

| Skin | `screen` | `target` |
|---|---|---|
| `mail-desktop`, `mail-web` | `app`, `account`, `folder`, `inbox` (list: `from`, `subject`, `preview`, `time`, `unread`), `message` (`from`, `address`, `to`, `subject`, `time`, `body`, `attachments`) | `sender`, `address`, `subject`, `attachment:N`, `link:N`, `inbox:N` |
| `chat-workspace` | `app`, `team`, `channel`, `channels`, `messages` (list: `from`, `time`, `text`, `me`) | `message:N`, `link:N` |
| `messenger` | `contact`, `status`, `messages` | `message:N`, `link:N` |
| `phone` | `caller`, `number`, `state` (`incoming`, `call`, `sms`), `time`, `messages` | `caller`, `number`, `message:N`, `link:N` |
| `browser` | `url`, `title`, `secure`, `body` | `url`, `lock`, `link:N` |

In the chat skins (`chat-workspace`, `messenger`, `phone`) the `messages` of each scene add up along the path: each scene
writes only its new messages. Use a skin whenever the situation happens on a screen (an email, a chat, a call, a web page): spotting the signal in a
realistic screen (`hotspots` with `target`) is the decision. Addresses and domains are invented (`.example`).

### Adaptive blocks

Content after a simulation may change with what the learner decided:

```markdown
:::if call.risk >= 3
You gave your password to the "technician". Let us see which levers he used.
:::else
You did not fall for it, but many people do. Let us see why.
:::
```

`:::else` is required (it is the version for everyone else and the one creator shows). The condition reads variables of
simulations that come before (`id.variable`). The branches may hold any content and directives; the words of the
`:::else` branch count.

## 3. Question directives (practice activities and tests)

The directives with `role: question`: `single-choice`, `multi-select`, `true-false`, `sorting`,
`match`, `sorting-groups`, `fill-in-the-blank`, `order-words`, `short-answer`.

```markdown
:::single-choice
{{t_question_key}} U1.2
{{k_question}}: <question>
- [ ] <distractor>
- [x] <correct answer>
- [ ] <distractor>
{{k_feedback_correct}}: <why it is right>
{{k_feedback_incorrect}}: <which section to review>
:::
```

- `single-choice` (exactly one `- [x]`) and `multi-select`: options `- [x]` / `- [ ]`.
- `match`: lines `- term :: definition`. `sorting`: list in the right order. `order-words`:
  `- full sentence` per sentence. `sorting-groups`: `#### Category` + list of items.
  `true-false`: `{{k_answer}}: {{w_true}}|{{w_false}}`. `fill-in-the-blank`: blanks in `{{k_question}}:` as
  `{{{k_answer}}}` (several accepted: `{a/b}`). `short-answer`: `{{k_answers}}: a | b | c`.
- Common keys: `{{t_question_key}}`, `{{k_question}}:`, `{{k_feedback_correct}}:`, `{{k_feedback_incorrect}}:`,
  `{{k_feedback}}:`. Each key on one line. Every question carries `{{t_question_key}}` and feedback.

## 4. Media placeholders

Exact format (shown as a visible box until the asset is produced):

```markdown
> **[{{t_placeholder}} — <type>]**
{{placeholder_field_lines}}
```

Allowed types (what is written in the placeholder, and its id in the configuration): {{placeholder_types}}. Per unit: {{placeholders_per_hour}} placeholders per hour
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
questionnaire. The learner sees the instructions, the simulations (wherever they are in the activity) and the question
bank, as written; the other subsections are for people. An activity made only of a scored simulation leaves its bank
empty, and it is graded by itself when the simulation ends (no submit button).
