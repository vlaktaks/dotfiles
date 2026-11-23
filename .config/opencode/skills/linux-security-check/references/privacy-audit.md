# Microphone, Camera, and Privacy Audit

Answer: is a microphone/camera being used, by what, and is there evidence of transmission? Distinguish observation from inference. Never claim audio or video was transmitted without evidence of the payload.

## Evidence levels (use these words)

1. **Available** — a capture device exists and is visible to the stack.
2. **Unmuted** — the source is not muted. This alone does not mean recording.
3. **Active capture client** — a client is connected to a capture stream/node.
4. **Suspicious capture activity** — hidden/background recorder, unexpected client, capture plus persistence/obfuscation.
5. **Network connection observed** — a process has a socket. This alone does not mean it sent audio.
6. **Consistent with exfiltration** — capture client plus network plus suspicious destination/behavior, with no legitimate explanation found.
7. **Exfiltration confirmed** — evidence of audio data leaving (captured payload, logs, file transfer, controlled test). Rare without instrumentation.

A process can hold a microphone stream and a network socket for entirely legitimate reasons (a video call). Correlation is a lead, not proof.

## 1. Detect the audio stack

```bash
pactl info 2>/dev/null
systemctl --user status pipewire wireplumber pipewire-pulse --no-pager 2>/dev/null | head -40
wpctl status 2>/dev/null
pw-cli info 0 2>/dev/null | head -40
```

Common stacks: PipeWire with WirePlumber, PipeWire's PulseAudio compatibility layer, or plain PulseAudio. Commands vary by version; prefer `wpctl`/`pw-dump` on Omarchy, fall back to `pactl`.

If the tools are missing or the session bus is inaccessible (e.g. run as another user), state the limitation.

## 2. Enumerate sources and mute state

```bash
pactl list short sources
pactl get-default-source
pactl get-source-mute @DEFAULT_SOURCE@ 2>/dev/null
pactl list sources | grep -E 'Name:|Description:|Mute:|State:| monitor' | head -80
wpctl status
```

In `wpctl status`, note the default source, its state, and the volume/mute marker. `pw-dump` gives structured JSON:

```bash
pw-dump > /tmp/lsc-pw-dump.json
python3 - <<'PY'
import json
d=json.load(open('/tmp/lsc-pw-dump.json'))
for o in d:
    p=o.get('info',{}).get('props',{})
    if p.get('media.class')=='Audio/Source' or p.get('media.class')=='Audio/Source/Virtual':
        print(o.get('id'), p.get('node.name'), p.get('node.description'), 'mute=', p.get('audio.mute'))
PY
```

Do not confuse `Audio/Source` (capture/microphone) with `Audio/Sink` (playback) or `monitor` sources (loopback of playback, not the microphone).

## 3. Active capture clients

PulseAudio compatibility view:

```bash
pactl list short source-outputs
pactl list source-outputs
```

Key properties: `application.name`, `application.process.id`, `application.process.binary`, `application.process.user`, `media.name`, `Source`, `Corked`. A source-output is an active capture stream.

PipeWire view:

```bash
pw-dump | python3 -c '
import json,sys
for o in json.load(sys.stdin):
    p=o.get("info",{}).get("props",{})
    if p.get("media.class")=="Stream/Input/Audio":
        print(o.get("id"), p.get("application.name"), p.get("application.process.id"), p.get("application.process.binary"), p.get("node.name"))
'
```

Verify PIDs:

```bash
ps -p <pid> -o pid,ppid,user,lstart,etime,args
ls -l /proc/<pid>/exe /proc/<pid>/cwd 2>/dev/null
tr '\0' ' ' < /proc/<pid>/cmdline; echo
```

Map the PID to a package if possible (`pacman -Qo /proc/<pid>/exe`). Unknown paths, deleted executables, or execution from `/tmp` raise suspicion.

## 4. Device handles and mediation

```bash
lsof /dev/snd/* 2>/dev/null | head -40
fuser -v /dev/snd/* 2>/dev/null
ls -l /dev/snd 2>/dev/null
```

On PipeWire, the server usually owns the ALSA device and clients connect over the PipeWire socket; a capture client may not hold `/dev/snd/*` directly. Check the client's file descriptors for PipeWire/Pulse sockets:

```bash
ls -l /proc/<pid>/fd 2>/dev/null | grep -Ei 'pipewire|pulse|snd'
```

A lack of direct device fds does not mean no capture; it means the server mediates it. Conversely, holding a device fd does not prove recording content.

## 5. Camera

```bash
ls -l /dev/video* 2>/dev/null
lsof /dev/video* 2>/dev/null
fuser -v /dev/video* 2>/dev/null
v4l2-ctl --list-devices 2>/dev/null
```

PipeWire/libcamera may mediate camera access; check `pw-dump` for camera nodes and clients. Some checks require root or membership in `video`; do not request elevation without approval. A camera LED or driver indicator is supporting evidence, not proof of transmission.

## 6. Network correlation

```bash
ss -tupn
ss -tupn state established
lsof -p <pid> -a -i 2>/dev/null
ss -tp | grep -E 'pid=<pid>'
```

Compare destinations with the application's documented services. Note:

- TLS hides payload contents; you can see endpoints, not what was sent.
- CDNs and cloud providers host both legitimate and abusive traffic; IP reputation is weak evidence.
- DNS may be encrypted/cached; absence of a visible query is not absence of traffic.
- A recording app with a persistent connection is normal for calls/streaming.
- A headless recorder with no UI, persistence, unusual destination, and obfuscation is high risk.

If the process runs as another user or root, `ss -p`/`lsof` may not show its sockets. State the limitation; ask before using sudo.

## 7. Files, services, and persistence

Look for evidence of stored or staged capture without opening personal audio:

```bash
ps -eo pid,user,args | grep -Ei 'pw-record|parecord|arecord|ffmpeg|obs|wf-recorder|grim|scrot|v4l2' | grep -v grep
systemctl --user list-units --type=service --state=running --no-pager
systemctl --user list-timers --all --no-pager
ls -la ~/.config/autostart 2>/dev/null
```

Check the application's config for capture/telemetry settings and its install provenance. Do not play, transcribe, or upload recordings. Report filenames/sizes only if necessary; avoid exposing personal content.

## 8. Privacy-specific indicators

- Microphone/camera accessed by an app with no relevant feature.
- Capture started at login or by a timer, with no user action.
- Recording to hidden paths or piping to an encoder/network client.
- Capture plus credential access, shell persistence, or security-tool disabling.
- Unexpected virtual sources/sinks or loopback modules (`module-null-sink`, `module-loopback`) used to hide routing.
- Unusual proxies, DNS, or egress from a capture client.
- Browser/Electron apps with microphone permission granted but no visible call.
- Screen capture combined with microphone capture and outbound traffic.

Legitimate explanations to check first: voice assistant, dictation (e.g. Superwhisper), meeting app, browser tab, game voice chat, streaming, accessibility tool, monitoring app the user installed.

## 9. What cannot be proven with these tools

- Audio content or whether speech was captured.
- Payload contents inside TLS.
- Kernel-level or rootkit capture that hides from userland tools.
- Other users' processes without privilege.
- Data already sent before the audit.
- A camera stream mediated by hardware/firmware outside the OS view.

Say "no active capture client was observed in the accessible session" rather than "the microphone is not being recorded."

## 10. Report wording

Use precise phrasing:

- "Microphone `alsa_input...` is unmuted; no active capture stream was observed."
- "PID 4242 (`app`) has an active capture stream and one established TLS connection to `example.com`; this is consistent with a call but does not prove what was transmitted."
- "An unknown binary at `/tmp/x` holds a capture stream and connects to a raw IP; this is consistent with exfiltration and warrants immediate investigation."
- "Capture activity could not be inspected for processes owned by other users without elevated privileges."

Provide recommendations: mute/revoke permission, quit/remove the app, review autostart, check the app's telemetry settings, use firewall rules, prefer sandboxed/Flatpak permissions. Do not perform these changes without approval.
