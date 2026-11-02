# Client review

Optional: the client reviews the assembled course and comments before it is delivered. Whether it is mandatory is a setting, `client_review.required` in the delivery configuration (default `false`; per project in `config/delivery.yaml`, per course in `course.yaml › delivery › client_review`: see [04-configuration.md](04-configuration.md#delivery-scorm-export-and-client-review)). The process and its statuses are in [02-workflow.md](02-workflow.md#client-review-optional).

With the html backend there are no platform links to create or record: the person hosts the package (the zip in a test LMS, or the preview folder on a web server) and gives the link when the round is opened: `coursekit client PWD send --where URL`. The rounds, `changes`, `approve` and `skip` work as described below; to apply the client's comments, edit the `.md`, run `coursekit verify` and build again (`coursekit assemble build`), then host the new package.

## The links of each unit

This subsection is about the creator backend. At the end of `/assemble` the assembly agent creates, for each unit (each is its own creator content), two links and records them with `coursekit assemble link`:

| Link | Creator tool | For whom |
|---|---|---|
| Live preview (`links.preview`) | `share_content` (enabled, with live updates) | The team. It shows the content as it is, with no comments |
| Review (`links.review`) | `enable_review` (no password unless you ask for one) | The client. It publishes version `v1` of the review and lets the client comment without an account. `get_review` reads it again |

```bash
coursekit assemble link PWD --unit 1 --preview https://acme.example.com/p/abc --review https://acme.example.com/r/xyz
# unit 1 -> preview https://acme.example.com/p/abc; review link https://acme.example.com/r/xyz
```

## Rounds

A round is the cycle "send to the client, the client answers". Only a person runs `coursekit client`; agents are denied it.

```bash
coursekit client PWD send --to "ACME training team"     # round 1: the course goes to client_review
```

`send` needs the course in `assembly`, no round open and the review links of the units recorded (or one link given with `--where URL`, which replaces them). It records in `course.yaml › client_review` the round number, who sent it and when, `--to`, and the links. Send those links to the client yourself.

While the client comments, the assembly agent handles the comments with `/client-feedback PWD` (or `/client-feedback PWD 2` for one unit). It uses the `client-review` skill and these creator tools:

| Step | Creator tool |
|---|---|
| Read the state and the pending threads | `get_review`, `list_review_comments` (status `pending`; `since` to read only what is new). Each thread says the lesson, the text and, if any, a screenshot |
| Apply what was agreed | edits the `.md` (never creator), `coursekit verify`, then `assemble plan`, `diff` and apply as in [the assembly flow](08-assembly.md#the-assembly-flow) |
| Publish what changed | `publish_review_version` with a label (`v1.1`, `v1.2`...). Only the latest version accepts comments |
| Answer | `reply_review_comment` on each thread, then `set_review_comment_status` with `resolved`. `verified` is the client's to set |

Before changing anything the agent shows a table with each comment, the section it refers to and what it proposes (apply, do not apply and why, or needs you), and waits for your decision; without an interface it applies only clear text corrections that fit the design. A comment that changes objectives, hours, activities or structure is a design change (`/design-change`), not a content edit. A unit edited after its signature goes back to `verified` and needs a new AI review and signature.

Then you close the round:

| Command | When |
|---|---|
| `coursekit client PWD changes --note "..."` | The client wants changes. The round closes (outcome `changes`) and the course goes back to `assembly`. Apply, reassemble and run `send` again: that is round 2 |
| `coursekit client PWD approve --by "Name" --note "..."` | The client agrees. The round closes (outcome `approved`) with the client's name and date, and the course can be delivered |
| `coursekit client PWD skip --reason "..."` | You deliver without the client's approval. It records a round with outcome `skipped` and the reason; it needs the course in `assembly` or `client_review` with no open round |

When you close a round, the agent can export the comments of the round with `export_review_comments`: it returns a CSV through a signed link that is valid for 24 hours, and the file is saved as `.cache/client-review/PWD-round-N.csv`, which git ignores and `coursekit publish` never copies. The CSV contains the e-mail addresses of the guests who commented: do not paste it anywhere nor move it into the course.

`coursekit status PWD` shows the last round and its outcome (`open`, `asked for changes`, `approved` or `skipped`), and the next step for `client_review` is to record the client's answer.

Next: [Troubleshooting](11-troubleshooting.md)
