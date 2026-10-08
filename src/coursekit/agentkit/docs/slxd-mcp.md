# slxd MCP (creator) — reference for coursekit

> Before using a tool, confirm its schema with `tool_schema` (or `get_brick_type_schema` for
> bricks): this page is a guide, not the contract.

## Connection

- The project server is **`{{mcp_name}}`** (`project.yaml › platform.slxd`), configured in
  `.mcp.json`, `opencode.json` and `.codex/config.toml` by `coursekit agents`. Each person
  authenticates with OAuth (slxd account) the first time.
- Streamable HTTP transport; **OAuth 2.1** or an `sk_…` key.
- An MCP credential always acts as **member**: owner/admin actions are not available.
- Destructive tools need `confirm: true`; without it they return a preview.
- **Direct tools** include `browse_workspace`, `get_content`, `get_lesson`, `create_content`,
  `update_content`, `create_lesson`, `update_lesson`, `reorder_lessons`, `delete_lesson`,
  `list_brick_types`, `get_brick_type_schema`, `add_brick`, `update_brick`, `move_brick`,
  `delete_brick`, `audit_content_accessibility`, `apply_accessibility_autofix`, `list_themes`,
  `get_theme`, `update_theme`, `request_asset_upload`, `search_stock_images`, `create_export`,
  `get_export_status` and `design_matrix_create/get/list/validate/generate_course`.
- **The rest** (other `design_matrix_*`, `design_matrix_export`, `create_snapshot`,
  `share_content`, `update_quiz_settings`, `set_content_theme`, `create_theme`,
  `import_stock_image`, `search_stock_icons`, `request_embed_upload`…) go through
  **`find_tools`** → **`tool_schema`** → **`run_tool`**.

## Tools by phase

| Phase | Tools |
|---|---|
| Theme | `list_themes`, `create_theme`, `get_theme`, `update_theme`, `set_content_theme` |
| Design | `design_matrix_*` (matrix, competencies, objectives, nodes, learning and assessment activities, validate, export) |
| Skeleton | `design_matrix_generate_course`, `design_matrix_redaccion_status` |
| Media | `request_asset_upload`, `request_embed_upload`, `search_stock_images`, `import_stock_image`, `search_stock_icons`, `import_stock_icon` |
| Assembly | lessons and bricks, `update_quiz_settings`, `set_lesson_bank_references`, accessibility audit, `create_snapshot` |
| Review | `share_content` (live preview) |
| Delivery | `create_export`, `get_export_status` |

Useful values:
- `design_matrix_create.patronEstructural`: `con_modulos | sin_modulos` (cannot be changed).
- `nivelBloom`: `recordar | comprender | aplicar | analizar | evaluar | crear`.
- Assessment `instrumento`: `cuestionario | caso_practico | entrega_portfolio | rubrica`.
- `create_export.standard`: `scorm_1_2 | scorm_2004`.
