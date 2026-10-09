---
name: delivery
description: Delivery of a course — snapshot and SCORM export of each unit from slxd creator by MCP (create_export), download, check, record in course.yaml and publication in the mirror folder. Use with /deliver or to export the packages of courses/<CODE>.
---

# SCORM delivery

Export settings: `coursekit config delivery`. Each unit is one creator content and one package.

{{> _slxd-tools}}

## With the html backend

The packages are built by coursekit, not exported by a platform: for each unit `coursekit assemble build <CODE> --unit N
--version X.Y` (it writes `delivery/<name>.zip`), then `coursekit delivery add <CODE> --unit N --version X.Y --file
courses/<CODE>/delivery/<name> ` with no `--job` or `--snapshot`. Everything else (requirements, gate, publication, summary) is the
same; `coursekit status <CODE>` says which backend the course uses.

## Requirements (stop if one is missing)

- Every unit assembled: `course.yaml › units[].content_id` set.
- `coursekit delivery check <CODE>` passes. It refuses while the course is on hold and, when the project
  requires the client's review (`coursekit config delivery`), until the client has approved it
  (`coursekit client <CODE> approve`) or the person has skipped it with a reason. Never run
  `coursekit client` or `coursekit hold`: they record decisions of people. Tell the person what is missing.
- Version: the one the person says; otherwise `1.0` the first time and the next minor version
  (`1.1`, `1.2`…) afterwards, according to `course.yaml › deliveries`.

## For each unit

1. `create_snapshot` of the content named `v<version>` (keep its id).
2. `create_export` with `contentId` and the values of `delivery › export` (`deliveryType`,
   `standard`, `reporting`, `scoreSource`). Keep `jobId` and `downloadUrl`.
3. `get_export_status` until `COMPLETE` (wait between calls; if `FAILED`, stop and show
   `errorMessage`).
4. File name: `coursekit delivery name <CODE> --unit N --version X.Y`. Download the
   `downloadUrl` to `courses/<CODE>/delivery/<that name>` (e.g. with `curl -fL -o`).
5. `coursekit delivery add <CODE> --unit N --version X.Y --file courses/<CODE>/delivery/<name> --job <jobId> --snapshot <id>`.
   It checks the zip has `imsmanifest.xml` at its root and records it; with a mirror folder configured it
   also copies the package there (never deleted) and updates the catalog.

## At the end

Summarise: version, packages, size, standard and course status. Recommend testing at least
one unit in the target LMS before closing it.

Do not commit unless asked (zip files are not versioned; `course.yaml` is).
