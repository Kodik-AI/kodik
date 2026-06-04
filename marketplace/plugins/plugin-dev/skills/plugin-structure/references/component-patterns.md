# Component Organization Patterns

Kodik plugin components are discovered by fixed directory conventions. Keep the manifest flat and organize files in the standard locations instead of adding custom path fields.

## Discovery Lifecycle

When Kodik loads enabled plugins:

1. Read `.kodik-plugin/plugin.json`.
2. Discover components from conventional root paths.
3. Parse frontmatter and configuration files.
4. Register components for the next Kodik session.
5. Load MCP server definitions from `.mcp.json` when present.

Supported component paths:

- `skills/<skill-name>/SKILL.md`
- `agents/*.md`
- `commands/*.md`
- `rules/*.md`
- `hooks/hooks.json`
- `.mcp.json`

## Commands

Commands are top-level markdown files in `commands/`.

```
commands/
├── build.md
├── test.md
├── deploy.md
└── review.md
```

For large command sets, keep files top-level and use filename prefixes:

```
commands/
├── ci-build.md
├── ci-test.md
├── ci-deploy.md
├── monitoring-status.md
└── monitoring-logs.md
```

Do not place command markdown under nested folders; nested command files are not discovered.

## Agents

Runnable plugin agents are top-level markdown files in `agents/`.

```
agents/
├── code-reviewer.md
├── test-generator.md
└── release-manager.md
```

Do not place runnable agents in nested folders. Skill-local `agents/openai.yaml` files are skill metadata, not plugin subagents.

## Skills

Each skill is a direct child directory under `skills/` and must contain `SKILL.md`.

```
skills/
├── code-review/
│   ├── SKILL.md
│   └── references/
│       └── checklist.md
└── release-planning/
    ├── SKILL.md
    └── examples/
        └── plan.md
```

Skills may contain supporting `references/`, `examples/`, `scripts/`, or `assets/` folders when the skill instructions reference them.

## Rules

Root plugin rules are markdown files in `rules/`.

```
rules/
├── no-inline-imports.md
└── typescript-exhaustive-switch.md
```

Kodik also discovers skill-local `rules/` directories, such as `skills/react-best-practices/rules/*.md`.

## Hooks

Plugin hooks live in one file:

```
hooks/
└── hooks.json
```

Hook scripts can live under `hooks/scripts/` or `scripts/`. Reference them with `${KODIK_PLUGIN_ROOT}`.

## MCP Servers

MCP configuration lives at the plugin root:

```
.mcp.json
```

Use the top-level `servers` key and optional `meta` entries. Do not use `mcpServers`.

## Assets

Marketplace icon:

```
assets/app-icon.svg
```

Keep plugin-level `assets/` limited to the marketplace icon unless a runtime file references additional assets. Skill-local assets belong under the relevant skill directory.

## Organization Guidance

- Start with the smallest component set that solves the plugin goal.
- Prefer skill directories for rich behavior and references.
- Prefer top-level command and agent files with clear prefixes over nested command or agent directories.
- Keep helper scripts under `scripts/` or the relevant skill directory.
- Keep `plugin.json` metadata-only; do not use it to declare component paths.
