# Full Linux System Security Audit

Read-only workflow for Arch Linux, Omarchy, and general Linux systems. Adapt commands to what is installed. Record every missing tool and permission error as a limitation.

## Rules for this mode

- Never run `pacman -Syu`, `-Sy`, `-S`, `-R`, AUR helpers, or installers during an audit.
- Never kill processes, disable services, change sysctls, alter permissions, or edit configs. Recommend only.
- Prefer `timeout`, `-xdev`, explicit directories, and limited output (`head`, `tail`, `--no-pager`).
- Do not dump `/proc/<pid>/environ`, shell history, key material, or full home contents. Inspect metadata and targeted paths.
- Use `sudo -n` for any sudo check so it fails instead of prompting. A failed privilege check is a limitation.

## 1. Environment

```bash
cat /etc/os-release
uname -a
getconf LONG_BIT
timedatectl 2>/dev/null | head -10
uptime
cat /proc/cmdline
```

Record distribution, kernel, architecture, boot parameters, and whether this is Omarchy (`omarchy` present, `/usr/share/omarchy`). Unexpected kernel parameters or a very old kernel relative to installed packages are worth noting.

## 2. Packages, provenance, and updates

```bash
pacman -Q | wc -l
pacman -Qe                     # explicitly installed
pacman -Qm                     # foreign/AUR packages
pacman -Qtdq 2>/dev/null       # orphaned dependencies
pacman -Qkk <package>          # file integrity for a bounded package set
pacman -Qii <package>          # source, install reason, scriptlets
pacman -Qi pacman | grep -E '^(Version|Packager|Build Date|Install Script)'
cat /etc/pacman.conf | grep -vE '^\s*#|^\s*$'
pacman-conf --repo-list 2>/dev/null
```

For updates without installing:

```bash
checkupdates 2>/dev/null        # pacman-contrib; uses a temporary synced DB copy
pacman -Qu 2>/dev/null          # against current local DB only
arch-audit 2>/dev/null          # if installed; package vulnerability view
```

- Foreign packages (`pacman -Qm`) need provenance review: AUR helper, manual `makepkg`, or vendored binary.
- `pacman -Qkk` on every package is slow. Bound it to security-relevant packages (`sudo`, `openssh`, `glibc`, `pacman`, `linux`, `systemd`, `polkit`, `dbus`, `hyprland`, `quickshell`, `omarchy-*`). Report checksum/size/mtime mismatches and missing files.
- Check `SigLevel` and enabled repos. Extra third-party repos or `TrustAll` are risk signals.
- Orphan count is hygiene, not a vulnerability.
- If `arch-audit`/`checkupdates` are absent, state that vulnerability/update coverage is incomplete.

Other distributions: `apt list --upgradable`, `apt-get -s upgrade`, `dnf check-update`, `zypper lu`, `rpm -Va`, `debsums -c`. Simulate; never upgrade.

## 3. Processes

```bash
ps -eo pid,ppid,user,pcpu,pmem,etime,stat,args --sort=-pcpu | head -40
ps -eo pid,user,args | grep -E '(/tmp/|/dev/shm/|/var/tmp/|/home/[^ ]+/\.[^ ]+)' | grep -v grep
ps -eo pid,user,comm,args | awk '$3 ~ /^(nc|ncat|socat|xmrig|minerd|cpuminer|masscan|zmap)$/'
```

For any suspicious PID:

```bash
ls -l /proc/<pid>/exe /proc/<pid>/cwd
tr '\0' ' ' < /proc/<pid>/cmdline; echo
cat /proc/<pid>/status | grep -E '^(Name|Uid|Gid|CapEff|NoNewPrivs|Seccomp)'
systemctl status <pid> 2>/dev/null | head -5   # if known
```

Signal interpretation:

- Execution from `/tmp`, `/dev/shm`, or a hidden home path is suspicious but can be legitimate (build tools, AppImage, game launchers).
- Deleted executable (`/path (deleted)`) warrants investigation.
- High CPU alone is not a cryptominer; correlate with network, command line, and persistence.
- CapEff with many capabilities is a privilege signal, especially for non-root processes.
- Root-owned processes with odd names are not automatically malicious; verify the owning package (`pacman -Qo /proc/<pid>/exe`).

## 4. Services, timers, and session startup

```bash
systemctl list-units --type=service --state=running --no-pager
systemctl list-units --type=service --state=failed --no-pager
systemctl list-unit-files --state=enabled --no-pager
systemctl --user list-units --type=service --state=running --no-pager
systemctl --user list-unit-files --state=enabled --no-pager
systemctl list-timers --all --no-pager
systemctl --user list-timers --all --no-pager
systemd-analyze security <unit> 2>/dev/null | tail -20
```

For each unexpected unit:

```bash
systemctl cat <unit>
systemctl show <unit> -p FragmentPath -p ExecStart -p User -p Restart -p Environment
```

Check `ExecStart`, `ExecStartPre`, `ExecStop`, `Environment`, `User`, `WorkingDirectory`, and unit file ownership. A unit running a shell with `-c`, a script under `/tmp`, or a downloader is high risk. Check drop-ins (`*.d/*.conf`) too.

User units and timers are a common unprivileged persistence path. Compare enabled units with packages that should own them.

## 5. Cron, autostart, and shell startup

```bash
crontab -l 2>/dev/null
ls -la /etc/cron.* /etc/cron.d /var/spool/cron 2>/dev/null
ls -la ~/.config/autostart /etc/xdg/autostart 2>/dev/null
grep -R --include='*.desktop' -nE '^(Exec|TryExec)=' ~/.config/autostart /etc/xdg/autostart 2>/dev/null
```

Review shell startup reachable by the user and root:

```bash
ls -la ~/.bashrc ~/.bash_profile ~/.profile ~/.config/fish/config.fish ~/.zshrc 2>/dev/null
grep -nE 'curl|wget|base64|eval|source|\. |http://|https://' ~/.bashrc ~/.bash_profile ~/.profile 2>/dev/null | head -60
ls -la /etc/profile.d/ 2>/dev/null
grep -R -nE 'curl|wget|base64|eval|/tmp/|/dev/shm/' /etc/profile.d 2>/dev/null | head -40
```

Do not print secret values from startup files. Report the line and category, redact tokens.

Also inspect: `~/.config/environment.d/`, `~/.config/systemd/user/*.service`, udev rules (`/etc/udev/rules.d`, `RUN+=`), pacman hooks (`/etc/pacman.d/hooks`), `~/.config/omarchy/`, Hyprland `exec`/`exec-once`, and Omarchy shell/plugin autostart.

## 6. Network exposure and egress

```bash
ss -tulpn
ss -tupn state established
ss -tupn state established '( dport = :443 or dport = :80 )'
lsof -i -P -n 2>/dev/null | head -60
cat /etc/resolv.conf
ip route
```

- `ss -p` shows process info only for processes you can inspect; missing process names are a limitation, not evidence of hiding.
- Unexpected public listeners are higher risk than localhost listeners. Verify the owning package and purpose.
- Outbound connections to rare domains, raw IPs, unusual ports, or dynamic-DNS providers warrant correlation with the owning process.
- Check proxy configuration: `env | grep -iE 'proxy'`, `/etc/environment`, `~/.config/environment.d/`, shell rc. An unexpected proxy can indicate interception or exfiltration.
- DNS inspection is limited by encrypted DNS and caches. Do not send queries to third-party resolvers without approval.

## 7. Privileges, SUID/SGID, capabilities, and sudo

```bash
sudo -n -l 2>&1 | head -40
find /usr/bin /usr/sbin /usr/local/bin /usr/local/sbin /opt -xdev -perm /6000 -type f -printf '%m %u:%g %p\n' 2>/dev/null
getcap -r /usr /opt 2>/dev/null | head -80
cat /etc/ld.so.preload 2>/dev/null
ls -la /etc/ld.so.conf.d/ 2>/dev/null
```

- Compare unexpected SUID/SGID files with `pacman -Qo <file>`. A file not owned by a package is a strong signal.
- Dangerous capabilities include `cap_setuid`, `cap_setgid`, `cap_sys_admin`, `cap_sys_ptrace`, `cap_dac_override`, `cap_net_raw` on unexpected binaries.
- `NOPASSWD: ALL` or wildcard sudo rules for shells/interpreters/systemctl are high risk.
- Inspect `~/.ssh`, `~/.gnupg`, and credential stores only for permissions and unexpected files, never contents.
- Check writable PATH directories: `IFS=:; for d in $PATH; do [ -w "$d" ] && echo "$d"; done`. A user-writable directory earlier in root's PATH is a privilege-escalation path.

## 8. SSH and credentials

```bash
ls -la ~/.ssh 2>/dev/null
stat -c '%a %U:%G %n' ~/.ssh ~/.ssh/* 2>/dev/null
cat ~/.ssh/config 2>/dev/null | grep -vE '^\s*#|^\s*$' | head -40
sshd -T 2>/dev/null | grep -Ei '^(permitrootlogin|passwordauthentication|pubkeyauthentication|x11forwarding|allowtcpforwarding|port)'
```

Expected permissions: `~/.ssh` 700, private keys 600, `authorized_keys`/`config` 600 or 644. Group/world-writable SSH material is a finding. Unknown keys in `authorized_keys` require user confirmation, not automatic deletion. `sshd -T` may need root; if unavailable, mark configuration coverage as limited. Never print key material.

## 9. Filesystem and persistence hygiene

```bash
find /etc /usr/local /opt /var/spool/cron -xdev -type d -perm -0002 -printf '%m %u:%g %p\n' 2>/dev/null | head -40
find /tmp /var/tmp /dev/shm -xdev -maxdepth 2 -type f -perm -111 -printf '%TY-%Tm-%Td %TH:%TM %m %u %p\n' 2>/dev/null | head -40
ls -la /etc/systemd/system /etc/systemd/user 2>/dev/null
```

- World-writable files in `/etc`, `/usr/local`, or cron paths are serious.
- Executables in `/tmp`/`/dev/shm` are suspicious, but transient build artifacts exist. Correlate with processes and timestamps.
- Check recently modified security-relevant configs with `stat` on a bounded list, not a full-home scan.
- Look for unexpected files under `~/.config/systemd/user`, `~/.config/autostart`, `~/.local/share`, and Omarchy/Hyprland config directories. Reference paths, do not dump content.

## 10. Logs and recent activity

```bash
journalctl -p err -b --no-pager | tail -60
journalctl -u sshd -b --no-pager | tail -40
journalctl _COMM=sudo -b --no-pager | tail -40
last -n 20 2>/dev/null
lastb -n 20 2>/dev/null
```

Look for repeated authentication failures, unexpected sudo escalation, service crash loops, OOM kills, kernel taint, and USB/device events. Logs may be rotated, volatile, or inaccessible; say so. Do not exfiltrate logs.

## 11. Arch and Omarchy specifics

- **AUR packages** are built from user-submitted recipes; review PKGBUILD provenance (see `software-supply-chain.md`).
- **Omarchy** layers shell, Hyprland, Quickshell, themes, and plugins on Arch. Check `omarchy` version and whether system files were modified away from package defaults.
- **Hyprland/Quickshell** configs can execute commands (`exec`, `exec-once`, QML `Process`). Treat user config and third-party plugins as code.
- **NVIDIA/DKMS/kernel** mismatches are availability risks, not malware. Track them for the update mode.
- **pacman hooks** run as root during package transactions. Unexpected hooks are high risk.
- Compare key system files with package ownership (`pacman -Qo`) before calling a modification suspicious.

## 12. Evidence quality and classification

Before writing findings, answer:

- What exactly was observed (command, path, line, output)?
- Is the component package-owned and expected?
- Does the behavior require privilege, network, or user interaction?
- Is there a legitimate explanation? State it.
- What would confirm or refute the concern?
- What could not be checked, and why?

Classify:

- **GREEN:** check completed and normal.
- **YELLOW:** anomalous, unexplained, weak configuration, or incomplete evidence with a plausible risk.
- **RED:** confirmed malicious behavior, an unowned privileged binary, credential exfiltration, active backdoor/persistence, or a directly exploitable high-impact misconfiguration.
- **UNKNOWN:** permission denied, tool missing, or scope not covered.

End with the report structure from `report-format.md`. Do not claim the machine is clean; state the inspected scope and residual unknowns.
