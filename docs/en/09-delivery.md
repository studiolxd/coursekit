# Delivery and publishing

How the SCORM packages of an assembled course are exported, recorded, published to the shared folder and tracked in the catalog. How the course is assembled is in [Assembly](08-assembly.md).

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

The exact texts are in [Troubleshooting](11-troubleshooting.md#the-course-is-on-hold-or-the-clients-review-blocks-the-delivery).

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

With the creator backend, the agent calls the creator export tool with the `export` values, waits for the job to finish and downloads the package. With the html backend only `export.standard` and `file_name` are used: the standard decides the manifest and the tracking of the package, and `reporting` and `scoreSource` do not apply (see [SCORM tracking](08-assembly.md#scorm-tracking)).

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

`delivery add` checks that the file is a valid zip with `imsmanifest.xml` at its root, that it is directly inside `courses/PWD/delivery/` and that the unit exists. It then appends an entry to `course.yaml › deliveries` with `version`, `unit`, `date`, `by` (the signing identity of `.env`), `standard`, `file`, `sha256`, `export_job` and `snapshot` (empty for an html package). When every unit has a package of the same version **and the course is in `assembly` or `client_review`**, the course status becomes `delivered` and a history entry is added. In any other status the package is recorded with the warning above and the course status does not change. While some unit has no package of the version, it prints `recorded <file> · pending units for v<version>: [2, 3]`. `courses/*/delivery/` is in the project `.gitignore`: the zips are not versioned, `course.yaml` is. When the unit still has visual resources that go in as [provisional images](07-media.md#provisional-images), it warns and names them; the package is recorded all the same.

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

- The catalog of the project (`courses/course-catalog.xlsx`) is refreshed, silently, and only written when its data changed since the last time (the rows of each course are cached in `.cache/catalog/`, so a refresh reads only the course that changed, however many courses the project has).
- Without a mirror (`mirror.provider: none`, or no `MIRROR_DIR`) nothing else happens and nothing is printed.
- If the mirror cannot be updated (the folder does not exist, the Excel is open), the command prints a warning on the error output and keeps its own exit code: its work is done and `coursekit publish` tries again.
- In a session of an agent without an interface (the handoff, `--headless`) the commands the agent runs do not publish (`COURSEKIT_MIRROR=deferred`): whoever started the session publishes once when it ends, and the handoff after each step. In a session you open yourself everything works as above.

What `publish` does:

- For each course it copies `course.yaml`, `design/`, `content/` and `reviews/` into `<MIRROR_DIR>/courses/PWD/`, only the files whose content changed. `brief/`, `media/` and `assembly/` are not mirrored.
- Files it published before that no longer exist in the course are removed from the mirror (tracked in `courses/PWD/.published.json`, inside the mirror), together with the folders left empty. Files it never published are not touched.
- `delivery/` is append-only: a package is copied once and never overwritten or deleted in the mirror, even if it is removed locally. A new version has a new file name.
- It writes the catalog to `<MIRROR_DIR>/<catalog file>`, with links to the course folders. If the Excel is open, it fails with `cannot replace … (is it open in Excel?)`.
- It first refreshes the catalog in `courses/` and prints `wrote <path> (N courses, M units)` (not with `--only-if-configured`). Then it prints one line per course that changed (`published PWD: 5 copied, 0 removed, 0 unchanged`) and one for the catalog of the mirror. With `mirror.provider: none` it prints the first line and says there is nothing to publish (exit code 0). With a provider and no `MIRROR_DIR`, it fails with `no mirror folder configured (project.yaml › mirror and MIRROR_DIR in .env)`.

## The tracking catalog

`coursekit catalog` builds the tracking Excel from every `courses/*/course.yaml`. It is generated: never edit it (changes go in each `course.yaml`). It is written next to the courses, in `courses/` (`--output PATH` to change it; git ignores it), and, by `publish`, to the mirror folder. The copy in `courses/` is refreshed by the same commands that publish, with or without a mirror, and has no folder links. The file name and every label follow the project's `ui_language`: `course-catalog.xlsx` in English, `catalogo-cursos.xlsx` in Spanish. The header colour is the `accent-ink` (else `accent`) token of `theme/tokens.json`, or dark grey; the `Courses` and `Units` sheets have a frozen header and filters. `coursekit catalog` alone leaves the **Folder** column empty: the links are written by `publish`.

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
# preview: coursekit preview PWD (with a simulated LMS), or open courses/PWD/assembly/html/unit-01/index.html in the browser
coursekit assemble build PWD --unit 1 --version 1.0
# package PWD-U01-v1.0-scorm12.zip (212.4 KB)
# (try the zip in the target LMS or SCORM Cloud, and host it for the client if there is a review)
coursekit client PWD send --to "ACME training team" --where https://lms.acme.example.com/courses/pwd
coursekit client PWD approve --by "ACME training lead"
coursekit delivery add PWD --unit 1 --version 1.0 --file courses/PWD/delivery/PWD-U01-v1.0-scorm12.zip
# recorded PWD-U01-v1.0-scorm12.zip · course delivered
```

Next: [Client review](10-client-review.md)
