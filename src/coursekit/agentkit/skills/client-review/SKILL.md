---
name: client-review
description: Comments of the client on the review link of a course in slxd creator — read them, apply the agreed changes in the .md, reload, publish a new review version and answer each comment. Use with /client-feedback or when the client has commented.
---

# The client's review

The review of each unit is a link of its creator content (`course.yaml › units[].links.review`); the client
comments on it without an account. A round is opened and closed by the person with `coursekit client`.
The `.md` rules still apply: never edit content directly in creator; fix the `.md` and reload it.

{{> _slxd-tools}}

## 1. Read the comments

For each unit with a `content_id` and a review link:
1. `get_review`: enabled, latest version and how many threads are pending.
2. `list_review_comments` with `status: pending` (use `since` to read only what is new). Each thread says the
   lesson (`lessonTitle`), the text and, if any, a screenshot (`screenshotUrl`: open it).
3. Map each comment to the section or activity of the `.md` (`coursekit outline <CODE> --section …`).

## 2. Decide with the person

Show a table per unit: comment, section, what you propose (apply, do not apply and why, needs the person).
In an interactive session wait for the person's decision; without an interface, apply only the clear text
corrections that fit the design and leave the rest in the summary. Comments that change objectives, hours,
activities or the structure are a design change: do not apply them, point to `/design-change`.

## 3. Apply

1. Edit the `.md` with the `content-writing` rules (language, tone, no emojis) and run `coursekit verify <CODE>`.
2. A unit edited after its signature goes back to `verified`: tell the person it needs a new review and signature
   (`/review-unit`, `/approve-unit`) before the course is delivered.
3. Reload what changed: `coursekit assemble plan`, `diff` and apply as in the `creator-assembly` skill.

## 4. Answer

For each unit that changed:
1. `publish_review_version` with a label (`v1.1`, `v1.2`…): the client sees the update. Only the latest version
   accepts comments.
2. For each applied comment: `reply_review_comment` on the root of the thread, saying what changed (and for the
   ones you did not apply, why), then `set_review_comment_status` with `resolved`. `verified` is for the client.
3. When the person closes the round, `export_review_comments` and download the CSV (the link lasts 24 hours) to
   `.cache/client-review/<CODE>-round-N.csv` (outside git and never published); it has the e-mail addresses of guests: do not paste it anywhere nor move it into the course.

## 5. Summary

Comments read, applied, discarded and pending; units reloaded and the new review version of each; what the
person has to do next (`coursekit client <CODE> send` for another round, or `approve` when the client agrees).
Do not commit unless asked.
