import path from "node:path";

import { createArtifact, createCheck, createMetric } from "../core/schema.js";
import { evaluateSkill } from "./skill.js";
import { discoverPluginSkillDirectories } from "../core/target.js";
import { pathExists, readJson, readText, relativePath } from "../lib/files.js";

const REQUIRED_MANIFEST_FIELDS = [
  "schemaVersion",
  "id",
  "version",
  "title",
  "description",
  "category",
  "icon",
  "author",
  "homepageUrl",
  "sourceUrl",
  "tags",
  "prompts",
  "userConfig",
];

const ALLOWED_MANIFEST_FIELDS = new Set(REQUIRED_MANIFEST_FIELDS);
const ALLOWED_CATEGORIES = new Set([
  "coding",
  "developer-tools",
  "productivity",
  "design",
  "engineering",
  "research",
  "api-integrations",
  "utilities",
]);

const rasterIconPattern = /<image\b|data:image\/(?:png|jpe?g|webp|gif)/i;

function isHyphenCase(value) {
  return /^[a-z0-9-]+$/.test(value) && !value.startsWith("-") && !value.endsWith("-") && !value.includes("--");
}

function isPlainObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function pushCheck(checks, targetPath, input) {
  checks.push(createCheck({ targetPath, ...input }));
}

export async function evaluatePlugin(pluginRoot) {
  const manifestPath = path.join(pluginRoot, ".kodik-plugin", "plugin.json");
  const targetPath = relativePath(process.cwd(), pluginRoot);
  const checks = [];
  const metrics = [];
  const artifacts = [];

  if (!(await pathExists(manifestPath))) {
    pushCheck(checks, targetPath, {
      id: "plugin-manifest-missing",
      category: "manifest",
      severity: "error",
      status: "fail",
      message: "The plugin root is missing .kodik-plugin/plugin.json.",
      evidence: [targetPath],
      remediation: ["Add .kodik-plugin/plugin.json to the plugin root."],
    });
    return { checks, metrics, artifacts };
  }

  let manifest;
  try {
    manifest = await readJson(manifestPath);
  } catch (error) {
    pushCheck(checks, targetPath, {
      id: "plugin-manifest-invalid-json",
      category: "manifest",
      severity: "error",
      status: "fail",
      message: "plugin.json could not be parsed as JSON.",
      evidence: [error instanceof Error ? error.message : String(error)],
      remediation: ["Fix the JSON syntax in .kodik-plugin/plugin.json."],
    });
    return { checks, metrics, artifacts };
  }

  for (const field of REQUIRED_MANIFEST_FIELDS) {
    if (!(field in manifest)) {
      pushCheck(checks, targetPath, {
        id: `manifest-missing-${field}`,
        category: "manifest",
        severity: "error",
        status: "fail",
        message: `plugin.json is missing the required \`${field}\` field.`,
        evidence: [manifestPath],
        remediation: [`Add \`${field}\` to plugin.json.`],
      });
    }
  }

  for (const field of Object.keys(manifest)) {
    if (!ALLOWED_MANIFEST_FIELDS.has(field)) {
      pushCheck(checks, targetPath, {
        id: `manifest-extra-${field}`,
        category: "manifest",
        severity: "error",
        status: "fail",
        message: `plugin.json contains unsupported field \`${field}\`.`,
        evidence: [manifestPath],
        remediation: [`Remove \`${field}\`; official plugins use the flat v1 manifest schema only.`],
      });
    }
  }

  if (manifest.schemaVersion !== 1) {
    pushCheck(checks, targetPath, {
      id: "manifest-schema-version-invalid",
      category: "manifest",
      severity: "error",
      status: "fail",
      message: "plugin.json schemaVersion must be 1.",
      evidence: [`Current value: ${String(manifest.schemaVersion)}`],
      remediation: ["Set schemaVersion to 1."],
    });
  }

  if (!isNonEmptyString(manifest.id) || !isHyphenCase(manifest.id)) {
    pushCheck(checks, targetPath, {
      id: "manifest-id-not-hyphen-case",
      category: "manifest",
      severity: "error",
      status: "fail",
      message: "The plugin id should be lowercase hyphen-case.",
      evidence: [`Current id: ${String(manifest.id)}`],
      remediation: ["Rename the plugin using lowercase letters, digits, and single hyphens only."],
    });
  }

  if (manifest.id && manifest.id !== path.basename(pluginRoot)) {
    pushCheck(checks, targetPath, {
      id: "manifest-id-directory-mismatch",
      category: "manifest",
      severity: "warning",
      status: "warn",
      message: "The plugin manifest id does not match the plugin directory name.",
      evidence: [`Directory: ${path.basename(pluginRoot)}`, `Manifest: ${manifest.id}`],
      remediation: ["Keep the plugin directory name and plugin.json id aligned."],
    });
  }

  for (const field of ["version", "title", "description", "homepageUrl", "sourceUrl"]) {
    if (!isNonEmptyString(manifest[field])) {
      pushCheck(checks, targetPath, {
        id: `manifest-${field}-invalid`,
        category: "manifest",
        severity: "error",
        status: "fail",
        message: `plugin.json \`${field}\` must be a non-empty string.`,
        evidence: [`Current value: ${String(manifest[field])}`],
        remediation: [`Set ${field} to a non-empty string.`],
      });
    }
  }

  if (!ALLOWED_CATEGORIES.has(manifest.category)) {
    pushCheck(checks, targetPath, {
      id: "manifest-category-invalid",
      category: "manifest",
      severity: "error",
      status: "fail",
      message: "plugin.json category must use one of the official category ids.",
      evidence: [`Current category: ${String(manifest.category)}`],
      remediation: [`Use one of: ${Array.from(ALLOWED_CATEGORIES).join(", ")}.`],
    });
  }

  if (!isPlainObject(manifest.author) || !isNonEmptyString(manifest.author.name)) {
    pushCheck(checks, targetPath, {
      id: "manifest-author-invalid",
      category: "manifest",
      severity: "error",
      status: "fail",
      message: "plugin.json author must be an object with a non-empty name.",
      evidence: [JSON.stringify(manifest.author)],
      remediation: ['Use "author": { "name": "Kodik" } for official marketplace plugins.'],
    });
  }

  if (!Array.isArray(manifest.tags) || manifest.tags.some((tag) => !isNonEmptyString(tag))) {
    pushCheck(checks, targetPath, {
      id: "manifest-tags-invalid",
      category: "manifest",
      severity: "error",
      status: "fail",
      message: "plugin.json tags must be an array of strings.",
      evidence: [JSON.stringify(manifest.tags)],
      remediation: ["Set tags to an array, or [] when the plugin has no useful tags."],
    });
  }

  if (!Array.isArray(manifest.prompts) || manifest.prompts.some((prompt) => !isNonEmptyString(prompt))) {
    pushCheck(checks, targetPath, {
      id: "manifest-prompts-invalid",
      category: "manifest",
      severity: "error",
      status: "fail",
      message: "plugin.json prompts must be an array of strings.",
      evidence: [JSON.stringify(manifest.prompts)],
      remediation: ["Set prompts to an array, or [] when the plugin has no starter prompts."],
    });
  } else {
    if (manifest.prompts.length > 3) {
      pushCheck(checks, targetPath, {
        id: "manifest-prompts-too-many",
        category: "manifest",
        severity: "warning",
        status: "warn",
        message: "Only the first three starter prompts are shown.",
        evidence: [`Prompt count: ${manifest.prompts.length}`],
        remediation: ["Trim prompts to three strong starters."],
      });
    }
    const oversizedPrompts = manifest.prompts.filter((prompt) => prompt.length > 128);
    if (oversizedPrompts.length > 0) {
      pushCheck(checks, targetPath, {
        id: "manifest-prompts-too-long",
        category: "manifest",
        severity: "warning",
        status: "warn",
        message: "One or more prompts exceed the UI-friendly length budget.",
        evidence: oversizedPrompts.map((prompt) => `${prompt.slice(0, 140)} (${prompt.length} chars)`),
        remediation: ["Keep prompts under 128 characters and ideally closer to 50."],
      });
    }
  }

  if (!isPlainObject(manifest.userConfig)) {
    pushCheck(checks, targetPath, {
      id: "manifest-user-config-invalid",
      category: "manifest",
      severity: "error",
      status: "fail",
      message: "plugin.json userConfig must be an object.",
      evidence: [JSON.stringify(manifest.userConfig)],
      remediation: ["Set userConfig to an object, or {} when the plugin has no user-configurable fields."],
    });
  }

  await validateIcon(pluginRoot, manifest, checks, targetPath);
  await validateMcp(pluginRoot, checks, targetPath);

  const skillDirs = await discoverPluginSkillDirectories(pluginRoot, manifest);
  if (skillDirs.length === 0) {
    pushCheck(checks, targetPath, {
      id: "plugin-skills-missing",
      category: "manifest",
      severity: "warning",
      status: "warn",
      message: "The plugin did not expose any discoverable skills.",
      evidence: ["./skills/"],
      remediation: ["Add at least one skill under ./skills/ when the plugin should provide skills."],
    });
  }

  for (const skillDir of skillDirs) {
    const prefix = `skill:${path.basename(skillDir)}`;
    const fragment = await evaluateSkill(skillDir, { prefix });
    checks.push(...fragment.checks);
    metrics.push(...fragment.metrics);
    artifacts.push(...fragment.artifacts);
  }

  metrics.push(
    createMetric({
      id: "plugin_skill_count",
      category: "manifest",
      value: skillDirs.length,
      unit: "skills",
      band: skillDirs.length > 0 ? "good" : "moderate",
      targetPath,
    }),
    createMetric({
      id: "plugin_tag_count",
      category: "manifest",
      value: Array.isArray(manifest.tags) ? manifest.tags.length : 0,
      unit: "tags",
      band: Array.isArray(manifest.tags) && manifest.tags.length > 0 ? "good" : "info",
      targetPath,
    }),
    createMetric({
      id: "plugin_prompt_count",
      category: "manifest",
      value: Array.isArray(manifest.prompts) ? manifest.prompts.length : 0,
      unit: "prompts",
      band: Array.isArray(manifest.prompts) && manifest.prompts.length <= 3 ? "good" : "moderate",
      targetPath,
    }),
  );

  artifacts.push(
    createArtifact({
      id: "plugin-skill-inventory",
      type: "inventory",
      label: "Plugin skills",
      description: "Discoverable skills under the plugin.",
      data: {
        skills: skillDirs.map((skillDir) => relativePath(pluginRoot, skillDir)),
      },
    }),
  );

  return { checks, metrics, artifacts, manifest };
}

async function validateIcon(pluginRoot, manifest, checks, targetPath) {
  if (manifest.icon !== "./assets/app-icon.svg") {
    pushCheck(checks, targetPath, {
      id: "manifest-icon-not-standard-path",
      category: "manifest",
      severity: "error",
      status: "fail",
      message: "plugin.json icon must use the standard plugin icon path.",
      evidence: [`Current value: ${String(manifest.icon)}`],
      remediation: ["Move the icon to ./assets/app-icon.svg and update icon."],
    });
    return;
  }

  const iconPath = path.resolve(pluginRoot, manifest.icon);
  if (!(await pathExists(iconPath))) {
    pushCheck(checks, targetPath, {
      id: "manifest-icon-missing",
      category: "manifest",
      severity: "error",
      status: "fail",
      message: "plugin.json icon points to a missing file.",
      evidence: [manifest.icon],
      remediation: ["Create ./assets/app-icon.svg."],
    });
    return;
  }

  const iconContent = await readText(iconPath);
  if (!iconContent.trim().startsWith("<svg")) {
    pushCheck(checks, targetPath, {
      id: "manifest-icon-invalid-svg",
      category: "manifest",
      severity: "error",
      status: "fail",
      message: "plugin.json icon must point to an SVG document.",
      evidence: [manifest.icon],
      remediation: ["Replace ./assets/app-icon.svg with a valid SVG file."],
    });
  }
  if (rasterIconPattern.test(iconContent)) {
    pushCheck(checks, targetPath, {
      id: "manifest-icon-embeds-raster",
      category: "manifest",
      severity: "error",
      status: "fail",
      message: "plugin.json icon must be vector SVG, not an SVG wrapper around raster image data.",
      evidence: [manifest.icon],
      remediation: ["Use a vector SVG path or generated SVG icon instead of embedded PNG/JPEG/WebP content."],
    });
  }
}

async function validateMcp(pluginRoot, checks, targetPath) {
  const mcpPath = path.join(pluginRoot, ".mcp.json");
  if (!(await pathExists(mcpPath))) {
    return;
  }

  let mcpConfig;
  try {
    mcpConfig = await readJson(mcpPath);
  } catch (error) {
    pushCheck(checks, targetPath, {
      id: "plugin-mcp-invalid-json",
      category: "manifest",
      severity: "error",
      status: "fail",
      message: ".mcp.json could not be parsed as JSON.",
      evidence: [error instanceof Error ? error.message : String(error)],
      remediation: ["Fix the JSON syntax in .mcp.json."],
    });
    return;
  }

  if (isPlainObject(mcpConfig.mcpServers)) {
    pushCheck(checks, targetPath, {
      id: "plugin-mcp-uses-legacy-key",
      category: "manifest",
      severity: "error",
      status: "fail",
      message: ".mcp.json uses legacy `mcpServers`; official Kodik plugins use `servers`.",
      evidence: [mcpPath],
      remediation: ["Rename the top-level `.mcp.json` key from `mcpServers` to `servers`."],
    });
  }

  if (!isPlainObject(mcpConfig.servers)) {
    pushCheck(checks, targetPath, {
      id: "plugin-mcp-missing-servers",
      category: "manifest",
      severity: "error",
      status: "fail",
      message: ".mcp.json is missing the top-level `servers` object.",
      evidence: [mcpPath],
      remediation: ["Add a top-level `servers` object containing each MCP server definition."],
    });
    return;
  }

  const meta = isPlainObject(mcpConfig.meta) ? mcpConfig.meta : {};
  for (const [serverName, serverConfig] of Object.entries(mcpConfig.servers)) {
    if (!isPlainObject(serverConfig) || !isNonEmptyString(serverConfig.type)) {
      pushCheck(checks, targetPath, {
        id: `plugin-mcp-${serverName}-missing-type`,
        category: "manifest",
        severity: "error",
        status: "fail",
        message: `MCP server \`${serverName}\` is missing an explicit type.`,
        evidence: [mcpPath],
        remediation: [`Add "type": "stdio", "sse", "http", or "streamableHttp" to ${serverName}.`],
      });
    }
    if (!isPlainObject(meta[serverName]) || !isNonEmptyString(meta[serverName].id)) {
      pushCheck(checks, targetPath, {
        id: `plugin-mcp-${serverName}-missing-meta-id`,
        category: "manifest",
        severity: "error",
        status: "fail",
        message: `MCP server \`${serverName}\` is missing meta.${serverName}.id.`,
        evidence: [mcpPath],
        remediation: [`Add a stable meta entry for ${serverName} with id, title, and description.`],
      });
    }
  }
}
