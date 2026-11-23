# Software Update Safety Assessment

Decide whether an update is advisable **now**, what it fixes, what it may break, and what precautions are needed. Never run `pacman -Syu`, AUR upgrades, installs, removals, downgrades, or rollbacks without explicit authorization.

## 1. Establish current and available versions

Read-only checks:

```bash
pacman -Q <pkg>
pacman -Si <pkg> | grep -E '^(Repository|Name|Version|Depends On|Conflicts With|Replaces|Packager|Build Date)'
checkupdates 2>/dev/null | head -60      # pacman-contrib; no system upgrade
pacman -Qu 2>/dev/null
```

AUR/foreign packages:

```bash
pacman -Qm
git -C <aur-clone> fetch --all --tags && git -C <aur-clone> log --oneline -10
```

For other ecosystems: `npm outdated`, `pip index versions`, upstream release pages. Record exact current and candidate versions and the source of the candidate.

## 2. Authenticity and channel

- Official repo package: signed, built by a packager, distributed by Arch mirrors.
- AUR: recipe, not a binary; the built artifact is only as trustworthy as the recipe and build environment.
- Third-party repo/Flatpak/AppImage/vendor binary: separate trust boundary; verify key/signature/checksum.
- Git install: exact commit/tag, signed tags/commits, build from pinned source.
- Self-updating app: mutable channel, signature/checksum, rollback support.

Flag HTTP downloads, disabled signature checks, unpinned branches, and update mechanisms that execute remote code.

## 3. Read the change, not just the version

- Release notes and changelog.
- Commit/PR diff for security-relevant changes.
- Package build diff (`PKGBUILD`, patches, dependencies, install script).
- Arch news (https://archlinux.org/news/) and package page.
- Upstream issue tracker for regressions and known breakage.
- Distribution security advisories (Arch Security Team/ASA), NVD, OSV, GitHub advisories, project security bulletins.

Determine:

- Is this a security fix, a bug fix, a feature release, or a rebuild?
- Does it change dependencies, sonames, config schema, CLI flags, data format, or minimum kernel/GPU requirements?
- Are there migrations, one-way data upgrades, or config rewrites?
- Does it replace/rename/conflict with installed packages?
- Does it drop support for your hardware, filesystem, initramfs setup, or session?

## 4. CVE and advisory discipline

Do not equate a version match with exploitability. Verify:

- Affected version range and whether the installed/candidate version is actually affected.
- Whether the distribution backported the fix or patched around it.
- Build configuration and optional features required for exploitation.
- Whether the vulnerable component is reachable in this setup.
- Whether exploitation requires local access, user interaction, a service exposed to the network, or specific hardware.
- Whether a fix is available and whether the update is the minimal way to get it.

A CVE with no exposure may be lower priority than a regression that breaks the desktop. A feature update that also fixes a CVE is still primarily a compatibility risk.

## 5. Arch rolling-release rules

- Arch supports **full upgrades**, not partial upgrades. Do not recommend upgrading one library/package while leaving the rest stale.
- Read Arch news before a large update; check for manual interventions.
- Plan a single `pacman -Syu` window (with approval), not piecemeal package updates.
- Rebuild AUR/foreign packages against updated libraries when needed.
- Review `.pacnew`/`.pacsave` files; do not blindly overwrite configs.
- Kernel/driver updates may require reboot; initramfs and bootloader must remain valid.
- Keep a fallback kernel (`linux-lts`) if the setup supports it.
- Know the rollback path before updating: Btrfs/snapper snapshot, filesystem backup, or cached packages. Do not assume downgrade is safe.

Never mix repos or force dependency resolution to make a partial update fit.

## 6. Omarchy-specific compatibility

Check:

- Omarchy version and release notes; Omarchy changes can include shell, theme, Hyprland, Quickshell, and config migrations.
- Hyprland config syntax and deprecated options; keybindings, monitors, layer rules, plugins.
- Quickshell/Omarchy shell API changes and plugin compatibility.
- Omarchy shell plugins and themes that may break on shell updates.
- Omarchy migrations and whether they rewrite user config.
- Wayland/session integration, portals, screen sharing, input methods.
- Kitty, Neovim, OpenCode, and shell configuration that depend on updated binaries.
- Whether an update resets or overwrites dotfiles-managed configuration; check before and after, do not assume.

If Omarchy's own update mechanism is involved, inspect what it does and whether it upgrades the whole system. Do not execute it during assessment.

## 7. GPU, kernel, DKMS, and firmware

- NVIDIA: driver branch vs kernel version, `nvidia` vs `nvidia-open` vs `nvidia-dkms`, Wayland support, known regressions, module signing, initramfs modules.
- DKMS: rebuild against the new kernel; missing headers or compiler mismatch breaks modules (NVIDIA, VirtualBox, ZFS, VMware, Wi-Fi).
- Kernel: module ABI, out-of-tree modules, filesystem support, firmware, microcode, Secure Boot signing.
- ZFS: kernel compatibility is strict; never update the kernel before the ZFS module supports it.
- Laptop/hardware: Wi-Fi, Bluetooth, GPU, suspend/resume regressions; check model-specific reports.
- Firmware (linux-firmware, BIOS/EC): rare but plausible regressions; check vendor notes.

Recommend deferring kernel/GPU updates when a critical module has no compatible build, or staging them with a known fallback.

## 8. Precautions by risk level

**Low risk** (leaf app, no deps, config-compatible):

- Normal update with approval; keep previous package cache.

**Medium risk** (desktop components, libraries, AUR rebuilds):

- Read release notes and Arch news.
- Snapshot/backup user config.
- Update in one transaction; reboot if required.
- Have a fallback kernel/session and a rollback plan.

**High risk** (kernel, GPU, filesystem, bootloader, Omarchy shell, major version jump):

- Take a verified snapshot or backup first.
- Verify free space and bootloader health.
- Check module/plugin compatibility and upstream regressions.
- Choose a time with recovery access (live USB).
- Update everything together, reboot, verify session/network/audio/GPU, and know how to roll back.
- Do not combine with unrelated risky changes.

## 9. Post-update verification (recommend, do not perform without approval)

```bash
uname -r
systemctl --failed
journalctl -p err -b --no-pager | tail -40
pacman -Qkk <critical-packages>
```

Check: boot, display/session, network, audio, microphone, camera, GPU acceleration, suspend, DKMS modules (`dkms status`), key applications, and Omarchy shell/plugins. Watch for `.pacnew` files.

## 10. Verdict

Use one of:

- **Update now:** low risk and/or important security fix; precautions noted.
- **Update with precautions:** advisable, but snapshot/backup and a rollback plan are required.
- **Defer:** no urgent security need and known compatibility risk; define what must change before updating.
- **Do not update:** incompatible with current hardware/config or unacceptable regression risk; propose an alternative or wait condition.
- **Insufficient evidence:** release notes/advisories unavailable or the change cannot be assessed.

State what the update fixes, what it may break, required precautions, whether a reboot is likely, and what remains unknown. Do not claim an update is "safe"; say what was reviewed.
