# Figma Plugin

This plugin packages Figma-driven design-to-code workflows in
`plugins/figma`.

It currently includes these skills:

- `figma-implement-design`
- `figma-code-connect`
- `figma-create-design-system-rules`
- `figma-create-new-file`
- `figma-generate-design`
- `figma-generate-library`
- `figma-use`

## What It Covers

- translating Figma frames and components into production-ready UI code
- inspecting design context and screenshots through the connected Figma tools
- creating parserless Code Connect template files for published Figma components
- generating project-specific design system rules for Figma-to-code workflows
- creating or updating full screens and design system libraries in Figma
- creating new Figma or FigJam files when needed for a workflow

## Plugin Structure

The plugin now lives at:

- `plugins/figma/`

with this shape:

- `.kodik-plugin/plugin.json`
  - required plugin manifest
  - defines plugin metadata and points Codex at the plugin contents

- `.app.json`
  - plugin-local app dependency manifest
  - points Codex at the connected Figma integration used by the bundled skills

- `agents/`
  - plugin-level agent metadata
  - currently includes `agents/openai.yaml` for the OpenAI surface

- `skills/`
  - the actual skill payload
  - each skill keeps the normal skill structure (`SKILL.md`, optional
    `agents/`, `references/`, `assets/`, `scripts/`)

- `assets/`
  - plugin-level icons referenced by the manifest

- `commands/`, `hooks.json`, `scripts/`, and `ui/`
  - example convention directories kept alongside the imported workflow bundle

## Connecting Figma

The plugin connects to Figma's desktop MCP server at
`http://127.0.0.1:3845/mcp`. It needs the Figma desktop app (macOS or Windows)
and a Dev or Full seat on a paid plan. To turn it on, open a Design file in the
desktop app, switch to Dev Mode (Shift+D), and in the MCP server section of the
right sidebar click Enable desktop MCP server.

The desktop server covers reading designs (`get_design_context`,
`get_screenshot`, `get_metadata`, Code Connect, variables). Writing to the
canvas (`use_figma`, `create_new_file`) is only on Figma's remote server
`https://mcp.figma.com/mcp`, which admits only clients in the Figma MCP
catalog. Kodik will switch to it once it is listed there.

## Notes

This plugin is app-backed through `.app.json` and uses the connected Figma
integration for the bundled skills. The workflows assume that the Figma tools
are available and that the user can supply Figma URLs with node IDs when
needed.

The current skill set is focused on these workflows:

- implementing designs from Figma with high visual fidelity
- creating parserless Code Connect templates for published Figma components
- generating durable project rules for future Figma-to-code work
- creating or updating Figma files, screens, and design system libraries

Use of the Figma skills and related files is governed by the Figma Developer
Terms. See `LICENSE.txt` and the per-skill license files for details.

This public repo keeps the bundled skills plus the example command, hook, and UI
scaffolding alongside the app-backed plugin wiring.
