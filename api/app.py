"""
Turbo History email capture.

Deliberately small: one SQLite file on Daniel's own box is the consent ledger. Each
signup is then copied to MailerLite (the processor that sends the emails, disclosed in the
privacy policy), carrying its consent history with it: opt-in time, IP, country, page
and the exact wording agreed to. The ledger stays authoritative; MailerLite is a copy.

Consent record is the point of this file. For anyone in an opt-in jurisdiction we store
what they agreed to, word for word, plus when and from where. That is what a regulator
asks for and what a generic form post cannot produce after the fact.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

DB = Path(os.environ.get("TH_DB", "/data/subscribers.db"))
ADMIN_KEY = os.environ.get("TH_ADMIN_KEY", "")

ML_API = "https://connect.mailerlite.com/api"
ML_KEY = os.environ.get("TH_ML_KEY", "")
ML_GROUP = os.environ.get("TH_ML_GROUP", "")
# The Monday routine submits the live form as a real reader would. Those rows prove the
# form works; they must never land on the mailing list and get a Saturday email.
ML_SKIP_PREFIXES = ("formtest-",)
# MailerLite states in which an address must not be put back on the list by us.
ML_SUPPRESSED = {"unsubscribed", "bounced", "junk"}
IP_RE = re.compile(r"^[0-9a-fA-F:.]{3,45}$")

# Opt-in regimes: consent must be explicit and recorded. This is the EMAIL list, and it
# deliberately no longer mirrors the cookie modal's list: the modal still asks Canadians
# about analytics (nothing changed there), but Canada is blocked from the email list
# entirely, so it does not belong here.
OPT_IN = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU",
          "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES",
          "SE", "IS", "LI", "NO", "GB", "CH", "BR"}

# Shown to Canadian visitors in place of the form, and returned by the API if one
# reaches it anyway (stale cache, devtools, direct POST).
CANADA_MSG = ("IN CANADA? Sorry, we are not risking Canada's anti-spam rules (CASL), "
              "so you cannot sign up. The books are still on Amazon.ca.")

EMAIL_RE = re.compile(r"^[^@\s,;]{1,64}@[A-Za-z0-9.-]{1,190}\.[A-Za-z]{2,24}$")

# Crude but effective: most junk signups are typos or throwaway domains.
BAD_DOMAINS = {"example.com", "test.com", "mailinator.com", "10minutemail.com"}


def db() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB, timeout=10)
    c.execute("""CREATE TABLE IF NOT EXISTS subscribers(
        id INTEGER PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        created_utc TEXT NOT NULL,
        country TEXT,
        consent_required INTEGER NOT NULL,
        consent_given INTEGER NOT NULL,
        consent_text TEXT,
        source_page TEXT,
        ip TEXT,
        user_agent TEXT,
        unsubscribed_utc TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS hits(
        ip TEXT PRIMARY KEY, n INTEGER, window_start REAL)""")
    cols = {r[1] for r in c.execute("PRAGMA table_info(subscribers)")}
    if "ml_sync" not in cols:
        # Last MailerLite outcome and when: "synced@<utc>", "suppressed@<utc>",
        # "skipped-test@<utc>", "error:<status>@<utc>". NULL = never attempted.
        try:
            c.execute("ALTER TABLE subscribers ADD COLUMN ml_sync TEXT")
        except sqlite3.OperationalError:
            pass  # another request added it first
    c.commit()
    return c


def _ml(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(
        ML_API + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {ML_KEY}", "Accept": "application/json",
                 "Content-Type": "application/json", "User-Agent": "turbohistory-api/1"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except ValueError:
            return e.code, {}
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, {}


def push_to_mailerlite(email: str) -> str:
    """Copy one ledger row to MailerLite and record the outcome on the row.

    Never raises: a MailerLite outage must not lose a signup. The row is already safe in
    the ledger, stays unsynced, and /api/subscribers/sync retries it later.
    """
    if not (ML_KEY and ML_GROUP):
        return "not-configured"
    c = db()
    try:
        row = c.execute("""SELECT email,created_utc,country,consent_required,consent_text,
                           source_page,ip FROM subscribers
                           WHERE email=? AND unsubscribed_utc IS NULL""", (email,)).fetchone()
        if not row:
            return "gone"
        email, created, country, required, consent_text, source, ip = row
        if email.startswith(ML_SKIP_PREFIXES):
            outcome = "skipped-test"
        else:
            status, data = _ml("GET", "/subscribers/" + urllib.parse.quote(email))
            if status == 200 and (data.get("data") or {}).get("status") in ML_SUPPRESSED:
                # They left (or bounce) on MailerLite's side. Re-adding them from here
                # would override their unsubscribe, which is the one thing we must never
                # do. A genuine change of heart goes through MailerLite's own resubscribe.
                outcome = "suppressed"
            elif status not in (200, 404):
                outcome = f"error:{status}"
            else:
                ts = created.replace("T", " ").rstrip("Z")
                body = {
                    "email": email,
                    "groups": [ML_GROUP],
                    "subscribed_at": ts,
                    "opted_in_at": ts,
                    "fields": {
                        "consent_text": consent_text or "",
                        "signup_page": source or "",
                        "signup_country": country or "",
                        "consent_required": "yes" if required else "no",
                        "country": country or "",
                    },
                }
                if ip and IP_RE.match(ip):
                    body["optin_ip"] = ip
                    body["ip_address"] = ip
                status, _ = _ml("POST", "/subscribers", body)
                outcome = "synced" if status in (200, 201) else f"error:{status}"
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        c.execute("UPDATE subscribers SET ml_sync=? WHERE email=?", (f"{outcome}@{now}", email))
        c.commit()
        return outcome
    except Exception as e:  # noqa: BLE001 - see docstring
        return f"error:{type(e).__name__}"
    finally:
        c.close()


def _after(email: str) -> BackgroundTask:
    return BackgroundTask(push_to_mailerlite, email)


def client_ip(req) -> str:
    # Two proxies in front: Cloudflare, then Traefik. Traefik appends its own hop to
    # X-Forwarded-For, so the first entry there is Cloudflare's edge, not the visitor.
    # CF-Connecting-IP is the only header that reliably holds the real address, and the
    # consent record is worth little if it points at a datacentre.
    cf = req.headers.get("cf-connecting-ip", "").strip()
    if cf:
        return cf[:45]
    fwd = req.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()[:45]
    return (req.client.host if req.client else "")[:45]


def rate_limited(c: sqlite3.Connection, ip: str, limit: int = 8,
                 window: int = 3600) -> bool:
    now = time.time()
    row = c.execute("SELECT n, window_start FROM hits WHERE ip=?", (ip,)).fetchone()
    if row and now - row[1] < window:
        if row[0] >= limit:
            return True
        c.execute("UPDATE hits SET n=n+1 WHERE ip=?", (ip,))
    else:
        c.execute("INSERT OR REPLACE INTO hits(ip,n,window_start) VALUES(?,1,?)", (ip, now))
    c.commit()
    return False


MAX_SIGNUP_BYTES = 16_384   # a real signup is a few hundred bytes


def parse_signup(raw: bytes) -> dict | None:
    """The signup body: JSON (the site's script) or a plain form post (no script). None = neither.

    The form fallback used to call Starlette's req.form(), which needs python-multipart; that was never installed,
    so every non-JSON post was a 500 (found 3 Nov 2026). A URL-encoded form is parsed here with the standard
    library instead, and anything that is not an object comes back as None (a 400), never a crash."""
    text = raw.decode("utf-8", "replace")
    try:
        data = json.loads(text)
    except ValueError:
        return {k: v[0] for k, v in urllib.parse.parse_qs(text, keep_blank_values=True).items()} or None
    return data if isinstance(data, dict) else None


async def subscribe(req):
    raw = await req.body()
    if len(raw) > MAX_SIGNUP_BYTES:
        return JSONResponse({"ok": False, "error": "That form was too large."}, status_code=413)
    body = parse_signup(raw)
    if body is None:
        return JSONResponse({"ok": False, "error": "That does not look like an email address."},
                            status_code=400)

    # Honeypot. Real people never fill a hidden field; bots fill everything.
    if (body.get("website") or "").strip():
        return JSONResponse({"ok": True}, status_code=200)

    email = (body.get("email") or "").strip().lower()[:255]
    if not EMAIL_RE.match(email) or email.split("@")[-1] in BAD_DOMAINS:
        return JSONResponse({"ok": False, "error": "That does not look like an email address."},
                            status_code=400)

    # Every genuine signup arrives through Cloudflare, because the form is only ever served
    # from turbohistory.com. A request carrying no Cloudflare headers came straight to the
    # origin IP: it skipped the WAF rule, and it brings no country we are willing to trust,
    # which is the one remaining route past the Canada block. There is no legitimate version
    # of this request, so refuse it rather than guess at a country.
    #
    # Deliberately fails loud, not open. If Cloudflare ever stopped sending these headers
    # the form would break rather than quietly start accepting unverifiable signups - and
    # the Monday signup check does a real browser submit, so it would surface within a week.
    if not (req.headers.get("cf-connecting-ip") or req.headers.get("cf-ipcountry")):
        return JSONResponse(
            {"ok": False, "error": "Please sign up at turbohistory.com."}, status_code=403)

    ip = client_ip(req)
    c = db()
    if rate_limited(c, ip):
        return JSONResponse({"ok": False, "error": "Too many attempts. Try again later."},
                            status_code=429)

    # Cloudflare gives us the country for free on every request through the proxy. Read it
    # from the header ONLY. It used to fall back to a country the client sent in the body,
    # which meant anyone posting straight to the origin IP - bypassing Cloudflare, and so
    # bypassing the WAF rule too - could simply claim to be somewhere they are not and walk
    # past the Canada block below. A missing header now means "cannot place this visitor",
    # which the opt-in test treats as consent-required rather than as permission.
    #
    # Note this does not make the origin unreachable: a determined bypass still skips the
    # geo check entirely, because without Cloudflare there is no country to test. Closing
    # that properly means firewalling the origin to Cloudflare's IP ranges, which needs
    # access to the box rather than a change here.
    country = (req.headers.get("cf-ipcountry") or "").upper()[:2]

    # Canada is excluded outright. CASL requires identifying info (incl. a mailing
    # address) at the point consent is sought, and a 60-day unsubscribe on every
    # message. We are not set up for that, so we never collect a Canadian address
    # rather than collect one we cannot lawfully mail. Cloudflare's country header is
    # authoritative here, not the client's - a tampered page cannot talk its way past.
    # Note this blocks the LIST only; Amazon.ca still sells to Canada.
    if country == "CA":
        return JSONResponse({"ok": False, "error": CANADA_MSG}, status_code=403)

    # Unknown geo -> treat as opt-in. "" is a missing header, XX is Cloudflare's
    # "could not place this IP", T1 is a Tor exit. In all three the visitor could be
    # sitting in the EEA, so ask for the tick rather than assume implied consent.
    required = country in OPT_IN or country in ("", "XX", "T1")
    given = bool(body.get("consent"))
    consent_text = (body.get("consent_text") or "").strip()[:500]

    if required and not given:
        return JSONResponse(
            {"ok": False, "error": "Please tick the box to confirm you want the emails."},
            status_code=400)

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        c.execute("""INSERT INTO subscribers
            (email,created_utc,country,consent_required,consent_given,consent_text,
             source_page,ip,user_agent)
            VALUES(?,?,?,?,?,?,?,?,?)""",
                  (email, now, country, int(required), int(given), consent_text,
                   (body.get("source") or "")[:200], ip,
                   (req.headers.get("user-agent") or "")[:300]))
        c.commit()
    except sqlite3.IntegrityError:
        # A row already exists for this address. If they had unsubscribed, this is a
        # genuine fresh opt-in and must be honoured: clear the flag and record the new
        # consent. Returning "already on the list" here would both be a lie and silently
        # drop a subscriber who just asked to come back.
        row = c.execute("SELECT unsubscribed_utc FROM subscribers WHERE email=?",
                        (email,)).fetchone()
        if row and row[0]:
            c.execute("""UPDATE subscribers SET unsubscribed_utc=NULL, created_utc=?,
                         country=?, consent_required=?, consent_given=?, consent_text=?,
                         source_page=?, ip=?, user_agent=? WHERE email=?""",
                      (now, country, int(required), int(given), consent_text,
                       (body.get("source") or "")[:200], ip,
                       (req.headers.get("user-agent") or "")[:300], email))
            c.commit()
            return JSONResponse({"ok": True, "message": "You are in."},
                                background=_after(email))
        # Also retried here: an address that signed up before the MailerLite copy
        # existed, or whose copy failed, gets another attempt when it comes back.
        return JSONResponse({"ok": True, "already": True,
                             "message": "You are already on the list."},
                            background=_after(email))
    finally:
        c.close()
    return JSONResponse({"ok": True, "message": "You are in."}, background=_after(email))


async def unsubscribe(req):
    """Mark addresses as unsubscribed. Admin-only, POST.

    The mail tool (MailerLite) owns the subscriber-facing unsubscribe link and honours
    it on its own. The problem this solves is the opposite direction: without a write
    path back into this file, an opt-out over there never reaches the consent ledger
    here, /export keeps handing back people who left, and the next import resurrects
    them. That is the actual violation risk, so this is the reconciliation hook.

    Paste MailerLite's unsubscribe export straight in - JSON list, or any blob of text
    with addresses separated by whitespace, commas or semicolons.

    Deletes outright rather than flagging: nothing here needs to remember them, and the
    less we keep the less there is to get wrong. The unsubscribed_utc column stays in the
    schema (export and count still filter on it) but nothing sets it any more.
    """
    if not ADMIN_KEY or req.query_params.get("key") != ADMIN_KEY:
        return PlainTextResponse("nope", status_code=403)

    try:
        body = await req.json()
        raw = body.get("emails") if isinstance(body, dict) else body
    except Exception:
        raw = (await req.body()).decode("utf-8", "replace")

    if isinstance(raw, str):
        candidates = re.split(r"[\s,;]+", raw)
    elif isinstance(raw, list):
        candidates = [str(x) for x in raw]
    else:
        candidates = []

    # Be liberal about what is pasted in, but only act on things shaped like an email:
    # a stray CSV header or quote must never be treated as an address.
    emails = []
    for e in candidates:
        e = e.strip().strip('"\'').lower()
        if e and EMAIL_RE.match(e) and e not in emails:
            emails.append(e)
    if not emails:
        return JSONResponse({"ok": False, "error": "No valid addresses found."},
                            status_code=400)

    c = db()
    done, missed = [], []
    try:
        for e in emails:
            # Hard delete, row and all. Once someone is off the list the consent proof
            # has no purpose left - we are not mailing them, so we will never need to
            # prove they agreed - and the privacy policy promises the lot goes. If they
            # ever come back it is a clean INSERT with a fresh consent record, so there
            # is no state to reconcile. Suppression lives in the mail tool, which keeps
            # its own permanent unsubscribe list; this file is the consent ledger.
            cur = c.execute("DELETE FROM subscribers WHERE email=?", (e,))
            (done if cur.rowcount else missed).append(e)
        c.commit()
    finally:
        c.close()
    return JSONResponse({"ok": True, "unsubscribed": len(done),
                         "already_gone_or_unknown": len(missed),
                         "missed": missed[:25]})


async def export(req):
    """CSV export, ready to paste into MailerLite when there are enough to bother."""
    if not ADMIN_KEY or req.query_params.get("key") != ADMIN_KEY:
        return PlainTextResponse("nope", status_code=403)
    c = db()
    rows = c.execute("""SELECT email,created_utc,country,consent_required,consent_given,
                        consent_text,source_page,ml_sync FROM subscribers
                        WHERE unsubscribed_utc IS NULL ORDER BY id""").fetchall()
    c.close()
    out = ["email,created_utc,country,consent_required,consent_given,consent_text,source_page,"
           "ml_sync"]
    for r in rows:
        out.append(",".join('"' + str(x or "").replace('"', '""') + '"' for x in r))
    return PlainTextResponse("\n".join(out), media_type="text/csv")


async def sync(req):
    """Admin-only, POST. Copy every row MailerLite does not have yet (or failed) across.

    Safe to run any time: rows already synced, suppressed or test rows are left alone,
    and push_to_mailerlite itself refuses to re-add anyone who unsubscribed over there.
    """
    if not ADMIN_KEY or req.query_params.get("key") != ADMIN_KEY:
        return PlainTextResponse("nope", status_code=403)
    if not (ML_KEY and ML_GROUP):
        return JSONResponse({"ok": False, "error": "TH_ML_KEY / TH_ML_GROUP not set"},
                            status_code=500)
    c = db()
    emails = [r[0] for r in c.execute(
        """SELECT email FROM subscribers WHERE unsubscribed_utc IS NULL AND
           (ml_sync IS NULL OR ml_sync LIKE 'error%' OR ml_sync LIKE 'not-configured%')
           ORDER BY id""")]
    c.close()
    tally: dict[str, int] = {}
    for e in emails:
        outcome = (await run_in_threadpool(push_to_mailerlite, e)).split(":")[0]
        tally[outcome] = tally.get(outcome, 0) + 1
    return JSONResponse({"ok": True, "attempted": len(emails), "outcomes": tally})


async def count(req):
    c = db()
    n = c.execute("SELECT COUNT(*) FROM subscribers WHERE unsubscribed_utc IS NULL").fetchone()[0]
    c.close()
    return JSONResponse({"subscribers": n})


async def health(req):
    return PlainTextResponse("ok")


app = Starlette(routes=[
    Route("/api/subscribe", subscribe, methods=["POST"]),
    Route("/api/subscribers/export", export, methods=["GET"]),
    Route("/api/subscribers/unsubscribe", unsubscribe, methods=["POST"]),
    Route("/api/subscribers/sync", sync, methods=["POST"]),
    Route("/api/subscribers/count", count, methods=["GET"]),
    Route("/api/health", health, methods=["GET"]),
])
