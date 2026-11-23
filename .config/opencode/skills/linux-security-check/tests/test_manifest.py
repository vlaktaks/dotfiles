#!/usr/bin/env python3
"""Tests for the Omarchy manifest/layout validator."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "check-omarchy-manifest.py"
FIXTURES = SKILL_DIR / "tests" / "fixtures"


def run_validate(path: Path) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        capture_output=True, text=True, timeout=60)
    return proc.returncode, json.loads(proc.stdout)


def checks(data: dict) -> set[str]:
    return {f["check"] for f in data["findings"]}


class ManifestTests(unittest.TestCase):
    def test_invalid_manifest_is_red(self) -> None:
        code, data = run_validate(FIXTURES / "omarchy-invalid")
        self.assertEqual(code, 1)
        self.assertEqual(data["status"], "RED")
        found = checks(data)
        self.assertIn("required-field", found)
        self.assertIn("plugin-id", found)
        self.assertIn("entry-point-file", found)

    def test_valid_manifest_with_suspicious_installer_passes_structure(self) -> None:
        code, data = run_validate(FIXTURES / "omarchy-suspicious")
        self.assertEqual(code, 0)
        self.assertEqual(data["status"], "GREEN", data["findings"])
        self.assertEqual(data["entry_points"], {"barWidget": "BarWidget.qml"})

    def test_missing_manifest_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, data = run_validate(Path(tmp))
            self.assertEqual(code, 1)
            self.assertEqual(data["status"], "RED")
            self.assertIn("manifest-present", checks(data))

    def test_wrong_entry_point_key_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Plugin.qml").write_text("import QtQuick\nItem {}\n",
                                             encoding="utf-8")
            (root / "manifest.json").write_text(json.dumps({
                "schemaVersion": 1,
                "id": "acme.widget",
                "name": "Widget",
                "version": "1.0.0",
                "author": "Acme",
                "description": "Fixture",
                "kinds": ["bar-widget"],
                "entryPoints": {"panel": "Plugin.qml"},
            }), encoding="utf-8")
            code, data = run_validate(root)
            self.assertEqual(code, 1)
            self.assertIn("entry-point-kind", checks(data))

    def test_symlink_in_plugin_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "BarWidget.qml").write_text("import QtQuick\nItem {}\n",
                                                encoding="utf-8")
            (root / "manifest.json").write_text(json.dumps({
                "schemaVersion": 1,
                "id": "acme.clock",
                "name": "Clock",
                "version": "1.0.0",
                "author": "Acme",
                "description": "Fixture",
                "kinds": ["bar-widget"],
                "entryPoints": {"barWidget": "BarWidget.qml"},
            }), encoding="utf-8")
            os.symlink("/etc/passwd", root / "passwd-link")
            code, data = run_validate(root)
            self.assertEqual(code, 1)
            self.assertIn("symlinks", checks(data))

    def test_traversal_entry_point_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "manifest.json").write_text(json.dumps({
                "schemaVersion": 1,
                "id": "acme.clock",
                "name": "Clock",
                "version": "1.0.0",
                "author": "Acme",
                "description": "Fixture",
                "kinds": ["bar-widget"],
                "entryPoints": {"barWidget": "../Escaped.qml"},
            }), encoding="utf-8")
            code, data = run_validate(root)
            self.assertEqual(code, 1)
            self.assertIn("entry-points", checks(data))

    def test_validator_never_claims_runtime_safety(self) -> None:
        _, data = run_validate(FIXTURES / "omarchy-suspicious")
        notes = " ".join(data["notes"]).lower()
        self.assertIn("does not make a plugin safe", notes)
        self.assertIn("no qml was loaded", notes)


if __name__ == "__main__":
    unittest.main()
