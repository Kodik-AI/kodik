---
description: Keep Kodik plugin manifests, paths, and component metadata valid during plugin authoring.
alwaysApply: true
---

# Plugin quality gates

When creating or editing Kodik plugins:

1. Ensure `.kodik-plugin/plugin.json` exists and uses the canonical flat manifest shape.
2. Keep component files in the conventional root directories: `skills/`, `agents/`, `commands/`, `rules/`, `hooks/`, and `.mcp.json`.
3. Do not add manifest component path overrides or removed aliases such as `name`, `interface`, `logo`, `composerIcon`, `keywords`, `repository`, or `license`.
4. Include YAML frontmatter for rules, skills, agents, and commands with required metadata.
5. Keep plugin scope focused and document installation and usage in `README.md`.
6. Save new local plugins to `~/Documents/Kodik/Plugins/<plugin-name>/` by default so they are immediately available to Kodik. Only use a different location when the user explicitly requests it.
