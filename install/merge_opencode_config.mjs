#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const [, , targetPath, managedPath] = process.argv;
if (!targetPath || !managedPath) {
  console.error('Usage: merge_opencode_config.mjs <target-opencode.json> <managed-opencode.json>');
  process.exit(2);
}

function readJsonFile(p, { mustExist = false } = {}) {
  if (!fs.existsSync(p)) return { ok: true, value: null, missing: true };
  let raw;
  try {
    raw = fs.readFileSync(p, 'utf8');
  } catch (e) {
    return { ok: false, error: `cannot read ${p}: ${e.message}` };
  }
  try {
    return { ok: true, value: JSON.parse(raw), missing: false };
  } catch (e) {
    return { ok: false, error: `invalid JSON in ${p}: ${e.message}` };
  }
}

const targetRes = readJsonFile(targetPath);
if (!targetRes.ok) {
  console.error(`[merge] ${targetRes.error}`);
  console.error('[merge] refusing to overwrite existing invalid configuration');
  process.exit(1);
}
const managedRes = readJsonFile(managedPath);
if (!managedRes.ok) {
  console.error(`[merge] ${managedRes.error}`);
  process.exit(1);
}

const target = targetRes.value && typeof targetRes.value === 'object' && !Array.isArray(targetRes.value)
  ? targetRes.value
  : { $schema: 'https://opencode.ai/config.json' };
const managed = managedRes.value && typeof managedRes.value === 'object' && !Array.isArray(managedRes.value)
  ? managedRes.value
  : {};

const out = { ...target };

if (!out.$schema && managed.$schema) out.$schema = managed.$schema;

// Merge scalar managed keys only if missing (do not override existing explicit choices)
for (const [k, v] of Object.entries(managed)) {
  if (k === 'plugins' || k === 'provider' || k === 'plugin') continue;
  if (!(k in out)) out[k] = v;
}

// Preserve existing update if set; otherwise apply managed
if (Object.prototype.hasOwnProperty.call(target, 'update')) out.update = target.update;
else if (Object.prototype.hasOwnProperty.call(managed, 'update')) out.update = managed.update;

// Plugins: union, preserve existing, ensure managed plugins present
const existingPlugins = Array.isArray(out.plugins)
  ? out.plugins.slice()
  : Array.isArray(out.plugin)
    ? out.plugin.slice()
    : [];
const managedPlugins = Array.isArray(managed.plugins) ? managed.plugins : [];
const seen = new Set();
const mergedPlugins = [];
for (const p of [...existingPlugins, ...managedPlugins]) {
  const key = typeof p === 'string' ? p : JSON.stringify(p);
  if (seen.has(key)) continue;
  seen.add(key);
  mergedPlugins.push(p);
}
if (mergedPlugins.length) out.plugins = mergedPlugins;
if (out.plugins && Object.prototype.hasOwnProperty.call(out, 'plugin')) delete out.plugin;

// Provider: merge per provider id without deleting others or overwriting existing provider config
if (managed.provider && typeof managed.provider === 'object' && !Array.isArray(managed.provider)) {
  out.provider = (out.provider && typeof out.provider === 'object' && !Array.isArray(out.provider)) ? { ...out.provider } : {};
  for (const [id, cfg] of Object.entries(managed.provider)) {
    if (!Object.prototype.hasOwnProperty.call(out.provider, id)) out.provider[id] = cfg;
  }
}

// MCP: union servers by name without overwriting existing entries; apply managed timeout defaults only if missing
if (managed.mcp && typeof managed.mcp === 'object' && !Array.isArray(managed.mcp)) {
  out.mcp = (out.mcp && typeof out.mcp === 'object' && !Array.isArray(out.mcp)) ? { ...out.mcp } : {};
  const servers = (out.mcp.servers && typeof out.mcp.servers === 'object' && !Array.isArray(out.mcp.servers))
    ? { ...out.mcp.servers }
    : {};
  if (managed.mcp.servers && typeof managed.mcp.servers === 'object' && !Array.isArray(managed.mcp.servers)) {
    for (const [name, cfg] of Object.entries(managed.mcp.servers)) {
      if (!Object.prototype.hasOwnProperty.call(servers, name)) servers[name] = cfg;
    }
  }
  out.mcp = { ...out.mcp, servers };
  if (managed.mcp.timeout && !out.mcp.timeout) out.mcp.timeout = managed.mcp.timeout;
}

// Permissions: append managed rules not already present (identical action/resource/effect)
if (Array.isArray(managed.permissions) && managed.permissions.length) {
  const existing = Array.isArray(out.permissions) ? out.permissions : [];
  const keys = new Set(existing.map(r => `${r?.action}|${r?.resource}|${r?.effect}`));
  const added = managed.permissions.filter(r => r && typeof r === 'object' && !keys.has(`${r.action}|${r.resource}|${r.effect}`));
  if (added.length) out.permissions = [...existing, ...added];
}

fs.mkdirSync(path.dirname(targetPath), { recursive: true });
fs.writeFileSync(targetPath, JSON.stringify(out, null, 2) + '\n');
console.log('merged');
