# Minimal Plugin Example

A bare-bones plugin with a single command.

## Directory Structure

```
hello-world/
├── .kodik-plugin/
│   └── plugin.json
├── assets/
│   └── app-icon.svg
└── commands/
    └── hello.md
```

## File Contents

### .kodik-plugin/plugin.json

```json
{
  "schemaVersion": 1,
  "id": "hello-world",
  "version": "1.0.0",
  "title": "Hello World",
  "description": "Adds a simple greeting command for testing plugin installation.",
  "category": "utilities",
  "icon": "./assets/app-icon.svg",
  "author": {
    "name": "Kodik"
  },
  "homepageUrl": "https://github.com/Kodik-AI/kodik/tree/main/marketplace/plugins/hello-world",
  "sourceUrl": "https://github.com/Kodik-AI/kodik/tree/main/marketplace/plugins/hello-world",
  "tags": ["example"],
  "prompts": [],
  "userConfig": {}
}
```

### commands/hello.md

```markdown
---
name: hello
description: Prints a friendly greeting message
---

# Hello Command

Print a friendly greeting to the user.

## Implementation

Output the following message to the user:

> Hello! This is a simple command from the hello-world plugin.
>
> Use this as a starting point for building more complex plugins.

Include the current timestamp in the greeting to show the command executed successfully.
```

## Usage

After installing the plugin:

```
$ kodik
> /hello
Hello! This is a simple command from the hello-world plugin.

Use this as a starting point for building more complex plugins.

Executed at: 2025-01-15 14:30:22 UTC
```

## Key Points

1. **Canonical manifest**: Uses the same flat fields as every marketplace plugin
2. **Single command**: One markdown file in `commands/` directory
3. **Auto-discovery**: Kodik finds the command automatically
4. **No dependencies**: No scripts, hooks, or external resources

## When to Use This Pattern

- Quick prototypes
- Single-purpose utilities
- Learning plugin development
- Internal team tools with one specific function

## Extending This Plugin

To add more functionality:

1. **Add commands**: Create more `.md` files in `commands/`
2. **Add metadata**: Update `plugin.json` fields without adding removed aliases
3. **Add agents**: Create `agents/` directory with agent definitions
4. **Add hooks**: Create `hooks/hooks.json` for event handling
