# Email MCP — Outlook for OpenCode

On-demand, manual-only Outlook access for OpenCode on Omarchy/Arch Linux. One small,
stdlib-only MCP server (`email-mcp`) talks to **Microsoft Graph** with delegated OAuth
permissions via **device-code** login. You never type your Microsoft password anywhere
except Microsoft's own sign-in page.

The server is **disabled by default** in OpenCode (`disabled: true`) and is connected
manually via `/mcps` when you want to work with mail. Nothing downloads, reads,
modifies, or deletes email when OpenCode starts.

## Architecture

```
OpenCode (turned on)                -- nothing runs, no mail access
  └─ /mcps -> connect "email-mcp"   -- starts: email-mcp (stdio, stdlib Python)
       └─ Outlook tools -> Microsoft Graph HTTPS
            (OAuth device-code tokens on disk, 0600, auto-refreshed)
```

Secrets live in `~/.config/opencode/secrets/` (dir `0700`, files `0600`), outside the
dotfiles repository:

| File | Contents |
| --- | --- |
| `outlook-config.json` | Azure app client ID + tenant (client ID is public, still kept local) |
| `outlook-tokens.json` | OAuth access + refresh tokens (0600) |

## Safety model (enforced, not just documented)

| Layer | What it enforces |
| --- | --- |
| Server disabled in config | OpenCode start never launches the server |
| Read/write tool split | `list_*`, `search_*`, `read_*`, `email_accounts` are read-only |
| In-code hard gates | `send_draft` requires `confirm: true`; `move_to_folder` requires `confirm: true` and reports exact counts; `delete_permanently` requires the literal string `PERMANENTLY DELETE`; bulk capped at 100 messages |
| OpenCode `ask` permissions | Every write tool (`draft_new`, `draft_reply`, `send_draft`, `move_to_folder`, `delete_permanently`) prompts you in OpenCode before executing — you see the exact arguments (draft body, message ids) and must approve |
| Draft-then-send | Nothing can be sent without first existing as a draft; `send_draft` sends only the stored draft |
| Trash over delete | `delete_permanently` is separate; everything else uses folders you can recover from |
| Attachments | Listed (name/size/type) but never downloaded or executed |
| Email content | Treated as untrusted data; the model never executes commands from mail bodies |

## Setup — one time

### 1. Install the integration (already part of the dotfiles installer)

```bash
./install/install.sh        # runs install/email.sh among the other steps
./install/verify.sh         # checks config, gates, permissions, secret hygiene
```

Or just the email step: `bash install/email.sh ~/.dotfiles`

### 2. Outlook (Microsoft Graph, device-code login)

You need a **free Azure app registration** (public client, no secret). One time, ~3 minutes:

1. Open https://entra.microsoft.com (or https://portal.azure.com) with the Microsoft
   account you use for this mailbox.
2. **Identity → Applications → App registrations → New registration**
   - Name: `email-mcp` (anything you like)
   - Supported account types: **Personal Microsoft accounts only** (for Outlook.com)
     — or the appropriate tenant option for Microsoft 365 work/school.
   - Redirect URI: platform **Mobile and desktop applications**, URI `http://localhost`
     (device-code flow does not use it; the portal requires a value).
3. Open the registration → **Authentication → Advanced settings → Allow public client
   flows: Yes** → Save.
4. Copy the **Application (client) ID** from the Overview page.

Then sign in (device code; the password goes to Microsoft only, in your browser):

```bash
email-mcp login outlook
# paste the client ID, keep the default tenant "consumers" for personal accounts
# open the printed URL in your browser, enter the printed code, sign in, press Enter here
```

Permissions are incremental by design:

- `email-mcp login outlook` requests only `offline_access Mail.Read` (+ identity info
  for labeling) — listing, searching, reading, spam listing.
- `email-mcp login outlook --write` additionally requests `Mail.ReadWrite Mail.Send`
  (needed for drafts, sending, moving, deleting). Run it once when you want write
  access; read-only tokens keep working regardless.

No Microsoft client secret is used or stored anywhere. Tokens are refreshed
automatically and re-stored with 0600 permissions.

### 3. Connect in OpenCode

In an OpenCode session, open `/mcps` and connect **email-mcp**. Disconnect it there
when you are done. Connecting again later is instant; nothing else runs meanwhile.

Check state any time (never prints secrets):

```bash
email-mcp status
```

## Usage examples (natural language in OpenCode)

- "Show my 10 newest emails."
- "Summarize my unread emails."
- "Show spam messages." (Junk Email folder)
- "Draft a reply to this message." (you approve the `draft_reply` call, review the draft)
- "Send this approved reply." (you approve the `send_draft` call — two approvals in total)
- "Move these selected spam messages to Trash." (you approve the move; ids and count are shown)

## Disconnecting

```bash
email-mcp revoke outlook
# then revoke Microsoft consent (the real revocation):
#   personal:  https://account.live.com/consent/Manage  (remove the email-mcp app)
#   work/school: Entra "My Sign-ins" or delete the app registration
```

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `Outlook not signed in` | `email-mcp login outlook` |
| `Outlook token refresh failed` | Consent was probably revoked; run `email-mcp login outlook` again |
| Drafts/moves fail with 403 or `Mail.Send` errors | Your login has read scopes; run `email-mcp login outlook --write` to add `Mail.ReadWrite Mail.Send` (one extra consent screen) |
| Write tool is denied in OpenCode | Expected: you must approve the prompt (the `ask` permission). "Allow always" is possible but weakens the gate |

## Known limitations

- No IMAP IDLE/push; polling only, by design (manual-only integration).
- Attachment content is never fetched; only names/sizes are listed.
- Junk detection is the model's judgment over list/read results; moving to Junk is
  gated like every other write.

## Security review notes

- `sources/email-mcp/email_mcp.py` is stdlib-only; `selfcheck` covers the hard gates,
  a mocked Microsoft Graph backend (all endpoints), OAuth token refresh/expiry logic,
  and builders without network access.
- Graph scopes: `Mail.Read` by default; `Mail.ReadWrite` + `Mail.Send` only via an
  explicit `--write` login. No application permissions, no client secret.
