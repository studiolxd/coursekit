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
2. Read the brand material of the client (`brief/index.md`, `brief/notes.md`) for colours, fonts and logos.

## 2. The theme in the platform (creator backend)

With the html backend (`coursekit status` says it) there is no platform theme: the theme is the stylesheet of the project. Write
or adapt `theme/maqueta.css` with the brand in the CSS variables of the base layout (`--color-accent`, `--color-text`,
`--color-background`, `--font-family`, `--radius`… the list is the `:root` of the base layout; `coursekit theme import` explains
what it understood), run `coursekit theme import theme/maqueta.css` and go to step 4; the build uses that stylesheet and the
tokens. Never edit `tokens.json` by hand.

For the creator backend:

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
3. If a pair fails the contrast, fix the colour in the platform (`update_theme`) and import again. Never edit the
   tokens by hand.

## 4. Link and tell the person

- Content that already exists: `set_content_theme` with the theme id (`coursekit theme show --course <CODE>`). Contents
  created later get it in the assembly.
- Summarise: the theme chosen, its id and version, the colours and fonts that resulted, what is derived and not in
  the platform (soft text, surfaces, radii, spacing), the notes (dark mode: the tokens are the light mode) and
  the contrast result. The person validates the theme as they validate the design.
- Do not commit unless asked.
