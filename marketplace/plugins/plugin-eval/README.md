# Plugin Eval

`plugin-eval` is both:

- a local Node.js CLI
- a Codex plugin bundle

It helps engineers evaluate a local skill or plugin, understand why it scored that way, see what to fix first, explain token budgets, measure real usage, and decide what to do next without having to memorize a command sequence first.

## What This Plugin Contains

- `scripts/plugin-eval.js`: the CLI entrypoint exposed as `plugin-eval`
- `.kodik-plugin/plugin.json`: the Codex plugin manifest
- `skills/`: the plugin's chat-facing skills

The plugin is designed to feel chat-first in Codex, while still routing to explicit local commands you can run yourself.

## Source

This directory packages the public [`thisdot/plugin-eval`](https://github.com/thisdot/plugin-eval) project for this plugin monorepo.

## Install As A CLI Tool

### Requirements

- Node.js `>=20`

This package is currently marked `"private": true`, so the expected install path is from a local checkout rather than the public npm registry.

### Run It Without Installing Globally

From the plugin root (`plugins/plugin-eval` in this monorepo):

```bash
node ./scripts/plugin-eval.js --help
```

You can use that form for every command in this README.

Examples:

```bash
node ./scripts/plugin-eval.js analyze ./skills/plugin-eval --format markdown
node ./scripts/plugin-eval.js analyze . --format markdown
```

### Install A Global `plugin-eval` Command

From the plugin root (`plugins/plugin-eval` in this monorepo):

```bash
npm link
```

After that, `plugin-eval` should be available on your `PATH`:

```bash
plugin-eval --help
plugin-eval analyze ./skills/plugin-eval --format markdown
```

If you prefer not to create a global link, keep using `node ./scripts/plugin-eval.js ...` directly.

## CLI Usage

### Start From Chat

`start` is the chat-first router:

```bash
plugin-eval start <path> --request "<chat request>" --format markdown
```

Examples:

```bash
plugin-eval start ~/.codex/skills/game-dev --request "Evaluate this skill." --format markdown
plugin-eval start ~/.codex/skills/game-dev --request "Why did this score that way?" --format markdown
plugin-eval start ~/.codex/skills/game-dev --request "What should I fix first?" --format markdown
plugin-eval start ~/.codex/skills/game-dev --request "Measure the real token usage of this skill." --format markdown
plugin-eval start . --request "Help me benchmark this plugin." --format markdown
```

`plugin-eval start` keeps the workflow chat-first:

- it recognizes the beginner request
- it explains why that workflow fits
- it shows the first local command that will run
- it lists the full local sequence when there are multiple steps
- it highlights one recommended next step for skimming engineers

### Core Commands

```bash
plugin-eval analyze <path> --format markdown
plugin-eval explain-budget <path> --format markdown
plugin-eval measurement-plan <path> --format markdown
plugin-eval init-benchmark <path>
plugin-eval benchmark <path> --format markdown
plugin-eval report <result.json> --format markdown
plugin-eval compare <before.json> <after.json> --format markdown
```

Compatibility aliases still work:

- `plugin-eval guide` -> `plugin-eval start`
- `plugin-eval recommend-measures` -> `plugin-eval measurement-plan`

### Recommended Workflow

1. Start with `plugin-eval start <path> --request "<natural request>" --format markdown`.
2. Run `analyze` when you want the static local report.
3. Run `explain-budget` before live measurement if cost is the concern.
4. Run `init-benchmark`, review and edit the config, then run `benchmark` when you want a live Codex CLI benchmark.
5. Feed observed usage back into `analyze` or `measurement-plan`.

### Local-First Behavior

- `analyze`, `explain-budget`, and `measurement-plan` are deterministic local workflows.
- `benchmark` runs real `codex exec` sessions in isolated temp workspaces.
- Benchmark runs preserve rich artifacts under `.plugin-eval/runs/` and write observed usage when telemetry is available.

## Safety And Execution Notes

- `analyze`, `explain-budget`, and `measurement-plan` inspect local files and write local reports only.
- `init-benchmark` creates starter benchmark configuration under `.plugin-eval/` for the target you choose.
- `benchmark` runs a live local Codex CLI workflow in an isolated temp workspace and writes artifacts under `.plugin-eval/`.
- Review the generated benchmark configuration before running it, especially when the target project or prompts did not come from you.
- Keep generated `.plugin-eval/` artifacts and local `node_modules/` directories out of commits unless you explicitly want to version them.

## How It Works As A Codex Plugin

This directory is also a Codex plugin bundle. The plugin manifest lives at [`.kodik-plugin/plugin.json`](./.kodik-plugin/plugin.json), and it exposes the skills under [`skills/`](./skills).

That means you can use it from Codex chat with natural prompts once the plugin is installed, for example:

- `$plugin-eval Evaluate this skill.`
- `$plugin-eval Give me an analysis of the game dev skill.`
- `$plugin-eval Why did this score that way?`
- `$plugin-eval What should I fix first?`
- `$plugin-eval Help me benchmark this plugin.`

The plugin side is responsible for the chat UX and routing. The CLI side is responsible for the local commands and reports.

## Manual Plugin Installation

Kodik plugin discovery is marketplace-based. The plugin itself lives in a folder with `.kodik-plugin/plugin.json`, and Kodik discovers it through a marketplace manifest at `.kodik-plugin/marketplace.json`.

For a local marketplace checkout, keep catalog entries source-only:

```json
{
  "name": "local",
  "plugins": [
    {
      "name": "plugin-eval",
      "source": "./plugins/plugin-eval"
    }
  ]
}
```

The plugin metadata comes from `plugins/plugin-eval/.kodik-plugin/plugin.json`; do not duplicate title, description, author, category, tags, or version in the marketplace entry.

## Use Cases

Use `plugin-eval` when you want to:

- evaluate a local skill directory or `SKILL.md`
- evaluate a local plugin root that contains `.kodik-plugin/plugin.json`
- explain why a score came out the way it did
- rank what to fix first
- estimate budget before running live usage
- benchmark starter scenarios and compare before/after results

## References

- [Chat-first workflows](./references/chat-first-workflows.md)
- [Observed usage inputs](./references/observed-usage.md)
- [Technical design](./references/technical-design.md)
