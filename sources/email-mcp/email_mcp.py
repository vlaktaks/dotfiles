#!/usr/bin/env python3
"""email-mcp: on-demand MCP server for Outlook (Microsoft Graph) and Proton Mail (Bridge IMAP/SMTP).

Design goals
- Python stdlib only (imaplib/smtplib/ssl/urllib/email): no dependency tree to review.
- Read tools are always safe. Write tools are gated IN CODE:
    * send_draft requires confirm=true and only ever sends an existing draft
    * move_to_folder requires confirm=true and reports exact counts
    * delete_permanently requires the literal string "PERMANENTLY DELETE"
  On top of that, OpenCode config sets "ask" permissions for every write tool.
- Secrets live in ~/.config/opencode/secrets/ (dir 0700, files 0600), never in the dotfiles repo.
- The Proton Mail Bridge is started lazily on the first Proton tool call and stopped by
  the email_shutdown tool (or when this process exits). Nothing runs at boot or on OpenCode startup.
- TLS to the Bridge is pinned to the Bridge's own CA certificate; verification is never disabled.

CLI (non-MCP) modes:
    email-mcp                 serve MCP over stdio (default)
    email-mcp status          show configuration state (no secrets)
    email-mcp login outlook [--write]   device-code login for Microsoft Graph
    email-mcp login proton    store Bridge IMAP/SMTP credentials (interactive, no echo)
    email-mcp revoke outlook  delete local tokens + print consent-revocation instructions
    email-mcp selfcheck       internal sanity tests (gates, builders, parsing); exits non-zero on failure
"""

import base64
import email.parser
import email.utils
import getpass
import glob
import imaplib
import json
import os
import re
import smtplib
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

VERSION = "1.0.0"
SERVER_NAME = "email-mcp"

SECRETS_DIR = os.path.expanduser("~/.config/opencode/secrets")
OUTLOOK_CFG = os.path.join(SECRETS_DIR, "outlook-config.json")
OUTLOOK_TOKENS = os.path.join(SECRETS_DIR, "outlook-tokens.json")
PROTON_CREDS = os.path.join(SECRETS_DIR, "proton-credentials.json")

GRAPH = "https://graph.microsoft.com/v1.0"
AUTH_HOST = "https://login.microsoftonline.com"
SCOPES_READ = ["offline_access", "Mail.Read", "openid", "profile", "email"]
SCOPES_WRITE = SCOPES_READ + ["Mail.ReadWrite"]

# Canonical folder -> Outlook well-known name / Proton IMAP name candidates.
WELL_KNOWN = {
    "inbox": "inbox",
    "spam": "junkemail",
    "trash": "deleteditems",
    "drafts": "drafts",
    "archive": "archive",
    "sent": "sentitems",
}
PROTON_FOLDERS = {
    "inbox": ["inbox"],
    "spam": ["spam", "junk", "junk email"],
    "trash": ["trash", "deleted items", "deleted"],
    "drafts": ["drafts"],
    "archive": ["archive"],
    "sent": ["sent"],
}
VALID_FOLDERS = sorted(WELL_KNOWN)
MOVE_TARGETS = ["spam", "trash", "archive"]

IMAP_HOST = os.environ.get("EMAIL_IMAP_HOST", "127.0.0.1")
IMAP_PORT = int(os.environ.get("EMAIL_IMAP_PORT", "1143"))
SMTP_PORT = int(os.environ.get("EMAIL_SMTP_PORT", "1025"))
BRIDGE_BIN = os.environ.get("EMAIL_BRIDGE_BIN", "protonmail-bridge-core")
BRIDGE_CERT = os.environ.get("EMAIL_BRIDGE_CERT", "")  # optional override

CONFIRM_SEND = "confirm must be exactly true. Show the final message to the user and obtain explicit approval for THIS send before setting confirm."
CONFIRM_MOVE = "confirm must be exactly true. Show the user the exact messages (ids and count) before moving them."
CONFIRM_DELETE = 'delete_permanently requires confirmation = "PERMANENTLY DELETE" (exact string) from the user, separate from any previous approval.'
MAX_BULK = 100

GRAPH_MSG_SELECT = "id,subject,from,sender,toRecipients,ccRecipients,receivedDateTime,isRead,bodyPreview,conversationId"

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ---------------------------------------------------------------- utilities

def log(*args):
    print(*args, file=sys.stderr, flush=True)


def ensure_secrets_dir():
    os.makedirs(SECRETS_DIR, mode=0o700, exist_ok=True)
    os.chmod(SECRETS_DIR, 0o700)


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def write_json_secret(path, obj):
    ensure_secrets_dir()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


class ToolError(Exception):
    """Raised for expected tool failures; surfaces as isError text."""


def collapse_ws(text):
    return re.sub(r"\s+", " ", text or "").strip()


def parse_iso_date(value):
    """Accept YYYY-MM-DD or full ISO timestamps; return date string YYYY-MM-DD."""
    if not value:
        return None
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(value).strip())
    if not m:
        raise ToolError("invalid date %r; use YYYY-MM-DD" % (value,))
    return "%s-%s-%s" % m.groups()


def imap_date(value):
    """YYYY-MM-DD -> dd-Mon-yyyy (locale-independent month names)."""
    y, m, d = value.split("-")
    return "%02d-%s-%s" % (int(d), _MONTHS[int(m) - 1], y)


def addr_list(header_val):
    """email.utils.getaddresses -> [{"name":..., "address":...}]."""
    out = []
    for name, addr in email.utils.getaddresses([header_val or ""]):
        if addr:
            out.append({"name": name, "address": addr})
    return out


def b64url_decode(segment):
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


def decode_id_token(id_token):
    """Read the unverified id_token payload (received over TLS from Microsoft) for the account email."""
    try:
        payload = json.loads(b64url_decode(id_token.split(".")[1]))
        return (payload.get("email") or payload.get("preferred_username")
                or payload.get("upn") or payload.get("unique_name"))
    except (IndexError, ValueError):
        return None


def html_to_text(html):
    """Strip tags out of HTML for display; never fetches external content."""
    from html.parser import HTMLParser

    class P(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts = []
            self.skip = 0

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style"):
                self.skip += 1
            elif tag in ("p", "div", "br", "tr", "li"):
                self.parts.append(" ")

        def handle_endtag(self, tag):
            if tag in ("script", "style") and self.skip:
                self.skip -= 1

        def handle_data(self, data):
            if not self.skip:
                self.parts.append(data)

    p = P()
    try:
        p.feed(html or "")
    except Exception:  # best effort for malformed HTML
        pass
    return collapse_ws("".join(p.parts))


def part_payload(part):
    try:
        payload = part.get_payload(decode=True)
        if payload is None:
            payload = part.get_payload()
    except Exception:
        payload = part.get_payload()
    if isinstance(payload, bytes):
        charset = part.get_content_charset() or "utf-8"
        try:
            return payload.decode(charset, "replace")
        except LookupError:
            return payload.decode("utf-8", "replace")
    return str(payload)


def body_to_text(eml):
    """Best-effort plain text of an EmailMessage (text/plain preferred, HTML fallback)."""
    text_part = html_part = None
    for part in eml.walk():
        if part.is_multipart():
            continue
        ctype = part.get_content_type()
        if ctype == "text/plain" and text_part is None:
            text_part = part
        elif ctype == "text/html" and html_part is None:
            html_part = part
    if text_part is not None:
        return part_payload(text_part)
    if html_part is not None:
        return html_to_text(part_payload(html_part))
    return ""


def attachments(eml):
    out = []
    for part in eml.walk():
        if part.is_multipart():
            continue
        fname = part.get_filename()
        if not fname and part.get_content_disposition() != "attachment":
            continue
        out.append({
            "name": fname or "(unnamed)",
            "contentType": part.get_content_type(),
            "size": len(part.get_payload(decode=True) or b""),
        })
    return out


def msg_dict(eml, account, message_id, folder, flags=""):
    """Normalize an EmailMessage into the shared message dict."""
    date = eml.get("Date")
    try:
        iso = email.utils.parsedate_to_datetime(date).strftime("%Y-%m-%dT%H:%M:%SZ") if date else None
    except (TypeError, ValueError):
        iso = None
    interesting = [
        "Message-ID", "In-Reply-To", "References", "Authentication-Results",
        "Received-SPF", "DKIM-Signature", "X-Spam-Flag", "X-Spam-Status",
        "X-Pm-External-Id", "Reply-To",
    ]
    return {
        "id": message_id,
        "account": account,
        "folder": folder,
        "from": addr_list(eml.get("From")),
        "to": addr_list(eml.get("To")),
        "cc": addr_list(eml.get("Cc")),
        "subject": str(eml.get("Subject", "")),
        "date": iso,
        "unread": "\\Seen" not in flags,
        "snippet": collapse_ws(body_to_text(eml))[:280],
        "attachments": attachments(eml),
        "headers": {k: str(eml.get(k)) for k in interesting if eml.get(k)},
    }


def fetch_raw(imap, uid):
    """imap.uid FETCH RFC822+FLAGS -> (raw_bytes, flags_string)."""
    typ, data = imap.uid("FETCH", uid, "(RFC822 FLAGS)")
    if typ != "OK" or not data:
        raise ToolError("message %s not found" % uid)
    raw, flags = b"", ""
    for item in data:
        if isinstance(item, tuple):
            raw = item[1]
        else:
            m = re.search(rb"FLAGS \(([^)]*)\)", item)
            if m:
                flags = m.group(1).decode("ascii", "replace")
    if not raw:
        raise ToolError("message %s not found (empty fetch)" % uid)
    return raw, flags


def search_uids(imap, criteria):
    typ, data = imap.uid("SEARCH", None, criteria or "ALL")
    if typ != "OK":
        raise ToolError("IMAP search failed: %r" % (data,))
    if not data or not data[0]:
        return []
    return [int(x) for x in data[0].split()]


def select_uids(imap, folder_name, readonly=True):
    typ, data = imap.select(folder_name, readonly=readonly)
    if typ != "OK":
        raise ToolError("IMAP select %s failed: %r" % (folder_name, data))
    uv = re.search(rb"UIDVALIDITY (\d+)", b"\n".join(d if isinstance(d, bytes) else b"" for d in data))
    return uv.group(1).decode() if uv else "0"


def _imap_quote(value):
    return str(value).replace("\\", "").replace('"', "")


def _which(binary):
    for p in os.environ.get("PATH", "").split(os.pathsep):
        cand = os.path.join(p, binary)
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def _parse_proton_id(message_id):
    m = re.fullmatch(r"([a-z]+):(\d+)", str(message_id))
    if not m or m.group(1) not in PROTON_FOLDERS:
        raise ToolError("invalid Proton message id %r; use ids returned by list/search/read tools" % (message_id,))
    return m.group(1), int(m.group(2))


def _parse_draft_id(draft_id):
    m = re.fullmatch(r"drafts:(\d+)@(\d+)", str(draft_id))
    if not m:
        raise ToolError("invalid Proton draft id %r; use the draft_id returned by draft_new/draft_reply" % (draft_id,))
    return int(m.group(1)), m.group(2)


# ---------------------------------------------------------------- Outlook (Microsoft Graph)

class Outlook:
    def __init__(self):
        self.tokens = read_json(OUTLOOK_TOKENS)
        self._folder_ids = {}

    @property
    def configured(self):
        return bool(self.tokens and self.tokens.get("refresh_token"))

    def account_email(self):
        return (self.tokens or {}).get("account_email")

    def scopes(self):
        return (self.tokens or {}).get("scope")

    def _token_endpoint(self, endpoint, fields):
        cfg = read_json(OUTLOOK_CFG) or {}
        tenant = cfg.get("tenant", "consumers")
        url = "%s/%s/oauth2/v2.0/%s" % (AUTH_HOST, tenant, endpoint)
        req = urllib.request.Request(
            url,
            data=urllib.parse.urlencode(fields).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            try:
                detail = json.loads(body)
                raise ToolError("OAuth error: %s (%s)" % (
                    detail.get("error_description", detail.get("error", "unknown")), e.code))
            except ValueError:
                raise ToolError("OAuth HTTP %s: %s" % (e.code, body[:300]))

    def device_login(self, write=False):
        cfg = read_json(OUTLOOK_CFG) or {}
        client_id = (cfg.get("client_id") or "").strip()
        if not client_id:
            client_id = input("Azure app registration Application (client) ID: ").strip()
            if not re.fullmatch(r"[0-9a-fA-F-]{36}", client_id):
                raise ToolError("client ID does not look like a UUID")
        tenant = (cfg.get("tenant") or "consumers").strip() or "consumers"
        scopes = SCOPES_WRITE if write else SCOPES_READ
        dc = self._token_endpoint("devicecode", {"client_id": client_id, "scope": " ".join(scopes)})
        print("\nTo sign in, open this page in your browser:")
        print("  %s" % dc["verification_uri"])
        print("and enter this code: %s" % dc["user_code"])
        print("\n%s" % dc.get("message", ""))
        print("(Use the browser of your choice; OpenCode never sees your Microsoft password.)")
        input("\nPress Enter once you have completed sign-in in the browser... ")
        deadline = time.time() + int(dc.get("expires_in", 900))
        interval = int(dc.get("interval", 5))
        while time.time() < deadline:
            try:
                tokens = self._token_endpoint("token", {
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "client_id": client_id,
                    "device_code": dc["device_code"],
                })
                tokens["expires_at"] = time.time() + int(tokens.get("expires_in", 3600)) - 60
                tokens["account_email"] = decode_id_token(tokens.get("id_token", ""))
                tokens["client_id"] = client_id
                tokens["tenant"] = tenant
                tokens.pop("id_token", None)
                write_json_secret(OUTLOOK_CFG, {"client_id": client_id, "tenant": tenant})
                write_json_secret(OUTLOOK_TOKENS, tokens)
                self.tokens = tokens
                print("Signed in as: %s (scopes: %s)" % (tokens.get("account_email") or "unknown", tokens.get("scope")))
                return
            except ToolError as e:
                if "authorization_pending" in str(e):
                    time.sleep(interval)
                    continue
                raise
        raise ToolError("device code expired before sign-in completed; run login again")

    def revoke(self):
        if os.path.exists(OUTLOOK_TOKENS):
            os.remove(OUTLOOK_TOKENS)
        self.tokens = None
        print("Local Outlook tokens deleted.")
        print("To revoke Microsoft's consent (the real revocation):")
        print("  - Personal Microsoft account: https://account.live.com/consent/Manage")
        print("  - Work/school: Microsoft Entra 'My Sign-ins' (https://mysignins.microsoft.com/security-info)")
        print("    or delete the app registration in the Entra admin center.")

    def _refresh(self):
        if not self.tokens or not self.tokens.get("refresh_token"):
            raise ToolError("Outlook not signed in. Run: email-mcp login outlook")
        try:
            tokens = self._token_endpoint("token", {
                "grant_type": "refresh_token",
                "client_id": self.tokens["client_id"],
                "refresh_token": self.tokens["refresh_token"],
            })
        except ToolError:
            raise ToolError("Outlook token refresh failed (consent may have been revoked). Run: email-mcp login outlook")
        tokens["expires_at"] = time.time() + int(tokens.get("expires_in", 3600)) - 60
        tokens.setdefault("account_email", self.tokens.get("account_email"))
        tokens["client_id"] = self.tokens["client_id"]
        tokens["tenant"] = self.tokens.get("tenant", "consumers")
        write_json_secret(OUTLOOK_TOKENS, tokens)
        self.tokens = tokens

    def _access_token(self):
        if not self.configured:
            raise ToolError("Outlook not signed in. Run: email-mcp login outlook")
        if time.time() >= float(self.tokens.get("expires_at", 0)):
            self._refresh()
        return self.tokens["access_token"]

    def _req(self, method, path, data=None, params=None, retry=True):
        url = GRAPH + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(
            url, data=body, method=method,
            headers={"Authorization": "Bearer " + self._access_token(),
                     "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
                return json.loads(raw.decode()) if raw else {}
        except urllib.error.HTTPError as e:
            if e.code == 401 and retry:
                self._refresh()
                return self._req(method, path, data, params, retry=False)
            detail = e.read().decode("utf-8", "replace")
            try:
                err = json.loads(detail).get("error", {})
                msg = err.get("message") or err.get("code") or detail[:200]
            except ValueError:
                msg = detail[:200]
            raise ToolError("Graph HTTP %s: %s" % (e.code, msg))

    def _folder_id(self, folder):
        if folder not in WELL_KNOWN:
            raise ToolError("unknown folder %r; use one of %s" % (folder, VALID_FOLDERS))
        if folder not in self._folder_ids:
            data = self._req("GET", "/me/mailFolders/" + WELL_KNOWN[folder], params={"$select": "id"})
            self._folder_ids[folder] = data.get("id")
        return self._folder_ids[folder]

    @staticmethod
    def _graph_msg(m):
        return {
            "id": m.get("id"),
            "account": "outlook",
            "folder": None,
            "from": [{"name": (m.get("from") or {}).get("emailAddress", {}).get("name"),
                      "address": (m.get("from") or {}).get("emailAddress", {}).get("address")}],
            "to": [{"name": a.get("emailAddress", {}).get("name"), "address": a.get("emailAddress", {}).get("address")}
                   for a in (m.get("toRecipients") or [])],
            "cc": [{"name": a.get("emailAddress", {}).get("name"), "address": a.get("emailAddress", {}).get("address")}
                   for a in (m.get("ccRecipients") or [])],
            "subject": m.get("subject"),
            "date": m.get("receivedDateTime"),
            "unread": not m.get("isRead", False),
            "snippet": m.get("bodyPreview") or "",
            "attachments": [],
            "headers": {},
            "conversationId": m.get("conversationId"),
        }

    def _list_params(self, limit):
        return {"$top": min(int(limit or 10), 51), "$orderby": "receivedDateTime desc",
                "$select": GRAPH_MSG_SELECT}

    def list_messages(self, folder="inbox", limit=10, unread_only=False, sender=None, subject=None, since=None, before=None):
        filters = []
        if unread_only:
            filters.append("isRead eq false")
        if sender:
            filters.append("from/emailAddress/address eq '%s'" % sender.replace("'", "''"))
        if subject:
            filters.append("contains(subject,'%s')" % subject.replace("'", "''"))
        if since:
            filters.append("receivedDateTime ge %sT00:00:00Z" % parse_iso_date(since))
        if before:
            filters.append("receivedDateTime lt %sT00:00:00Z" % parse_iso_date(before))
        params = self._list_params(limit)
        if filters:
            params["$filter"] = " and ".join(filters)
        data = self._req("GET", "/me/mailFolders/%s/messages" % WELL_KNOWN[folder], params=params)
        return [self._graph_msg(m) for m in data.get("value", [])]

    def search(self, query, folder="inbox", limit=25):
        params = self._list_params(limit)
        params["$search"] = '"%s"' % str(query).replace('"', "'")
        data = self._req("GET", "/me/mailFolders/%s/messages" % WELL_KNOWN[folder], params=params)
        return [self._graph_msg(m) for m in data.get("value", [])]

    def read(self, message_id):
        data = self._req("GET", "/me/messages/" + urllib.parse.quote(message_id),
                         params={"$select": "%s,body,internetMessageId,hasAttachments" % GRAPH_MSG_SELECT})
        out = self._graph_msg(data)
        body = data.get("body") or {}
        content = body.get("content") or ""
        out["body"] = html_to_text(content) if body.get("contentType") == "html" else content
        out["snippet"] = collapse_ws(out["body"])[:280]
        out["headers"] = {"Message-ID": data.get("internetMessageId")}
        return out

    def thread(self, message_id):
        first = self.read(message_id)
        cid = first.get("conversationId")
        if not cid:
            return [first]
        params = {
            "$filter": "conversationId eq '%s'" % cid.replace("'", "''"),
            "$orderby": "receivedDateTime asc",
            "$top": 100,
            "$select": GRAPH_MSG_SELECT,
        }
        data = self._req("GET", "/me/messages", params=params)
        return [self._graph_msg(m) for m in data.get("value", [])]

    def draft_new(self, to, subject, body, cc=None):
        payload = {
            "subject": subject,
            "body": {"contentType": "Text", "content": body},
            "toRecipients": [{"emailAddress": {"address": t}} for t in _split_addrs(to)],
        }
        if cc:
            payload["ccRecipients"] = [{"emailAddress": {"address": t}} for t in _split_addrs(cc)]
        data = self._req("POST", "/me/messages", data=payload)
        return {"draft_id": data.get("id"), "account": "outlook",
                "to": payload["toRecipients"], "cc": payload.get("ccRecipients", []),
                "subject": subject, "body": body,
                "note": "Draft saved to Drafts. Nothing was sent."}

    def draft_reply(self, message_id, body):
        draft = self._req("POST", "/me/messages/%s/createReply" % urllib.parse.quote(message_id), data={})
        updated = self._req("PATCH", "/me/messages/" + urllib.parse.quote(draft["id"]),
                            data={"body": {"contentType": "Text", "content": body}})
        return {"draft_id": updated.get("id"), "account": "outlook",
                "reply_to": [a.get("emailAddress", {}).get("address") for a in draft.get("toRecipients", [])],
                "subject": draft.get("subject"), "body": body,
                "note": "Reply draft saved to Drafts with thread metadata preserved. Nothing was sent."}

    def send_draft(self, draft_id):
        draft = self._req("GET", "/me/messages/" + urllib.parse.quote(draft_id),
                          params={"$select": "id,subject,toRecipients,body"})
        self._req("POST", "/me/messages/%s/send" % urllib.parse.quote(draft_id), data={})
        return {"sent": True, "draft_id": draft_id, "subject": draft.get("subject"),
                "to": [a.get("emailAddress", {}).get("address") for a in draft.get("toRecipients", [])]}

    def move(self, message_ids, folder):
        dest = self._folder_id(folder)
        moved, failed = [], []
        for mid in message_ids:
            try:
                self._req("POST", "/me/messages/%s/move" % urllib.parse.quote(mid),
                          data={"destinationId": dest})
                moved.append(mid)
            except ToolError as e:
                failed.append({"id": mid, "error": str(e)})
        return {"moved": moved, "count": len(moved), "failed": failed, "folder": folder}

    def delete_permanently(self, message_ids):
        deleted, failed = [], []
        trash = self._folder_id("trash")
        for mid in message_ids:
            try:
                self._req("POST", "/me/messages/%s/move" % urllib.parse.quote(mid),
                          data={"destinationId": trash})
                self._req("DELETE", "/me/messages/" + urllib.parse.quote(mid))
                deleted.append(mid)
            except ToolError as e:
                failed.append({"id": mid, "error": str(e)})
        return {"permanently_deleted": deleted, "count": len(deleted), "failed": failed}


def _split_addrs(value):
    return [a for _, a in email.utils.getaddresses([str(value)]) if a]


# ---------------------------------------------------------------- Proton (Bridge IMAP/SMTP)

class Proton:
    def __init__(self):
        self.creds = read_json(PROTON_CREDS)
        self.spawned_pid = None

    @property
    def configured(self):
        return bool(self.creds and self.creds.get("username") and self.creds.get("password"))

    def username(self):
        if not self.configured:
            return None
        u = self.creds["username"]
        return u if "@" not in u else u.split("@")[0][:2] + "***@" + u.split("@")[1]

    def _port_open(self, port):
        try:
            with socket.create_connection((IMAP_HOST, port), timeout=2):
                return True
        except OSError:
            return False

    def ensure_bridge(self):
        """Start the Bridge daemon only if nothing is listening; remember that we started it."""
        if self._port_open(IMAP_PORT):
            return
        if not _which(BRIDGE_BIN):
            raise ToolError(
                "Proton Mail Bridge is not installed. Install it from the official Arch repo: "
                "sudo pacman -S protonmail-bridge")
        try:
            self.spawned_pid = subprocess.Popen(
                [BRIDGE_BIN, "--noninteractive"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True).pid
        except OSError as e:
            raise ToolError("failed to start Proton Mail Bridge: %s" % e)
        deadline = time.time() + 20
        while time.time() < deadline:
            if self._port_open(IMAP_PORT):
                return
            time.sleep(0.5)
        raise ToolError("Proton Mail Bridge started but IMAP port %s did not open "
                        "(is a secret service/keyring running, e.g. gnome-keyring?)." % IMAP_PORT)

    def shutdown(self):
        if self.spawned_pid:
            try:
                os.kill(self.spawned_pid, 15)
            except OSError:
                pass
            self.spawned_pid = None

    def _cert_path(self):
        if BRIDGE_CERT and os.path.exists(BRIDGE_CERT):
            return BRIDGE_CERT
        candidates = []
        for pat in ("~/.config/protonmail/bridge-v3/**/cert.pem",
                    "~/.config/protonmail/bridge-v3/**/cert.pem.tmp",
                    "~/.config/protonmail/bridge/**/cert.pem"):
            candidates.extend(glob.glob(os.path.expanduser(pat), recursive=True))
        if not candidates:
            raise ToolError("Could not find the Bridge TLS certificate. Open the Bridge GUI, "
                            "go to Settings -> Advanced -> Export TLS certificate, and set "
                            "EMAIL_BRIDGE_CERT to the exported file.")
        return max(candidates, key=os.path.getmtime)

    def _ssl_ctx(self):
        ctx = ssl.create_default_context(cafile=self._cert_path())
        # The Bridge cert is issued for 127.0.0.1; standard hostname checks still apply.
        return ctx

    def _connect(self):
        self.ensure_bridge()
        try:
            imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=self._ssl_ctx(), timeout=30)
        except (OSError, ssl.SSLError, imaplib.IMAP4.error) as e:
            raise ToolError("cannot connect to Bridge IMAP: %s" % e)
        try:
            typ, data = imap.login(self.creds["username"], self.creds["password"])
            if typ != "OK":
                raise ToolError("Bridge IMAP login failed: %r" % (data,))
        except imaplib.IMAP4.error as e:
            raise ToolError("Bridge IMAP login failed (%s). If the Bridge has no account yet, "
                            "open the GUI and add your account first (requires a paid Proton plan)." % e)
        return imap

    def _folder_name(self, imap, canonical):
        """Resolve canonical name to the actual IMAP folder; raises for missing folders (e.g. no Spam)."""
        typ, data = imap.list()
        if typ != "OK":
            raise ToolError("IMAP LIST failed")
        names = []
        for item in data:
            m = re.search(rb'"([^"]*)"\s*$', item)
            if m:
                names.append(m.group(1).decode("utf-8", "replace"))
        wanted = PROTON_FOLDERS[canonical]
        for name in names:
            if name.lower() in wanted:
                return name
        raise ToolError("folder %r not found on the Bridge (available: %s)" % (canonical, ", ".join(names)))

    def _criteria(self, sender, subject, text, since, before, unread_only):
        terms = []
        if sender:
            terms.append('FROM "%s"' % _imap_quote(sender))
        if subject:
            terms.append('SUBJECT "%s"' % _imap_quote(subject))
        if text:
            terms.append('TEXT "%s"' % _imap_quote(text))
        if since:
            terms.append("SINCE %s" % imap_date(parse_iso_date(since)))
        if before:
            terms.append("BEFORE %s" % imap_date(parse_iso_date(before)))
        if unread_only:
            terms.append("UNSEEN")
        return " ".join(terms)

    def _fetch_msg(self, imap, canonical, uid):
        raw, flags = fetch_raw(imap, uid)
        eml = email.parser.BytesParser().parsebytes(raw)
        return msg_dict(eml, "proton", "%s:%s" % (canonical, uid), canonical, flags)

    def list_messages(self, folder="inbox", limit=10, unread_only=False, sender=None, subject=None, since=None, before=None):
        with _imap_ctx(self) as (imap, _name, _uv):
            select_uids(imap, self._folder_name(imap, folder))
            uids = search_uids(imap, self._criteria(sender, subject, None, since, before, unread_only))
            uids = uids[-min(int(limit or 10), 50):]  # IMAP returns oldest first
            out = [self._fetch_msg(imap, folder, uid) for uid in uids]
            out.reverse()
            return out

    def search(self, query, folder="inbox", limit=25):
        with _imap_ctx(self) as (imap, _name, _uv):
            select_uids(imap, self._folder_name(imap, folder))
            uids = search_uids(imap, 'TEXT "%s"' % _imap_quote(query))
            uids = uids[-min(int(limit or 25), 50):]
            out = [self._fetch_msg(imap, folder, uid) for uid in uids]
            out.reverse()
            return out

    def read(self, message_id):
        folder, uid = _parse_proton_id(message_id)
        with _imap_ctx(self) as (imap, _name, _uv):
            select_uids(imap, self._folder_name(imap, folder))
            raw, flags = fetch_raw(imap, uid)
            eml = email.parser.BytesParser().parsebytes(raw)
            out = msg_dict(eml, "proton", message_id, folder, flags)
            out["body"] = body_to_text(eml)
            return out

    def thread(self, message_id):
        folder, uid = _parse_proton_id(message_id)
        with _imap_ctx(self) as (imap, _name, _uv):
            select_uids(imap, self._folder_name(imap, folder))
            raw, _ = fetch_raw(imap, uid)
            root = email.parser.BytesParser().parsebytes(raw)
            mids = set()
            for hdr in ("Message-ID", "In-Reply-To", "References"):
                val = root.get(hdr)
                if val:
                    mids.update(re.findall(r"<[^>]+>", val))
            related = {uid}
            # shortcut: walk at most 10 reference ids; enough for normal threads, avoids unbounded searches
            for mid in list(mids)[:10]:
                for hdr in ("Message-ID", "References", "In-Reply-To"):
                    for u in search_uids(imap, 'HEADER %s "%s"' % (hdr, _imap_quote(mid.strip("<>")))):
                        related.add(u)
                    if len(related) >= 50:
                        break
                if len(related) >= 50:
                    break
            msgs = []
            for u in related:
                raw_u, flags_u = fetch_raw(imap, u)
                eml = email.parser.BytesParser().parsebytes(raw_u)
                msgs.append(msg_dict(eml, "proton", "%s:%s" % (folder, u), folder, flags_u))
            msgs.sort(key=lambda m: m.get("date") or "")
            return msgs

    def draft_new(self, to, subject, body, cc=None):
        msg = email.message.EmailMessage()
        msg["From"] = self.creds["username"]
        msg["To"] = to
        if cc:
            msg["Cc"] = cc
        msg["Subject"] = subject
        msg["Date"] = email.utils.formatdate(localtime=True)
        msg["Message-ID"] = email.utils.make_msgid()
        msg.set_content(body)
        with _imap_ctx(self, readonly=False) as (imap, _name, _uv):
            drafts_name = self._folder_name(imap, "drafts")
            imap.append(drafts_name, "(\\Draft)", None, msg.as_bytes())
            uv = select_uids(imap, drafts_name)
            uids = search_uids(imap, 'HEADER Message-ID "%s"' % _imap_quote(msg["Message-ID"]))
            if not uids:
                raise ToolError("draft appended but could not be re-found")
        return {"draft_id": "drafts:%s@%s" % (uids[-1], uv), "account": "proton",
                "to": to, "cc": cc, "subject": subject, "body": body,
                "note": "Draft saved to Drafts. Nothing was sent."}

    def draft_reply(self, message_id, body):
        folder, uid = _parse_proton_id(message_id)
        with _imap_ctx(self) as (imap, _name, _uv):
            select_uids(imap, self._folder_name(imap, folder))
            raw, _ = fetch_raw(imap, uid)
            orig = email.parser.BytesParser().parsebytes(raw)
            to = orig.get("Reply-To") or orig.get("From")
            subj = orig.get("Subject") or "(no subject)"
            if not subj.lower().startswith("re:"):
                subj = "Re: " + subj
            msg = email.message.EmailMessage()
            msg["From"] = self.creds["username"]
            msg["To"] = to
            msg["Subject"] = subj
            msg["Date"] = email.utils.formatdate(localtime=True)
            if orig.get("Message-ID"):
                msg["In-Reply-To"] = orig["Message-ID"]
                refs = (orig.get("References") or "").strip()
                msg["References"] = (refs + " " if refs else "") + orig["Message-ID"]
            msg["Message-ID"] = email.utils.make_msgid()
            msg.set_content(body)
            drafts_name = self._folder_name(imap, "drafts")
            imap.append(drafts_name, "(\\Draft)", None, msg.as_bytes())
            uv = select_uids(imap, drafts_name)
            uids = search_uids(imap, 'HEADER Message-ID "%s"' % _imap_quote(msg["Message-ID"]))
        return {"draft_id": "drafts:%s@%s" % (uids[-1], uv), "account": "proton",
                "reply_to": addr_list(to), "subject": subj, "body": body,
                "note": "Reply draft saved to Drafts with In-Reply-To/References preserved. Nothing was sent."}

    def send_draft(self, draft_id):
        uid, uv = _parse_draft_id(draft_id)
        with _imap_ctx(self) as (imap, _name, _uv):
            drafts_name = self._folder_name(imap, "drafts")
            cur_uv = select_uids(imap, drafts_name)
            if cur_uv != uv:
                raise ToolError("draft id is stale (UIDVALIDITY changed); find the draft again via list_messages(folder='drafts')")
            raw, _ = fetch_raw(imap, uid)
            msg = email.parser.BytesParser().parsebytes(raw)
        self._smtp_send(msg)
        # Standard client behaviour: a sent draft is consumed. Move it to Trash (recoverable).
        with _imap_ctx(self, readonly=False) as (imap, _name, _uv):
            drafts_name = self._folder_name(imap, "drafts")
            select_uids(imap, drafts_name, readonly=False)
            trash_name = self._folder_name(imap, "trash")
            imap.uid("COPY", str(uid), trash_name)
            imap.uid("STORE", str(uid), "+FLAGS", "(\\Deleted)")
            imap.expunge()
        return {"sent": True, "draft_id": draft_id, "subject": msg.get("Subject"),
                "to": [a["address"] for a in addr_list(msg.get("To"))],
                "note": "Sent via the Bridge SMTP; the consumed draft was moved to Trash."}

    def _smtp_send(self, msg):
        ctx = self._ssl_ctx()
        server = None
        try:
            server = smtplib.SMTP(IMAP_HOST, SMTP_PORT, timeout=30)
            server.ehlo()
            server.starttls(context=ctx)
            server.ehlo()
        except (smtplib.SMTPException, ssl.SSLError, OSError):
            # Bridge may offer implicit TLS on the SMTP port instead.
            try:
                server = smtplib.SMTP_SSL(IMAP_HOST, SMTP_PORT, context=ctx, timeout=30)
            except (smtplib.SMTPException, ssl.SSLError, OSError) as e:
                raise ToolError("cannot reach Bridge SMTP on %s:%s: %s" % (IMAP_HOST, SMTP_PORT, e))
        try:
            server.login(self.creds["username"], self.creds["password"])
            server.send_message(msg)
        except (smtplib.SMTPException, ssl.SSLError) as e:
            raise ToolError("Bridge SMTP send failed: %s" % e)
        finally:
            try:
                server.quit()
            except Exception:
                pass

    def move(self, message_ids, folder):
        moved, failed = [], []
        with _imap_ctx(self, readonly=False) as (imap, _name, _uv):
            target = self._folder_name(imap, folder)
            per_source = {}
            for mid in message_ids:
                src, uid = _parse_proton_id(mid)
                per_source.setdefault(src, []).append(uid)
            for src, uids in per_source.items():
                try:
                    select_uids(imap, self._folder_name(imap, src), readonly=False)
                    uidset = ",".join(str(u) for u in uids)
                    typ, data = imap.uid("COPY", uidset, target)
                    if typ != "OK":
                        raise ToolError("COPY failed: %r" % (data,))
                    imap.uid("STORE", uidset, "+FLAGS", "(\\Deleted)")
                    imap.expunge()
                    moved.extend("%s:%s" % (src, u) for u in uids)
                except (ToolError, imaplib.IMAP4.error) as e:
                    failed.append({"ids": ["%s:%s" % (src, u) for u in uids], "error": str(e)})
        return {"moved": moved, "count": len(moved), "failed": failed, "folder": folder}

    def delete_permanently(self, message_ids):
        deleted, failed = [], []
        with _imap_ctx(self, readonly=False) as (imap, _name, _uv):
            trash_name = self._folder_name(imap, "trash")
            to_purge = []
            for mid in message_ids:
                src, uid = _parse_proton_id(mid)
                try:
                    if src != "trash":
                        select_uids(imap, self._folder_name(imap, src), readonly=False)
                        raw, _ = fetch_raw(imap, uid)
                        msgid = email.parser.BytesParser().parsebytes(raw).get("Message-ID")
                        imap.uid("COPY", str(uid), trash_name)
                        imap.uid("STORE", str(uid), "+FLAGS", "(\\Deleted)")
                        imap.expunge()
                        to_purge.append(msgid)
                    else:
                        select_uids(imap, trash_name, readonly=False)
                        raw, _ = fetch_raw(imap, uid)
                        msgid = email.parser.BytesParser().parsebytes(raw).get("Message-ID")
                        to_purge.append(msgid)
                    deleted.append(mid)
                except (ToolError, imaplib.IMAP4.error) as e:
                    failed.append({"id": mid, "error": str(e)})
            if to_purge:
                select_uids(imap, trash_name, readonly=False)
                for msgid in to_purge:
                    for f in search_uids(imap, 'HEADER Message-ID "%s"' % _imap_quote(msgid or "")):
                        imap.uid("STORE", str(f), "+FLAGS", "(\\Deleted)")
                imap.expunge()
        return {"permanently_deleted": deleted, "count": len(deleted), "failed": failed}


class _imap_ctx:
    """Context manager: one authenticated IMAP session. readonly=False allows writes."""

    def __init__(self, proton, readonly=True):
        self.proton = proton
        self.readonly = readonly
        self.imap = None

    def __enter__(self):
        if not self.proton.configured:
            raise ToolError("Proton credentials missing. Run: email-mcp login proton")
        self.imap = self.proton._connect()
        uv = select_uids(self.imap, "INBOX", readonly=self.readonly)
        return self.imap, "inbox", uv

    def __exit__(self, *exc):
        if self.imap is not None:
            try:
                self.imap.logout()
            except Exception:
                pass
        return False


# ---------------------------------------------------------------- gates (enforced in code)

def gate_send(confirm):
    if confirm is not True:
        raise ToolError(CONFIRM_SEND)


def gate_move(confirm, count):
    if confirm is not True:
        raise ToolError(CONFIRM_MOVE + " (%d message(s) affected)" % count)
    if count > MAX_BULK:
        raise ToolError("refusing bulk operation over %d messages; narrow the selection" % MAX_BULK)


def gate_delete(confirmation):
    if confirmation != "PERMANENTLY DELETE":
        raise ToolError(CONFIRM_DELETE)


# ---------------------------------------------------------------- tool layer

def _tool_schema(props, required):
    return {
        "type": "object",
        "properties": props,
        "required": required,
        "additionalProperties": False,
    }


def _str(desc, **kw):
    return dict(kw, type="string", description=desc)


def _bool(desc):
    return {"type": "boolean", "description": desc}


TOOLS = [
    {
        "name": "email_accounts",
        "description": "Show which mail accounts are configured and their status (no secrets). Use this first to see what is available.",
        "inputSchema": _tool_schema({}, []),
    },
    {
        "name": "list_messages",
        "description": "List messages newest-first. account: 'outlook', 'proton', or 'both'. "
                       "folder: inbox, spam, trash, drafts, archive, sent. Optional filters: sender, subject, unread_only, since/before (YYYY-MM-DD).",
        "inputSchema": _tool_schema({
            "account": _str("Account to query: outlook, proton, or both", enum=["outlook", "proton", "both"]),
            "folder": _str("Folder name", enum=VALID_FOLDERS),
            "limit": {"type": "integer", "description": "Max messages (default 10, max 50)"},
            "unread_only": _bool("Only unread messages"),
            "sender": _str("Filter by sender email address"),
            "subject": _str("Filter by subject substring"),
            "since": _str("Only messages on/after this date (YYYY-MM-DD)"),
            "before": _str("Only messages before this date (YYYY-MM-DD)"),
        }, ["account"]),
    },
    {
        "name": "search_messages",
        "description": "Full-text/keyword search in one account or both. Returns matching messages newest-first.",
        "inputSchema": _tool_schema({
            "account": _str("Account to query", enum=["outlook", "proton", "both"]),
            "query": _str("Keywords to search for"),
            "folder": _str("Folder to search in", enum=VALID_FOLDERS),
            "limit": {"type": "integer", "description": "Max results (default 25, max 50)"},
        }, ["account", "query"]),
    },
    {
        "name": "read_message",
        "description": "Read one full message: sender, recipients, subject, date, headers and complete body. Attachments are listed but never downloaded.",
        "inputSchema": _tool_schema({
            "account": _str("Account", enum=["outlook", "proton"]),
            "message_id": _str("Message id from list/search results"),
        }, ["account", "message_id"]),
    },
    {
        "name": "read_thread",
        "description": "Read the full conversation a message belongs to, oldest-first.",
        "inputSchema": _tool_schema({
            "account": _str("Account", enum=["outlook", "proton"]),
            "message_id": _str("Any message id from the thread"),
        }, ["account", "message_id"]),
    },
    {
        "name": "list_spam",
        "description": "List messages in the Spam/Junk folder (newest first) for one or both accounts.",
        "inputSchema": _tool_schema({
            "account": _str("Account", enum=["outlook", "proton", "both"]),
            "limit": {"type": "integer", "description": "Max messages (default 20, max 50)"},
        }, ["account"]),
    },
    {
        "name": "draft_new",
        "description": "Create a draft email (NOT sent). Returns a draft_id. Sending requires the separate send_draft tool with user approval.",
        "inputSchema": _tool_schema({
            "account": _str("Account to draft in", enum=["outlook", "proton"]),
            "to": _str("Recipient address(es)"),
            "subject": _str("Subject"),
            "body": _str("Message body (plain text)"),
            "cc": _str("CC address(es), optional"),
        }, ["account", "to", "subject", "body"]),
    },
    {
        "name": "draft_reply",
        "description": "Create a reply draft to an existing message (NOT sent). Thread metadata (In-Reply-To/References/conversation) is preserved. Returns a draft_id.",
        "inputSchema": _tool_schema({
            "account": _str("Account", enum=["outlook", "proton"]),
            "message_id": _str("Message id to reply to"),
            "body": _str("Reply body (plain text)"),
        }, ["account", "message_id", "body"]),
    },
    {
        "name": "send_draft",
        "description": "Send a previously created draft. HARD GATE: confirm must be true, set only after the user has seen the complete final message and approved THIS send.",
        "inputSchema": _tool_schema({
            "account": _str("Account", enum=["outlook", "proton"]),
            "draft_id": _str("draft_id from draft_new/draft_reply"),
            "confirm": _bool("User-approved send: set true only after explicit approval"),
        }, ["account", "draft_id", "confirm"]),
    },
    {
        "name": "move_to_folder",
        "description": "Move selected messages to spam, trash, or archive. HARD GATE: confirm must be true after showing the user the exact messages and count.",
        "inputSchema": _tool_schema({
            "account": _str("Account", enum=["outlook", "proton"]),
            "message_ids": {"type": "array", "items": {"type": "string"},
                            "description": "Message ids to move (max 100 per call)"},
            "folder": _str("Target folder", enum=MOVE_TARGETS),
            "confirm": _bool("User-approved move"),
        }, ["account", "message_ids", "folder", "confirm"]),
    },
    {
        "name": "delete_permanently",
        "description": "Permanently delete messages (unrecoverable). HARD GATE: confirmation must be the exact string 'PERMANENTLY DELETE', given separately from any other approval. Prefer move_to_folder(trash) instead.",
        "inputSchema": _tool_schema({
            "account": _str("Account", enum=["outlook", "proton"]),
            "message_ids": {"type": "array", "items": {"type": "string"},
                            "description": "Message ids to permanently delete"},
            "confirmation": _str("Must be the exact string: PERMANENTLY DELETE"),
        }, ["account", "message_ids", "confirmation"]),
    },
    {
        "name": "email_shutdown",
        "description": "Stop any Proton Mail Bridge process that was started on demand. Safe to call any time; an already-running Bridge is left alone.",
        "inputSchema": _tool_schema({}, []),
    },
]

BACKENDS = {}


def _backend(account):
    if account == "outlook":
        if "outlook" not in BACKENDS:
            BACKENDS["outlook"] = Outlook()
        return BACKENDS["outlook"]
    if account == "proton":
        if "proton" not in BACKENDS:
            BACKENDS["proton"] = Proton()
        return BACKENDS["proton"]
    raise ToolError("unknown account %r; use outlook or proton" % (account,))


def _both_or_one(account, fn):
    if account == "both":
        out = {}
        for acc in ("outlook", "proton"):
            try:
                out[acc] = fn(acc)
            except ToolError as e:
                out[acc] = {"error": str(e)}
        return out
    return fn(account)


def tool_email_accounts(_args):
    o = _backend("outlook")
    p = _backend("proton")
    return {
        "outlook": {
            "configured": o.configured,
            "email": o.account_email(),
            "scopes": o.scopes(),
            "expires_at": (o.tokens or {}).get("expires_at"),
        },
        "proton": {
            "configured": p.configured,
            "username": p.username(),
            "bridge_listening": p._port_open(IMAP_PORT),
        },
    }


def tool_list_messages(args):
    def one(acc):
        b = _backend(acc)
        return {"account": acc, "messages": b.list_messages(
            folder=args.get("folder") or "inbox",
            limit=args.get("limit", 10),
            unread_only=bool(args.get("unread_only")),
            sender=args.get("sender"),
            subject=args.get("subject"),
            since=args.get("since"),
            before=args.get("before"))}
    return _both_or_one(args["account"], one)


def tool_search(args):
    def one(acc):
        b = _backend(acc)
        return {"account": acc, "messages": b.search(
            args["query"], folder=args.get("folder") or "inbox", limit=args.get("limit", 25))}
    return _both_or_one(args["account"], one)


def tool_read(args):
    def one(acc):
        return _backend(acc).read(args["message_id"])
    return _both_or_one(args["account"], one)


def tool_thread(args):
    def one(acc):
        return {"account": acc, "messages": _backend(acc).thread(args["message_id"])}
    return _both_or_one(args["account"], one)


def tool_list_spam(args):
    def one(acc):
        return {"account": acc, "messages": _backend(acc).list_messages(folder="spam", limit=args.get("limit", 20))}
    return _both_or_one(args["account"], one)


def tool_draft_new(args):
    return _backend(args["account"]).draft_new(args["to"], args["subject"], args["body"], args.get("cc"))


def tool_draft_reply(args):
    return _backend(args["account"]).draft_reply(args["message_id"], args["body"])


def tool_send_draft(args):
    gate_send(args.get("confirm"))
    return _backend(args["account"]).send_draft(args["draft_id"])


def tool_move(args):
    ids = list(args.get("message_ids") or [])
    if not ids:
        raise ToolError("message_ids is empty")
    gate_move(args.get("confirm"), len(ids))
    return _backend(args["account"]).move(ids, args["folder"])


def tool_delete(args):
    ids = list(args.get("message_ids") or [])
    if not ids:
        raise ToolError("message_ids is empty")
    gate_delete(args.get("confirmation"))
    return _backend(args["account"]).delete_permanently(ids)


def tool_shutdown(_args):
    p = _backend("proton")
    was_spawned = p.spawned_pid is not None
    p.shutdown()
    return {"bridge_spawned_by_us": was_spawned,
            "note": "Bridge stopped" if was_spawned else "Bridge was not started by this session; left running"}


TOOL_IMPL = {
    "email_accounts": tool_email_accounts,
    "list_messages": tool_list_messages,
    "search_messages": tool_search,
    "read_message": tool_read,
    "read_thread": tool_thread,
    "list_spam": tool_list_spam,
    "draft_new": tool_draft_new,
    "draft_reply": tool_draft_reply,
    "send_draft": tool_send_draft,
    "move_to_folder": tool_move,
    "delete_permanently": tool_delete,
    "email_shutdown": tool_shutdown,
}


# ---------------------------------------------------------------- MCP stdio transport

def handle_request(msg):
    method = msg.get("method")
    req_id = msg.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": req_id, "result": {
            "protocolVersion": msg.get("params", {}).get("protocolVersion") or "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": VERSION},
        }}
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = msg.get("params", {})
        name = params.get("name")
        impl = TOOL_IMPL.get(name)
        if impl is None:
            return {"jsonrpc": "2.0", "id": req_id,
                    "error": {"code": -32602, "message": "unknown tool: %s" % name}}
        try:
            result = impl(params.get("arguments") or {})
            text = json.dumps(result, indent=2, default=str)
            return {"jsonrpc": "2.0", "id": req_id, "result": {
                "content": [{"type": "text", "text": text}], "isError": False}}
        except ToolError as e:
            return {"jsonrpc": "2.0", "id": req_id, "result": {
                "content": [{"type": "text", "text": str(e)}], "isError": True}}
        except Exception as e:  # never crash the MCP session on unexpected errors
            log("tools/call %s failed: %r" % (name, e))
            return {"jsonrpc": "2.0", "id": req_id, "result": {
                "content": [{"type": "text", "text": "internal error: %s" % e}], "isError": True}}
    return {"jsonrpc": "2.0", "id": req_id,
            "error": {"code": -32601, "message": "method not found: %s" % method}}


def serve():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            log("invalid JSON line ignored")
            continue
        resp = handle_request(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


# ---------------------------------------------------------------- CLI modes

def cmd_status():
    o = _backend("outlook")
    p = _backend("proton")
    print("email-mcp status")
    print("  Outlook:  %s" % ("signed in as %s (scopes: %s)" % (o.account_email(), o.scopes())
                             if o.configured else "not signed in (run: email-mcp login outlook)"))
    print("  Proton:   %s" % ("credentials stored for %s" % p.username()
                             if p.configured else "no credentials (run: email-mcp login proton)"))
    print("  Bridge:   %s" % ("listening on %s:%s" % (IMAP_HOST, IMAP_PORT)
                             if p._port_open(IMAP_PORT) else "not running (starts on demand)"))
    print("  Secrets:  %s (no secrets printed here)" % SECRETS_DIR)


def cmd_login(args):
    account = args[0] if args else None
    if account == "outlook":
        Outlook().device_login(write="--write" in args)
    elif account == "proton":
        username = input("Proton address (as shown in Bridge account settings): ").strip()
        if not username or "@" not in username:
            raise SystemExit("invalid Proton address")
        password = getpass.getpass("Bridge IMAP/SMTP password (from Bridge account settings): ")
        if not password:
            raise SystemExit("empty password")
        write_json_secret(PROTON_CREDS, {"username": username, "password": password})
        print("Stored in %s (chmod 600)." % PROTON_CREDS)
        p = _backend("proton")
        try:
            with _imap_ctx(p) as (imap, _name, _uv):
                typ, data = imap.list()
                folders = [re.search(rb'"([^"]*)"\s*$', d).group(1).decode() for d in data
                           if re.search(rb'"([^"]*)"\s*$', d)]
                print("Connection OK. Folders: %s" % ", ".join(folders))
        except ToolError as e:
            print("Warning: could not verify the credentials yet: %s" % e)
    else:
        raise SystemExit("usage: email-mcp login outlook|proton [--write]")


def cmd_revoke(args):
    account = args[0] if args else None
    if account == "outlook":
        Outlook().revoke()
    elif account == "proton":
        if os.path.exists(PROTON_CREDS):
            os.remove(PROTON_CREDS)
        print("Local Proton credentials deleted. To fully disconnect, also remove the account "
              "in the Bridge GUI (Settings -> Accounts).")
    else:
        raise SystemExit("usage: email-mcp revoke outlook|proton")


# ---------------------------------------------------------------- selfcheck (mocks/dry runs)

def selfcheck():
    failures = []

    def check(name, fn):
        try:
            fn()
            print("ok - %s" % name)
        except Exception as e:
            failures.append(name)
            print("FAIL - %s: %r" % (name, e))

    def gates():
        for bad in (None, False, 0, "yes"):
            try:
                gate_send(bad)
                raise AssertionError("send gate accepted %r" % (bad,))
            except ToolError:
                pass
        gate_send(True)
        for bad in (None, False, "yes"):
            try:
                gate_move(bad, 3)
                raise AssertionError("move gate accepted %r" % (bad,))
            except ToolError:
                pass
        try:
            gate_move(True, 1000)
            raise AssertionError("bulk cap not enforced")
        except ToolError:
            pass
        gate_move(True, 3)
        for bad in ("yes", "", None, "permanently delete"):
            try:
                gate_delete(bad)
                raise AssertionError("delete gate accepted %r" % (bad,))
            except ToolError:
                pass
        gate_delete("PERMANENTLY DELETE")

    def schemas():
        for tool in TOOLS:
            assert tool.get("name") and tool.get("description"), tool
            json.dumps(tool["inputSchema"])
        assert set(TOOL_IMPL) == {t["name"] for t in TOOLS}, "impl/tool mismatch"

    def builders():
        assert imap_date("2026-11-26") == "26-Nov-2026"
        assert parse_iso_date("2026-11-26T10:00:00Z") == "2026-11-26"
        try:
            parse_iso_date("garbage")
            raise AssertionError("bad date accepted")
        except ToolError:
            pass
        p = Proton()
        c = p._criteria("a@b.c", "hello", None, "2026-01-02", None, True)
        assert 'FROM "a@b.c"' in c and "SUBJECT" in c and "SINCE 02-Jan-2026" in c and "UNSEEN" in c, c
        assert _imap_quote('say "hi"') == "say hi"
        assert html_to_text("<p>Hello <b>world</b><script>x()</script></p>") == "Hello world"
        assert _parse_proton_id("spam:42") == ("spam", 42)
        assert _parse_draft_id("drafts:7@123") == (7, "123")
        try:
            _parse_proton_id("bad")
            raise AssertionError("bad proton id accepted")
        except ToolError:
            pass
        assert decode_id_token("x." + base64.urlsafe_b64encode(
            b'{"email":"me@example.com"}').decode().rstrip("=") + ".y") == "me@example.com"

    def email_parse():
        raw = ("From: Alice <alice@example.com>\r\nTo: bob@example.com\r\n"
               "Subject: Test\r\nDate: Wed, 26 Nov 2026 10:00:00 +0000\r\n"
               "Message-ID: <x@y>\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nHello body\r\n")
        eml = email.parser.BytesParser().parsebytes(raw.encode())
        d = msg_dict(eml, "proton", "inbox:1", "inbox", "")
        assert d["from"][0]["address"] == "alice@example.com"
        assert d["snippet"] == "Hello body"
        assert d["unread"] is True

    def oauth_offline():
        # login prompts must never run unattended; just verify config path wiring
        assert SECRETS_DIR.startswith(os.path.expanduser("~")), SECRETS_DIR
        assert read_json("/nonexistent/definitely-not-there.json") is None

    check("hard gates (send/move/bulk/delete)", gates)
    check("tool schemas and impl coverage", schemas)
    check("IMAP criteria/date/id builders + HTML stripping", builders)
    check("RFC822 parsing to shared message dict", email_parse)
    check("offline paths (no network touched)", oauth_offline)
    if failures:
        print("selfcheck FAILED: %s" % ", ".join(failures))
        return 1
    print("selfcheck passed")
    return 0


def main(argv):
    cmd = argv[0] if argv else "serve"
    if cmd == "selfcheck":
        return selfcheck()
    if cmd == "status":
        cmd_status()
        return 0
    if cmd == "login":
        cmd_login(argv[1:])
        return 0
    if cmd == "revoke":
        cmd_revoke(argv[1:])
        return 0
    if cmd in ("serve", "mcp"):
        try:
            serve()
        except KeyboardInterrupt:
            pass
        finally:
            _backend("proton").shutdown()
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
