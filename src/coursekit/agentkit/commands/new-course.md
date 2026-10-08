---
description: Create a course from its title and hours and build the instructional design proposal in slxd for human review.
argument-hint: "\"<title>\" <hours> [--code ABC101] [--no-intro] [--no-summary] [indications]"
---

Create a new course and its instructional design **proposal**. Arguments from the person:

$ARGUMENTS

1. Separate the title (in quotes), the hours, the options `--code`, `--no-intro`, `--no-summary`
   and the rest as free indications. If the title or the hours are missing, ask for them and stop.
2. Run `coursekit new "<title>" <hours> [options] --notes "<indications>"`.
3. Run `coursekit brief <CODE>` and read `brief/index.md` and `brief/notes.md`. If there is no
   material, say so in the final summary: the person can drop files in `brief/sources/` or URLs
   in `brief/links.md` and ask for `/design-change`.
4. Load the `instructional-design` skill and follow its **Proposal** section.
5. Publish for review: `coursekit publish <CODE>`.
6. Finish with a short summary for the person, in {{ui_language_name}}: units with hours and
   objectives, decisions and assumptions to check, where the Excel is, and how to go on: changes
   with `/design-change <CODE> <changes>` and sign-off with `/approve-design <CODE>`.

Do not sign anything and do not commit.
