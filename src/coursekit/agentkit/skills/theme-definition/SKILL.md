---
name: theme-definition
description: Theme of a project or of a course in slxd creator and the design tokens derived from it for the media (tokens.json, tokens.css). Use with /define-theme, or when media needs tokens that do not exist.
---

# Theme and design tokens

The graphics, simulations and videos of a course use the colours and fonts of its theme, so they look like the
course. The theme lives in the platform (creator); coursekit derives the tokens from it and records where they
come from. One theme per project, which every course inherits; a course can have its own.

{{> _slxd-tools}}

## 1. Where are we

1. `coursekit theme show` (project) or `coursekit theme show --course <CODE>`. If the tokens already come from a
   platform theme, say which and ask whether to redo them; do not change them unprompted.
2. The brand material: run `coursekit brand` (the project's) or `coursekit brand <CODE>` (a course with a brand of its own).
   It converts what the person left in `theme/branding/` (`sources/`: brand book, token files, fonts, logos; `links.md`: a
   Storybook or brand website read whole, the npm page of the package of the design system, and websites whose style is
   observed in a browser; `notes.md`: their indications)
   and writes `theme/branding/index.md`. Read the index, then `notes.md`, then the material: every page of brand and
   foundations whole (colours, typography, iconography, data graphics, motion, shape, logo), the index of the components
   whole, and whole the components that resources draw like (cards, charts, icons, alerts, tags, buttons); search the rest
   with `coursekit brief --find`. What was observed on a website is a clue, never a rule: when it contradicts the brand
   material, the brand wins. Also `brief/index.md` and `brief/notes.md`. If the index lists fonts without files, ask the
   person for them (with their licence) instead of using others. If the brand says its icons, fonts or logos are published in
   a package (npm) and the index has none, ask the person to add the page of that package on npm to `links.md` and run
   `coursekit brand` again.
3. The choice made when the project was created is `project.yaml › theme › source` (creator backend): `tenant_default` (the
   default theme of the organization) or `branding` (a theme made from `theme/branding/`). Follow it; ask only when you can ask.

## 2. The theme in the platform (creator backend)

With the html backend (`coursekit status` says it) there is no platform theme: the theme is the stylesheet of the project. Write
or adapt `theme/maqueta.css` with the brand (from `theme/branding/`) in the CSS variables of the base layout (`--color-accent`, `--color-text`,
`--color-background`, `--font-family`, `--radius`… the list is the `:root` of the base layout; `coursekit theme import` explains
what it understood), run `coursekit theme import theme/maqueta.css` and go to step 4; the build uses that stylesheet and the
tokens. If there is no brand material at all and the person has no stylesheet, write nothing and run
`coursekit theme import` without a file: the tokens are those of the base layout. Never edit `tokens.json` by hand.

For the creator backend:

- `source: tenant_default`: `list_themes`, take the theme with `isDefault`, and go to step 3 with it. Do not create or
  change themes (the system default is read-only); new contents get it by themselves. In a session with a person, say
  which theme it is before importing it.
- `source: branding`: make the theme from `theme/branding/` as in the list below. If that folder has no material, use
  the default theme as above and say so in your summary.

Otherwise, or when the person asks for something else:

1. `list_themes`: show the library to the person.
2. Choose with them: an existing theme; a new one (`create_theme` from nothing, from a preset
   (`list_theme_presets`) or as a copy of the project's with `fromThemeId`); or, for a course that needs a look of
   its own, a copy of the project theme to adapt. A theme change in the platform changes every content that uses
   it: to change one course, copy its theme and link the copy.
3. Adapt it with `update_theme` using the colours and fonts of the brand (read the theme and its `version` first with
   `get_theme`; `get_theme_schema` describes each field). Report the `warnings` of the result. Font files are uploaded
   with `request_asset_upload`; text and accent colours must contrast (4.5:1 for text).

## 3. Derive the tokens

1. `get_theme` of the chosen theme: save the whole result to `.cache/theme/get_theme.json`.
2. `coursekit theme import .cache/theme/get_theme.json` (project) or add `--course <CODE>` (own theme of the
   course; it also records `slxd.theme_id` in `course.yaml`). It writes `tokens.json` (with its origin) and
   `tokens.css`, prints the notes and the contrast of each pair.
3. If a pair fails the contrast, fix the colour in the platform (`update_theme`) and import again, unless the theme is
   read-only or the brand says the platform theme is not to be touched: then explain the failure and how the brand already
   handles it (a colour used only as a fill, for example) and let the person decide. Never edit the tokens by hand.

## 4. The brand in the media

The tokens come from the platform theme; some roles the platform does not have are derived by coursekit (mixed from other
colours, `origin.derived`), and the radius and the shadow are its defaults. The media must follow the brand, so compare:

1. `coursekit theme roles` (or `--course <CODE>`): each colour role, its value, where it comes from and **where it is seen**;
   the palette of the theme with its names. For each role derived by coursekit, and for the radius and the shadow, look for
   the colour or the value the brand gives for that use.
2. Propose, never decide alone, what differs. Each proposal or question says, in {{ui_language_name}}, the role, its
   value now, where it is seen (the text of `coursekit theme roles`, as it is), the colour of the brand you propose with
   its name in the palette, and the place of the brand material you read it from (file and section). One example:
   «`surface` es `#F5F6F7`, calculado por coursekit. Se ve en el fondo de las tarjetas de una comparación en un vídeo y en
   la banda de fondo de una escena. La marca tiene el gris `grey-lightest` `#F2F2F2` para las superficies secundarias
   (Foundations › Colores, neutrales). ¿Lo uso?». When the brand has no answer, say so and ask.
3. Write each answer of the person in `theme/branding/notes.md` (a course with its own brand: its `notes.md`), one line per
   decision, in their words: it is the source the guide cites for it (`[notes.md]`), and the next time the guide is written
   nobody asks again. Never cite «agreed» or a conversation: what is not in a file is not a source.
4. What the person accepts goes in `project.yaml › theme` (a course with its own tokens: `course.yaml › theme`): `roles`
   (a role → the name of a colour of the palette, or another role; a hex only when the brand defines it and the palette of
   the theme lacks it), `radius` (px), `shadow` (`none`, or a CSS shadow), `border` (px) and `weights` (`normal`, `strong`).
   Every colour role can be fixed, also one that comes from the platform when the brand says otherwise (the text on a fill
   of state, for example): say so, because the course in the platform keeps the platform's. Then import the tokens again (step 3): they
   come out with those values, recorded as fixed by the project. The platform theme is not touched.
5. The style of the videos: propose in `config/video.yaml` what the brand says of shapes and weights (`shapes`: radius,
   shadow, border; `weights`: the normal and the strong weight), of the background of the scenes (`background`: `plain`,
   `band` or `shape`, soft shapes of the accent, a tint a brand without tints does not admit) and of the motion (`motion`:
   its character and its timings, from the durations and curves of the brand), and what the brand does not allow of the scenes
   (`scenes`: `"*": {allow: {align: [left]}}` for a brand without centred texts, `"*"` also for a rule about every scene that
   has a prop, such as the place of the titles, so the scenes added later follow it; `allow` and `defaults` for one scene,
   `<name>: false` for a scene it does not use; `coursekit video catalog` lists the props and their values), and the
   typography of each role of the text (`text`: `display`, `heading`, `kicker`, `body`, `quote`, `statement`, `stat`, `step`…
   with the family of one of the fonts of the brand, the size, the weight, the case, the tracking and the colour of a role of
   the theme, from the type scale of the brand); the fonts reach the videos by themselves from
   `theme/branding/fonts/fonts.css`. A logo in the videos only if the brand or the person asks for it.
   The case and the tracking of a role come from what the components of the brand do, never from the name or the comment of
   a token: a token meant for uppercase labels that no component uses says nothing about the brand. The defaults of the
   package (`config/video.example.yaml`) are not the brand: read them, and set every value the brand contradicts (a kicker in
   uppercase when the brand writes nothing in uppercase: `transform: none` and its tracking). How the brand marks what is
   active in its navigation (a menu, tabs, the steps of a process: a bar, a fill, a line, only the weight; the rest stepping
   back or not) becomes the defaults of the `chapter` scene (`mark`, `emphasis`, `others`, `done`).
6. Write `theme/branding/media-style.md` (a course with its own brand: `courses/<CODE>/theme/branding/media-style.md`), in the
   language of the courses, with these sections and only what the brand material says, each rule followed by its source
   (file and section) in brackets:
   - what the guide is for, and that in the resources it wins over the tokens when they differ;
   - the material of the folder (foundations, tokens, fonts, icons, logos) and where each one is;
   - colour: a table with each colour of the brand (name, hex, use), which ones are fills and which can be ink, what the
     colours of state are for; no colour outside the brand;
   - data graphics: the palettes and the order of their colours, how many series, how the rest is grouped;
   - typography: the families, their weights and what each one is for, and that the files are in `fonts/`;
   - shape: corners, borders, shadows;
   - icons: which set and where its files are (`icons/`, when the brand brings them), its rules measured on those files
     (grid, stroke, joins, live area), and how to draw a missing one with the same criteria;
   - motion: durations and curves, reduced motion;
   - videos: what the brand and `notes.md` say of the videos made as a montage: the background of the scenes, the shapes and
     the weights, the character of the motion (each with the value of `config/video.yaml` it becomes), how the text enters
     and stays on screen, and the scenes to prefer or to avoid; the gallery (`coursekit video gallery`) shows them drawn;
   - images and illustration: what the brand and `notes.md` say of photography and of each kind of illustration (a concept
     illustration that goes with the content, a scene with characters, a diagram): its style, its palette, when the accent
     may appear, and its sources (the illustration sources of `links.md`, with the previews of `style/`; the reference scenes of `style/scenes/`);
   - logo: when it is used and when not;
   - what never appears;
   - the indications of `notes.md`: a table with **every** line of `notes.md`, copied exactly as it is, and the section of
     the guide where it is applied (or why it does not apply to the media). Before you finish, check the table against the
     file line by line: an indication that is not in the guide is lost for the media. `coursekit approve media-style` and
     `coursekit media plan` warn of the lines the guide does not quote.
   A rule you infer and the brand does not state is not written as a rule: it goes as a question. The person's
   `notes.md` weighs more than the rest.
7. **Job aids** (the checklists and quick guides the learner downloads as a PDF): every one comes out of one template,
   `theme/templates/job-aid.html` (a course with its own brand: `courses/<CODE>/theme/templates/`). Without one, coursekit uses
   its own, neutral, with the tokens and the fonts of the brand. When the brand has printed or downloadable material (a
   letterhead, a document template, a one-pager), copy the template of coursekit (`coursekit theme sample` says which one is in
   use) and adapt it to the brand: header, hierarchy of headings, checkboxes, tables, a highlight, the margins. Keep its
   values in double braces (`title`, `content`, `page`, `tokens_css`…) and the semantic HTML (headings, lists, tables: the PDF is tagged for screen readers from them). Then
   `coursekit theme sample` (or `--course <CODE>`) prints `theme/branding/samples/job-aid.pdf` with sample text: tell the
   person to open it, change what they ask and print it again. The page is `media › job_aid` (`page`, `orientation`). Add to
   the guide a section on the job aids (what the template does and why, with its sources). The template is signed with the
   guide: changing it asks for a new signature.
8. Tell the person to look at the gallery of the videos (`coursekit video gallery`, the project's; with `<CODE>`, a course's),
   and at the sample of the job aids, to read the guide and to sign it: the guide of the project once for every course that uses it
   (`coursekit approve media-style`), the own guide of a course with its code (`coursekit approve media-style <CODE>`). No
   visual resource is produced until it is signed, and it is signed again when it changes. You never sign it.

In a session with no one to ask (`--headless`, the handoff): apply only what has one clear answer in the brand (a colour of
the palette named for that same use, a rule stated in so many words), leave everything else as it is, write the guide, and
list in `theme/branding/brand-report.md` each difference found, what you applied (with its source) and each question you
could not ask. The handoff signs the guide itself.

## 5. Link and tell the person

- Content that already exists: `set_content_theme` with the theme id (`coursekit theme show --course <CODE>`). Contents
  created later get it in the assembly.
- Summarise: the theme chosen, its id and version, the colours and fonts that resulted, what is derived by coursekit,
  what is fixed by the project and from which colour of the brand, the notes (dark mode: the tokens are the light mode),
  the contrast result, the guide written and what is pending (questions, fonts without files, the signature of the guide).
  Say which values come from the platform and which do not, never mixing them.
- Do not commit unless asked.
