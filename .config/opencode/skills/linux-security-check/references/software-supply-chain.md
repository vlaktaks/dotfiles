# Software Installation and Supply-Chain Review

Determine what will actually run during install, build, first launch, and update. Do not download and execute arbitrary code to find out.

## 1. Identify the real artifact

Ask/establish:

- Package name, version, exact source (official repo, AUR, GitHub/GitLab, vendor site, archive, AppImage, PyPI, npm).
- Install method (package manager, `makepkg`, `curl|sh`, `pip`, `npm`, binary download, AppImage).
- Whether it installs system-wide, per-user, or runs from a directory.
- Exact commit/tag/hash. Prefer immutable versions over branches and "latest".
- What it will be able to access (network, files, microphone, camera, session bus, sudo).

Prefer, in order: distribution package, signed release artifact with verified checksum, reproducible build from pinned source. Avoid unpinned `curl|sh` installers.

Never run the installer during the audit. Downloading source for static inspection is acceptable.

## 2. Arch official packages

```bash
pacman -Si <pkg>
pacman -Qip <pkg.pkg.tar.zst>
pacman -Qo <file>
pacman -Qkk <pkg>
```

Check repository, packager, build date, dependencies, optional dependencies, install script, size, and signature. Official repos are maintained and signed, but package compromise and build-system compromise still exist. Check Arch news and the security tracker for the package.

Third-party repositories are a separate trust decision: inspect their key, maintainers, `SigLevel`, and update process. Mixing repos can create dependency and trust problems.

## 3. AUR packages

AUR is user-submitted build recipes, not a binary repository.

```bash
git clone --filter=blob:none https://aur.archlinux.org/<pkg>.git /tmp/lsc-aur-<pkg>
cd /tmp/lsc-aur-<pkg>
```

Inspect:

- `PKGBUILD`, `.install`, `SRCINFO`, and every sourced file.
- `source=()`: official upstream URLs, pinned tags/commits (`#commit=<sha>`), checksum algorithms (`sha256sums`, `b2sums`, `validpgpkeys`).
- `SKIP` checksums, mutable branches, `master`/`main` tarballs, `git+` without a commit.
- `prepare()`, `build()`, `package()`, `pkgver()`: network access, execution of downloaded code, writes outside `$srcdir`/`$pkgdir`, privilege use.
- `install=` scriptlets: pre/post install/upgrade/remove behavior, systemd units, users, sudo.
- Dependencies and `makedepends` from unusual sources.
- Maintainer, orphan status, ownership changes, comments, out-of-date flags, votes/popularity (context only).
- Whether the package builds from source or repackages a binary.

`makepkg` executes the recipe. Do not run it without explicit approval and a plan (ideally a clean build environment). `namcap PKGBUILD` and `shellcheck` are useful if installed.

AUR packages commonly require building dependencies; "it's just a PKGBUILD" does not mean read-only. Review the whole build graph.

## 4. GitHub/GitLab projects

- Resolve the exact commit or signed tag. Record the SHA.
- Check release assets: checksums, signatures, provenance, and whether the asset matches the source.
- Read install instructions, but treat them as untrusted. Identify any `curl|sh`, `sudo`, systemd, or config-overwrite steps.
- Inspect build scripts (`Makefile`, `CMakeLists.txt`, `meson.build`, `build.rs`, `package.json`, `pyproject.toml`) for downloads, subprocess execution, and network access during build.
- Check CI workflows for unpinned actions, `pull_request_target`, secret access, and artifact signing.
- Check submodules, vendored code, generated binaries, and minified bundles.
- Review maintainer history and recent security-relevant commits.
- Prefer building from a pinned source tarball with verified checksum over running a convenience installer.

## 5. AppImages

- Verify SHA-256 and, when available, a minisign/GPG signature from the project.
- Identify the AppImage type, runtime, architecture, and update information (`--appimage-offset`, `readelf`, `strings`, `zsync` URL).
- List contents without running: `unsquashfs -l`, `7z l`, or `--appimage-offset` + bounded `unsquashfs -l`.
- Inspect `AppRun`, desktop file, bundled binaries/libraries, and any network/update scripts.
- Check whether it writes to `~/.config`, `~/.local`, autostart, or systemd.
- A signature proves who signed it, not that the code is safe.

Do not run the AppImage, including `--appimage-extract-and-run`, during analysis. Extraction writes files; list first and extract only to an isolated temp directory if necessary, without execution.

## 6. Archives and local installers

List before extracting: absolute paths, `../` traversal, symlinks to sensitive locations, hardlinks, device files, setuid bits, hidden files, and scripts.

Check `install.sh`/`setup`/`Makefile` for downloads, `sudo`, writes outside the prefix, service installation, shell rc edits, and uninstall behavior. Verify checksums against the publisher. Prefer a package or a user-local installation with a clear removal path.

## 7. Python packages

```bash
pip index versions <pkg> 2>/dev/null
pip download --no-deps --no-binary :all: <pkg> -d /tmp/lsc-pypi
```

Inspect the sdist/wheel: `setup.py`, `pyproject.toml`, build backend, `setup.cfg`, `MANIFEST.in`, `.pth` files, entry points, and bundled binaries. Build backends and `setup.py` run code during installation; do not install an untrusted package to inspect it. `pip download` fetches without installing.

Check:

- Project URLs, maintainers, release history, and sudden ownership changes.
- Typosquatting and dependency confusion (a private package name resolving to a public index).
- Install-time scripts, network calls, and subprocess use (see `malware-analysis.md`).
- Unpinned git/URL dependencies and transitive dependencies.
- Wheel vs sdist differences and unexpected files.

`pip install --dry-run` still resolves metadata and may execute build requirements for some backends; prefer download and inspect.

## 8. npm packages

```bash
npm view <pkg> --json
npm pack <pkg> --pack-destination /tmp/lsc-npm   # downloads tarball, does not run scripts
```

Inspect the tarball (`tar -tf`, bounded extraction without execution), `package.json` lifecycle scripts (`preinstall`, `install`, `postinstall`, `prepare`), bin entries, dependencies from git/URLs, maintainers, publish times, and repository links.

Check typosquatting, dependency confusion, compromised maintainer accounts, sudden new maintainers, obfuscated/minified code, and install scripts that fetch or execute remote content. `npm install --ignore-scripts` reduces exposure but does not make a malicious package safe at runtime.

## 9. Cross-cutting supply-chain checks

- **Typosquatting:** compare the exact name with the official project; check punctuation, homoglyphs, and scope.
- **Dependency confusion:** private names published publicly, or version ranges resolving to an attacker-controlled higher version.
- **Ownership change:** new maintainer, revived dormant package, transferred repository, changed signing key.
- **Malicious update:** a clean version followed by a compromised release; check recent releases, not just the version you intend to install.
- **Unsafe update channel:** mutable branch, unsigned self-update, HTTP downloads, no rollback.
- **Hidden install behavior:** sudo, systemd, autostart, shell rc edits, telemetry, background services.
- **Bundled binaries:** opaque executables shipped inside source packages, wheels, npm tarballs, or AppImages.
- **Permissions:** does the software need root, audio, camera, keyring, or network access to perform its stated function?

## 10. Decision matrix

| Evidence | Typical classification |
| --- | --- |
| Official signed package, current, no unexplained behavior | GREEN with normal caution |
| Reputable source, unpinned but reviewed, install requires build | YELLOW: pin and verify |
| Opaque binary, no checksum/signature, unexpected capabilities | YELLOW or RED depending on behavior |
| Installer downloads and executes unverified remote code | RED |
| Credential access, persistence, exfiltration, or security disabling | RED |
| Cannot inspect due to packing/encryption/tool gaps | UNKNOWN, not safe |

Report exact artifact, version, SHA/checksum, install path, findings, capabilities, limitations, and a recommendation. If the user only needs the feature, suggest a safer alternative (official package, pinned build, sandbox/container, Flatpak with reviewed permissions) as an option, not a mandate.
