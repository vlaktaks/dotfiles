#!/usr/bin/env python3
"""Tests for report rendering, severity labels, and NO_COLOR behavior."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "report.py"
SAMPLE = SKILL_DIR / "tests" / "fixtures" / "sample-report.json"

sys.path.insert(0, str(SKILL_DIR / "scripts"))
import report  # noqa: E402


def run_report(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, env=env or os.environ.copy(), timeout=60)


class ReportTests(unittest.TestCase):
    def test_markdown_has_required_sections_and_no_ansi(self) -> None:
        proc = run_report(str(SAMPLE), "--format", "markdown")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for heading in (
            "# Linux-Security-Check — Security Audit Report",
            "## Executive Summary",
            "## Security Findings",
            "## Malware Indicators",
            "## Permissions and Privileges",
            "## Network and Privacy",
            "## Compatibility and Update Risks",
            "## Recommended Actions",
            "## Final Verdict",
        ):
            self.assertIn(heading, proc.stdout)
        self.assertNotIn("\x1b", proc.stdout)
        self.assertIn("🔴 CRITICAL/HIGH", proc.stdout)
        self.assertIn("🟡 WARNING", proc.stdout)
        self.assertIn("⚪ UNKNOWN", proc.stdout)
        self.assertIn("🟢 GREEN — PASS", proc.stdout)

    def test_markdown_never_emits_ansi_even_when_forced(self) -> None:
        proc = run_report(str(SAMPLE), "--format", "markdown", "--color", "always")
        self.assertEqual(proc.returncode, 0)
        self.assertNotIn("\x1b", proc.stdout)

    def test_terminal_color_always_emits_ansi_and_text_label(self) -> None:
        proc = run_report(str(SAMPLE), "--format", "terminal", "--color", "always")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("\x1b[0;31m", proc.stdout)
        self.assertIn("CRITICAL/HIGH", proc.stdout)
        self.assertIn("WARNING", proc.stdout)

    def test_terminal_color_never_has_no_ansi(self) -> None:
        proc = run_report(str(SAMPLE), "--format", "terminal", "--color", "never")
        self.assertEqual(proc.returncode, 0)
        self.assertNotIn("\x1b", proc.stdout)
        self.assertIn("CRITICAL/HIGH", proc.stdout)

    def test_piped_auto_has_no_ansi(self) -> None:
        proc = run_report(str(SAMPLE), "--format", "terminal", "--color", "auto")
        self.assertEqual(proc.returncode, 0)
        self.assertNotIn("\x1b", proc.stdout)

    def test_no_color_disables_auto_on_a_tty(self) -> None:
        fake_stdout = types.SimpleNamespace(isatty=lambda: True)
        with mock.patch.object(report.sys, "stdout", fake_stdout):
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("NO_COLOR", None)
                os.environ.pop("TERM", None)
                self.assertTrue(report.color_enabled("terminal", "auto"))
                os.environ["NO_COLOR"] = "1"
                self.assertFalse(report.color_enabled("terminal", "auto"))

    def test_dumb_terminal_disables_auto(self) -> None:
        fake_stdout = types.SimpleNamespace(isatty=lambda: True)
        with mock.patch.object(report.sys, "stdout", fake_stdout):
            with mock.patch.dict(os.environ, {"TERM": "dumb"}, clear=False):
                os.environ.pop("NO_COLOR", None)
                self.assertFalse(report.color_enabled("terminal", "auto"))

    def test_missing_fields_render_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "minimal.json"
            path.write_text(json.dumps({"findings": []}), encoding="utf-8")
            proc = run_report(str(path), "--format", "markdown")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("Insufficient evidence to determine safety", proc.stdout)
            self.assertIn("Not provided", proc.stdout)

    def test_non_object_findings_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "odd.json"
            path.write_text(json.dumps({"findings": ["not-an-object"]}),
                            encoding="utf-8")
            proc = run_report(str(path), "--format", "markdown")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("No findings were recorded.", proc.stdout)

    def test_severity_aliases_are_normalized(self) -> None:
        self.assertEqual(report.normalize_severity("critical"), "RED")
        self.assertEqual(report.normalize_severity("warn"), "YELLOW")
        self.assertEqual(report.normalize_severity("pass"), "GREEN")
        self.assertEqual(report.normalize_severity("nonsense"), "UNKNOWN")

    def test_invalid_json_exits_two(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{not json", encoding="utf-8")
            proc = run_report(str(path))
            self.assertEqual(proc.returncode, 2)
            self.assertIn("cannot read report", proc.stderr)


if __name__ == "__main__":
    unittest.main()
