#!/usr/bin/env python3
"""email-mcp: on-demand MCP server for Outlook (Microsoft Graph).

Design goals
- Python stdlib only (urllib/email/html): no dependency tree to review.
- Read tools are always safe. Write tools are gated IN CODE:
    * send_draft requires confirm=true and only ever sends an existing draft
    * move_to_folder requires confirm=true and reports exact counts
    * delete_permanently requires the literal string "PERMANENTLY DELETE"
  On top of that, OpenCode config sets "ask" permissions for every write tool.
- Secrets live in ~/.config/opencode/secrets/ (dir 0700, files 0600), never in the dotfiles repo.
- Authentication: OAuth 2.0 device-code flow (public client, no client secret).
  Incremental scopes: read login = offline_access + Mail.Read (+ identity labels);
  write login (--write) additionally requests Mail.ReadWrite + Mail.Send.
- Nothing runs at boot or on OpenCode startup; the MCP server is disabled by default
  and connected manually via /mcps.

CLI (non-MCP) modes:
    email-mcp                 serve MCP over stdio (default)
    email-mcp status          show configuration state (no secrets)
    email-mcp login outlook [--write]   device-code login for Microsoft Graph
    email-mcp revoke outlook  delete local tokens + print consent-revocation instructions
    email-mcp selfcheck       internal sanity tests (gates, Graph mocks, token logic); exits non-zero on failure
"""

import base64
import email.utils
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

VERSION = "2.0.0"
SERVER_NAME = "email-mcp"

SECRETS_DIR = os.path.expanduser("~/.config/opencode/secrets")
OUTLOOK_CFG = os.path.join(SECRETS_DIR, "outlook-config.json")
OUTLOOK_TOKENS = os.path.join(SECRETS_DIR, "outlook-tokens.json")

GRAPH = "https://graph.microsoft.com/v1.0"
AUTH_HOST = "https://login.microsoftonline.com"
SCOPES_READ = ["offline_access", "Mail.Read", "openid", "profile", "email"]
SCOPES_WRITE = SCOPES_READ + ["Mail.ReadWrite", "Mail.Send"]

# Canonical folder -> Outlook well-known name.
WELL_KNOWN = {
    "inbox": "inbox",
    "spam": "junkemail",
    "trash": "deleteditems",
    "drafts": "drafts",
    "archive": "archive",
    "sent": "sentitems",
}
VALID_FOLDERS = sorted(WELL_KNOWN)
MOVE_TARGETS = ["spam", "trash", "archive"]

CONFIRM_SEND = "confirm must be exactly true. Show the final message to the user and obtain explicit approval for THIS send before setting confirm."
CONFIRM_MOVE = "confirm must be exactly true. Show the user the exact messages (ids and count) before moving them."
CONFIRM_DELETE = 'delete_permanently requires confirmation = "PERMANENTLY DELETE" (exact string) from the user, separate from any previous approval.'
MAX_BULK = 100

GRAPH_MSG_SELECT = "id,subject,from,sender,toRecipients,ccRecipients,receivedDateTime,isRead,bodyPreview,conversationId"


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


def addr_list(header_val):
    """email.utils.getaddresses -> [{"name":..., "address":...}]."""
    out = []
    for name, addr in email.utils.getaddresses([header_val or ""]):
        if addr:
            out.append({"name": name, "address": addr})
    return out


def split_addrs(value):
    return [a for _, a in email.utils.getaddresses([str(value)]) if a]


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
            if e.code == 403 and "Send" in msg:
                msg += " (your login has read scopes; run: email-mcp login outlook --write to add Mail.ReadWrite + Mail.Send)"
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
            "toRecipients": [{"emailAddress": {"address": t}} for t in split_addrs(to)],
        }
        if cc:
            payload["ccRecipients"] = [{"emailAddress": {"address": t}} for t in split_addrs(cc)]
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


def _int(desc):
    return {"type": "integer", "description": desc}


TOOLS = [
    {
        "name": "email_accounts",
        "description": "Show the Outlook account status (signed in as, granted scopes, token expiry; no secrets). Use this first to see whether the account is ready.",
        "inputSchema": _tool_schema({}, []),
    },
    {
        "name": "list_messages",
        "description": "List Outlook messages newest-first. folder: inbox, spam (Junk Email), trash, drafts, archive, sent. Optional filters: sender, subject, unread_only, since/before (YYYY-MM-DD).",
        "inputSchema": _tool_schema({
            "folder": _str("Folder name", enum=VALID_FOLDERS),
            "limit": _int("Max messages (default 10, max 50)"),
            "unread_only": _bool("Only unread messages"),
            "sender": _str("Filter by sender email address"),
            "subject": _str("Filter by subject substring"),
            "since": _str("Only messages on/after this date (YYYY-MM-DD)"),
            "before": _str("Only messages before this date (YYYY-MM-DD)"),
        }, []),
    },
    {
        "name": "search_messages",
        "description": "Full-text/keyword search in Outlook. Returns matching messages newest-first.",
        "inputSchema": _tool_schema({
            "query": _str("Keywords to search for"),
            "folder": _str("Folder to search in", enum=VALID_FOLDERS),
            "limit": _int("Max results (default 25, max 50)"),
        }, ["query"]),
    },
    {
        "name": "read_message",
        "description": "Read one full Outlook message: sender, recipients, subject, date, headers and complete body. Attachments are listed but never downloaded.",
        "inputSchema": _tool_schema({
            "message_id": _str("Message id from list/search results"),
        }, ["message_id"]),
    },
    {
        "name": "read_thread",
        "description": "Read the full Outlook conversation a message belongs to, oldest-first.",
        "inputSchema": _tool_schema({
            "message_id": _str("Any message id from the thread"),
        }, ["message_id"]),
    },
    {
        "name": "list_spam",
        "description": "List messages in the Outlook Junk Email folder (newest first).",
        "inputSchema": _tool_schema({
            "limit": _int("Max messages (default 20, max 50)"),
        }, []),
    },
    {
        "name": "draft_new",
        "description": "Create an Outlook draft email (NOT sent). Returns a draft_id. Sending requires the separate send_draft tool with user approval.",
        "inputSchema": _tool_schema({
            "to": _str("Recipient address(es)"),
            "subject": _str("Subject"),
            "body": _str("Message body (plain text)"),
            "cc": _str("CC address(es), optional"),
        }, ["to", "subject", "body"]),
    },
    {
        "name": "draft_reply",
        "description": "Create an Outlook reply draft to an existing message (NOT sent). Thread metadata (conversation, recipients) is preserved. Returns a draft_id.",
        "inputSchema": _tool_schema({
            "message_id": _str("Message id to reply to"),
            "body": _str("Reply body (plain text)"),
        }, ["message_id", "body"]),
    },
    {
        "name": "send_draft",
        "description": "Send a previously created Outlook draft. HARD GATE: confirm must be true, set only after the user has seen the complete final message and approved THIS send.",
        "inputSchema": _tool_schema({
            "draft_id": _str("draft_id from draft_new/draft_reply"),
            "confirm": _bool("User-approved send: set true only after explicit approval"),
        }, ["draft_id", "confirm"]),
    },
    {
        "name": "move_to_folder",
        "description": "Move selected Outlook messages to Junk Email, Deleted Items, or Archive. HARD GATE: confirm must be true after showing the user the exact messages and count.",
        "inputSchema": _tool_schema({
            "message_ids": {"type": "array", "items": {"type": "string"},
                            "description": "Message ids to move (max 100 per call)"},
            "folder": _str("Target folder", enum=MOVE_TARGETS),
            "confirm": _bool("User-approved move"),
        }, ["message_ids", "folder", "confirm"]),
    },
    {
        "name": "delete_permanently",
        "description": "Permanently delete Outlook messages (unrecoverable). HARD GATE: confirmation must be the exact string 'PERMANENTLY DELETE', given separately from any other approval. Prefer move_to_folder(trash) instead.",
        "inputSchema": _tool_schema({
            "message_ids": {"type": "array", "items": {"type": "string"},
                            "description": "Message ids to permanently delete"},
            "confirmation": _str("Must be the exact string: PERMANENTLY DELETE"),
        }, ["message_ids", "confirmation"]),
    },
]

_backend = None


def _get_backend():
    global _backend
    if _backend is None:
        _backend = Outlook()
    return _backend


def tool_email_accounts(_args):
    o = _get_backend()
    return {
        "outlook": {
            "configured": o.configured,
            "email": o.account_email(),
            "scopes": o.scopes(),
            "expires_at": (o.tokens or {}).get("expires_at"),
            "write_enabled": bool(o.scopes() and "Mail.ReadWrite" in o.scopes()),
        },
    }


def tool_list_messages(args):
    return {"account": "outlook", "messages": _get_backend().list_messages(
        folder=args.get("folder") or "inbox",
        limit=args.get("limit", 10),
        unread_only=bool(args.get("unread_only")),
        sender=args.get("sender"),
        subject=args.get("subject"),
        since=args.get("since"),
        before=args.get("before"))}


def tool_search(args):
    return {"account": "outlook", "messages": _get_backend().search(
        args["query"], folder=args.get("folder") or "inbox", limit=args.get("limit", 25))}


def tool_read(args):
    return _get_backend().read(args["message_id"])


def tool_thread(args):
    return {"account": "outlook", "messages": _get_backend().thread(args["message_id"])}


def tool_list_spam(args):
    return {"account": "outlook", "messages": _get_backend().list_messages(folder="spam", limit=args.get("limit", 20))}


def tool_draft_new(args):
    return _get_backend().draft_new(args["to"], args["subject"], args["body"], args.get("cc"))


def tool_draft_reply(args):
    return _get_backend().draft_reply(args["message_id"], args["body"])


def tool_send_draft(args):
    gate_send(args.get("confirm"))
    return _get_backend().send_draft(args["draft_id"])


def tool_move(args):
    ids = list(args.get("message_ids") or [])
    if not ids:
        raise ToolError("message_ids is empty")
    gate_move(args.get("confirm"), len(ids))
    return _get_backend().move(ids, args["folder"])


def tool_delete(args):
    ids = list(args.get("message_ids") or [])
    if not ids:
        raise ToolError("message_ids is empty")
    gate_delete(args.get("confirmation"))
    return _get_backend().delete_permanently(ids)


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
    o = _get_backend()
    print("email-mcp status")
    if o.configured:
        print("  Outlook:  signed in as %s (scopes: %s)" % (o.account_email(), o.scopes()))
    else:
        print("  Outlook:  not signed in (run: email-mcp login outlook)")
    print("  Secrets:  %s (no secrets printed here)" % SECRETS_DIR)


def cmd_login(args):
    account = args[0] if args else None
    if account == "outlook":
        Outlook().device_login(write="--write" in args)
    else:
        raise SystemExit("usage: email-mcp login outlook [--write]")


def cmd_revoke(args):
    account = args[0] if args else None
    if account == "outlook":
        Outlook().revoke()
    else:
        raise SystemExit("usage: email-mcp revoke outlook")


# ---------------------------------------------------------------- selfcheck (mocks/dry runs)

class _FakeGraph:
    """Canned Microsoft Graph backend recording every request; no network."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []
        self._regexes = [(re.compile("^" + re.escape(k[1]).replace(r"\#", r"[^/]+") + "$"), k)
                         for k in routes]

    def __call__(self, method, path, data=None, params=None, retry=True):
        self.calls.append({"method": method, "path": path, "data": data, "params": params})
        handler = self.routes.get((method, path))
        if handler is None:
            for rx, key in self._regexes:
                if key[0] == method and rx.match(path):
                    handler = self.routes[key]
                    break
        if handler is None:
            raise ToolError("unexpected call %s %s" % (method, path))
        return handler(path, data, params, self.calls)


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
        assert len(TOOLS) == 11, "expected 11 Outlook tools, got %d" % len(TOOLS)
        # No Proton remnants: no account selection, no bridge tool
        for tool in TOOLS:
            blob = json.dumps(tool)
            assert "account" not in tool["inputSchema"]["properties"], tool["name"]
            assert "both" not in blob and "proton" not in blob and "bridge" not in blob.lower(), tool["name"]
        assert "email_shutdown" not in TOOL_IMPL

    def builders():
        assert parse_iso_date("2026-11-26T10:00:00Z") == "2026-11-26"
        try:
            parse_iso_date("garbage")
            raise AssertionError("bad date accepted")
        except ToolError:
            pass
        assert html_to_text("<p>Hello <b>world</b><script>x()</script></p>") == "Hello world"
        assert split_addrs("Alice <alice@example.com>, bob@example.com") == ["alice@example.com", "bob@example.com"]
        assert addr_list("Alice <alice@example.com>")[0]["address"] == "alice@example.com"
        assert decode_id_token("x." + base64.urlsafe_b64encode(
            b'{"email":"me@example.com"}').decode().rstrip("=") + ".y") == "me@example.com"

    def graph_mocks():
        msg = {"id": "m1", "subject": "Hi", "from": {"emailAddress": {"name": "A", "address": "a@x.com"}},
               "toRecipients": [{"emailAddress": {"address": "me@x.com"}}], "ccRecipients": [],
               "receivedDateTime": "2026-11-26T10:00:00Z", "isRead": False, "bodyPreview": "hello",
               "conversationId": "c1"}
        routes = {
            ("GET", "/me/mailFolders/#/messages"): lambda p, d, pr, calls: {"value": [msg]},
            ("GET", "/me/messages/#"): lambda p, d, pr, calls: {**msg, "body": {"contentType": "Text", "content": "hello"}},
            ("GET", "/me/messages"): lambda p, d, pr, calls: {"value": [msg]},
            ("POST", "/me/messages"): lambda p, d, pr, calls: {"id": "d1", **d},
            ("POST", "/me/messages/#/createReply"): lambda p, d, pr, calls: {"id": "d2", "subject": "RE: Hi",
                                                                             "toRecipients": [{"emailAddress": {"address": "a@x.com"}}]},
            ("PATCH", "/me/messages/#"): lambda p, d, pr, calls: {"id": "d2", **d},
            ("POST", "/me/messages/#/send"): lambda p, d, pr, calls: {},
            ("POST", "/me/messages/#/move"): lambda p, d, pr, calls: {"id": "m1"},
            ("DELETE", "/me/messages/#"): lambda p, d, pr, calls: {},
            ("GET", "/me/mailFolders/#"): lambda p, d, pr, calls: {"id": "folder-%s" % p.split("/")[-1]},
        }
        o = Outlook()
        o._req = _FakeGraph(routes)
        o.tokens = {"refresh_token": "r", "access_token": "t", "expires_at": time.time() + 3600}

        lst = o.list_messages(limit=5, unread_only=True, sender="a@x.com", since="2026-11-01")
        assert lst[0]["id"] == "m1" and lst[0]["account"] == "outlook"
        c = o._req.calls[-1]
        assert c["params"]["$filter"] == "isRead eq false and from/emailAddress/address eq 'a@x.com' and receivedDateTime ge 2026-11-01T00:00:00Z", c["params"]

        assert o.search("hello")[0]["subject"] == "Hi"
        assert o.read("m1")["body"] == "hello"
        assert o.thread("m1")[0]["conversationId"] == "c1"

        d = o.draft_new("a@x.com", "Subj", "Body")
        assert d["draft_id"] == "d1"
        assert o._req.calls[-1]["data"]["body"]["content"] == "Body"

        r = o.draft_reply("m1", "reply body")
        assert r["draft_id"] == "d2" and r["reply_to"] == ["a@x.com"]
        patch = [c for c in o._req.calls if c["method"] == "PATCH"][-1]
        assert patch["data"]["body"]["content"] == "reply body"

        assert o.send_draft("d2")["sent"] is True
        send = [c for c in o._req.calls if c["path"].endswith("/send")][-1]
        assert send["method"] == "POST"

        m = o.move(["m1"], "trash")
        assert m["count"] == 1 and m["moved"] == ["m1"]
        move_call = [c for c in o._req.calls if c["method"] == "POST" and c["path"].endswith("/move")][-1]
        assert move_call["data"] == {"destinationId": "folder-deleteditems"}

        dp = o.delete_permanently(["m1"])
        assert dp["count"] == 1
        seq = [c["method"] + " " + c["path"] for c in o._req.calls]
        assert "POST /me/messages/m1/move" in seq and "DELETE /me/messages/m1" in seq

    def token_logic():
        # Expired tokens trigger a real refresh (writer no-op'd: no disk, no network).
        saved_writer = write_json_secret

        def noop_writer(path, obj):
            pass

        globals()["write_json_secret"] = noop_writer
        try:
            def fake_refresh(endpoint, fields):
                assert endpoint == "token" and fields["grant_type"] == "refresh_token", fields
                return {"access_token": "new", "refresh_token": "newr", "expires_in": 3600}

            o = Outlook()
            o.tokens = {"refresh_token": "r", "access_token": "old",
                        "expires_at": time.time() - 5, "client_id": "c", "tenant": "consumers"}
            o._token_endpoint = fake_refresh
            assert o._access_token() == "new"
            assert o.tokens["access_token"] == "new" and o.tokens["expires_at"] > time.time()

            # Fresh token: no refresh call
            def fail_refresh(endpoint, fields):
                raise AssertionError("refresh must not be called for a fresh token")

            o2 = Outlook()
            o2.tokens = {"refresh_token": "r", "access_token": "fresh",
                         "expires_at": time.time() + 3600, "client_id": "c"}
            o2._token_endpoint = fail_refresh
            assert o2._access_token() == "fresh"
        finally:
            globals()["write_json_secret"] = saved_writer

        # Not configured -> clear error, no crash
        o3 = Outlook()
        o3.tokens = None
        try:
            o3._access_token()
            raise AssertionError("unconfigured backend returned a token")
        except ToolError as e:
            assert "not signed in" in str(e)

        # authorization_pending surfaces as ToolError for the poll loop
        class E(Outlook):
            def _token_endpoint(self, endpoint, fields):
                raise ToolError("OAuth error: authorization_pending (400)")

        try:
            E()._token_endpoint("token", {})
            raise AssertionError("no error raised")
        except ToolError as e:
            assert "authorization_pending" in str(e)

    def offline():
        assert SECRETS_DIR.startswith(os.path.expanduser("~")), SECRETS_DIR
        assert read_json("/nonexistent/definitely-not-there.json") is None
        # no Proton-era imports may remain in this module
        m = sys.modules["__main__"]
        for banned in ("imaplib", "smtplib", "getpass", "glob", "subprocess", "socket", "ssl", "email.parser"):
            assert banned not in m.__dict__, banned

    check("hard gates (send/move/bulk/delete)", gates)
    check("tool schemas (Outlook-only, no account/both/proton/bridge)", schemas)
    check("date/address/html builders + id_token decode", builders)
    check("mocked Microsoft Graph backend (list/search/read/thread/draft/send/move/delete)", graph_mocks)
    check("OAuth token handling (refresh decision, unconfigured, pending)", token_logic)
    check("offline paths + no Proton imports (no network touched)", offline)
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
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
