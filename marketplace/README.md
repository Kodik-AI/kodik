# Kodik Plugins Marketplace

This directory is the source-of-truth for the **official** Kodik plugins marketplace. The Kodik IDE auto-registers it on first launch via `https://github.com/Kodik-AI/kodik` (subdir: `marketplace/`).

## Layout

```
marketplace/
  .kodik-plugin/marketplace.json   # catalog (this directory's manifest)
  plugins/                          # first-party plugins shipped in-repo
    <plugin-id>/
      .kodik-plugin/plugin.json
      skills/, agents/, hooks/, .mcp.json, …
```

## Adding a plugin

A plugin entry in `marketplace.json` describes how to fetch the plugin. Five source types are supported:

| Type | Shape | When to use |
|------|-------|-------------|
| Relative path (string) | `"./plugins/my-plugin"` | First-party plugin shipped in this repo (most common). |
| `local` | `{ "source": "local", "path": "./plugins/x" }` | Same as relative path, explicit form. |
| `github` | `{ "source": "github", "repo": "owner/repo", "ref": "v1.0.0", "sha": "..." }` | Plugin lives in another GitHub repo. |
| `url` | `{ "source": "url", "url": "https://gitlab.com/x.git", "ref": "main" }` | Plugin lives in a non-GitHub git repo. |
| `git-subdir` | `{ "source": "git-subdir", "url": "...", "path": "packages/x", "ref": "main" }` | Plugin lives in a subdir of an external repo (monorepo). |
| `npm` | `{ "source": "npm", "package": "@scope/x", "version": "1.0.0" }` | Plugin published to the npm registry. |

Relative paths and `local` sources are sandboxed: paths that escape the marketplace root (via `..` or symlinks) are rejected.

`ref` selects a git branch / tag; `sha` pins to an exact commit and overrides `ref`.

## Legacy

The `Kodik-AI/kodik-plugins` repo is deprecated. New installations register this marketplace directly; existing installations keep working until they sync.

## Local development

```bash
# Develop against a local marketplace without publishing:
kodik --plugin-dir ./marketplace/plugins/my-plugin
```
