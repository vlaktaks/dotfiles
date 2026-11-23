# Omarchy Plugin Security Audit

Answer the question: **is this exact plugin revision safe to install and run?** Separate official-contract compliance, source security, runtime risk, missing evidence, and recommendation.

Official references (verify current versions before relying on details):

- Development: https://plugins.omarchy.org/develop.html
- Publishing: https://plugins.omarchy.org/publish.html
- Marketplace: https://github.com/omacom/omarchy-plugin-marketplace
- Marketplace security baseline: `SECURITY.md` in that repository
- Marketplace verification model: `VERIFICATION.md` in that repository
- Shell/plugin contract: https://github.com/omacom/omarchy/tree/quattro/shell

## Trust context (state this in the report)

- Plugins run **unsandboxed inside the shared, long-running Omarchy shell (Quickshell) process** with the user's permissions.
- Marketplace validation checks a listing's **exact commit** with deterministic static patterns. It is **not a security audit, certification, endorsement, or guarantee**.
- Upstream code can change after review. `omarchy plugin add`/`update` currently fetch **mutable upstream HEAD** and are not commit-bound. A previously verified commit does not protect a newer commit.
- Popularity, stars, automated "passed" labels, and a valid manifest do not establish safety.
- Never enable or install the plugin as part of the audit.

## 1. Scope and exact revision

Accept: GitHub/GitLab URL, local directory, specific commit, tag, or marketplace plugin ID.

Resolve to an immutable full commit SHA. For a repository:

```bash
git clone --filter=blob:none --no-checkout <url> /tmp/lsc-plugin-<random>
cd /tmp/lsc-plugin-<random>
git fetch --all --tags
git rev-parse HEAD
git log -1 --format='%H%n%an <%ae>%n%ad%n%s'
```

Then check out the exact revision to inspect (checkout does not execute code):

```bash
git checkout --detach <full-sha>
```

Do not use `--recurse-submodules`; inspect submodules separately. For a local directory, record the path, `git rev-parse HEAD` if available, and whether the working tree is dirty.

For a marketplace listing, record:

- listing plugin ID and repository,
- `listingValidatedCommit` (the exact verified snapshot SHA),
- current upstream HEAD observed,
- verification status (`Snapshot verified`, `Update unverified`, or `Unverified`).

If the inspected SHA differs from the verified SHA, write: **"The inspected revision and the marketplace-verified revision are not identical; the older verification does not cover this code."**

## 2. Stage safely

Copy or clone the plugin to a temporary directory outside `~/.config/omarchy/plugins`. Do not run `omarchy plugin clone` (it creates/enables a live plugin), `omarchy plugin add`, or any command that registers it with the shell.

Manifest and layout validation is safe on a staged directory:

```bash
omarchy plugin validate <staged-dir>
python3 <skill>/scripts/check-omarchy-manifest.py <staged-dir>
```

If `qmllint` is installed, lint only files that exist, without loading the plugin:

```bash
qmllint -I "$OMARCHY_PATH/shell" <staged-dir>/<EntryPoint>.qml
```

`omarchy plugin validate` and `qmllint` check structure/syntax, not intent or safety. If the tools are unavailable, report the gap.

## 3. Manifest contract

A current manifest is JSON with:

```json
{
  "schemaVersion": 1,
  "id": "yourname.plugin",
  "name": "Plugin name",
  "version": "1.0.0",
  "author": "Your name",
  "description": "What the plugin does.",
  "kinds": ["bar-widget"],
  "entryPoints": { "barWidget": "BarWidget.qml" }
}
```

Validate:

- `schemaVersion` is the supported integer (currently `1`).
- `id` is namespaced, stable, and does not use the reserved `omarchy.*` namespace.
- `name`, `version`, `author`, `description` are present and plausible.
- `kinds` is a non-empty list of supported kinds.
- `entryPoints` contains the key for every declared kind and points to an existing regular file with a safe relative path.
- No symlinks anywhere in the plugin directory.
- Manifest entry-point paths do not escape the plugin directory.
- Referenced files are actually loaded; watch for unused or misleading entry points.

Kind-to-entry-point mapping (current Quattro contract):

| Kind | Entry key | File |
| --- | --- | --- |
| `bar-widget` | `barWidget` | `BarWidget.qml` |
| `panel` | `panel` | `Panel.qml` |
| `overlay` | `overlay` | `Overlay.qml` |
| `menu` | `menu` | `Menu.qml` |
| `service` | `service` | `Service.qml` |
| `bar` | `bar` | `Bar.qml` |

Also check nested QML loaded by the entry point (`Loader`, `source`, `import`, `Qt.createQmlObject`). The manifest is not the whole reachable surface.

## 4. Full execution chain

Build the chain:

```text
manifest -> entry point QML -> nested QML/JS -> process/service/file/network APIs
         -> install.sh/update.sh helpers -> downloaded payloads -> persistence
```

Inspect every reachable file, including helper scripts referenced by install/update/uninstall, bundled JS, generated assets, and service definitions. Filenames like `install.sh`, `setup`, `update`, `helper`, and extensionless executables are high priority.

Use `malware-analysis.md` for script-level patterns. Additionally inspect:

- `Process`/`Quickshell.Io.Process`/`exec`/`sh -c` calls and how arguments are built.
- `XMLHttpRequest`, `fetch`, WebSocket, image loading from remote URLs.
- `FileView`/file APIs and what paths are read/written.
- Clipboard, notifications, DBus, MPRIS, Hyprland dispatch, shell command execution.
- Microphone, camera, screen capture, or keystroke access.
- Autostart, keybindings, shell integration, and changes to Omarchy internals.
- `sudo`/`pkexec`, systemd units, package managers, remote builds, and mutable downloads.

## 5. Capability-to-purpose mismatch

List the plugin's stated purpose, then every capability it actually needs. Flag capabilities unrelated to that purpose:

- A clock widget that reads SSH keys or browser cookies.
- A theme switcher that opens network connections or starts services.
- A bar widget that needs `sudo`, modifies system files, or installs packages.
- A plugin that captures audio/camera/clipboard without a clear feature.
- A plugin that downloads and executes code at runtime.
- A plugin that self-updates from a mutable branch.

Capabilities are not proof of malice, but unexplained ones are a strong warning.

## 6. Installer, updater, and lifecycle

If present, read `install.sh`, `uninstall.sh`, `update.sh`, setup scripts, and anything they call.

Check for:

- Download-and-execute (`curl|sh`, `wget|bash`), unverified remote scripts, missing checksums/signatures.
- `sudo`, `pkexec`, sudoers edits, setuid/capabilities.
- systemd system/user units, timers, autostart, cron.
- Modification of Omarchy/Hyprland/Quickshell/Omarchy shell files or plugin directories.
- Package manager calls, `makepkg`, `cargo install --git`, `pip install git+`, `npm install <url>`.
- Writes outside the plugin/config directory, destructive deletion, or overwriting user config.
- Update mechanism that pulls mutable HEAD and executes it.
- Hidden behavior, telemetry, or contacting unrelated servers.
- Uninstall behavior that leaves persistence or deletes unrelated data.

The marketplace baseline's documented findings include `curl-pipe-shell`, unpinned `cargo install --git`, unpinned remote Git execution, dangerous passwordless sudoers rules, and privileged process control from predictable `/tmp` PID files. Review capabilities include installers, package managers, privilege use, remote builds, bundled executable binaries, service management, and sudoers modification. Use these as review prompts, not as the only checks.

## 7. Supply chain

Inspect:

- Repository owner, maintainers, contributors, and ownership changes.
- Commit history around entry points, installers, and update logic; recent suspicious changes.
- Tags/releases and whether they point to reviewed commits.
- Submodules and vendored dependencies.
- External download URLs and their domains, TLS, pinning, and checksums.
- GitHub Actions: unpinned third-party actions, `pull_request_target`, secrets, artifact provenance.
- Bundled/generated binaries, minified bundles, and executables without source.
- Package scripts and dependency sources.
- Release signing and commit signing, if present.
- Stars/forks/downloads as context only, never as trust.

## 8. Exact-commit comparison

Record both SHAs and the verification status. State clearly:

- verified SHA, inspected SHA, whether identical;
- what the verification covered (static baseline patterns/capabilities, exact commit, no execution);
- whether later upstream commits exist and are covered;
- that install/update commands are mutable and may fetch different code.

Do not describe a plugin as "verified safe." Say "the exact snapshot passed the documented automated baseline; this is not a security audit."

## 9. Required conclusion

The report must contain five separate statements:

1. **Official compliance:** Does the manifest/layout satisfy the current Omarchy contract? Which checks passed or failed?
2. **Source security:** What does the reachable code actually do? List capabilities, data access, network endpoints, privilege use, persistence.
3. **Installation and runtime risk:** What happens on install/update/use? Blast radius inside the shared shell process? Reversibility?
4. **Missing evidence:** What could not be inspected (tools unavailable, packed binaries, private deps, TLS payloads, runtime behavior)? What would confirm safety or malice?
5. **Recommendation:** One of the verdicts from `report-format.md`, with conditions.

A plugin can satisfy every manifest requirement and still contain malware. Never let "valid manifest" or "marketplace verified" replace source review.

## 10. Report checklist

- Exact repository, commit, tag/branch, and plugin ID.
- Marketplace verified commit vs inspected commit.
- Manifest validation results and tool versions/absence.
- Full reachable file list and entry-point chain.
- Findings with severity, file:line, evidence, impact, confidence.
- Capability inventory and purpose mismatch.
- Installer/updater behavior and persistence.
- Supply-chain observations.
- Limitations and unknowns.
- Recommendation and safe installation conditions (pin exact commit, review diff before update, disable network if feasible, remove if unused).
