---
description: Sync the directive registry of the project with the slxd creator brick catalog (list_brick_types).
---

Update the directive registry with the current creator catalog.

1. Call `list_brick_types` (slxd MCP) and save the JSON as it is in `.cache/list_brick_types.json`.
2. Run `coursekit directives check .cache/list_brick_types.json`.
3. If it says `ok`, update only `synced_with_creator` with today's date in
   `config/directives.yaml` (create it with that key if missing) and finish.
4. For each `NEW`: call `get_brick_type_schema` of the type and decide whether it should be a
   directive.
   - If so: add it to `directives` in `config/directives.yaml` with a kebab-case name, `brick`,
     `role` (`interactive`, `question` or `static`) and `use` in {{ui_language_name}}.
   - If not: add it to `not_directives` with the reason.
5. For each `REMOVED`: remove it from the registry. If it was a directive, find its uses in
   `courses/*/content/**/*.md` and list the affected files (do not change them).
6. Update `synced_with_creator`, run step 2 again until it says `ok` and summarise the changes.
   Do not commit.
