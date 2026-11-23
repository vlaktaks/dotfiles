#!/usr/bin/env python3
"""Render a Linux-Security-Check finding report.

Input is the JSON schema documented in references/report-format.md. Output is
either Markdown (never ANSI) or terminal text (ANSI only when enabled).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
COLORS = {
    "GREEN": "\033[0;32m",
    "YELLOW": "\033[0;33m",
    "RED": "\033[0;31m",
    "UNKNOWN": "\033[0;90m",
    "ACCENT": "\033[0;36m",
}
ICONS = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴", "UNKNOWN": "⚪"}
LABELS = {
    "GREEN": "GREEN — PASS",
    "YELLOW": "WARNING",
    "RED": "CRITICAL/HIGH",
    "UNKNOWN": "UNKNOWN",
}
ORDER = {"RED": 0, "YELLOW": 1, "UNKNOWN": 2, "GREEN": 3}
ALIASES = {
    "CRITICAL": "RED", "HIGH": "RED", "CRIT": "RED",
    "WARN": "YELLOW", "WARNING": "YELLOW", "MEDIUM": "YELLOW",
    "PASS": "GREEN", "OK": "GREEN", "SAFE": "GREEN",
    "INFO": "UNKNOWN", "GRAY": "UNKNOWN", "GREY": "UNKNOWN",
}


def normalize_severity(value) -> str:
    text = str(value or "UNKNOWN").strip().upper()
    if text in LABELS:
        return text
    return ALIASES.get(text, "UNKNOWN")


def color_enabled(fmt: str, mode: str) -> bool:
    if fmt == "markdown":
        return False
    if mode == "always":
        return True
    if mode == "never":
        return False
    if "NO_COLOR" in os.environ:
        return False
    if os.environ.get("TERM", "") == "dumb":
        return False
    return sys.stdout.isatty()


class Styler:
    def __init__(self, enabled: bool):
        self.enabled = enabled

    def paint(self, text: str, key: str, bold: bool = False) -> str:
        if not self.enabled or key not in COLORS:
            return text
        prefix = COLORS[key] + (BOLD if bold else "")
        return f"{prefix}{text}{RESET}"

    def severity(self, severity: str) -> str:
        return (f"{ICONS[severity]} "
                f"{self.paint(LABELS[severity], severity, bold=True)}")


def as_list(value) -> list:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def bullet_block(items: list) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- Not provided"]


def render_findings(findings: list[dict], style: Styler, markdown: bool) -> list[str]:
    out: list[str] = []
    findings = [f for f in findings if isinstance(f, dict)]
    findings = sorted(findings, key=lambda f: ORDER.get(
        normalize_severity(f.get("severity")), 9))
    if not findings:
        return ["No findings were recorded."]
    for index, item in enumerate(findings, 1):
        sev = normalize_severity(item.get("severity"))
        fid = item.get("id") or f"LSC-{index:03d}"
        title = item.get("title") or item.get("component") or "Finding"
        out.append(f"### {fid} — {style.severity(sev)}: {title}" if not markdown
                   else f"### {fid} — {ICONS[sev]} {LABELS[sev]}: {title}")
        out.append("")
        fields = (
            ("Severity", LABELS[sev]),
            ("Affected component", item.get("component")),
            ("Evidence", item.get("evidence")),
            ("Location", item.get("location")),
            ("Explanation", item.get("explanation")),
            ("Potential impact", item.get("impact")),
            ("Confidence", item.get("confidence")),
            ("Recommended action", item.get("action")),
        )
        for label, value in fields:
            if value not in (None, "", []):
                out.append(f"- **{label}:** {value}")
        out.append("")
    return out


def render_markdown(data: dict) -> str:
    style = Styler(False)
    risk = normalize_severity(data.get("overall_risk"))
    lines = [
        "# Linux-Security-Check — Security Audit Report",
        "",
        f"**Target:** {data.get('target') or 'Not provided'}",
        "",
        f"**Audit date:** {data.get('audit_date') or 'Not provided'}",
        "",
        f"**Environment:** {data.get('environment') or 'Not provided'}",
        "",
        f"**Audit mode:** {data.get('audit_mode') or 'Not provided'}",
        "",
        f"**Inspected version or commit:** {data.get('inspected_version') or 'Not provided'}",
        "",
        f"**Overall risk:** {style.severity(risk)}",
        "",
        f"**Confidence:** {data.get('confidence') or 'Not provided'}",
        "",
        "**Coverage and limitations:**",
        "",
    ]
    coverage = as_list(data.get("coverage"))
    limitations = as_list(data.get("limitations"))
    if coverage:
        lines += [f"- Coverage: {c}" for c in coverage]
    if limitations:
        lines += [f"- Limitation: {x}" for x in limitations]
    if not coverage and not limitations:
        lines.append("- Not provided")

    lines += ["", "## Executive Summary", "",
              str(data.get("summary") or "Not provided"), "",
              "## Security Findings", ""]
    lines += render_findings(data.get("findings") or [], style, True)

    for heading, key in (
        ("Malware Indicators", "malware_indicators"),
        ("Permissions and Privileges", "permissions"),
        ("Network and Privacy", "network_privacy"),
        ("Compatibility and Update Risks", "update_risks"),
    ):
        value = data.get(key)
        lines += ["", f"## {heading}", ""]
        if isinstance(value, list):
            lines += bullet_block([str(v) for v in value])
        else:
            lines.append(str(value) if value else "Not applicable to this mode.")

    lines += ["", "## Recommended Actions", ""]
    actions = data.get("actions") or []
    if actions:
        for action in actions:
            if isinstance(action, dict):
                priority = action.get("priority") or "P?"
                lines.append(f"- **{priority}:** {action.get('action') or action}")
            else:
                lines.append(f"- {action}")
    else:
        lines.append("- Not provided")

    lines += ["", "## Final Verdict", "",
              str(data.get("verdict") or "Insufficient evidence to determine safety")]
    return "\n".join(lines).rstrip() + "\n"


def render_terminal(data: dict, style: Styler) -> str:
    risk = normalize_severity(data.get("overall_risk"))
    lines = [
        style.paint("Linux-Security-Check — Security Audit Report", "ACCENT", bold=True),
        "",
        f"Target: {data.get('target') or 'Not provided'}",
        f"Audit date: {data.get('audit_date') or 'Not provided'}",
        f"Environment: {data.get('environment') or 'Not provided'}",
        f"Audit mode: {data.get('audit_mode') or 'Not provided'}",
        f"Inspected version or commit: {data.get('inspected_version') or 'Not provided'}",
        f"Overall risk: {style.severity(risk)}",
        f"Confidence: {data.get('confidence') or 'Not provided'}",
        "",
        style.paint("Coverage and limitations:", "ACCENT", bold=True),
    ]
    for item in as_list(data.get("coverage")):
        lines.append(f"  - Coverage: {item}")
    for item in as_list(data.get("limitations")):
        lines.append(f"  - Limitation: {item}")
    if not as_list(data.get("coverage")) and not as_list(data.get("limitations")):
        lines.append("  - Not provided")

    lines += ["", style.paint("Executive Summary", "ACCENT", bold=True), "",
              str(data.get("summary") or "Not provided"), "",
              style.paint("Security Findings", "ACCENT", bold=True), ""]
    lines += render_findings(data.get("findings") or [], style, False)

    for heading, key in (
        ("Malware Indicators", "malware_indicators"),
        ("Permissions and Privileges", "permissions"),
        ("Network and Privacy", "network_privacy"),
        ("Compatibility and Update Risks", "update_risks"),
    ):
        value = data.get(key)
        lines += ["", style.paint(heading, "ACCENT", bold=True), ""]
        if isinstance(value, list):
            lines += bullet_block([str(v) for v in value])
        else:
            lines.append(str(value) if value else "Not applicable to this mode.")

    lines += ["", style.paint("Recommended Actions", "ACCENT", bold=True), ""]
    actions = data.get("actions") or []
    if actions:
        for action in actions:
            if isinstance(action, dict):
                priority = action.get("priority") or "P?"
                lines.append(f"- {priority}: {action.get('action') or action}")
            else:
                lines.append(f"- {action}")
    else:
        lines.append("- Not provided")

    lines += ["", style.paint("Final Verdict", "ACCENT", bold=True), "",
              str(data.get("verdict") or "Insufficient evidence to determine safety")]
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render a Linux-Security-Check report.")
    parser.add_argument("report", help="JSON report path, or - for stdin")
    parser.add_argument("--format", choices=("terminal", "markdown"),
                        default="terminal")
    parser.add_argument("--color", choices=("auto", "always", "never"),
                        default="auto",
                        help="ANSI color; markdown output never uses ANSI")
    args = parser.parse_args()

    try:
        if args.report == "-":
            data = json.load(sys.stdin)
        else:
            with open(args.report, "r", encoding="utf-8") as fh:
                data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"report.py: cannot read report: {exc}", file=sys.stderr)
        return 2

    if not isinstance(data, dict):
        print("report.py: report root must be a JSON object", file=sys.stderr)
        return 2
    if not isinstance(data.get("findings", []), list):
        print("report.py: findings must be a list", file=sys.stderr)
        return 2

    style = Styler(color_enabled(args.format, args.color))
    output = (render_markdown(data) if args.format == "markdown"
              else render_terminal(data, style))
    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
