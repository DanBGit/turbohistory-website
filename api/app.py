"""
Turbo History email capture.

Deliberately small: one endpoint, one SQLite file, no third-party processor. Subscriber
data never leaves Daniel's own box, which keeps the privacy story simple (no processor
agreement, no international transfer, nothing to disclose beyond "we store it ourselves").

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
from pathlib import Path

from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

DB = Path(os.environ.get("TH_DB", "/data/subscribers.db"))
ADMIN_KEY = os.environ.get("TH_ADMIN_KEY", "")

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
    c.commit()
    return c


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


async def subscribe(req):
    try:
        body = await req.json()
    except Exception:
        form = await req.form()
        body = dict(form)

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
            return JSONResponse({"ok": True, "message": "You are in."})
        return JSONResponse({"ok": True, "already": True,
                             "message": "You are already on the list."})
    finally:
        c.close()
    return JSONResponse({"ok": True, "message": "You are in."})


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
                        consent_text,source_page FROM subscribers
                        WHERE unsubscribed_utc IS NULL ORDER BY id""").fetchall()
    c.close()
    out = ["email,created_utc,country,consent_required,consent_given,consent_text,source_page"]
    for r in rows:
        out.append(",".join('"' + str(x or "").replace('"', '""') + '"' for x in r))
    return PlainTextResponse("\n".join(out), media_type="text/csv")


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
    Route("/api/subscribers/count", count, methods=["GET"]),
    Route("/api/health", health, methods=["GET"]),
])
