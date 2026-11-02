# Changelog

[Español](CHANGELOG.es.md)

What changes in each version of coursekit, newest first. What is solid, what is still to prove and what is not done is in the
status of the [README](README.md#status). Versions are published on PyPI as `slxd-coursekit`.

## Unreleased

## 0.9.0 — 2026-11-02

- More visual courses. The writing decides what the learner sees by the kind of content (a capture for each step on a real screen, a photo of the situation, an illustration of an idea, an icon, an infographic for a comparison), and `verify` warns, never fails, of a long section with too few visuals, of a unit without a photograph or capture and of a unit whose visuals are almost all infographics and diagrams (`content.visual_per_words`, `photos_per_unit`, `visual_mix_max`). The AI review adds the placeholders that are missing instead of only proposing them.
- A visual resource still to produce (a capture waiting for a person, a recording, an image with no generator) is never left out of the course: it goes in as a provisional image in the theme, with its title and what is missing, in both backends (`coursekit media provisional` and `media set --provisional-path` for creator). `delivery add` warns of the units delivered with them.
- Licensed photographs in every project, also without creator: `coursekit media stock CODE ID --photos` searches Pexels (new key `PEXELS_API_KEY`, no credit needed) and the photographs of Magnific, those that ask for no credit first; a photograph that asks for one gets it in its caption.
- The icon set of the project: `coursekit brand` indexes the icons of the design system (`icons/index.json` and a contact sheet), `/define-theme` designs the ones the brand lacks, the icons the media agent draws join the set, and `coursekit media icons CODE --find` searches it. An icon the set lacks may start from the shape of a free icon (`--base`, Lucide), always redrawn with the rules of the brand. The generic icon catalogue of creator is no longer a source.
- `coursekit media stock` searches the whole catalogue of illustrations when the brand names no illustration sources.
- Media in their place: a placeholder inside a panel of an accordion, tabs or a carousel becomes the medium of that panel (a capture for each step of a procedure), an image placeholder with `Layout: beside the text` goes beside its paragraph, and images written one after the other go together as a grid or a carousel of images, in creator and in the html backend. `verify` fails on a placeholder that would be lost inside another directive. The numbering of the placeholders of a section now counts those inside panels, as the manifest does.
- `coursekit capture plan CODE`: which resources wait for a capture of a real application and what is missing to make them (capture on, the permission, the session of a profile), with the commands; `status` and the handoff remind it in time. A capture session takes the captures of other resources on the same walk (`save_shot` with their `asset_id`).
- The visual plan of the design (`design/visuals.yaml`): what the learner sees in each section, decided by the design agent and signed with the design; `sync` shows it in the skeleton and `verify` warns when a section carries less than its plan. The design Excel has a sheet with the visual plan.
- Videos of official channels: `coursekit videos find CODE "<what>"` searches the official channels of the project (`rules › videos › channels`; with `YOUTUBE_API_KEY`, the YouTube API, else the search provider of `research`), and a line `> **[Video]** <address> <caption>` becomes a player in both backends (the privacy-enhanced YouTube player in html, with the address under it) instead of a link.
- Icons in the text, from the icon set of the project: a `:::note` with `kind: tip|warning|info|example` (or `icon:`) carries the icon of its kind, and a panel of an accordion, tabs or a carousel with `icon: <name>` carries it above its text, in creator and in html. `media extract` takes each icon from the set as an asset `ICON-<name>`, uploaded to every unit that shows it.
- An `Icon` atom for the videos (an icon of the set of the project painted in a colour of the theme), and `marker: icon` in the `list` and `split` scenes (and the `BulletList` molecule), each item with its icon.
- `coursekit media report CODE`: how much of each unit is seen (sections with a visual produced, visuals by type produced, pending and planned); `media plan` and the report of the handoff sum it up.
- The import of eXeLearning keeps the images of a gallery in their order, one per paragraph, without the links to the files inside the package that broke in the course.
- A stage of a capture is refused on Windows with a clear message (its commands run in bash); it was failing with an obscure error.

## 0.8.0 — 2026-11-02

- The review asks for a procedure as a carousel, one slide per step, as the writing does (it still asked for numbered steps), and in an imported course the writer uses `research` only to check a fact or find the reference documentation.
- The documentation of assembly and delivery is split in three chapters: [Assembly](docs/en/08-assembly.md), [Delivery and publishing](docs/en/09-delivery.md) and [Client review](docs/en/10-client-review.md); troubleshooting is now chapter 11.
- `verify` names the family of each finding (`structure`, `words`, `style`, `language`, `readability`, `media`, `activities`, `simulations`, `assembly`), takes `--only` and `--ignore` to see some of them (a partial check never changes the status), sums up the errors and warnings of each unit when it checks several, and prints JSON with `--json`. `status`, `doctor` and `media check` print JSON with `--json` too, for the agents.
- `coursekit help COMMAND`: the options of a command and its part of the reference of the commands, in the language of the person.
- Every command starts faster: a command loads only the modules it uses (`coursekit --version` takes about half the time), and the output of ffmpeg, git and the other programs is read as UTF-8 also in a console of Windows.
- MarkItDown, which converts the documents of the brief and of the brand material, moves to the optional extra `docs`: the base installation goes from 48 packages to 7, about 250 MB less. Without it, `brief` still reads Markdown, text, eXeLearning packages and web links. **To keep converting PDF, Word or PowerPoint files after upgrading:** `uv tool install --force "slxd-coursekit[docs]"` (with `capture` too, name both: `[docs,capture]`).
- Every message that asks for an extra gives the command with the extras already installed, because reinstalling with one removes the others. `doctor` asks for `docs` only when there are documents to convert, and warns when more than one OpenCV package is installed.
- `coursekit config --check`: the keys of `config/*.yaml`, `project.yaml` and each `course.yaml` that coursekit does not read (misspelt, or of an older version), each with the key it probably meant.
- coursekit runs on Python 3.12 to 3.14, the `capture` extra included: its OCR is now `rapidocr` 3 (it carries its models and reads a name split in several boxes as one line) and its OpenCV the headless one, which on Linux needs no graphics library.
- The options of the questions are shuffled for each learner, in the practice and in the tests (`delivery › shuffle_options`, per project, course and question with `shuffle: yes|no`), in creator, the html backend and Moodle XML. The question bank says how to turn on shuffling in the LMS, since it cannot carry the order itself.
- `verify` fails on a feedback that names an option by its position or letter, and the writing asks every feedback to say why. It also warns of an objective quoted by its id in the text the learner reads, of a list with titles that goes as tabs or an accordion, of numbered steps that go as a carousel, of a flashcard back too long for a card, and of a resource type that cannot be decorative.
- The plan of creator sends the fields of one line (the options of a question, the titles of panels) without inline code, links or line breaks, so it is applied as it is; `assemble plan` and `verify` warn of each field changed.
- `coursekit media gallery CODE`: one page with every resource of a course, where it goes and how it was made; with `--serve` it stays up to date while the media are produced.
- A labelled graphic shows its image once, and its image is a light base, not an infographic.
- A browser session with a stage serves the site of the stage locally, with no profile and no server to start by hand.
- Terminal capture with wide characters, a capture server that does not crash, and a handoff that stops with its whole summary.
- `coursekit media redo --recapture`: a resource that shows a real interface forgets its capture and is recorded again; the old recordings are set aside so they are not used again.
- `handoff.media_tools` accepts `"*"`: the media agent can run any program, and what is always denied stays denied.

## 0.7.0 — 2026-10-19

- Visual support of the sections: an introduction and a summary always carry an image, an illustration, an icon or an infographic; a content section carries one or says why not, and `verify` checks it. New resource types `illustration` and `icon`.
- Terminal mode: the waits of the program are sped up (never cut), chapters mark where a terminal demo stops, a recording can have several parts (a terminal and a browser), and the captures the handoff approved are reviewed on one page.
- The zooms of a screen recording are only for details, framed by the box of the element and with a mark that can be read.
- The help of `coursekit media` no longer fails on a `%` in its texts.
- The tests pass on Windows, and CI checks the types of the videos.

## 0.6.0 — 2026-10-19

- Pedagogical criteria in the writing. Every content section of an expository course follows a cycle (`rules › expository.cycle`: a problem of the work of the audience, activation of what they know, a worked example, practice with less help each time, integration in their work; a project or a course can leave out any part), which the introduction and the summary of the unit share. The writing follows rules of cognitive load, `verify` warns of long runs of prose (`content.chunk_max_words`) and the review has a criterion of pedagogy.
- Job aids (`job_aid`): a checklist or a quick guide the learner downloads as a PDF, written by the writer in its placeholder and printed with a template of the theme (`theme/templates/job-aid.html`, signed with the style guide of the media; `coursekit theme sample` prints a sample to adjust it), tagged for screen readers, and assembled as a download in both backends.
- Crosshairs on the images with points (`coursekit media anchors`): where each point of a labelled graphic and each hotspot of a simulation goes, drawn on the image from the content so that the reviewer sees it and can ask to move it; `verify` fails when they no longer match.
- Capture permissions of the project, extendable per course, with several modes. The handoff signs the scripts of what can be captured, records again after assembly, and for a delivered course says how to record what the permission allows.
- Terminal mode: a shell of its own in a stage of the course that the media agent prepares (a project with invented data, mounted from scratch before each take), recorded as it goes into a `.cast`, a video or a capture, with its output covered in the text.
- `/define-theme` completes what is missing in a theme already defined.
- Portraits shared between units in creator.
- The output of coursekit is always UTF-8, also in the cp1252 console of Windows.

## 0.5.0 — 2026-10-18

- Lessons of a whole pilot course. Each course keeps a record of what people decided and of the interface labels they checked (`decisions.md`), which writing and review respect, and the reviewer checks every pending item against the current state before repeating it.
- `verify` warns of an activity not written with the directive of its type, of a test question that repeats a practice situation and of a simulation error with no consequence; the writing rules cover sorting questions with one order, feedback and the current interface only.
- The media manifest is locked while it is written (agents in parallel), `media render` retries the browser, `brief` converts linked PDFs, the style guide of the media quotes every line of `notes.md` (and `approve media-style` warns of those left out), speakers can go without a portrait or with a brand avatar, and several scripts are signed at once.

## 0.4.0 — 2026-10-18

- Videos as data (`coursekit video`): a montage of scenes in the theme of the course, from a library of atoms, molecules and scenes that the project and each course extend, each scene lasting what its voice lasts. Scenes and layers are configurable and follow the brand of the project (`config/video.yaml`); `coursekit video gallery` paints them all with the theme and style of the course, and `coursekit video export` writes the timeline for DaVinci Resolve, Final Cut or Premiere.
- Checks of the audios and videos produced (`coursekit media check`: loudness, captions too fast to read, what is on screen and not said), their accessible transcript and track of descriptions (`coursekit media transcript`), a contact sheet to look at a video without playing it (`coursekit media sheet`), and zooms of a screen recording that follow the narration (the `Screencast` component).
- The Gemini TTS voice (provider `gemini`, with a style instruction and the model fixed in each course), at half the price: in the `flex` tier by default, or in batch for a whole course (`coursekit tts-batch`: queued with `--batch`, collected hours later, by the handoff too). The long scripts of Azure, Google and Gemini are joined as uncompressed audio and encoded once. The voice of the project is inherited by the courses that do not fix their own.
- The brand in the media. `coursekit brand` reads the brand material left in `theme/branding/` (a brand book, a Storybook read whole, the website of the company observed in a browser) and takes out its fonts, logos and tokens; the theme agent writes from it the style guide of the media, which a person signs once for every course of the project (`coursekit approve media-style`), and proposes the colour of the brand for each role the platform lacks (`project.yaml › theme.roles`, `coursekit theme roles`). The fonts of the brand go inside the videos and the SVGs exported as PNG.
- Illustration sources of the brand. The Magnific page of an author whose illustrations fit the brand goes in `theme/branding/links.md`; `coursekit brand` keeps previews of their work as style references, and `coursekit media stock` finds among their illustrations the one a concept needs, takes it as SVG and recolours it to the ink and paper of the brand (`media › stock`), with its origin and licence in the manifest. Decorative images come from the catalogue first; the necessary ones are generated.
- Where the tests go (`delivery › assessment`): inside each unit, or apart in one package of their own after the units (`placement: separate`); and their questions as lessons of the packages or as a question bank the LMS imports (`format: aiken | gift | moodle-xml | qti`: with the creator backend creator exports it from a content of its own, with html `coursekit delivery questions` writes it), with `verify` refusing the question types the format cannot take. Units without assessment can be graded by completion.
- Inclusive language (`rules › inclusive_language`: `none`, `neutral` by default, `split`, `slash`): the design, the writing and the review follow it, and `verify` warns about the generic masculine and the slashes with a lexicon per language.
- The same review Excel for a design made in slxd as for a local one (`coursekit design CODE` writes it from `matrix.json` and `validation.json`): competencies, objectives with where they are developed, practised and assessed, hours and minimum words per section, grading of the tests, common errors, and the validation with the expected warnings apart. The Excel slxd exports is kept as a copy, in the language of the person.
- Official sources through a web search API (`coursekit research`: Exa, Perplexity, Brave or Tavily, chosen in the `.env`). The design looks for the reference documentation with it and the writer for the source of a fact the brief does not have; it only proposes addresses, in the language of the course when the site has a translation, and they enter the course through `brief/links.md`. `coursekit brief` opens in the browser of the machine the official pages that refuse a direct download.
- Captures of real applications (`coursekit capture`): profiles of the web applications and the permission to capture, given only by a person; covering the personal data of a recording a person provides (`capture redact`, `review`, `approve`, `reject`: OCR, reviewed and approved by a person); an agent driving a web application in the browser with the personal data replaced on screen (`capture serve`, an MCP server); its video recorded by repeating the steps at a human pace (`capture replay`); the course itself (its html package served locally or its review link in creator, with no login); and a window of a desktop program, covered on the pixels, on macOS, Windows and Linux with X11.
- The script of a recording or of a video is approved before it is made, and a proposed official video holds its resource.
- The galleries carry the interface of Studio LXD and speak the language of the person. MCP connectors of the project, the npm package of the brand and the language of the conversation are set per project.

## 0.3.0 — 2026-10-16

- Migrating an existing course from eXeLearning packages: a reader and a converter (`coursekit import`), a migration mode that reuses the text, `/update-unit` with an optional check that the content is current, and a handoff that stops where a person must decide.
- Videos of official channels on sites that forbid downloading them (`coursekit videos`).
- Optimisation of images and video, configurable, with `coursekit media optimize` and in the html backend.
- The interface of a real application is never invented: `--depicts`, recipes of real material and a recording script.
- `coursekit media redo --clean`: the resource forgets its file, alternative text, transcript, captions and tool.
- A cheaper catalogue and mirror folder: a cache per course, written only when it changes, and publishing postponed during agent sessions.

## 0.2.1 — 2026-10-15

- `/new-course` asks the approach of the course when `--approach` is not given.

## 0.2.0 — 2026-10-14

- The decision-based approach: the approach of the course and its rules, a narrative bible in the design, simulations (`:::scenario`, `:::conversation`) with application skins, scenes in other applications, portraits and voices per character, audio per scene, mechanics (diagnosis, investigation, inbox and assignment), strict timing and adaptive blocks (`:::if`); games and project skins in the html backend; `coursekit paths` reports the paths of a simulation.
- Simulations in creator through the `slxd-embed` protocol: a simulation that opens a section holds the lesson until its end, and reports its state, score and decisions.
- Local instructional design, with no slxd and no creator.
- `coursekit preview`: the html units with a simulated LMS; `assemble check` plays the html package in a browser before it is delivered.
- Common errors: the design collects them, the content shows them and `verify` checks them.
- Readability and reflection checks, a correction report in the handoff and search in the reference material.
- `coursekit media fit` and `render`: size and SVG locally, with no credits. Model, resolution and versions per media recipe.

## 0.1.4 — 2026-10-11

- A house style for the resources.

## 0.1.3 — 2026-10-11

- coursekit says when a newer version is published.

## 0.1.2 — 2026-10-10

- Publishing to PyPI no longer depends on a variable of the repository.

## 0.1.1 — 2026-10-10

- The tests no longer depend on `claude` being installed.

## 0.1.0 — 2026-10-10

First published version.

- Projects: `coursekit init` and `init --update`, the root of the project and configuration in layers; projects follow the installed coursekit by themselves.
- The course engine: `new`, `status`, `sync`, `outline`, `verify`, `reviewed`, `approve`, `brief`, `rules`.
- Agents: skills, commands and agents for Claude Code, opencode and Codex (`coursekit agents`), and `write`, `review` and `run` to launch the agent of each role.
- `coursekit setup` and `doctor`.
- Media: `coursekit media`, `voice`, `tts` and `subtitles`, with headless media agents limited to the programs of their recipes.
- Assembly in creator (`coursekit assemble`, `directives check`) and the html backend, which builds a SCORM package per unit.
- Delivery: download of the package, record of the closing, catalogue, `publish` and the shared folder with its tracking spreadsheet.
- Client review, the choice of theme when a project is created, and the grading of each test from the design.
- The handoff mode: a pause for the reference material, signed agent logs, review links after uploading, and `--new-version` to reopen a delivered course.
