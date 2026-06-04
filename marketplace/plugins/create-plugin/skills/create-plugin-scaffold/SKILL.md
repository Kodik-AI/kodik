---
name: create-plugin-scaffold
description: Create a new Kodik plugin scaffold with a valid flat manifest, component directories, and marketplace wiring. Use when starting a new plugin or adding a plugin to a multi-plugin repository.
---

# Create plugin scaffold

## Trigger

You need to create a new Kodik plugin from scratch and make it ready for local use or marketplace submission.

## Required Inputs

- Plugin name (lowercase kebab-case)
- Plugin purpose and target users
- Component set to include (`rules`, `skills`, `agents`, `commands`, `hooks`, `MCP servers`)
- Repository style (`single-plugin` or `multi-plugin marketplace`)

## Output Location

By default, create the plugin inside the user's local plugin directory:

```
~/Documents/Kodik/Plugins/<plugin-name>/
```

This path makes the plugin immediately available to Kodik without any install step. If the user explicitly asks to create the plugin elsewhere (e.g. inside an existing repo or a specific directory), respect that choice instead.

## Workflow

1. Validate plugin name format: lowercase kebab-case, starts and ends with an alphanumeric character.
2. Determine the target directory:
   - Default: `~/Documents/Kodik/Plugins/<plugin-name>/`
   - Override: use the path the user specifies, if any.
   - Create the directory (and parents) if it does not exist.
3. Create base files inside the target directory:
   - `.kodik-plugin/plugin.json`
   - `assets/app-icon.svg`
   - only the component directories the plugin actually uses
4. Populate `plugin.json`:
   - Required flat fields: `schemaVersion`, `id`, `version`, `title`, `description`, `category`, `icon`, `author`, `homepageUrl`, `sourceUrl`, `tags`, `prompts`, `userConfig`
   - Use `author: { "name": "Kodik" }`
   - Use `icon: "./assets/app-icon.svg"`
   - Do not add component path fields; use the standard directories.
5. Create component files with valid frontmatter:
	   - Rules: `rules/*.md` with clear markdown guidance
	   - Skills: `skills/<skill-name>/SKILL.md` with `name`, `description`
	   - Agents: `agents/*.md` with `name`, `description`
	   - Commands: `commands/*.md` with `name`, `description`
6. If repository uses `.kodik-plugin/marketplace.json`, add plugin entry:
   - `name`
   - `source`
7. Ensure all runtime files live under the conventional plugin directories.

## Guardrails

- Keep the plugin focused on one use case.
- Prefer concise, actionable skill and rule text over long prose.
- Do not reference files that do not exist.
- Use folder discovery defaults; do not add custom component paths to the manifest.
- Always save to `~/Documents/Kodik/Plugins/<plugin-name>/` unless the user provides a different path.

## Output

- Created file tree for the plugin (with full path to the output directory)
- Final `plugin.json`
- Marketplace entry (if applicable)
- Short validation report of required fields and component metadata
- Confirmation that the plugin is saved under `~/Documents/Kodik/Plugins/` and ready for use
