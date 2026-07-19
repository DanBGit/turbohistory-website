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
<script>
// Google Consent Mode v2. Default DENIED everywhere; granted immediately for visitors
// outside consent-required jurisdictions, or on explicit Accept. No tag fires before this.
window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}
gtag('consent','default',{{ad_storage:'denied',ad_user_data:'denied',
 ad_personalization:'denied',analytics_storage:'denied',functionality_storage:'granted',
 security_storage:'granted',wait_for_update:1500}});
</script>
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>gtag('js',new Date());gtag('config','{GA_ID}',{{anonymize_ip:true}});</script>"""

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
html.ck-lock,html.ck-lock body{overflow:hidden}
.hp{position:absolute!important;left:-9999px;width:1px;height:1px;opacity:0}
.consent{display:flex;gap:10px;align-items:flex-start;text-align:left;margin-top:12px;font-size:14.5px;line-height:1.5}
.consent input{width:19px;height:19px;accent-color:var(--gold);flex-shrink:0;margin-top:2px}
.submsg{min-height:1em;margin-top:12px;font-size:15px}
.submsg.err{color:#e08b7a}
.submsg.ok{color:var(--gold);font-size:17px}
.pick{padding:22px 0;border-bottom:1px solid #221c16}
.pick-ours{background:rgba(201,162,75,.06);border:1px solid #4a3c22;border-radius:5px;padding:22px 24px;margin:10px 0}
.pick-ours h3{color:var(--gold)}
.tag{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink);background:var(--gold);padding:3px 8px;border-radius:3px;vertical-align:middle;margin-left:8px;font-family:system-ui,sans-serif}
tr.ours td{background:rgba(201,162,75,.08);border-top:1px solid #4a3c22;border-bottom:1px solid #4a3c22}
#ck[hidden],#ck-prefs[hidden]{display:none!important}
#ck{position:fixed;inset:0;z-index:999;background:rgba(6,5,4,.86);backdrop-filter:blur(3px);display:flex;align-items:center;justify-content:center;padding:20px}
.ck-box{background:var(--panel);border:1px solid #3a3025;border-radius:6px;max-width:520px;width:100%;padding:32px;box-shadow:0 20px 60px rgba(0,0,0,.7);text-align:center;max-height:90vh;overflow-y:auto}
.ck-box h2{font-size:24px;margin-bottom:12px}
.ck-box p{font-size:15.5px;color:var(--parchment);margin-bottom:20px}
.ck-acts{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
.ck-acts .btn{margin:0;min-width:150px}
.ck-acts .btn.ghost{opacity:.8;font-weight:400}
.ck-link{display:block;margin:16px auto 0;background:none;border:none;color:var(--muted);font-family:Georgia,serif;font-size:14px;text-decoration:underline;cursor:pointer}
.ck-link:hover{color:var(--gold)}
#ck-prefs{margin-top:18px;border-top:1px solid #2a231b;padding-top:16px;text-align:left}
.ck-row{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;padding:12px 0;border-bottom:1px solid #221c16;font-size:14.5px}
.ck-row input{width:20px;height:20px;accent-color:var(--gold);flex-shrink:0;margin-top:2px}
#ck-save{margin-top:14px;width:100%}
.ck-fine{font-size:13px;color:var(--muted);margin:18px 0 0}
@media(max-width:620px){.ck-box{padding:24px 20px}.ck-acts .btn{flex:1;min-width:0}}
.bookhead{display:flex;gap:34px;align-items:flex-start;flex-wrap:wrap;padding:26px 0 8px}
.bookhead img{width:230px;border-radius:4px;box-shadow:0 10px 32px rgba(0,0,0,.6)}
.bookhead .meta{flex:1;min-width:270px}
.bookhead h1{text-align:left;font-size:clamp(25px,4vw,38px)}
.kicker{color:var(--gold);font-family:Futura,'Trebuchet MS',Arial,sans-serif;font-size:12.5px;letter-spacing:.22em;text-transform:uppercase}
.blurb{max-width:760px;margin:0 auto;font-size:17px}
.blurb p{margin:14px 0}.blurb ul{margin:14px 0 14px 22px}.blurb li{margin:7px 0}
.crumbs{font-size:13.5px;color:var(--muted);padding:14px 0}
.lede{font-size:19px;line-height:1.6}
.note{font-size:14.5px;font-style:italic}
.tablewrap{overflow-x:auto;max-width:900px;margin:0 auto}
table.picks{width:100%;border-collapse:collapse;font-size:15.5px}
table.picks th{text-align:left;padding:12px 14px;border-bottom:2px solid var(--gold);color:var(--gold);font-family:Futura,'Trebuchet MS',Arial,sans-serif;font-size:13px;letter-spacing:.1em;text-transform:uppercase}
table.picks td{padding:14px;border-bottom:1px solid #262019;vertical-align:top}
table.picks tr.ours{background:rgba(201,162,75,.09)}
table.picks tr.ours td{border-bottom:none}
.blurb h3{margin:26px 0 4px;font-size:20px;color:var(--parchment);font-weight:400}
.byline{color:var(--muted);font-size:14.5px;margin:0 0 8px}
footer{border-top:1px solid #262019;margin-top:26px;padding:28px 0 42px;text-align:center;color:var(--muted);font-size:13.5px}
footer .links{margin-bottom:9px;font-size:14.5px}
@media(max-width:640px){.bookhead{gap:22px}.bookhead img{width:160px;margin:0 auto}}
"""

# Jurisdictions where we ask BEFORE firing analytics. EEA + UK + Switzerland (opt-in
# regimes) and Brazil/Canada. US is opt-out under CCPA/CPRA, so US visitors get analytics
# immediately plus a "Your privacy choices" footer link that opens the same panel.
CONSENT_JS = """
<div id="ck" hidden role="dialog" aria-modal="true" aria-labelledby="ck-h">
  <div class="ck-box">
    <h2 id="ck-h">Before you read on</h2>
    <p>We use Google Analytics to see which books people are actually interested in.
       That is the only thing we track, we run no ads, and we never sell anything to anyone.</p>
    <div class="ck-acts">
      <button id="ck-yes" class="btn">Accept All</button>
      <button id="ck-no" class="btn ghost">Reject</button>
    </div>
    <button id="ck-man" class="ck-link">Manage preferences</button>
    <div id="ck-prefs" hidden>
      <label class="ck-row"><span><b>Strictly necessary</b><br>
        <span class="muted">Needed for the site to work. Always on.</span></span>
        <input type="checkbox" checked disabled></label>
      <label class="ck-row"><span><b>Analytics</b><br>
        <span class="muted">Google Analytics: which pages get read. No ads, no profiling.</span></span>
        <input type="checkbox" id="ck-an"></label>
      <button id="ck-save" class="btn ghost">Save preferences</button>
    </div>
    <p class="ck-fine">Read our <a href="/privacy/">privacy policy</a>. You can change your
       mind any time using "Your privacy choices" at the bottom of any page.</p>
  </div>
</div>
<script>
(function(){
  var ASK=['AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','GR','HU','IE','IT','LV',
  'LT','LU','MT','NL','PL','PT','RO','SK','SI','ES','SE','IS','LI','NO','GB','CH','BR','CA'];
  var K='th_consent', el=document.getElementById('ck'), root=document.documentElement;
  function grant(v){ try{ gtag('consent','update',{ad_storage:v,ad_user_data:v,
    ad_personalization:v,analytics_storage:v}); }catch(e){} }
  function open_(){ el.hidden=false; root.classList.add('ck-lock'); }
  function shut(){ el.hidden=true; root.classList.remove('ck-lock'); }
  function save(v){ try{localStorage.setItem(K,v);}catch(e){} grant(v==='yes'?'granted':'denied'); shut(); }
  document.getElementById('ck-yes').onclick=function(){ save('yes'); };
  document.getElementById('ck-no').onclick=function(){ save('no'); };
  document.getElementById('ck-man').onclick=function(){
    var p=document.getElementById('ck-prefs'); p.hidden=!p.hidden; };
  document.getElementById('ck-save').onclick=function(){
    save(document.getElementById('ck-an').checked?'yes':'no'); };
  window.thPrivacy=function(){
    var saved=null; try{saved=localStorage.getItem(K);}catch(e){}
    document.getElementById('ck-an').checked = (saved==='yes');
    open_(); };

  var saved=null; try{saved=localStorage.getItem(K);}catch(e){}
  if(saved){ grant(saved==='yes'?'granted':'denied'); return; }

  // Country comes free from Cloudflare on our own domain. No third party.
  fetch('/cdn-cgi/trace').then(function(r){return r.text();}).then(function(t){
    var m=/loc=([A-Z]{2})/.exec(t);
    if(m && ASK.indexOf(m[1])>-1){ open_(); }   // decision required before reading
    else { grant('granted'); }                   // opt-out regions: on by default
  }).catch(function(){ open_(); });
})();
</script>
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

    # Real capture, posted to our own /api on our own box. No third-party form host,
    # so subscriber data never leaves infrastructure Daniel controls.
    #
    # The consent tick is shown only where consent must be explicit (EEA/UK/CH/BR/CA).
    # Elsewhere the notice alone is enough and an extra click just costs signups. The
    # server enforces the same rule, so removing the box in devtools gains nothing, and
    # if the geo lookup fails we show the box rather than guess.
    consent_text = ("Yes, email me when Turbo History books are free. "
                    "I can unsubscribe any time.")
    form = f"""<form class="signup" id="sub" novalidate>
      {hidden}
      <input type="email" name="email" placeholder="you@example.com" required
             autocomplete="email" aria-label="Email address">
      <button class="btn" type="submit">Tell Me When They Are Free</button>
      <input type="text" name="website" class="hp" tabindex="-1" autocomplete="off"
             aria-hidden="true">
      {extra}
      <label class="opt consent" hidden><input type="checkbox" name="consent">
        <span>{esc(consent_text)}</span></label>
      <p class="submsg" role="status" aria-live="polite"></p>
      <p class="fineprint">We only ever use it to tell you when a book is free. No ads, no
      sharing, no selling. Unsubscribe in one click. See our
      <a href="/privacy/">privacy policy</a>.</p>
    </form>
    <script>
    (function(){{
      var f=document.getElementById('sub'); if(!f) return;
      var msg=f.querySelector('.submsg'), box=f.querySelector('.consent');
      var TEXT={json.dumps(consent_text)};
      var ASK=['AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','GR','HU','IE','IT',
      'LV','LT','LU','MT','NL','PL','PT','RO','SK','SI','ES','SE','IS','LI','NO','GB','CH','BR','CA'];
      var country='';
      fetch('/cdn-cgi/trace').then(function(r){{return r.text();}}).then(function(t){{
        var m=/loc=([A-Z]{{2}})/.exec(t); country=m?m[1]:'';
        if(!country||ASK.indexOf(country)>-1) box.hidden=false;
      }}).catch(function(){{ box.hidden=false; }});
      f.addEventListener('submit',function(e){{
        e.preventDefault();
        var btn=f.querySelector('button'), body={{
          email:f.email.value, website:f.website.value, country:country,
          consent:box.hidden?true:f.consent.checked, consent_text:TEXT,
          source:location.pathname }};
        if(!box.hidden && !f.consent.checked){{
          msg.className='submsg err'; msg.textContent='Please tick the box so we know you want them.'; return; }}
        btn.disabled=true; msg.className='submsg'; msg.textContent='One moment...';
        fetch('/api/subscribe',{{method:'POST',headers:{{'Content-Type':'application/json'}},
          body:JSON.stringify(body)}})
          .then(function(r){{return r.json();}})
          .then(function(d){{
            if(d.ok){{ f.innerHTML='<p class="submsg ok">'+(d.message||'You are in.')+
              ' We will email you the next time a book goes free.</p>'; }}
            else {{ msg.className='submsg err'; msg.textContent=d.error||'Something went wrong.';
              btn.disabled=false; }}
          }})
          .catch(function(){{ msg.className='submsg err';
            msg.textContent='Could not reach us. Please try again.'; btn.disabled=false; }});
      }});
    }})();
    </script>"""

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
  <div class="links"><a href="/">Home</a> &middot; <a href="{AMAZON_AUTHOR}">Amazon Author Page</a> &middot; <a href="/privacy/">Privacy</a> &middot; <a href="#" onclick="thPrivacy();return false;">Your privacy choices</a> &middot; <a href="mailto:{EMAIL}">{EMAIL}</a></div>
  <div>&copy; Turbo History. All books available on Amazon and Kindle Unlimited.</div>
</div></footer>
{CONSENT_JS}
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



CURATION_DIR = PROJECT / "seo" / "curation"


def curated_page(c: dict, b: dict, books: list[dict]) -> str:
    """Curated-list page. Beats the incumbents by being more useful: honest picks,
    real reading times, and a clear 'start here'. FAQ schema included because AI
    assistants weight it heavily when choosing what to cite."""
    slug = c["slug"]
    # Ours is slotted in at its honest place in the list, not bolted on the end and
    # not floated to the top. Highlighted so nobody can claim we hid the fact it is ours.
    o = c["ours"]
    ours = dict(title=b["title"], author="Turbo History", year=None,
                length=o["length"], time=o["time"], best_for=o["best_for"],
                why=o["why"], is_ours=True)
    items = list(c["picks"])
    items.insert(min(max(int(o.get("position", len(items) + 1)) - 1, 0), len(items)), ours)

    def byline(p):
        return esc(p["author"]) + (" &middot; ours" if p.get("is_ours")
                                   else ", " + str(p["year"]))

    rows = []
    for p in items:
        cls = " class='ours'" if p.get("is_ours") else ""
        rows.append(
            "<tr" + cls + "><td><b>" + esc(p["title"]) + "</b><br>"
            "<span class='muted'>" + byline(p) + "</span></td>"
            "<td>" + esc(p["length"]) + "<br><span class='muted'>" + esc(p["time"]) +
            "</span></td><td>" + esc(p["best_for"]) + "</td></tr>")
    rows = "".join(rows)

    detail = []
    for i, p in enumerate(items, 1):
        mine = p.get("is_ours")
        cls = " pick pick-ours" if mine else " pick"
        anchor = " id='ours'" if mine else ""
        tag = " <span class='tag'>ours</span>" if mine else ""
        cta = ("<p><a class='btn' href='" + b["amazon"] + "'>Read it on Amazon</a></p>"
               if mine else "")
        body_ps = "".join("<p>" + esc(x) + "</p>" for x in p["why"].split("\n\n"))
        detail.append(
            "<div class='" + cls.strip() + "'" + anchor + "><h3>" + str(i) + ". " +
            esc(p["title"]) + tag + "</h3><p class='byline'>" + byline(p) + " &middot; " +
            esc(p["length"]) + " &middot; " + esc(p["time"]) + " &middot; <b>" +
            esc(p["best_for"]) + "</b></p>" + body_ps + cta + "</div>")
    detail = "".join(detail)

    faqs = "".join(f"<h3>{esc(f['q'])}</h3><p>{esc(f['a'])}</p>" for f in c["faq"])

    others = [x for x in books if x["slug"] != slug][:6]
    rel = "".join(
        f'<a href="/books/{o["slug"]}/"><img src="/covers/{o["slug"]}.jpg" alt="{esc(o["name"])} book cover" loading="lazy"><span>{esc(o["name"])}</span></a>'
        for o in others)

    schema = {"@context": "https://schema.org", "@graph": [
        {"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": f["q"],
             "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in c["faq"]]},
        {"@type": "Book", "name": b["title"],
         "author": {"@type": "Organization", "name": "Turbo History"},
         "about": b["name"], "bookFormat": "https://schema.org/EBook",
         "url": f"{BASE}/books/{slug}/", "image": f"{BASE}/covers/{slug}.jpg",
         "isPartOf": {"@type": "BookSeries", "name": "Turbo History"},
         "offers": {"@type": "Offer", "price": "2.99", "priceCurrency": "USD",
                    "url": b["amazon"], "availability": "https://schema.org/InStock"}}]}

    body = f"""
<div class="wrap"><div class="crumbs"><a href="/">Turbo History</a> &rsaquo; {esc(b['name'])}</div></div>
<header class="wrap"><h1>{esc(c['h1'])}</h1></header>
<section class="wrap"><div class="blurb">
  <p class="lede">{esc(c['intro_answer'])}</p>
  <p class="muted note">{esc(c['note'])}</p>
</div></section>

<section class="wrap"><h2>The short version</h2>
<p class="sub">Sorted by what you want, not by what is most famous.</p>
<div class="tablewrap"><table class="picks">
<thead><tr><th>Book</th><th>Length</th><th>Best for</th></tr></thead>
<tbody>{rows}</tbody></table></div>
</section>

<section class="wrap"><div class="blurb"><h2 style="text-align:left">The picks, in detail</h2>
{detail}
</div></section>


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



CURATION_DIR = PROJECT / "seo" / "curation"


def curated_page(c: dict, b: dict, books: list[dict]) -> str:
    """Curated-list page. Beats the incumbents by being more useful: honest picks,
    real reading times, and a clear 'start here'. FAQ schema included because AI
    assistants weight it heavily when choosing what to cite."""
    slug = c["slug"]
    # Ours is slotted in at its honest place in the list, not bolted on the end and
    # not floated to the top. Highlighted so nobody can claim we hid the fact it is ours.
    o = c["ours"]
    ours = dict(title=b["title"], author="Turbo History", year=None,
                length=o["length"], time=o["time"], best_for=o["best_for"],
                why=o["why"], is_ours=True)
    items = list(c["picks"])
    items.insert(min(max(int(o.get("position", len(items) + 1)) - 1, 0), len(items)), ours)

    def byline(p):
        return esc(p["author"]) + (" &middot; ours" if p.get("is_ours")
                                   else ", " + str(p["year"]))

    rows = []
    for p in items:
        cls = " class='ours'" if p.get("is_ours") else ""
        rows.append(
            "<tr" + cls + "><td><b>" + esc(p["title"]) + "</b><br>"
            "<span class='muted'>" + byline(p) + "</span></td>"
            "<td>" + esc(p["length"]) + "<br><span class='muted'>" + esc(p["time"]) +
            "</span></td><td>" + esc(p["best_for"]) + "</td></tr>")
    rows = "".join(rows)

    detail = []
    for i, p in enumerate(items, 1):
        mine = p.get("is_ours")
        cls = " pick pick-ours" if mine else " pick"
        anchor = " id='ours'" if mine else ""
        tag = " <span class='tag'>ours</span>" if mine else ""
        cta = ("<p><a class='btn' href='" + b["amazon"] + "'>Read it on Amazon</a></p>"
               if mine else "")
        body_ps = "".join("<p>" + esc(x) + "</p>" for x in p["why"].split("\n\n"))
        detail.append(
            "<div class='" + cls.strip() + "'" + anchor + "><h3>" + str(i) + ". " +
            esc(p["title"]) + tag + "</h3><p class='byline'>" + byline(p) + " &middot; " +
            esc(p["length"]) + " &middot; " + esc(p["time"]) + " &middot; <b>" +
            esc(p["best_for"]) + "</b></p>" + body_ps + cta + "</div>")
    detail = "".join(detail)

    faqs = "".join(f"<h3>{esc(f['q'])}</h3><p>{esc(f['a'])}</p>" for f in c["faq"])

    others = [x for x in books if x["slug"] != slug][:6]
    rel = "".join(
        f'<a href="/books/{o["slug"]}/"><img src="/covers/{o["slug"]}.jpg" alt="{esc(o["name"])} book cover" loading="lazy"><span>{esc(o["name"])}</span></a>'
        for o in others)

    schema = {"@context": "https://schema.org", "@graph": [
        {"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": f["q"],
             "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in c["faq"]]},
        {"@type": "Book", "name": b["title"],
         "author": {"@type": "Organization", "name": "Turbo History"},
         "about": b["name"], "bookFormat": "https://schema.org/EBook",
         "url": f"{BASE}/books/{slug}/", "image": f"{BASE}/covers/{slug}.jpg",
         "isPartOf": {"@type": "BookSeries", "name": "Turbo History"},
         "offers": {"@type": "Offer", "price": "2.99", "priceCurrency": "USD",
                    "url": b["amazon"], "availability": "https://schema.org/InStock"}}]}

    body = f"""
<div class="wrap"><div class="crumbs"><a href="/">Turbo History</a> &rsaquo; {esc(b['name'])}</div></div>
<header class="wrap"><h1>{esc(c['h1'])}</h1></header>
<section class="wrap"><div class="blurb">
  <p class="lede">{esc(c['intro_answer'])}</p>
  <p class="muted note">{esc(c['note'])}</p>
</div></section>

<section class="wrap"><h2>The short version</h2>
<p class="sub">Sorted by what you want, not by what is most famous.</p>
<div class="tablewrap"><table class="picks">
<thead><tr><th>Book</th><th>Length</th><th>Best for</th></tr></thead>
<tbody>{rows}</tbody></table></div>
</section>

<section class="wrap"><div class="blurb"><h2 style="text-align:left">The picks, in detail</h2>
{detail}
</div></section>

<section class="wrap"><div class="bookhead">
  <img src="/covers/{slug}.jpg" alt="{esc(b['title'])} book cover">
  <div class="meta">
    <div class="kicker">And ours, honestly</div>
    <h1 style="font-size:clamp(23px,3.4vw,32px)">{esc(b['title'])}</h1>
    <p>{esc(c['ours']['why'])}</p>
    <p><a class="btn" href="{b['amazon']}">Read it on Amazon</a>
       <a class="btn ghost" href="{AMAZON_AUTHOR}">The whole series</a></p>
    <p class="muted">&pound;2.99 / $2.99, free on Kindle Unlimited.</p>
  </div>
</div></section>

<section class="wrap"><div class="blurb"><h2 style="text-align:left">Questions people actually ask</h2>
{faqs}
</div></section>
{capture(b)}
<section class="wrap"><h2>More from the series</h2>
  <p class="sub">One figure or one event per book. About an hour each.</p>
  <div class="grid">{rel}</div>
</section>
"""
    return shell(c["meta_title"], c["meta_description"], f"{BASE}/books/{slug}/",
                 body, schema, og_image=f"{BASE}/covers/{slug}.jpg")


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



PRIVACY_BODY = f"""
<div class="wrap"><div class="crumbs"><a href="/">Turbo History</a> &rsaquo; Privacy</div></div>
<header class="wrap"><h1 style="font-size:clamp(26px,4vw,40px)">Privacy Policy</h1></header>
<section class="wrap"><div class="blurb">
<p class="muted">Last updated: {{updated}}. Short version: we run Google Analytics to see which
books people are interested in, and if you give us your email we use it to tell you when
books are free. We do not sell anything to anyone, ever.</p>

<h2 style="text-align:left;margin-top:30px">Who we are</h2>
<p>This site is run by Turbo History, an independent publisher of short history books.
Contact us about anything on this page at <a href="mailto:privacy@turbohistory.com">privacy@turbohistory.com</a>.</p>

<h2 style="text-align:left;margin-top:30px">What we collect</h2>
<p><b>Analytics.</b> We use Google Analytics 4 to count visits and see which book pages are
popular. It sets cookies and collects things like your approximate location, device and
which pages you viewed. Your IP address is anonymised. In the UK, EEA, Switzerland, Brazil
and Canada none of this runs unless you press Accept. Everywhere else it runs by default
and you can turn it off any time using "Your privacy choices" in the footer.</p>
<p><b>Your email, if you give it.</b> If you sign up for free book alerts we store your email
address and, if you told us, which book you were interested in. We use it for one thing:
telling you when Turbo History books are free or newly released. We do not sell, rent or
share it. Every email has a one-click unsubscribe.</p>
<p><b>Proof that you agreed.</b> When you subscribe we also record the date and time, your
country, your IP address and the exact wording you agreed to. That is not marketing data. It
exists so we can show you really did ask to be on the list, and it is deleted along with your
email the moment you unsubscribe.</p>
<p><b>Server logs.</b> Our host keeps standard web server logs (IP, page, time) for security
and troubleshooting.</p>

<h2 style="text-align:left;margin-top:30px">Legal basis</h2>
<p>Analytics: your consent, where consent is required. Email alerts: your consent, given when
you subscribe. Server logs: our legitimate interest in keeping the site up and secure.</p>

<h2 style="text-align:left;margin-top:30px">Who else sees it</h2>
<p>Google, for analytics, and only if you consented. That is the only third party involved.
Your email address is stored on our own server rather than handed to a mailing list company,
so nobody else touches it. If that ever changes we will say so here first. We never sell data.</p>

<h2 style="text-align:left;margin-top:30px">How long we keep it</h2>
<p>Analytics data: 14 months. Your email: until you unsubscribe or ask us to delete it.</p>

<h2 style="text-align:left;margin-top:30px">Your rights</h2>
<p>You can ask us for a copy of what we hold about you, ask us to correct it, or ask us to
delete it. Email <a href="mailto:privacy@turbohistory.com">privacy@turbohistory.com</a> and we
will sort it. If you are in the UK or EEA and think we have handled your data badly, you can
also complain to your national data protection authority.</p>

<h2 style="text-align:left;margin-top:30px">Cookies</h2>
<p>Only Google Analytics cookies, and only with consent where consent is required. No
advertising cookies, no tracking pixels, no third-party ad networks. You can change your
choice any time via "Your privacy choices" in the footer.</p>

<h2 style="text-align:left;margin-top:30px">Buying the books</h2>
<p>Our books are sold by Amazon, not by this website. We never see your payment details.
Amazon's own privacy policy covers anything you do on their site.</p>

<h2 style="text-align:left;margin-top:30px">Changes</h2>
<p>If we change this policy we will update the date at the top.</p>
</div></section>
"""


def privacy_page() -> str:
    from datetime import date as _d
    body = PRIVACY_BODY.replace("{updated}", _d.today().strftime("%d %B %Y"))
    return shell("Privacy Policy | Turbo History",
                 "How Turbo History handles analytics, email sign-ups and cookies. Short "
                 "version: analytics to see which books people like, email only for free "
                 "book alerts, nothing sold to anyone.",
                 BASE + "/privacy/", body)


def main() -> None:
    books = load_books()
    SITE.mkdir(parents=True, exist_ok=True)
    make_thumbs(books)

    (SITE / "index.html").write_text(index_page(books))
    (SITE / "privacy").mkdir(exist_ok=True)
    (SITE / "privacy" / "index.html").write_text(privacy_page())

    books_dir = SITE / "books"
    if books_dir.exists():
        shutil.rmtree(books_dir)
    for b in books:
        d = books_dir / b["slug"]
        d.mkdir(parents=True, exist_ok=True)
        cur = CURATION_DIR / f"{b['slug']}.json"
        if cur.exists():
            (d / "index.html").write_text(
                curated_page(json.loads(cur.read_text()), b, books))
        else:
            (d / "index.html").write_text(book_page(b, books))

    today = date.today().isoformat()
    urls = ([(BASE + "/", "1.0")]
            + [(f"{BASE}/books/{b['slug']}/", "0.8") for b in books]
            + [(BASE + "/privacy/", "0.2")])
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
