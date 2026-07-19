#!/usr/bin/env python3
"""
Turbo History website generator.

catalogue.json (source of truth, written by the book pipeline)  ->  site/

Run after publishing new books / syncing ASINs:

    python3 turbohistory-website/build.py
    cd turbohistory-website && git commit -am "rebuild" && git push   # Coolify redeploys

Generates:
    site/index.html                 brand page + full catalogue grid
    site/books/<slug>/index.html    one page per book (SEO target: "<subject> book")
    site/sitemap.xml, site/robots.txt
    site/covers/<slug>.jpg          480px thumbnails (only for new/changed books)

SEO model (see seo/STRATEGY.md): category terms are a dead end (~2k/mo total). The
prize is per-subject book-buying intent ("napoleon book", "best books about X"),
~283k/mo across the catalogue at KD 0-15. Each book page targets its own subject.
Writer-subjects (Poe, Austen, Shakespeare, Shelley) are flagged SEO_WRITERS: their
"<name> books" volume means the subject's OWN works, not books about them, so we do
not chase that intent.
"""
from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
PROJECT = ROOT.parent
CATALOGUE = PROJECT / "catalogue.json"
READY = Path.home() / "Downloads" / "turbo-history-ready"
BASE = "https://turbohistory.com"
EMAIL = "turbo@turbohistory.com"
AMAZON_AUTHOR = "https://www.amazon.com/author/turbohistory"
GA_ID = "G-D8J4PNSQ9J"

HEAD_EXTRA = f"""<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}
gtag('js',new Date());gtag('config','{GA_ID}');</script>"""

# Subjects whose "<name> books" search intent means their own writing, not
# biographies of them. We still give them pages; we just don't chase that phrase.
SEO_WRITERS = {"edgar-allan-poe", "jane-austen", "william-shakespeare", "mary-shelley"}

# Featured on the homepage hero grid, in order. Falls back to catalogue order.
FEATURED = ["cleopatra", "genghis-khan", "anne-boleyn", "blackbeard", "napoleon",
            "elizabeth-i", "hannibal", "joan-of-arc", "leonardo-da-vinci",
            "marie-curie", "edgar-allan-poe", "world-war-ii"]

TAGLINE = "41 books and counting. Start anywhere. Finish everything."

CSS = """
:root{--ink:#0d0b08;--panel:#161210;--parchment:#e9ddc6;--gold:#c9a24b;--gold-soft:#a8873d;--muted:#9d907a}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--ink);color:var(--parchment);font-family:Georgia,'Times New Roman',serif;line-height:1.65}
a{color:var(--gold);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:1060px;margin:0 auto;padding:0 22px}
.nav{padding:22px 0;display:flex;justify-content:space-between;align-items:center;font-family:Futura,'Trebuchet MS',Arial,sans-serif}
.nav .logo{font-size:13px;letter-spacing:.4em;text-transform:uppercase;color:var(--gold);font-weight:700}
.nav a{font-size:14px;margin-left:20px}
header{padding:44px 0 8px;text-align:center}
h1{font-size:clamp(28px,5vw,50px);margin:14px 0 6px;font-weight:400;line-height:1.15}
.hero{padding:10px 0 30px;text-align:center;max-width:760px;margin:0 auto}
.hero p{font-size:clamp(16px,2.2vw,19px);margin:15px 0}
.muted{color:var(--muted)}
.rule{width:64px;height:2px;background:var(--gold);margin:26px auto}
.tag{font-size:clamp(17px,2.5vw,22px);color:var(--gold);font-style:italic}
.btn{display:inline-block;background:var(--gold);color:#161210;padding:13px 28px;border-radius:3px;font-family:Futura,'Trebuchet MS',Arial,sans-serif;font-weight:700;font-size:15px;letter-spacing:.05em;text-transform:uppercase;margin:8px 6px}
.btn:hover{background:var(--gold-soft);text-decoration:none}
.btn.ghost{background:transparent;color:var(--gold);border:1px solid var(--gold)}
.btn.ghost:hover{background:rgba(201,162,75,.12)}
section{padding:38px 0}
h2{font-size:clamp(21px,3.2vw,29px);text-align:center;font-weight:400;margin-bottom:6px}
.sub{color:var(--muted);text-align:center;margin-bottom:30px;font-size:16px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(148px,1fr));gap:20px}
.grid a{display:block;text-align:center;color:var(--parchment);font-size:14px}
.grid img{width:100%;border-radius:3px;box-shadow:0 6px 22px rgba(0,0,0,.55);transition:transform .15s}
.grid a:hover img{transform:translateY(-4px)}
.grid span{display:block;margin-top:8px}
.warning{background:var(--panel);border-left:3px solid var(--gold);padding:24px 28px;max-width:760px;margin:0 auto;font-size:17px}
.warning b{color:var(--gold)}
.capture{background:var(--panel);border:1px solid #2a231b;border-radius:5px;padding:30px;max-width:640px;margin:0 auto;text-align:center}
.capture h2{margin-bottom:10px}
.capture .why{color:var(--muted);font-size:15.5px;margin-bottom:18px}
.signup{display:block}
.signup input[type=email]{width:min(340px,86%);padding:13px 15px;border-radius:3px;border:1px solid #3a3025;background:#0d0b08;color:var(--parchment);font-family:Georgia,serif;font-size:16px;margin:0 6px 10px 0}
.signup input[type=email]:focus{outline:none;border-color:var(--gold)}
.signup button{border:none;cursor:pointer;vertical-align:top}
.opt{display:block;margin-top:12px;color:var(--muted);font-size:14.5px;cursor:pointer}
.opt input{margin-right:7px}
.fineprint{color:var(--muted);font-size:13.5px;margin-top:12px}
.bookhead{display:flex;gap:34px;align-items:flex-start;flex-wrap:wrap;padding:26px 0 8px}
.bookhead img{width:230px;border-radius:4px;box-shadow:0 10px 32px rgba(0,0,0,.6)}
.bookhead .meta{flex:1;min-width:270px}
.bookhead h1{text-align:left;font-size:clamp(25px,4vw,38px)}
.kicker{color:var(--gold);font-family:Futura,'Trebuchet MS',Arial,sans-serif;font-size:12.5px;letter-spacing:.22em;text-transform:uppercase}
.blurb{max-width:760px;margin:0 auto;font-size:17px}
.blurb p{margin:14px 0}.blurb ul{margin:14px 0 14px 22px}.blurb li{margin:7px 0}
.crumbs{font-size:13.5px;color:var(--muted);padding:14px 0}
footer{border-top:1px solid #262019;margin-top:26px;padding:28px 0 42px;text-align:center;color:var(--muted);font-size:13.5px}
footer .links{margin-bottom:9px;font-size:14.5px}
@media(max-width:640px){.bookhead{gap:22px}.bookhead img{width:160px;margin:0 auto}}
"""

# Set once the Turbo History MailerLite account exists (separate from the business
# account - different brand, different sender domain, different consent purpose).
# Paste the embedded-form action URL here and the real form renders automatically.
ML_FORM_ACTION = ""


def capture(book: dict | None = None) -> str:
    """Email capture. Honest hook: the books really are free most weekends."""
    if book:
        head = "This book is free sometimes. Want to know when?"
        why = (f"{esc(book['name'])} goes free on Amazon from time to time, along with the "
               f"rest of the series. Leave your email and we will tell you the moment it does.")
        extra = ('<label class="opt"><input type="checkbox" name="groups[]" value="all" checked> '
                 'Tell me about every free Turbo History book, not just this one</label>')
        hidden = f'<input type="hidden" name="fields[book_interest]" value="{esc(book["slug"])}">'
    else:
        head = "Turbo History books are free most weekends."
        why = ("Most weekends one book in the series goes completely free on Amazon. Leave "
               "your email and we will tell you which one, before it goes back to full price.")
        extra = ""
        hidden = ""

    if ML_FORM_ACTION:
        form = f"""<form class="signup" action="{ML_FORM_ACTION}" method="post" target="_blank">
      {hidden}
      <input type="email" name="fields[email]" placeholder="you@example.com" required aria-label="Email address">
      <button class="btn" type="submit">Notify Me</button>
      {extra}
      <p class="fineprint">Free books only. No spam, unsubscribe any time.</p>
    </form>"""
    else:
        form = f"""<p><a class="btn" href="mailto:{EMAIL}?subject=Free%20book%20alerts">Email Us to Join the List</a></p>
      <p class="fineprint">Free books only. No spam, unsubscribe any time.</p>"""

    return f"""<section class="wrap"><div class="capture">
  <h2>{head}</h2>
  <p class="why">{why}</p>
  {form}
</div></section>"""


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def shell(page_title: str, description: str, canonical: str, body: str,
          schema: dict | None = None, og_image: str | None = None) -> str:
    schema_tag = ""
    if schema:
        schema_tag = ('<script type="application/ld+json">'
                      + json.dumps(schema, ensure_ascii=False) + "</script>")
    og = og_image or f"{BASE}/covers/blackbeard.jpg"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(page_title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{esc(page_title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{canonical}">
<meta property="og:type" content="website">
<meta property="og:image" content="{og}">
<meta name="twitter:card" content="summary_large_image">
{HEAD_EXTRA}
{schema_tag}
<style>{CSS}</style>
</head>
<body>
<div class="wrap"><nav class="nav">
  <a class="logo" href="/">Turbo History</a>
  <span><a href="/#books">The Books</a><a href="{AMAZON_AUTHOR}">Amazon</a></span>
</nav></div>
{body}
<footer><div class="wrap">
  <div class="links"><a href="/">Home</a> &middot; <a href="{AMAZON_AUTHOR}">Amazon Author Page</a> &middot; <a href="mailto:{EMAIL}">{EMAIL}</a></div>
  <div>&copy; Turbo History. All books available on Amazon and Kindle Unlimited.</div>
</div></footer>
</body>
</html>
"""


def load_books() -> list[dict]:
    books = json.loads(CATALOGUE.read_text())
    out = []
    for b in books:
        if not b.get("asin"):
            continue  # blocked/unpublished: never link to a dead product page
        meta_path = READY / b["slug"] / "metadata.json"
        meta = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
            except Exception:
                pass
        b["title"] = meta.get("title") or b["name"]
        b["hook"] = (b["title"].split(":", 1)[1].strip()
                     if ":" in b["title"] else b.get("hook", ""))
        b["blurb"] = meta.get("blurb", "")
        b["amazon"] = f"https://www.amazon.com/dp/{b['asin']}"
        out.append(b)
    out.sort(key=lambda x: x.get("series_n", 999))
    return out


def make_thumbs(books: list[dict]) -> None:
    (SITE / "covers").mkdir(parents=True, exist_ok=True)
    for b in books:
        src = READY / b["slug"] / "cover.jpg"
        dst = SITE / "covers" / f"{b['slug']}.jpg"
        if src.exists() and (not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime):
            subprocess.run(["sips", "-Z", "480", str(src), "--out", str(dst)],
                           capture_output=True)


def blurb_html(blurb: str) -> str:
    """Pipeline blurbs are plain text with bullet lines. Render as real HTML."""
    out, bullets = [], []
    for raw in (blurb or "").split("\n"):
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
        if line.startswith(("•", "-", "*")):
            bullets.append(f"<li>{line.lstrip('•-* ').strip()}</li>")
        else:
            if bullets:
                out.append("<ul>" + "".join(bullets) + "</ul>")
                bullets = []
            out.append(f"<p>{line}</p>")
    if bullets:
        out.append("<ul>" + "".join(bullets) + "</ul>")
    return "".join(out)


def book_page(b: dict, books: list[dict]) -> str:
    name, slug = b["name"], b["slug"]
    is_writer = slug in SEO_WRITERS
    # SEO title targets the money phrase: "<subject> book" / "best books about <subject>"
    title = (f"{name}: A Short Biography You Can Finish in an Hour | Turbo History"
             if is_writer else
             f"{name} Book: The Short Version, Read in Under an Hour | Turbo History")
    desc = (f"Want a book about {name} without the 600 pages? {b['title']} tells the "
            f"story in about an hour. The rise, the fall, why it still matters. "
            f"Free on Kindle Unlimited.")
    others = [x for x in books if x["slug"] != slug][:6]
    rel = "".join(
        f'<a href="/books/{o["slug"]}/"><img src="/covers/{o["slug"]}.jpg" alt="{esc(o["name"])} book cover" loading="lazy"><span>{esc(o["name"])}</span></a>'
        for o in others)
    schema = {
        "@context": "https://schema.org", "@type": "Book",
        "name": b["title"], "author": {"@type": "Organization", "name": "Turbo History"},
        "about": name, "bookFormat": "https://schema.org/EBook",
        "inLanguage": "en", "url": f"{BASE}/books/{slug}/",
        "image": f"{BASE}/covers/{slug}.jpg", "isPartOf": {"@type": "BookSeries", "name": "Turbo History"},
        "description": desc, "offers": {"@type": "Offer", "price": "2.99",
                                        "priceCurrency": "USD", "url": b["amazon"],
                                        "availability": "https://schema.org/InStock"},
    }
    body = f"""
<div class="wrap"><div class="crumbs"><a href="/">Turbo History</a> &rsaquo; {esc(name)}</div></div>
<div class="wrap"><div class="bookhead">
  <img src="/covers/{slug}.jpg" alt="{esc(b['title'])} book cover">
  <div class="meta">
    <div class="kicker">Turbo History #{b.get('series_n','')}</div>
    <h1>{esc(name)}</h1>
    <p class="tag">{esc(b['hook'])}</p>
    <p class="muted" style="margin-top:14px">About an hour to read. &pound;2.99 / $2.99, free on Kindle Unlimited.</p>
    <p><a class="btn" href="{b['amazon']}">Read it on Amazon</a>
       <a class="btn ghost" href="{AMAZON_AUTHOR}">All {len(books)} Books</a></p>
  </div>
</div></div>
<section class="wrap"><div class="blurb">{blurb_html(b['blurb'])}</div></section>
<section class="wrap"><div class="warning">
  <b>Looking for the definitive doorstop instead?</b> This is not that book, and it does not
  pretend to be. No footnotes, no family trees, no ten pages on a treaty. If you want the
  full scholarly treatment of {esc(name)}, buy the big one. If you want the story and the
  big picture in an hour, this is built for you.
</div></section>
{capture(b)}
<section class="wrap" id="more"><h2>More from the series</h2>
  <p class="sub">One figure or one event per book. About an hour each.</p>
  <div class="grid">{rel}</div>
</section>
"""
    return shell(title, desc, f"{BASE}/books/{slug}/", body, schema,
                 og_image=f"{BASE}/covers/{slug}.jpg")


def index_page(books: list[dict]) -> str:
    by_slug = {b["slug"]: b for b in books}
    featured = [by_slug[s] for s in FEATURED if s in by_slug] or books[:12]
    fg = "".join(
        f'<a href="/books/{b["slug"]}/"><img src="/covers/{b["slug"]}.jpg" alt="{esc(b["title"])} book cover" loading="lazy"><span>{esc(b["name"])}</span></a>'
        for b in featured)
    allg = "".join(
        f'<a href="/books/{b["slug"]}/"><img src="/covers/{b["slug"]}.jpg" alt="{esc(b["title"])} book cover" loading="lazy"><span>{esc(b["name"])}</span></a>'
        for b in books)
    n = len(books)
    desc = (f"Love history, but hate how it was taught at school? Turbo History: one figure "
            f"or one event per book, told in about an hour. {n} books. No filler, no "
            f"600-page epics. Free on Kindle Unlimited.")
    schema = {
        "@context": "https://schema.org", "@type": "BookSeries", "name": "Turbo History",
        "url": BASE + "/", "numberOfItems": n,
        "description": ("Short history books for casual history lovers. One figure or one "
                        "event per book, told in about an hour: the story, the turning "
                        "points, why it still matters. Not academic."),
        "author": {"@type": "Organization", "name": "Turbo History",
                   "email": EMAIL, "url": BASE + "/"},
        "genre": ["History", "Biography"], "sameAs": [AMAZON_AUTHOR],
    }
    body = f"""
<header class="wrap"><h1>Love history, but hate<br>how it was taught at school?</h1></header>
<div class="hero wrap">
  <p class="muted">Same. School taught history like a memory test: names, dates, family trees, exam. The actual story never stood a chance.</p>
  <div class="rule"></div>
  <p>Turbo History is different. One figure or one event per book, told in about an hour. The rise, the fall, the why-it-still-matters. Straight to the point, every time: no filler, no waffle, no 600-page epics. Dates included, memorizing optional.</p>
  <p class="tag">{n} books and counting. Start anywhere. Finish everything.</p>
  <p><a class="btn" href="{AMAZON_AUTHOR}">Browse the Series on Amazon</a></p>
  <p class="muted" style="font-size:15px">&pound;2.99 / $2.99 each, free with Kindle Unlimited, and most weekends one of them is free for everyone.</p>
</div>
<section class="wrap"><h2>Queens and conquerors. Pirates and rebels.</h2>
  <p class="sub">Minds that changed everything, and the wars that changed everything else.</p>
  <div class="grid">{fg}</div>
</section>
<section class="wrap"><div class="warning">
  <b>Fair warning:</b> these are not academic books. No footnotes, no family trees, no ten
  pages on a treaty. If you want that depth, you'll want a bigger book. If you want the
  story and the big picture, you're home.
</div></section>
{capture()}
<section class="wrap" id="books"><h2>Every book in the series</h2>
  <p class="sub">{n} and counting. Start anywhere.</p>
  <div class="grid">{allg}</div>
</section>
<section class="wrap" id="contact" style="text-align:center">
  <h2>Contact</h2>
  <p class="sub" style="margin-bottom:12px">Questions, requests for who to cover next, or anything else.</p>
  <p style="font-size:18px"><a href="mailto:{EMAIL}">{EMAIL}</a></p>
  <p class="muted" style="font-size:14.5px;margin-top:10px">Turbo History is written and published by Turbo History.<br>Every book is available on Amazon and Kindle Unlimited.</p>
</section>
"""
    return shell(
        "Turbo History | One-Hour History Books for People Who Hate How History Was Taught",
        desc, BASE + "/", body, schema)


def main() -> None:
    books = load_books()
    SITE.mkdir(parents=True, exist_ok=True)
    make_thumbs(books)

    (SITE / "index.html").write_text(index_page(books))

    books_dir = SITE / "books"
    if books_dir.exists():
        shutil.rmtree(books_dir)
    for b in books:
        d = books_dir / b["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(book_page(b, books))

    today = date.today().isoformat()
    urls = [(BASE + "/", "1.0")] + [(f"{BASE}/books/{b['slug']}/", "0.8") for b in books]
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{u}</loc><lastmod>{today}</lastmod>"
                  f"<priority>{p}</priority></url>\n" for u, p in urls)
        + "</urlset>\n")
    (SITE / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")

    print(f"built {len(books)} book pages + index")
    print(f"  sitemap: {len(urls)} urls")
    missing = [b["slug"] for b in books if not (SITE / "covers" / f"{b['slug']}.jpg").exists()]
    if missing:
        print(f"  WARNING missing covers: {missing}")


if __name__ == "__main__":
    main()
