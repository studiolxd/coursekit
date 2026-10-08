## Calling the slxd tools

The MCP server `{{mcp_name}}` lists only its main tools directly. **If a tool named in this skill
is not in your list** (e.g. `design_matrix_competencia_create`, `design_matrix_export`,
`create_snapshot`, `share_content`, `update_quiz_settings`), do not assume it does not exist:
1. `find_tools` with keywords (e.g. `"design_matrix objective"`) to get its exact name;
2. `tool_schema` with that name to see its arguments;
3. `run_tool` with `name` and `arguments`.
Direct tools are called as usual. Destructive tools (`confirm: true`) are confirmed with the
person first.
