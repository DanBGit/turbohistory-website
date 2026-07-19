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

# Opt-in regimes: consent must be explicit and recorded. Mirrors the ASK list the
# cookie modal uses, so a visitor never sees one standard for cookies and another here.
OPT_IN = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU",
          "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES",
          "SE", "IS", "LI", "NO", "GB", "CH", "BR", "CA"}

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

    ip = client_ip(req)
    c = db()
    if rate_limited(c, ip):
        return JSONResponse({"ok": False, "error": "Too many attempts. Try again later."},
                            status_code=429)

    # Cloudflare gives us the country for free on every request through the proxy.
    country = (req.headers.get("cf-ipcountry") or body.get("country") or "").upper()[:2]
    required = country in OPT_IN or country == ""      # unknown geo -> treat as opt-in
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
        return JSONResponse({"ok": True, "already": True,
                             "message": "You are already on the list."})
    finally:
        c.close()
    return JSONResponse({"ok": True, "message": "You are in."})


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
    Route("/api/subscribers/count", count, methods=["GET"]),
    Route("/api/health", health, methods=["GET"]),
])
