# Plugin Manifest Reference

Complete reference for Kodik plugin manifests.

## File Location

Required path: `.kodik-plugin/plugin.json`

The manifest must live at the plugin root under `.kodik-plugin/`. Kodik discovers plugin components by convention from sibling paths such as `skills/`, `agents/`, `commands/`, `rules/`, `hooks/hooks.json`, root `.mcp.json`, and `assets/app-icon.svg`.

## Canonical Shape

Official marketplace plugins use one flat manifest shape:

```json
{
  "schemaVersion": 1,
  "id": "plugin-name",
  "version": "1.0.0",
  "title": "Plugin Name",
  "description": "Brief explanation of plugin purpose.",
  "category": "developer-tools",
  "icon": "./assets/app-icon.svg",
  "author": {
    "name": "Kodik"
  },
  "homepageUrl": "https://example.com/plugin",
  "sourceUrl": "https://github.com/Kodik-AI/kodik/tree/main/marketplace/plugins/plugin-name",
  "tags": ["automation"],
  "prompts": [],
  "userConfig": {}
}
```

Every key above is present in official marketplace manifests. Use `[]` for empty `tags` or `prompts`, and `{}` for empty `userConfig`.

## Fields

### schemaVersion

Type: number

Value: `1`

Identifies the manifest schema. Do not omit it for marketplace plugins.

### id

Type: string

Format: lower kebab-case, matching the plugin directory name.

Examples:

- `figma`
- `code-review`
- `build-web-apps`

Rules:

- Use lowercase letters, numbers, and hyphens.
- Do not use spaces, slashes, underscores, or leading/trailing hyphens.
- Keep the value stable across releases.

### version

Type: string

Use semantic versioning, for example `1.0.0`.

### title

Type: string

Human-readable marketplace title. This replaces the old `name`, `interface.displayName`, `logo`, and `composerIcon` conventions.

### description

Type: string

Short user-facing description shown in the marketplace and plugin details. Keep it concise and specific.

### category

Type: string

Allowed values:

- `coding`
- `developer-tools`
- `productivity`
- `design`
- `engineering`
- `research`
- `api-integrations`
- `utilities`

### icon

Type: string

Value: `./assets/app-icon.svg`

All marketplace plugins use the same vector icon path. The file must be SVG and must not embed raster images through `<image>` tags or `data:image/...` payloads.

### author

Type: object

Official marketplace plugins use:

```json
{
  "author": {
    "name": "Kodik"
  }
}
```

### homepageUrl

Type: string URL

User-facing page for docs, sign-in, product details, or the most useful landing page for the integration. If there is no better public page, use the plugin source page.

### sourceUrl

Type: string URL

Source location for the plugin, usually the plugin directory in the public Kodik marketplace repository.

### tags

Type: array of strings

Search and filtering labels. Keep tags short and lowercase where practical.

### prompts

Type: array of strings

Starter prompts shown in plugin UI. Use at most three short prompts in marketplace plugins.

### userConfig

Type: object

Optional user-provided configuration fields, keyed by config variable name. Values can be referenced from `.mcp.json` as `${user_config.<key>}`.

```json
{
  "userConfig": {
    "apiKey": {
      "type": "string",
      "title": "API key",
      "description": "Used to authenticate the plugin MCP server.",
      "required": true,
      "sensitive": true
    }
  }
}
```

Supported field types are `string`, `number`, and `boolean`.

## Component Discovery

Do not configure component paths in the manifest. Kodik uses these fixed locations:

- Skills: `skills/<skill-name>/SKILL.md`
- Agents: `agents/*.md`
- Commands: `commands/*.md`
- Rules: `rules/*.md`
- Hooks: `hooks/hooks.json`
- MCP servers: `.mcp.json`
- Icon: `assets/app-icon.svg`

Nested assets inside skill directories are allowed when the skill references them. Plugin-level marketplace assets should be limited to `assets/app-icon.svg`.

## MCP Configuration

MCP server definitions live in root `.mcp.json`, not in `plugin.json`.

Use the top-level `servers` key:

```json
{
  "servers": {
    "example": {
      "type": "stdio",
      "command": "node",
      "args": ["${KODIK_PLUGIN_ROOT}/server.js"]
    }
  },
  "meta": {
    "example": {
      "id": "example",
      "title": "Example",
      "description": "Example MCP server."
    }
  }
}
```

Do not use the legacy `mcpServers` key.

## Removed Fields

Do not add these fields to marketplace plugin manifests:

- `name`
- `interface`
- `logo`
- `composerIcon`
- `homepage`
- `repository`
- `license`
- `keywords`
- `originalAuthor`
- `sourceMarketplace`
- `skills`
- `agents`
- `commands`
- `rules`
- `hooks`
- `mcpServers`

If a plugin needs documentation or legal details, link to them through `homepageUrl` or `sourceUrl`.

## Validation Checklist

- `.kodik-plugin/plugin.json` exists and parses as JSON.
- Manifest keys match the canonical flat shape.
- `id` matches the plugin directory name.
- `icon` is exactly `./assets/app-icon.svg`.
- `assets/app-icon.svg` exists, is SVG, and does not embed raster data.
- `.mcp.json`, when present, uses `servers` and has matching `meta` entries.
- Component files live in conventional root directories.
