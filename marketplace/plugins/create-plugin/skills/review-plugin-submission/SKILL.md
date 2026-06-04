---
name: review-plugin-submission
description: Audit a Kodik plugin for marketplace readiness. Use when validating manifests, component metadata, discovery paths, and submission quality before publishing.
---

# Review plugin submission

## Trigger

A plugin is implemented and needs a final quality check before submission or release.

## Workflow

1. Verify manifest validity:
   - `.kodik-plugin/plugin.json` exists
   - `id` is valid lowercase kebab-case and matches the folder name
   - manifest uses only the flat v1 fields: `schemaVersion`, `id`, `version`, `title`, `description`, `category`, `icon`, `author`, `homepageUrl`, `sourceUrl`, `tags`, `prompts`, `userConfig`
   - no import-only fields such as `originalAuthor`, `sourceMarketplace`, `keywords`, `repository`, `license`, or `interface`
2. Verify component discoverability:
   - Skills in `skills/*/SKILL.md`
	   - Rules in `rules/*.md`
	   - Agents in `agents/` markdown files
	   - Commands in `commands/*.md`
   - Hooks in `hooks/hooks.json`
   - MCP config in root `.mcp.json` with a top-level `servers` object
3. Verify component metadata:
   - Skills include `name` and `description` frontmatter
   - Rules include valid frontmatter and clear guidance
   - Agents and commands include `name` and `description`
4. Verify repository integration:
   - For marketplace repos, plugin entry exists in `.kodik-plugin/marketplace.json`
   - `source` resolves to plugin directory and names are unique
5. Verify documentation quality:
   - `homepageUrl` and `sourceUrl` point to useful destinations
   - `icon` is `./assets/app-icon.svg`, SVG-only, and contains no embedded raster image data

## Checklist

- Manifest exists and parses as valid JSON
- Manifest uses the exact flat v1 field set
- No broken file references
- No missing frontmatter on skills/rules/agents/commands
- Plugin scope is clear and focused
- Marketplace registration complete (if multi-plugin repo)

## Output

- Pass/fail report by section
- Prioritized fix list
- Final submission recommendation
