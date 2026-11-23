#!/usr/bin/env python3
"""Bounded, read-only static pattern scan for Linux-Security-Check.

This is a triage aid, not a verdict. It never executes, imports, sources, or
extracts the inspected files. Pattern matches can be legitimate; correlate
with context before reporting malicious behavior.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlsplit

EXCLUDED_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv",
    "target", "dist", "build", "vendor", ".cache", ".mypy_cache",
    ".pytest_cache", ".tox",
}

SEVERITY_ORDER = {"RED": 0, "YELLOW": 1, "UNKNOWN": 2, "GREEN": 3}


@dataclass(frozen=True)
class Rule:
    rule_id: str
    severity: str
    category: str
    pattern: str
    message: str
    extensions: tuple[str, ...] = ()
    capability: str | None = None
    finding: bool = True


RULES: tuple[Rule, ...] = (
    Rule(
        "destructive-rm", "RED", "destructive",
        r"\brm\s+(?:-[a-zA-Z-]+\s+)*--no-preserve-root"
        r"|\brm\s+(?:-[a-zA-Z]*[rR][a-zA-Z]*\s+)+(?:/|/\*|~|\$HOME|\$\{HOME\})(?=\s|$|[\"'])",
        "Recursive deletion targeting /, ~, /home, or with --no-preserve-root.",
    ),
    Rule(
        "fork-bomb", "RED", "resource-exhaustion",
        r":\s*\(\s*\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",
        "Shell fork bomb pattern.",
    ),
    Rule(
        "disk-destroy", "RED", "destructive",
        r"\bdd\b[^\n]*\bof=/dev/(?:sd|nvme|vd|hd|mmcblk)"
        r"|\bmkfs(?:\.[a-z0-9]+)?\b|\bwipefs\b|\bshred\b[^\n]*/dev/",
        "Writes to a block device or destroys a filesystem.",
    ),
    Rule(
        "download-pipe-shell", "RED", "download-execute",
        r"\b(?:curl|wget)\b[^\n|;]*\|\s*(?:env\s+)?(?:sudo\s+)?"
        r"(?:/usr/bin/|/bin/)?(?:ba|z|k|da)?sh\b"
        r"|\b(?:curl|wget)\b[^\n|;]*\|\s*(?:sudo\s+)?"
        r"(?:python[0-9.]*|perl|ruby|node|lua)\b",
        "Downloads remote content and pipes it directly to an interpreter.",
    ),
    Rule(
        "base64-decode-exec", "RED", "obfuscation-execute",
        r"\b(?:base64\s+(?:-d|--decode)|openssl\s+base64\s+-d|xxd\s+-r)"
        r"[^\n|]*\|\s*(?:sudo\s+)?(?:ba|z|k|da)?sh\b",
        "Decodes an encoded blob and executes it.",
    ),
    Rule(
        "reverse-shell", "RED", "remote-control",
        r"/dev/(?:tcp|udp)/|\bnc(?:at)?\b[^\n]*\s-e\s+|socat[^\n]*\bexec:"
        r"|\b(?:ba|z|da)?sh\s+-i\b",
        "Reverse-shell or interactive shell pattern.",
    ),
    Rule(
        "credential-exfil", "RED", "credential-theft",
        r"(?:cat|less|more|head|tail|cp|tar|zip|base64|gpg|openssl)[^\n]*"
        r"(?:\.ssh/id_|authorized_keys|\.aws/credentials|\.netrc|Cookies|Login Data)"
        r"[^\n]*\|[^\n]*(?:curl|wget|nc|ssh|scp)"
        r"|\b(?:curl|wget|nc|scp|rsync)\b[^\n]*(?:-F|--data|--upload-file|--post-file|@)"
        r"[^\n]*(?:\.ssh|\.aws|\.netrc|Cookies|Login Data|/etc/shadow)",
        "Reads credentials and sends them over the network.",
    ),
    Rule(
        "security-disable", "RED", "defense-evasion",
        r"ufw\s+disable|ip6?tables\s+-F|nft\s+flush\s+ruleset|setenforce\s+0"
        r"|aa-disable|apparmor[^\n]*disable"
        r"|systemctl\s+(?:disable|stop|mask)\s+[^\n]*"
        r"(?:firewalld|ufw|apparmor|auditd|clamav|nftables|fail2ban)",
        "Disables a security control.",
    ),
    Rule(
        "cryptominer", "RED", "cryptomining",
        r"\bxmrig\b|stratum\+tcp|\bminerd\b|\bcpuminer\b|--donate-level|cryptonight",
        "Cryptominer or mining-pool indicator.",
    ),
    Rule(
        "sudoers-nopasswd", "RED", "privilege",
        r"NOPASSWD\s*:\s*ALL",
        "Passwordless sudo grant for all commands.",
    ),
    Rule(
        "service-shell-exec", "RED", "service-execution",
        r"^\s*Exec(?:Start|StartPre|Stop|Reload)\s*=.*"
        r"(?:/bin/(?:ba|z|da)?sh|/usr/bin/(?:ba|z|da)?sh|\bcurl\b|\bwget\b|\bnc\b|\bsocat\b)",
        "Service unit executes a shell/downloader instead of a fixed binary.",
        extensions=(".service", ".socket", ".timer"),
    ),
    Rule(
        "download-then-exec", "YELLOW", "download-execute",
        r"\b(?:curl|wget)\b[^\n]*(?:-o|--output|-O)\s*\S+[^\n]*(?:&&|;)"
        r"[^\n]*(?:chmod\s+\+x[^\n]*&&\s*)?(?:\./|(?:ba|z)?sh\s|exec\s)",
        "Downloads a file and then executes it; verify pinning and checksums.",
    ),
    Rule(
        "shell-eval-substitution", "YELLOW", "dynamic-execution",
        r"\beval\b[^\n]*(?:\$\(|`)|(?:ba|z)?sh\s+-c\s+[\"']?\$",
        "Executes dynamically constructed shell content.",
    ),
    Rule(
        "python-dynamic-exec", "YELLOW", "dynamic-execution",
        r"\b(?:exec|eval|compile)\s*\(|__import__\s*\(|pickle\.loads\s*\(|marshal\.loads\s*\(",
        "Dynamic Python code execution or unsafe deserialization.",
        extensions=(".py", ".pyw"),
    ),
    Rule(
        "js-dynamic-code", "YELLOW", "dynamic-execution",
        r"\beval\s*\(|new\s+Function\s*\(|vm\.runIn|child_process|execSync\s*\(|spawnSync\s*\(",
        "Dynamic code execution or subprocess use in JavaScript/TypeScript.",
        extensions=(".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"),
    ),
    Rule(
        "lua-dynamic-load", "YELLOW", "dynamic-execution",
        r"\b(?:loadstring|load)\s*\(|\bos\.execute\b|\bio\.popen\b|vim\.fn\.system|vim\.uv\.spawn",
        "Dynamic loading or process execution in Lua.",
        extensions=(".lua",),
    ),
    Rule(
        "qml-process-exec", "YELLOW", "process-execution",
        r"\b(?:Quickshell\.Io\.)?Process\s*\{|\bexec\s*[:(]|\bsh\s+-c\b|\bcommand\s*:",
        "QML can launch processes; review arguments and triggers.",
        extensions=(".qml",),
    ),
    Rule(
        "qml-remote-load", "YELLOW", "network",
        r"XMLHttpRequest|\bfetch\s*\(|WebSocket|Loader\s*\{[^}]*source\s*:\s*[\"']https?://",
        "QML loads data or components from the network.",
        extensions=(".qml", ".js"),
    ),
    Rule(
        "credential-access", "YELLOW", "credential-access",
        r"\.ssh\b|\.aws/credentials|\.config/gh/hosts\.yml|\.config/gcloud"
        r"|\.netrc|\.git-credentials"
        r"|/etc/shadow|Cookies|Login Data|Local State|keyring|wallet\.dat",
        "Accesses credential, key, browser, or wallet material; confirm need and destination.",
    ),
    Rule(
        "persistence-systemd", "YELLOW", "persistence",
        r"systemctl\s+(?:--user\s+)?enable|systemd-run|/etc/systemd/(?:system|user)"
        r"|\.config/systemd/user",
        "Installs or enables a systemd service/timer.",
    ),
    Rule(
        "persistence-cron", "YELLOW", "persistence",
        r"crontab\s+-|/etc/cron\.|@reboot",
        "Installs cron persistence.",
    ),
    Rule(
        "shell-rc-modification", "YELLOW", "persistence",
        r"(?:>>?|tee\s+(?:-a\s+)?)[^\n]*(?:\.bashrc|\.bash_profile|\.profile|\.zshrc"
        r"|/etc/profile\.d|\.config/fish/config\.fish)",
        "Modifies shell startup files.",
    ),
    Rule(
        "setuid-capability", "YELLOW", "privilege",
        r"chmod\s+(?:[ugo]*\+?s|4[0-7]{3}|2[0-7]{3})|\bsetcap\b",
        "Sets SUID/SGID bits or Linux file capabilities.",
    ),
    Rule(
        "audio-capture", "YELLOW", "privacy",
        r"\b(?:pw-record|parecord|arecord)\b"
        r"|ffmpeg[^\n]*(?:-f\s+(?:pulse|alsa)|-i\s+(?:default|hw:|plughw:))"
        r"|/dev/snd/|pactl\s+load-module[^\n]*(?:module-loopback|module-null-sink)",
        "Captures or reroutes audio; verify purpose and data destination.",
    ),
    Rule(
        "camera-capture", "YELLOW", "privacy",
        r"/dev/video\d*|\bv4l2|fswebcam|ffmpeg[^\n]*-f\s+v4l2",
        "Accesses a camera device.",
    ),
    Rule(
        "screen-capture", "YELLOW", "privacy",
        r"\b(?:grim|scrot|spectacle|wf-recorder|gnome-screenshot|import\s+-window)\b",
        "Captures the screen.",
    ),
    Rule(
        "clipboard-access", "YELLOW", "privacy",
        r"\b(?:wl-paste|xclip|xsel|pbpaste)\b",
        "Reads the clipboard.",
    ),
    Rule(
        "http-post-upload", "YELLOW", "exfiltration",
        r"\b(?:curl|wget)\b[^\n]*(?:-F\s|--data-binary|--data\s|--upload-file"
        r"|-X\s*POST|--post-data)",
        "Uploads data over HTTP; verify destination, consent, and content.",
    ),
    Rule(
        "webhook-endpoint", "YELLOW", "exfiltration",
        r"discord(?:app)?\.com/api/webhooks|api\.telegram\.org/bot|hooks\.slack\.com"
        r"|pastebin\.com|transfer\.sh|0x0\.st|ngrok\.io|trycloudflare\.com"
        r"|webhook\.site|requestbin",
        "Contacts a paste, webhook, or tunnel service commonly used for exfiltration.",
    ),
    Rule(
        "ifs-obfuscation", "YELLOW", "obfuscation",
        r"\$\{?IFS\}?",
        "Uses IFS manipulation, often to hide command names or arguments.",
    ),
    Rule(
        "long-encoded-blob", "YELLOW", "obfuscation",
        r"[A-Za-z0-9+/]{240,}={0,2}",
        "Long encoded-looking blob; decode statically only.",
    ),
    Rule(
        "kernel-module", "YELLOW", "kernel",
        r"\b(?:insmod|modprobe|rmmod)\b|/etc/modprobe\.d|/lib/modules",
        "Loads or configures kernel modules.",
    ),
    Rule(
        "ssh-tunnel", "YELLOW", "network",
        r"\bssh\b[^\n]*(?:\s-[RLD]\s|\s-[RLD][0-9])",
        "Creates an SSH tunnel or proxy.",
    ),
    Rule(
        "firewall-modification", "YELLOW", "network",
        r"\b(?:iptables|ip6tables|nft|ufw|firewall-cmd)\b[^\n]*"
        r"(?:-A|-I|-F|add|delete|disable|enable|allow|deny|flush|policy)",
        "Modifies firewall or network policy.",
    ),
    Rule(
        "untrusted-remote-build", "YELLOW", "supply-chain",
        r"cargo\s+install[^\n]*--git(?!\s+[^\n]*--rev\s+[0-9a-f]{40})"
        r"|pip[0-9.]*\s+install[^\n]*git\+https?://"
        r"|npm\s+install[^\n]*https?://",
        "Builds or installs code from an unpinned remote source.",
    ),
    Rule(
        "sudo-use", "YELLOW", "privilege", r"\b(?:sudo|pkexec|doas)\b",
        "Uses privilege elevation.", capability="privilege-elevation", finding=False,
    ),
    Rule(
        "package-install", "YELLOW", "install",
        r"\b(?:pacman\s+-S|apt(?:-get)?\s+install|dnf\s+install|zypper\s+(?:in|install)"
        r"|npm\s+(?:install|i)\s+(?:-g|--global)|pip[0-9.]*\s+install|cargo\s+install"
        r"|makepkg|yay\s+-S|paru\s+-S)\b",
        "Installs software.", capability="package-install", finding=False,
    ),
    Rule(
        "remote-fetch", "YELLOW", "network", r"https?://[^\s\"'<>)\]]+",
        "References a remote URL.", capability="remote-fetch", finding=False,
    ),
    Rule(
        "tmp-path", "YELLOW", "execution-path",
        r"/(?:tmp|dev/shm|var/tmp)/",
        "References a world-writable temporary path.", capability="tmp-path", finding=False,
    ),
)

COMPILED = tuple(
    (rule, re.compile(rule.pattern, re.IGNORECASE | re.MULTILINE)) for rule in RULES
)

REDACTIONS = (
    (re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd|authorization)"
                r"(\s*[:=]\s*)(\S+)"), r"\1\2<redacted>"),
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"), r"\1<redacted>"),
)
URL_RE = re.compile(r"https?://[^\s\"'<>)\]]+")

def redact(text: str) -> str:
    for pattern, repl in REDACTIONS:
        text = pattern.sub(repl, text)
    text = URL_RE.sub(lambda m: sanitize_url(m.group(0).rstrip(".,;")), text)
    return text


def sanitize_url(value: str) -> str:
    """Keep only scheme and host so tokens in paths/queries cannot leak."""
    try:
        parts = urlsplit(value)
        if parts.scheme and parts.netloc:
            return f"{parts.scheme}://{parts.netloc}"
    except ValueError:
        pass
    return "<redacted-url>"


def is_text(data: bytes) -> bool:
    return b"\x00" not in data


def iter_files(root: str, excluded_dirs: set[str], skipped: dict) -> Iterable[str]:
    if os.path.isfile(root):
        yield root
        return
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        kept = []
        for d in sorted(dirnames):
            full = os.path.join(dirpath, d)
            if d in excluded_dirs:
                skipped["excluded_dirs"].append(full)
            elif os.path.islink(full):
                skipped["symlinks"].append(full)
            else:
                kept.append(d)
        dirnames[:] = kept
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            if os.path.islink(full):
                skipped["symlinks"].append(full)
                continue
            yield full


def scan(paths: list[str], excluded_dirs: set[str], max_files: int,
         max_file_bytes: int, max_total_bytes: int) -> dict:
    skipped: dict = {"excluded_dirs": [], "symlinks": [], "binary": [],
                     "too_large": [], "unreadable": []}
    findings: list[dict] = []
    capabilities: dict[str, dict] = {}
    seen: set[tuple[str, str, int]] = set()
    urls: set[str] = set()
    scanned = 0
    total_bytes = 0
    truncated = False

    for root in paths:
        for filename in iter_files(root, excluded_dirs, skipped):
            if scanned >= max_files or total_bytes >= max_total_bytes:
                truncated = True
                break
            try:
                size = os.path.getsize(filename)
            except OSError:
                skipped["unreadable"].append(filename)
                continue
            if size > max_file_bytes:
                skipped["too_large"].append(filename)
                continue
            try:
                with open(filename, "rb") as fh:
                    data = fh.read(max_file_bytes + 1)
            except OSError:
                skipped["unreadable"].append(filename)
                continue
            if not is_text(data):
                skipped["binary"].append(filename)
                continue
            total_bytes += len(data)
            scanned += 1
            text = data.decode("utf-8", errors="replace")
            rel = os.path.relpath(filename, os.getcwd())
            ext = os.path.splitext(filename)[1].lower()

            for rule, regex in COMPILED:
                if rule.extensions and ext not in rule.extensions:
                    continue
                for match in regex.finditer(text):
                    line_no = text.count("\n", 0, match.start()) + 1
                    excerpt = redact(text.splitlines()[line_no - 1].strip())[:200]
                    if rule.finding:
                        key = (rule.rule_id, rel, line_no)
                        if key in seen:
                            continue
                        seen.add(key)
                        findings.append({
                            "id": f"LSC-SCAN-{len(findings) + 1:03d}",
                            "rule": rule.rule_id,
                            "severity": rule.severity,
                            "category": rule.category,
                            "file": rel,
                            "line": line_no,
                            "excerpt": excerpt,
                            "message": rule.message,
                        })
                        if len(findings) >= 500:
                            truncated = True
                            break
                    if rule.capability:
                        cap = capabilities.setdefault(
                            rule.capability, {"name": rule.capability, "count": 0,
                                              "samples": []})
                        cap["count"] += 1
                        if len(cap["samples"]) < 5:
                            cap["samples"].append(
                                {"file": rel, "line": line_no, "excerpt": excerpt})
                    if rule.rule_id == "remote-fetch":
                        urls.add(sanitize_url(match.group(0).rstrip(".,;")))
                if len(findings) >= 500:
                    break
            if len(findings) >= 500:
                truncated = True
                break
        if truncated:
            break

    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f["severity"], 9),
                                 f["file"], f["line"]))
    counts = {s: 0 for s in ("RED", "YELLOW", "UNKNOWN", "GREEN")}
    for f in findings:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1

    return {
        "tool": "linux-security-check/scan-patterns",
        "version": 1,
        "roots": paths,
        "scanned_files": scanned,
        "total_bytes": total_bytes,
        "truncated": truncated,
        "counts": counts,
        "findings": findings,
        "capabilities": sorted(capabilities.values(), key=lambda c: c["name"]),
        "urls": sorted(urls)[:100],
        "skipped": {k: v[:50] for k, v in skipped.items()},
        "notes": [
            "Static pattern triage only; files were not executed, sourced, imported, or extracted.",
            "Pattern matches include false positives and miss context-dependent behavior. Review each location.",
            "Excluded by name: " + ", ".join(sorted(excluded_dirs)),
            "Truncated output/scan limits may hide later findings; inspect remaining files manually.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only static pattern scan (never executes samples).")
    parser.add_argument("paths", nargs="+", help="files or directories to inspect")
    parser.add_argument("--max-files", type=int, default=2000)
    parser.add_argument("--max-file-bytes", type=int, default=512 * 1024)
    parser.add_argument("--max-total-bytes", type=int, default=8 * 1024 * 1024)
    parser.add_argument("--exclude-dir", action="append", default=[],
                        help="additional directory name to skip")
    parser.add_argument("--no-default-excludes", action="store_true",
                        help="scan .git, node_modules, build, dist, etc.")
    parser.add_argument("--compact", action="store_true", help="single-line JSON")
    args = parser.parse_args()

    missing = [p for p in args.paths if not os.path.exists(p)]
    if missing:
        print(json.dumps({"error": "path not found", "paths": missing}),
              file=sys.stderr)
        return 2
    if args.max_files < 1 or args.max_file_bytes < 1 or args.max_total_bytes < 1:
        print(json.dumps({"error": "limits must be positive"}), file=sys.stderr)
        return 2

    excluded = set() if args.no_default_excludes else set(EXCLUDED_DIRS)
    excluded.update(args.exclude_dir)

    result = scan(args.paths, excluded, args.max_files, args.max_file_bytes,
                  args.max_total_bytes)
    print(json.dumps(result, indent=None if args.compact else 2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
