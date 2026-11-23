#!/usr/bin/env python3
"""Validate an Omarchy Quattro plugin manifest and layout without activating it.

Checks the documented manifest contract, entry-point files, safe paths, and the
no-symlink rule. It does not load QML, run installers, or register the plugin.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

KIND_ENTRY_POINTS = {
    "bar-widget": "barWidget",
    "panel": "panel",
    "overlay": "overlay",
    "menu": "menu",
    "service": "service",
    "bar": "bar",
}
REQUIRED = ("schemaVersion", "id", "name", "version", "author", "description",
            "kinds", "entryPoints")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def finding(severity: str, check: str, message: str, path: str | None = None) -> dict:
    return {"severity": severity, "check": check, "message": message,
            "path": path}


def safe_relpath(value: str) -> bool:
    if not value or os.path.isabs(value):
        return False
    norm = os.path.normpath(value)
    return not (norm == ".." or norm.startswith("../") or norm.startswith("/"))


def find_symlinks(root: str) -> list[str]:
    links = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in dirnames + filenames:
            full = os.path.join(dirpath, name)
            if os.path.islink(full):
                links.append(os.path.relpath(full, root))
    return sorted(links)


def validate(plugin_dir: str) -> dict:
    findings: list[dict] = []
    manifest_path = os.path.join(plugin_dir, "manifest.json")

    if not os.path.isdir(plugin_dir):
        return {"tool": "linux-security-check/check-omarchy-manifest",
                "plugin_dir": plugin_dir, "status": "RED",
                "manifest_present": False,
                "findings": [finding("RED", "plugin-dir", "Plugin directory not found.")],
                "entry_points": {}, "notes": []}
    if not os.path.isfile(manifest_path):
        return {"tool": "linux-security-check/check-omarchy-manifest",
                "plugin_dir": plugin_dir, "status": "RED",
                "manifest_present": False,
                "findings": [finding("RED", "manifest-present",
                                     "manifest.json is missing at the repository root.")],
                "entry_points": {}, "notes": []}

    try:
        with open(manifest_path, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        return {"tool": "linux-security-check/check-omarchy-manifest",
                "plugin_dir": plugin_dir, "status": "RED",
                "manifest_present": True,
                "findings": [finding("RED", "manifest-json",
                                     f"manifest.json is not valid JSON: {exc}",
                                     "manifest.json")],
                "entry_points": {}, "notes": []}

    if not isinstance(manifest, dict):
        findings.append(finding("RED", "manifest-object",
                                "Manifest root must be a JSON object.", "manifest.json"))
        manifest = {}

    for field in REQUIRED:
        if field not in manifest or manifest[field] in ("", None, [], {}):
            findings.append(finding("RED", "required-field",
                                    f"Missing or empty required field: {field}.",
                                    "manifest.json"))

    schema = manifest.get("schemaVersion")
    if schema is not None and (not isinstance(schema, int) or isinstance(schema, bool)):
        findings.append(finding("RED", "schema-version",
                                "schemaVersion must be an integer (currently 1).",
                                "manifest.json"))
    elif schema is not None and schema != 1:
        findings.append(finding("YELLOW", "schema-version",
                                f"schemaVersion is {schema}; the documented current version is 1.",
                                "manifest.json"))

    for field in ("name", "author", "description"):
        value = manifest.get(field)
        if value is not None and not isinstance(value, str):
            findings.append(finding("RED", "field-type",
                                    f"{field} must be a string.", "manifest.json"))

    plugin_id = manifest.get("id")
    if isinstance(plugin_id, str):
        if not ID_RE.match(plugin_id) or " " in plugin_id:
            findings.append(finding("RED", "plugin-id",
                                    "id must be lowercase, namespaced, and contain no spaces.",
                                    "manifest.json"))
        if plugin_id.startswith("omarchy."):
            findings.append(finding("RED", "plugin-id",
                                    "Third-party plugins cannot use the reserved omarchy.* namespace.",
                                    "manifest.json"))
        if "." not in plugin_id:
            findings.append(finding("YELLOW", "plugin-id",
                                    "id is not namespaced (expected author.plugin); confirm it is intentional.",
                                    "manifest.json"))
    elif plugin_id is not None:
        findings.append(finding("RED", "plugin-id", "id must be a string.", "manifest.json"))

    version = manifest.get("version")
    if isinstance(version, str) and not VERSION_RE.match(version):
        findings.append(finding("YELLOW", "version",
                                "version is not semver-like (expected x.y.z).",
                                "manifest.json"))

    kinds = manifest.get("kinds")
    if kinds is not None:
        if not isinstance(kinds, list) or not all(isinstance(k, str) for k in kinds):
            findings.append(finding("RED", "kinds", "kinds must be a list of strings.",
                                    "manifest.json"))
            kinds = []
        else:
            if len(set(kinds)) != len(kinds):
                findings.append(finding("YELLOW", "kinds", "kinds contains duplicates.",
                                        "manifest.json"))
            unknown = [k for k in kinds if k not in KIND_ENTRY_POINTS]
            if unknown:
                findings.append(finding("RED", "kinds",
                                        "Unknown plugin kind(s): " + ", ".join(unknown),
                                        "manifest.json"))

    entry_points = manifest.get("entryPoints")
    resolved = {}
    if entry_points is not None:
        if not isinstance(entry_points, dict):
            findings.append(finding("RED", "entry-points",
                                    "entryPoints must be an object.", "manifest.json"))
            entry_points = {}
        else:
            for key, value in entry_points.items():
                if key not in KIND_ENTRY_POINTS.values():
                    findings.append(finding("YELLOW", "entry-points",
                                            f"Unexpected entryPoints key: {key}.",
                                            "manifest.json"))
                if not isinstance(value, str) or not safe_relpath(value):
                    findings.append(finding("RED", "entry-points",
                                            f"Unsafe or invalid path for {key}: {value!r}.",
                                            "manifest.json"))
                    continue
                full = os.path.join(plugin_dir, value)
                resolved[key] = value
                if not os.path.isfile(full):
                    findings.append(finding("RED", "entry-point-file",
                                            f"Entry point not found: {value}", value))
                elif os.path.islink(full):
                    findings.append(finding("RED", "entry-point-symlink",
                                            f"Entry point is a symlink: {value}", value))

            if isinstance(kinds, list):
                for kind in kinds:
                    if kind not in KIND_ENTRY_POINTS:
                        continue
                    key = KIND_ENTRY_POINTS[kind]
                    if key not in entry_points:
                        findings.append(finding("RED", "entry-point-kind",
                                                f"Kind {kind!r} requires entryPoints.{key}.",
                                                "manifest.json"))
                    elif entry_points.get(key) != resolved.get(key):
                        findings.append(finding("RED", "entry-point-kind",
                                                f"entryPoints.{key} is invalid or missing.",
                                                "manifest.json"))

    links = find_symlinks(plugin_dir)
    if links:
        findings.append(finding("RED", "symlinks",
                                "Plugin directories cannot contain symlinks: "
                                + ", ".join(links[:20]),
                                "plugin directory"))

    order = {"RED": 0, "YELLOW": 1, "UNKNOWN": 2, "GREEN": 3}
    findings.sort(key=lambda f: order.get(f["severity"], 9))
    status = "GREEN"
    if any(f["severity"] == "RED" for f in findings):
        status = "RED"
    elif any(f["severity"] == "YELLOW" for f in findings):
        status = "YELLOW"

    return {
        "tool": "linux-security-check/check-omarchy-manifest",
        "version": 1,
        "plugin_dir": plugin_dir,
        "manifest_present": True,
        "id": manifest.get("id"),
        "version_value": manifest.get("version"),
        "kinds": manifest.get("kinds"),
        "entry_points": resolved,
        "status": status,
        "findings": findings,
        "notes": [
            "Structural validation only; a valid manifest does not make a plugin safe.",
            "Compliance with the Omarchy contract is separate from source security.",
            "No QML was loaded, no installer was run, and the plugin was not registered.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate an Omarchy plugin manifest without activating it.")
    parser.add_argument("plugin_dir")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    result = validate(args.plugin_dir)
    print(json.dumps(result, indent=None if args.compact else 2))
    return 0 if result["status"] != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
