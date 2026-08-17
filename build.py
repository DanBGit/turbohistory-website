#!/usr/bin/env python3
"""
Turbo History website generator.

catalogue.json (source of truth, written by the book pipeline)  ->  site/

Run after publishing new books / syncing ASINs:

    python3 turbohistory-website/build.py
    cd turbohistory-website && git commit -am "rebuild" && git push   # Coolify redeploys

Generates:
    site/index.html                      brand page + full catalogue grid
    site/books/<slug>/index.html         one page per book (SEO target: "<subject> book")
    site/collections/index.html          index of every collection hub
    site/collections/<slug>/index.html   one curated reading-path hub per collection
    site/sitemap.xml, site/robots.txt
    site/covers/<slug>.jpg               480px thumbnails (only for new/changed books)

Design: "Cinematic Archive" (mockups/01b-simple-font). Near-black ink ground, one
accent (gold), self-hosted Source Serif 4 + Archivo from /fonts/, film grain, an
animated inline hourglass used exactly once per page, IntersectionObserver reveals
whose hidden state is applied by JS only so a no-JS visitor sees a finished page.

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
READY = PROJECT / "turbo-history-ready"
BASE = "https://turbohistory.com"
EMAIL = "turbo@turbohistory.com"
AMAZON_AUTHOR = "https://www.amazon.com/author/turbohistory"
GA_ID = "G-D8J4PNSQ9J"

LOGO_NAV_SVG = """<svg viewBox="0 0 300 96" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <g transform="translate(150,16) scale(0.26)">
    <rect x="-32" y="-52" width="64" height="9" rx="4" fill="#c9a24b"/>
    <rect x="-32" y="43" width="64" height="9" rx="4" fill="#c9a24b"/>
    <path d="M-28,-45 L28,-45 L2,0 L28,45 L-28,45 L-2,0 Z" fill="none" stroke="#c9a24b" stroke-width="4.2" stroke-linejoin="round"/>
    <path d="M-22,-40 L22,-40 L2,-3 L-2,-3 Z" fill="#e9ddc6" opacity="0.9"/>
    <path d="M-17,45 L17,45 L0,26 Z" fill="#e9ddc6"/>
  </g>
  <text x="150" y="62" text-anchor="middle" font-family="'Arial Black','Helvetica Neue',Arial,sans-serif" font-weight="900" font-size="30" letter-spacing="0.5" fill="#c9a24b">TURBO</text>
  <text x="150" y="90" text-anchor="middle" font-family="'Arial Black','Helvetica Neue',Arial,sans-serif" font-weight="900" font-size="30" letter-spacing="4.5" fill="#e9ddc6">HISTORY</text>
</svg>"""

HEAD_EXTRA = f"""<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="preload" href="/fonts/SourceSerif4-latin.woff2?v=1" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/fonts/Archivo-latin.woff2?v=1" as="font" type="font/woff2" crossorigin>
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

# ============================================================================
# The sheet. Ported verbatim from mockups/01b-simple-font (audited: 0 detector
# findings, 19/20 health) and merged into one constant: the three hero scenes are
# scoped under .hero / .bhero / .chero, everything else is shared. Fonts are the
# self-hosted files under site/fonts, referenced absolutely because nginx serves
# site/ at the web root.
# ============================================================================
CSS = """
@font-face{
  font-family:'Source Serif 4';
  src:url('/fonts/SourceSerif4-latin.woff2?v=1') format('woff2-variations'),
      url('/fonts/SourceSerif4-latin.woff2?v=1') format('woff2');
  font-weight:200 900;font-style:normal;font-display:swap;
}
@font-face{
  font-family:'Source Serif 4';
  src:url('/fonts/SourceSerif4-Italic-latin.woff2?v=1') format('woff2-variations'),
      url('/fonts/SourceSerif4-Italic-latin.woff2?v=1') format('woff2');
  font-weight:200 900;font-style:italic;font-display:swap;
}
@font-face{
  font-family:'Archivo';
  src:url('/fonts/Archivo-latin.woff2?v=1') format('woff2-variations'),
      url('/fonts/Archivo-latin.woff2?v=1') format('woff2');
  font-weight:100 900;font-style:normal;font-display:swap;
}
:root{
  --ink:#0d0b08;
  --ink-2:#131009;
  --ink-3:#060504;
  --line:rgba(233,221,198,.14);
  --hairline:rgba(233,221,198,.09);
  --parchment:#e9ddc6;
  --muted:#a39781;
  --gold:#c9a24b;
  --ease:cubic-bezier(.16,1,.3,1);
  --t-label:.75rem;
  --t-body:1.125rem;
  --t-lede:1.4375rem;
  --t-h2:clamp(1.9rem,3.6vw,2.6rem);
  --t-display:clamp(3.1rem,8.6vw,7.4rem);
  --sans:'Archivo',Futura,'Avenir Next','Trebuchet MS',Arial,sans-serif;
  --serif:'Source Serif 4',Georgia,'Times New Roman',serif;
}
/* the display step is set per template, exactly as the three mockups had it */
body.p-book{--t-display:clamp(2.5rem,5.6vw,4.6rem)}
body.p-collection{--t-display:clamp(2.7rem,7vw,6rem)}
body.p-plain{--t-display:clamp(2.5rem,5.6vw,4.6rem)}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
body{background:var(--ink);color:var(--parchment);font-family:var(--serif);font-size:var(--t-body);line-height:1.68}
img{max-width:100%;display:block}
a{color:var(--gold);text-decoration:none;transition:opacity .2s var(--ease)}
a:hover{opacity:.82}
::selection{background:var(--gold);color:var(--ink)}
.muted{color:var(--muted)}

/* film grain over everything */
.grain{position:fixed;inset:0;z-index:1000;pointer-events:none;opacity:.055;mix-blend-mode:overlay;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")}

/* floating pill nav */
.nav{position:fixed;top:18px;left:50%;transform:translateX(-50%);z-index:200;
  display:flex;align-items:center;gap:26px;padding:9px 26px 9px 16px;border-radius:999px;
  background:rgba(9,7,5,.74);border:1px solid var(--line);
  backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);white-space:nowrap}
.nav .logo{display:inline-flex;align-items:center}
.nav .logo svg{height:38px;width:auto;display:block}
.nav a{transition:color .2s var(--ease),opacity .2s var(--ease)}
.nav .links{display:flex;gap:22px}
.nav .links a{font-family:var(--sans);font-size:var(--t-label);letter-spacing:.18em;text-transform:uppercase;color:var(--parchment)}
.nav .links a:hover{color:var(--gold);opacity:1}

/* label style */
.label{font-family:var(--sans);font-size:var(--t-label);letter-spacing:.04em;color:var(--muted)}
.label b{color:var(--gold);font-weight:700}
.label a{color:var(--gold)}

/* ============ homepage hero ============ */
.hero{position:relative;min-height:100svh;display:flex;align-items:flex-end;overflow:hidden;background:var(--ink)}
.scene{position:absolute;inset:0;overflow:hidden}
.scene .base{position:absolute;inset:0}
.hero .scene .base{background:
  radial-gradient(130% 100% at 50% 118%, rgba(201,162,75,.34) 0%, rgba(201,162,75,.10) 34%, rgba(201,162,75,0) 58%),
  radial-gradient(52% 40% at 71% 80%, rgba(226,178,86,.26) 0%, rgba(226,178,86,0) 62%),
  radial-gradient(40% 34% at 23% 74%, rgba(158,110,44,.16) 0%, rgba(158,110,44,0) 66%),
  radial-gradient(150% 130% at 50% -10%, #1c150c 0%, #120e08 44%, #0d0b08 72%)}
.scene .drift,.scene .drift2{position:absolute;inset:-22%;will-change:transform}
.hero .scene .drift{background:
  radial-gradient(38% 30% at 30% 62%, rgba(233,221,198,.05) 0%, rgba(233,221,198,0) 70%),
  radial-gradient(30% 26% at 74% 48%, rgba(233,221,198,.04) 0%, rgba(233,221,198,0) 70%)}
.hero .scene .drift2{background:
  radial-gradient(46% 34% at 60% 70%, rgba(201,162,75,.09) 0%, rgba(201,162,75,0) 70%),
  radial-gradient(26% 22% at 22% 40%, rgba(201,162,75,.05) 0%, rgba(201,162,75,0) 72%)}
@media (prefers-reduced-motion:no-preference){
  .scene .drift{animation:drift 76s var(--ease) infinite alternate}
  .scene .drift2{animation:drift2 104s var(--ease) infinite alternate}
}
@keyframes drift{from{transform:translate3d(-2.5%,1.5%,0) scale(1.02) rotate(-1deg)}to{transform:translate3d(2.5%,-2%,0) scale(1.07) rotate(1.4deg)}}
@keyframes drift2{from{transform:translate3d(2%,-1%,0) scale(1.05)}to{transform:translate3d(-2.5%,2%,0) scale(1)}}
.scene .table{position:absolute;inset:auto 0 0 0;height:30%;background:linear-gradient(to top,#060504 0%,rgba(6,5,4,.88) 22%,rgba(6,5,4,0) 100%)}
.scene .streak{position:absolute;left:8%;right:8%;bottom:27%;height:1px;background:linear-gradient(to right,rgba(201,162,75,0) 0%,rgba(201,162,75,.5) 38%,rgba(233,221,198,.65) 50%,rgba(201,162,75,.5) 62%,rgba(201,162,75,0) 100%);filter:blur(.4px)}
.scene .vignette{position:absolute;inset:0;background:radial-gradient(120% 100% at 50% 42%, rgba(6,5,4,0) 46%, rgba(6,5,4,.62) 100%)}

.hero-inner{position:relative;z-index:2;width:100%;max-width:1160px;margin:0 auto;padding:150px 26px 96px}
.hero h1{font-size:var(--t-display);font-weight:400;line-height:1.02;letter-spacing:-.015em;max-width:15.7ch}
.hero h1 .line{display:block;overflow:hidden}
.hero h1 .line>span{display:block}
.hero h1 em{font-style:italic;color:var(--gold)}
.hero .deck{max-width:70ch;margin:34px 0 10px;font-size:var(--t-lede);line-height:1.5;color:var(--muted)}
.hero .deck b{color:var(--parchment);font-weight:400}
.hero .cta{margin-top:34px;display:flex;gap:14px;flex-wrap:wrap;align-items:center}
.hero .since{margin-top:40px}
.motion .hero h1 .line>span{transform:translateY(112%);opacity:0;animation:rise 1s var(--ease) forwards}
.motion .hero h1 .line:nth-child(2)>span{animation-delay:.14s}
.motion .hero h1 .line:nth-child(3)>span{animation-delay:.28s}
.motion .hero .deck,.motion .hero .cta,.motion .hero .since{opacity:0;transform:translateY(26px);animation:rise2 1.1s var(--ease) .55s forwards}
.motion .hero .cta{animation-delay:.7s}
.motion .hero .since{animation-delay:.85s}
.motion .scene{opacity:0;animation:sceneIn 2.2s ease-out forwards}
@keyframes rise{to{transform:translateY(0);opacity:1}}
@keyframes rise2{to{transform:translateY(0);opacity:1}}
@keyframes sceneIn{to{opacity:1}}

/* ============ book / curated hero ============ */
.bhero{position:relative;overflow:hidden;background:var(--ink)}
.bhero .scene .base{background:
  radial-gradient(90% 80% at 26% 90%, rgba(201,162,75,.20) 0%, rgba(201,162,75,0) 58%),
  radial-gradient(46% 40% at 78% 30%, rgba(158,110,44,.10) 0%, rgba(158,110,44,0) 64%),
  radial-gradient(150% 130% at 50% -10%, #1a130b 0%, #110d08 46%, #0d0b08 74%)}
.bhero .scene .drift{background:
  radial-gradient(40% 32% at 34% 66%, rgba(233,221,198,.045) 0%, rgba(233,221,198,0) 70%),
  radial-gradient(30% 24% at 72% 44%, rgba(201,162,75,.07) 0%, rgba(201,162,75,0) 70%)}
.bhero .inner{position:relative;z-index:2;max-width:1160px;margin:0 auto;padding:132px 26px 84px}
.crumbs{font-family:var(--sans);font-size:var(--t-label);letter-spacing:.04em;color:var(--muted);margin-bottom:56px}
.crumbs a{color:var(--muted)}
.crumbs a:hover{color:var(--gold);opacity:1}
.crumbs .sep{margin:0 10px;color:var(--gold)}
.bookhead{display:flex;gap:64px;align-items:center;flex-wrap:wrap}
.bookhead .covwrap{position:relative;flex:0 0 auto;margin:0 auto}
/* the authored hero moment: a projector glow behind the cover on dark ground */
.bookhead .halo{position:absolute;inset:-46%;background:radial-gradient(50% 50% at 50% 50%, rgba(201,162,75,.34) 0%, rgba(201,162,75,.08) 48%, rgba(201,162,75,0) 70%);pointer-events:none}
@media (prefers-reduced-motion:no-preference){
  .bookhead .halo{animation:breathe 9s ease-in-out infinite alternate}
}
@keyframes breathe{from{opacity:.75;transform:scale(.97)}to{opacity:1;transform:scale(1.05)}}
.bookhead .covwrap img{position:relative;width:min(272px,64vw);aspect-ratio:5/8;object-fit:cover;border-radius:2px;box-shadow:0 30px 60px -18px rgba(0,0,0,.85)}
.bookhead .meta{flex:1;min-width:300px}
.bookhead h1{font-size:var(--t-display);font-weight:400;line-height:1.06;letter-spacing:-.015em;max-width:21ch}
.bookhead h1 .line{display:block;overflow:hidden}
.bookhead h1 .line>span{display:block}
.bookhead h1 em{font-style:italic;color:var(--gold)}
.bookhead .tag{margin-top:22px;font-size:var(--t-lede);line-height:1.5;color:var(--muted);max-width:56ch}
.bookhead .partof{margin-top:24px}
.bookhead .partof a{color:var(--gold)}
.bookhead .acts{margin-top:34px;display:flex;gap:14px;flex-wrap:wrap}
.motion .bookhead h1 .line>span{transform:translateY(112%);opacity:0;animation:rise 1s var(--ease) forwards}
.motion .bookhead h1 .line:nth-child(2)>span{animation-delay:.14s}
.motion .bookhead .tag,.motion .bookhead .partof,.motion .bookhead .acts{opacity:0;transform:translateY(24px);animation:rise2 1s var(--ease) .5s forwards}
.motion .bookhead .partof{animation-delay:.6s}
.motion .bookhead .acts{animation-delay:.72s}
.motion .bookhead .covwrap{opacity:0;transform:translateY(34px);animation:rise2 1.2s var(--ease) .2s forwards}

/* ============ collection hero ============ */
.chero{position:relative;overflow:hidden;background:var(--ink)}
.chero .scene .base{background:
  radial-gradient(120% 96% at 50% 116%, rgba(201,162,75,.30) 0%, rgba(201,162,75,.09) 36%, rgba(201,162,75,0) 60%),
  radial-gradient(44% 36% at 18% 62%, rgba(158,110,44,.14) 0%, rgba(158,110,44,0) 66%),
  radial-gradient(150% 130% at 50% -12%, #1b140b 0%, #120e08 46%, #0d0b08 74%)}
.chero .scene .drift{background:
  radial-gradient(38% 30% at 32% 60%, rgba(233,221,198,.05) 0%, rgba(233,221,198,0) 70%),
  radial-gradient(28% 24% at 76% 46%, rgba(233,221,198,.035) 0%, rgba(233,221,198,0) 70%)}
.chero .scene .drift2{background:
  radial-gradient(46% 34% at 62% 72%, rgba(201,162,75,.09) 0%, rgba(201,162,75,0) 70%),
  radial-gradient(24% 20% at 20% 38%, rgba(201,162,75,.05) 0%, rgba(201,162,75,0) 72%)}
.chero .inner{position:relative;z-index:2;max-width:1160px;margin:0 auto;padding:132px 26px 76px}
.chero h1{font-size:var(--t-display);font-weight:400;line-height:1.02;letter-spacing:-.015em;max-width:17ch}
.chero h1 .line{display:block;overflow:hidden}
.chero h1 .line>span{display:block}
.chero h1 em{font-style:italic;color:var(--gold)}
.chero .deck{max-width:72ch;margin:32px 0 0;font-size:var(--t-lede);line-height:1.5;color:var(--muted)}
.chero .deck b{color:var(--parchment);font-weight:400}
.chero .stats{margin-top:34px}
.chero .acts{margin-top:32px;display:flex;gap:14px;flex-wrap:wrap;align-items:center}
/* the authored hero moment: the spines deal in, left to right, like cards on a table */
.strip{position:relative;z-index:2;max-width:1160px;margin:0 auto;padding:0 26px 92px;display:flex;gap:14px;flex-wrap:wrap}
.strip a{display:block;flex:0 0 auto;transition:transform .22s var(--ease),filter .22s var(--ease)}
.strip img{width:clamp(78px,10vw,124px);aspect-ratio:5/8;object-fit:cover;border-radius:2px;filter:brightness(.86);
  box-shadow:0 22px 40px -16px rgba(0,0,0,.85);transition:filter .22s var(--ease)}
.strip a:hover{transform:translateY(-9px);opacity:1}
.strip a:hover img{filter:brightness(1.05)}
.motion .chero h1 .line>span{transform:translateY(112%);opacity:0;animation:rise 1s var(--ease) forwards}
.motion .chero h1 .line:nth-child(2)>span{animation-delay:.14s}
.motion .chero .deck,.motion .chero .stats,.motion .chero .acts{opacity:0;transform:translateY(26px);animation:rise2 1.05s var(--ease) .48s forwards}
.motion .chero .stats{animation-delay:.62s}
.motion .chero .acts{animation-delay:.76s}
.motion .strip a{opacity:0;transform:translateY(42px);animation:rise2 .9s var(--ease) forwards}
.motion .strip a:nth-child(1){animation-delay:.80s}
.motion .strip a:nth-child(2){animation-delay:.88s}
.motion .strip a:nth-child(3){animation-delay:.96s}
.motion .strip a:nth-child(4){animation-delay:1.04s}
.motion .strip a:nth-child(5){animation-delay:1.12s}
.motion .strip a:nth-child(6){animation-delay:1.20s}
.motion .strip a:nth-child(7){animation-delay:1.28s}
.motion .strip a:nth-child(n+8){animation-delay:1.36s}

/* buttons */
.btn{display:inline-block;background:var(--gold);color:var(--ink);padding:15px 30px;border-radius:2px;border:none;cursor:pointer;
  font-family:var(--sans);font-weight:700;font-size:var(--t-label);letter-spacing:.16em;text-transform:uppercase;
  transition:transform .2s var(--ease),filter .2s var(--ease),opacity .2s var(--ease)}
.btn:hover{transform:translateY(-2px);filter:brightness(1.09);opacity:1}
.btn.ghost{background:transparent;color:var(--gold);box-shadow:inset 0 0 0 1px var(--gold)}
.btn.ghost:hover{filter:brightness(1.15)}

/* ============ sections ============ */
.wrap{max-width:1160px;margin:0 auto;padding:0 26px}
section{padding:88px 0}
.sect-head{text-align:center;max-width:78ch;margin:0 auto 52px}
.sect-head h2{font-size:var(--t-h2);font-weight:400;line-height:1.15;letter-spacing:-.01em}
.sect-head .sub{color:var(--muted);margin-top:14px}
.sect-head .rule{width:52px;height:1px;background:var(--gold);margin:26px auto 0}
.prose,.blurb{max-width:84ch;margin:0 auto}
.prose p,.blurb p{margin:16px 0}
.prose .lede,.blurb .lede{font-size:var(--t-lede);line-height:1.55}
.prose .note,.blurb .note{color:var(--muted);font-style:italic}
.blurb ul{margin:16px 0 16px 24px}
.blurb li{margin:8px 0}
.blurb h2{font-size:var(--t-h2);font-weight:400;line-height:1.15;margin:44px 0 10px}
.blurb h3{font-size:var(--t-lede);font-weight:400;line-height:1.25;margin:32px 0 6px}
.pagehead{max-width:84ch;margin:0 auto 8px}
.pagehead h1{font-size:var(--t-display);font-weight:400;line-height:1.06;letter-spacing:-.015em}

/* cover grid */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(158px,1fr));gap:30px 24px}
.grid a{display:block;color:var(--parchment)}
.grid a:hover{opacity:1}
.grid .cov{display:block;overflow:hidden;border-radius:2px;box-shadow:0 18px 34px -14px rgba(0,0,0,.7)}
.grid img{width:100%;aspect-ratio:5/8;object-fit:cover;transition:transform .25s var(--ease),filter .25s var(--ease);filter:brightness(.94)}
.grid a:hover img{transform:scale(1.035);filter:brightness(1.04)}
.grid span.t{display:block;margin-top:14px;text-align:center;font-family:var(--sans);font-size:var(--t-label);letter-spacing:.14em;text-transform:uppercase;color:var(--muted);transition:color .2s var(--ease)}
.grid a:hover span.t{color:var(--gold)}

/* collections billboard */
.bill{position:relative;overflow:hidden;padding:84px 0;background:var(--ink-2);border-top:1px solid var(--hairline);border-bottom:1px solid var(--hairline)}
.bill .glow{position:absolute;inset:0;background:radial-gradient(70% 90% at 85% 60%, rgba(201,162,75,.13) 0%, rgba(201,162,75,0) 62%)}
.bill .inner{position:relative;display:flex;align-items:center;gap:56px;flex-wrap:wrap}
.bill .copy{flex:1;min-width:300px}
.bill h2{font-size:var(--t-h2);font-weight:400;line-height:1.12;max-width:23ch}
.bill p{color:var(--muted);max-width:64ch;margin:18px 0 30px}
.bill .fan{display:flex;flex:0 1 auto;min-width:280px;justify-content:center}
.bill .fan img{width:150px;aspect-ratio:5/8;object-fit:cover;border-radius:2px;box-shadow:0 20px 38px -12px rgba(0,0,0,.75)}
.bill .fan .f1{transform:rotate(-7deg) translateY(10px)}
.bill .fan .f2{transform:rotate(-1deg) translateY(-8px);z-index:2}
.bill .fan .f3{transform:rotate(6deg) translateY(12px)}
.bill .fan a{display:block;transition:transform .25s var(--ease)}
.bill .fan a:hover{transform:translateY(-8px);opacity:1}

/* ============ the reading path ============ */
.path{position:relative;max-width:940px;margin:0 auto}
.path .spine{position:absolute;left:31px;top:14px;bottom:120px;width:1px;
  background:linear-gradient(to bottom,rgba(201,162,75,0) 0%,rgba(201,162,75,.55) 8%,rgba(201,162,75,.55) 88%,rgba(201,162,75,0) 100%);
  transform-origin:top center}
.motion .path .spine{transform:scaleY(0);transition:transform 1.8s var(--ease) .1s}
.motion .path.lit .spine{transform:scaleY(1)}
.step{position:relative;display:grid;grid-template-columns:64px 172px 1fr;gap:0 34px;align-items:start;padding:0 0 62px}
.step:last-of-type{padding-bottom:0}
.step .num{position:relative;font-size:var(--t-h2);font-weight:400;line-height:1;color:var(--gold);text-align:center;padding-top:4px}
.step .num::after{content:"";position:absolute;left:50%;top:-14px;width:9px;height:9px;margin-left:-4.5px;border-radius:50%;background:var(--gold);box-shadow:0 0 0 5px var(--ink)}
.step .cov{display:block;border-radius:2px;overflow:hidden;box-shadow:0 20px 38px -14px rgba(0,0,0,.78)}
.step .cov img{width:100%;aspect-ratio:5/8;object-fit:cover;filter:brightness(.92);transition:transform .25s var(--ease),filter .25s var(--ease)}
.step .cov:hover img{transform:scale(1.035);filter:brightness(1.05)}
.step .body{padding-top:2px}
.step h3{font-size:var(--t-lede);font-weight:400;line-height:1.25;margin-bottom:8px}
.step h3 a{color:var(--parchment)}
.step h3 a:hover{color:var(--gold);opacity:1}
.step .byline{color:var(--muted);font-family:var(--sans);font-size:var(--t-label);letter-spacing:.04em;margin-bottom:16px}
.step .byline b{color:var(--gold);font-weight:700}
.step .why{max-width:74ch}
.step .why b{color:var(--parchment);font-weight:400;font-style:italic}
.step .go{display:inline-block;margin-top:14px;font-family:var(--sans);font-size:var(--t-label);letter-spacing:.04em;
  transition:transform .2s var(--ease),opacity .2s var(--ease)}
.step .go:hover{transform:translateX(4px);opacity:1}
.step .go .arr{display:inline-block;margin-left:8px}
.step.here{background:rgba(201,162,75,.06);border-radius:2px;padding:34px 30px 40px;margin:0 -30px 62px}
.step.here .num::after{top:-48px}
.step.here h3 a{color:var(--gold)}
.pathend{position:relative;margin-top:8px;padding-left:98px;color:var(--muted)}
.pathend b{color:var(--gold);font-family:var(--sans);font-size:var(--t-label);letter-spacing:.22em;text-transform:uppercase;display:block;margin-bottom:10px;font-weight:700}
.pathend p{max-width:69ch}

/* collections index */
.cols{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:34px 30px}
.colcard{display:block;background:var(--ink-2);border:1px solid var(--hairline);border-radius:2px;padding:28px 28px 30px;
  transition:transform .25s var(--ease),border-color .25s var(--ease)}
.colcard:hover{transform:translateY(-4px);border-color:var(--line);opacity:1}
.colcard h3{font-size:var(--t-lede);font-weight:400;line-height:1.25;color:var(--gold)}
.colcard p{color:var(--muted);margin-top:10px}
.colcard .spines{display:flex;gap:8px;margin-top:22px}
.colcard .spines img{width:52px;aspect-ratio:5/8;object-fit:cover;border-radius:2px;filter:brightness(.9);box-shadow:0 14px 26px -12px rgba(0,0,0,.8)}
.colcard .count{display:block;margin-top:20px;font-family:var(--sans);font-size:var(--t-label);letter-spacing:.04em;color:var(--muted)}

/* ============ curated picks ============ */
.tablewrap{overflow-x:auto;max-width:980px;margin:0 auto}
table.picks{width:100%;min-width:640px;border-collapse:collapse}
table.picks th{text-align:left;padding:14px 16px;border-bottom:1px solid var(--gold);color:var(--gold);font-family:var(--sans);font-size:var(--t-label);letter-spacing:.18em;text-transform:uppercase;font-weight:700}
table.picks td{padding:18px 16px;border-bottom:1px solid var(--hairline);vertical-align:top}
table.picks .m{color:var(--muted)}
table.picks tr.ours td{background:rgba(201,162,75,.07)}
.ourstag{font-family:var(--sans);font-size:var(--t-label);letter-spacing:.16em;text-transform:uppercase;color:var(--ink);background:var(--gold);padding:3px 9px;border-radius:2px;margin-left:10px;vertical-align:middle;font-weight:700}
.pick{max-width:84ch;margin:0 auto;padding:44px 0;border-bottom:1px solid var(--hairline)}
.pick:last-child{border-bottom:none}
.pick .num{font-family:var(--serif);font-size:var(--t-h2);line-height:1;color:var(--gold);font-weight:400;margin-bottom:4px}
.pick h3{font-size:var(--t-lede);font-weight:400;margin:10px 0 6px;line-height:1.25}
.pick .byline{color:var(--muted);font-family:var(--sans);font-size:var(--t-label);letter-spacing:.04em;margin-bottom:14px}
.pick p{margin:14px 0}
.pick-ours{background:rgba(201,162,75,.06);padding:44px 36px;max-width:calc(84ch + 72px)}
.pick-ours h3{color:var(--gold)}
@media (max-width:640px){.pick-ours{padding:36px 22px}}

/* fair warning interlude */
.warning{background:var(--ink-3);border-top:1px solid var(--hairline);border-bottom:1px solid var(--hairline)}
.warning .inner{max-width:81ch;margin:0 auto;padding:88px 26px;text-align:center}
.warning p{font-size:var(--t-lede);line-height:1.55;font-style:italic}
.warning b{color:var(--gold);font-style:normal;font-family:var(--sans);font-size:var(--t-label);letter-spacing:.22em;text-transform:uppercase;display:block;margin-bottom:22px}

/* ============ email capture ============ */
.capture{position:relative;overflow:hidden;background:var(--ink-2);border-top:1px solid var(--hairline);border-bottom:1px solid var(--hairline)}
.capture .glow{position:absolute;inset:0;background:radial-gradient(60% 80% at 50% 110%, rgba(201,162,75,.15) 0%, rgba(201,162,75,0) 60%)}
.capture .inner{position:relative;max-width:640px;margin:0 auto;padding:92px 26px;text-align:center}
.capture h2{font-size:var(--t-h2);font-weight:400;line-height:1.15}
.capture .why{color:var(--muted);margin:18px auto 34px;max-width:59ch}
.signup{display:flex;gap:12px;justify-content:center;flex-wrap:wrap}
.signup input[type=email]{flex:1 1 260px;max-width:360px;padding:14px 16px;border-radius:2px;
  border:1px solid var(--line);background:rgba(6,5,4,.6);color:var(--parchment);font-family:var(--serif);font-size:var(--t-body)}
.signup input[type=email]::placeholder{color:var(--muted)}
.signup input[type=email]:focus{border-color:var(--gold)}
.hp{position:absolute!important;left:-9999px;width:1px;height:1px;opacity:0}
.opt,.consent{display:flex;gap:10px;justify-content:center;align-items:flex-start;margin-top:20px;color:var(--muted);cursor:pointer;text-align:left;max-width:57ch;margin-left:auto;margin-right:auto}
.opt input,.consent input{accent-color:var(--gold);width:18px;height:18px;flex-shrink:0;margin-top:4px}
.opt[hidden],.consent[hidden]{display:none}
.submsg{min-height:1em;margin-top:18px;color:var(--muted)}
.submsg.err{color:#e5a08e}
.submsg.ok{color:var(--gold);font-size:var(--t-lede)}
.fineprint{color:var(--muted);font-size:var(--t-label);letter-spacing:.02em;margin-top:22px;font-family:var(--sans)}
.fineprint a{color:var(--muted);text-decoration:underline}
.fineprint a:hover{color:var(--gold)}

/* contact + footer */
.contact{text-align:center}
.contact h2{font-size:var(--t-h2);font-weight:400}
.contact .mail{display:inline-block;margin-top:22px;font-size:var(--t-lede)}
.contact p.small{color:var(--muted);margin-top:18px}
footer{border-top:1px solid var(--hairline);padding:44px 0 56px;text-align:center;color:var(--muted);font-family:var(--sans);font-size:var(--t-label);letter-spacing:.04em}
footer .links{margin-bottom:12px}
footer .links a{color:var(--muted)}
footer .links a:hover{color:var(--gold)}
footer .links span{margin:0 10px;opacity:.5}

/* ============ cookie dialog ============ */
html.ck-lock,html.ck-lock body{overflow:hidden}
#ck[hidden],#ck-prefs[hidden]{display:none!important}
#ck{position:fixed;inset:0;z-index:1001;background:rgba(6,5,4,.86);backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px);display:flex;align-items:center;justify-content:center;padding:20px}
.ck-box{background:var(--ink-2);border:1px solid var(--line);border-radius:2px;max-width:520px;width:100%;padding:34px;box-shadow:0 24px 70px rgba(0,0,0,.7);text-align:center;max-height:90vh;overflow-y:auto}
.ck-box h2{font-size:var(--t-h2);font-weight:400;line-height:1.15;margin-bottom:16px}
.ck-box p{color:var(--muted);margin-bottom:24px}
.ck-acts{display:flex;gap:12px;justify-content:center;flex-wrap:wrap}
.ck-acts .btn{min-width:150px}
.ck-link{display:block;margin:20px auto 0;background:none;border:none;color:var(--muted);font-family:var(--serif);font-size:var(--t-body);text-decoration:underline;cursor:pointer;padding:6px 2px}
.ck-link:hover{color:var(--gold)}
#ck-prefs{margin-top:20px;border-top:1px solid var(--hairline);padding-top:18px;text-align:left}
.ck-row{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;padding:14px 0;border-bottom:1px solid var(--hairline)}
.ck-row input{width:20px;height:20px;accent-color:var(--gold);flex-shrink:0;margin-top:5px}
#ck-save{margin-top:16px;width:100%}
.ck-fine{font-family:var(--sans);font-size:var(--t-label);letter-spacing:.02em;color:var(--muted);margin:20px 0 0}
@media(max-width:620px){.ck-box{padding:26px 20px}.ck-acts .btn{flex:1;min-width:0}}

/* scroll reveals - hidden state applied via JS only */
.pre{opacity:0;transform:translateY(44px);transition:opacity .95s var(--ease),transform .95s var(--ease)}
.pre.in{opacity:1;transform:translateY(0)}

@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{animation:none!important;transition:none!important}
}
@media (max-width:820px){
  .step{grid-template-columns:52px 132px 1fr;gap:0 24px}
  .path .spine{left:25px}
  .pathend{padding-left:76px}
}
@media (max-width:640px){
  .nav{gap:14px;padding:8px 18px 8px 12px;top:12px}
  .nav .logo svg{height:30px}
  .nav .links{gap:14px}
  section{padding:62px 0}
  .grid{grid-template-columns:repeat(auto-fill,minmax(118px,1fr));gap:22px 16px}
  .bill .fan img{width:104px}
  .bill .fan .f1{transform:rotate(-7deg) translateY(6px)}
  .bill .fan .f3{transform:rotate(6deg) translateY(8px)}
  .hero-inner{padding:130px 22px 72px}
  .bhero .inner{padding:116px 22px 64px}
  .chero .inner{padding:112px 22px 44px}
  .crumbs{margin-bottom:34px}
  .bookhead{gap:40px}
  .strip{padding:0 22px 64px;gap:9px}
  .step{grid-template-columns:44px 1fr;gap:0 18px}
  .step .cov{grid-column:2;max-width:132px;margin-bottom:18px}
  .step .body{grid-column:2}
  .path .spine{left:21px}
  .step .num{font-size:var(--t-lede)}
  .step.here{padding:26px 20px 30px;margin:0 -20px 62px}
  .pathend{padding-left:62px}
  .cols{grid-template-columns:1fr;gap:22px}
}

/* ============ the sand timer: the brand's own object, one per viewport ============ */
.hg{display:block;overflow:hidden}
.hg .glass{fill:none;stroke:var(--parchment);stroke-opacity:.38;stroke-width:1.2;stroke-linejoin:round;vector-effect:non-scaling-stroke}
.hg .cap{fill:var(--gold)}
.hg .sand{fill:var(--gold)}
.hg .mote{fill:var(--gold)}
.hg-rot{transform-origin:120px 120px}
/* resting/base state = full top chamber, empty bottom, no stream */
.hg-topmask{transform:translateY(0)}
.hg-botmask{transform:translateY(88px)}
.hg-stream{opacity:0}
@keyframes hgDrain{0%{transform:translateY(0)}86%,100%{transform:translateY(86px)}}
@keyframes hgFill{0%{transform:translateY(88px)}86%,100%{transform:translateY(0)}}
@keyframes hgPour{0%{opacity:0}5%{opacity:1}80%{opacity:1}86%,100%{opacity:0}}
@keyframes hgFall{from{transform:translateY(0)}to{transform:translateY(9px)}}
/* the flip at the loop seam: 180deg-symmetric glass + swapped sand = invisible restart */
@keyframes hgFlip{0%{transform:rotate(0deg)}88%{transform:rotate(0deg);animation-timing-function:var(--ease)}100%{transform:rotate(180deg)}}
@media (prefers-reduced-motion:no-preference){
  .hg-run .hg-topmask{animation:hgDrain var(--hg-dur,20s) linear var(--hg-rep,infinite) both}
  .hg-run .hg-botmask{animation:hgFill var(--hg-dur,20s) linear var(--hg-rep,infinite) both}
  .hg-run .hg-stream{animation:hgPour var(--hg-dur,20s) linear var(--hg-rep,infinite) both}
  .hg-run .hg-fall{animation:hgFall .5s linear infinite}
  .hg-loop .hg-rot{animation:hgFlip var(--hg-dur,20s) linear infinite both}
}
@media (prefers-reduced-motion:reduce){
  /* static, sensible resting state: about half drained, sand column standing still */
  .hg .hg-topmask{transform:translateY(48px)}
  .hg .hg-botmask{transform:translateY(40px)}
  .hg .hg-stream{opacity:1}
}
.hg-inline{display:inline-block;height:2.64em;width:auto;vertical-align:-1em;margin:0 -.36em 0 -.61em;--hg-dur:18s}
/* the hero's monumental object: one slow, calm cycle */
.hg-hero{--hgw:clamp(264px,28vw,396px);position:absolute;width:var(--hgw);
  right:calc(22px - .25 * var(--hgw));bottom:calc(104px - .08333 * var(--hgw));
  z-index:2;pointer-events:none;--hg-dur:26s}
.motion .hg-hero{opacity:0;transform:translateY(28px);animation:rise2 1.5s var(--ease) .95s forwards}
@media (max-width:1000px){
  .hg-hero{position:static;--hgw:176px;margin:-15px 0 15px -22px;--hg-dur:22s}
  .motion .hg-hero{animation-delay:.1s}
}

/* --- audit fixes: browser surfaces, focus, hit areas --- */
body{caret-color:var(--gold)}
:focus-visible{outline:2px solid var(--gold);outline-offset:3px;border-radius:2px}
.signup input[type=email]:focus-visible{outline:2px solid var(--gold);outline-offset:2px}
h1,h2,h3{text-wrap:balance}
.deck,.lede{text-wrap:pretty}
.nav .links a{padding:12px 2px}
footer .links a{display:inline-block;padding:6px 2px}
@media (max-width:640px){
  .nav{left:12px;right:12px;transform:none;width:auto;
    justify-content:space-between;gap:10px;padding:6px 14px 6px 10px}
  .nav .logo svg{height:26px}
  .nav .links{gap:12px}
  .nav .links a{font-size:.6875rem;letter-spacing:.08em;padding:10px 1px}
}
@media (prefers-reduced-motion:reduce){:focus-visible{outline:2px solid var(--gold)}}
"""

# The hourglass. Authored geometry in a 240x240 viewBox: the group's rotation diagonal
# is ~209 user units, so a tighter box makes every intermediate angle of the flip paint
# outside the SVG (it bled off the left edge of the page at 375px). Do not "simplify"
# this box. Exactly one instance per page.
HG_INNER = """
  <defs>
    <clipPath id="hgT"><rect class="hg-topmask" x="78" y="34" width="84" height="90"/></clipPath>
    <clipPath id="hgB"><rect class="hg-botmask" x="78" y="118" width="84" height="88"/></clipPath>
    <clipPath id="hgN"><rect x="114" y="120" width="12" height="80"/></clipPath>
  </defs>
  <g class="hg-rot">
    <path class="sand" clip-path="url(#hgT)" d="M87,38 L153,38 C153,70 127,104 123,119 L117,119 C113,104 87,70 87,38 Z"/>
    <path class="sand" clip-path="url(#hgB)" d="M153,202 L87,202 C87,170 113,136 117,121 L123,121 C127,136 153,170 153,202 Z"/>
    <g class="hg-stream" clip-path="url(#hgN)"><g class="hg-fall">
      <circle class="mote" cx="120" cy="117" r="1.5"/><circle class="mote" cx="119.1" cy="126" r="1.2"/>
      <circle class="mote" cx="120.8" cy="135" r="1.5"/><circle class="mote" cx="119.4" cy="144" r="1.2"/>
      <circle class="mote" cx="120.5" cy="153" r="1.5"/><circle class="mote" cx="119.2" cy="162" r="1.3"/>
      <circle class="mote" cx="120.7" cy="171" r="1.5"/><circle class="mote" cx="119.6" cy="180" r="1.2"/>
      <circle class="mote" cx="120.3" cy="189" r="1.5"/><circle class="mote" cx="119.3" cy="198" r="1.3"/>
      <circle class="mote" cx="120.6" cy="207" r="1.5"/>
    </g></g>
    <path class="glass" d="M84,35 L156,35 C156,70 128,104 124,119 L124,121 C128,136 156,170 156,205 L84,205 C84,170 112,136 116,121 L116,119 C112,104 84,70 84,35 Z"/>
    <rect class="cap" x="74" y="26" width="92" height="9" rx="4"/>
    <rect class="cap" x="74" y="205" width="92" height="9" rx="4"/>
  </g>
</svg>"""

HG_HERO = ('<svg class="hg hg-hero hg-run hg-loop" viewBox="0 0 240 240" role="img" '
           'aria-label="An hourglass with sand running: every book reads in under an hour">'
           + HG_INNER)
# Book/curated pages: one cycle, started by an observer, then it rests drained.
HG_INLINE = ('<svg class="hg hg-inline" viewBox="0 0 240 240" aria-hidden="true" '
             'focusable="false">' + HG_INNER)
# Collection hubs: keeps turning, like the mockup.
HG_INLINE_LOOP = ('<svg class="hg hg-inline hg-run hg-loop" viewBox="0 0 240 240" '
                  'aria-hidden="true" focusable="false">' + HG_INNER)

# Motion system, identical in behaviour to the audited mockups: reveals get their
# hidden class from JS only (a JS failure leaves the page fully readable), the whole
# thing returns early under prefers-reduced-motion.
MOTION_JS = """<script>
(function(){
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  document.documentElement.classList.add('motion');
  document.querySelectorAll('[data-stagger]').forEach(function(g){
    Array.prototype.forEach.call(g.children,function(c,i){
      c.setAttribute('data-reveal','');
      c.style.transitionDelay = Math.min(i*60,540)+'ms';
    });
  });
  var els = document.querySelectorAll('[data-reveal]');
  els.forEach(function(el){ el.classList.add('pre'); });
  var io = new IntersectionObserver(function(entries){
    entries.forEach(function(e){
      if (e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target); }
    });
  },{rootMargin:'0px 0px -10% 0px',threshold:.08});
  els.forEach(function(el){ io.observe(el); });
  // sand timer: runs one cycle when it reaches the viewport, then rests drained
  var hg = document.querySelector('.hg-inline:not(.hg-loop)');
  if (hg){
    hg.style.setProperty('--hg-rep','1');
    var hio = new IntersectionObserver(function(entries){
      entries.forEach(function(e){
        if (e.isIntersecting){ e.target.classList.add('hg-run'); hio.unobserve(e.target); }
      });
    },{threshold:.6});
    hio.observe(hg);
  }
  // the spine draws itself once the reading path enters view
  var path = document.getElementById('thepath');
  if (path){
    var pio = new IntersectionObserver(function(entries){
      entries.forEach(function(e){
        if (e.isIntersecting){ e.target.classList.add('lit'); pio.unobserve(e.target); }
      });
    },{rootMargin:'0px 0px -12% 0px',threshold:.04});
    pio.observe(path);
  }
})();
</script>"""

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


def capture(book: dict | None = None, collection: dict | None = None) -> str:
    """Email capture. Honest hook: the books really are free most weekends."""
    if book:
        head = "This book is free sometimes. Want to know when?"
        why = (f"{esc(book['name'])} goes free on Amazon from time to time, along with the "
               f"rest of the series. Leave your email and we will tell you the moment it does.")
        extra = ('<label class="opt"><input type="checkbox" name="groups[]" value="all" checked> '
                 '<span>Tell me about every free Turbo History book, not just this one</span></label>')
        hidden = f'<input type="hidden" name="fields[book_interest]" value="{esc(book["slug"])}">'
    elif collection:
        head = collection["capture_head"]
        why = (f"Most weekends one Turbo History book goes completely free on Amazon, and "
               f"often it is one of these. Leave your email and we will tell you which one, "
               f"before it goes back to full price.")
        extra = ('<label class="opt"><input type="checkbox" name="groups[]" value="all" checked> '
                 '<span>Tell me about every free Turbo History book, not just the '
                 + esc(collection["title"]) + '</span></label>')
        hidden = ('<input type="hidden" name="fields[collection_interest]" value="'
                  + esc(collection["slug"]) + '">')
    else:
        head = "Turbo History books are free most weekends."
        why = ("Most weekends one book in the series goes completely free on Amazon. Leave "
               "your email and we will tell you which one, before it goes back to full price.")
        extra = ""
        hidden = ""

    # Real capture, posted to our own /api on our own box. No third-party form host,
    # so subscriber data never leaves infrastructure Daniel controls.
    #
    # The consent tick is shown only where consent must be explicit (EEA/UK/CH/BR).
    # Canada is not on that list because Canada is blocked outright - see CANADA_MSG.
    # Elsewhere the notice alone is enough and an extra click just costs signups. The
    # server enforces the same rule, so removing the box in devtools gains nothing, and
    # if the geo lookup fails we show the box rather than guess.
    consent_text = ("Yes, email me when Turbo History books are free. "
                    "I can unsubscribe any time.")
    # Kept word-for-word in step with CANADA_MSG in api/app.py.
    canada_msg = ("IN CANADA? Sorry, we are not risking Canada's anti-spam rules "
                  "(CASL), so you cannot sign up. The books are still on Amazon.ca.")
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
      <p class="fineprint">We only ever use it to tell you when a book is free, we never
      share it with anyone, and you can unsubscribe in one click. See our
      <a href="/privacy/">privacy policy</a>.</p>
    </form>
    <script>
    (function(){{
      var f=document.getElementById('sub'); if(!f) return;
      var msg=f.querySelector('.submsg'), box=f.querySelector('.consent');
      var TEXT={json.dumps(consent_text)}, CA_MSG={json.dumps(canada_msg)};
      var ASK=['AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','GR','HU','IE','IT',
      'LV','LT','LU','MT','NL','PL','PT','RO','SK','SI','ES','SE','IS','LI','NO','GB','CH','BR'];
      var country='';
      fetch('/cdn-cgi/trace').then(function(r){{return r.text();}}).then(function(t){{
        var m=/loc=([A-Z]{{2}})/.exec(t); country=m?m[1]:'';
        if(country==='CA'){{ f.innerHTML='<p class="submsg err">'+CA_MSG+'</p>'; return; }}
        var UNKNOWN=(!country||country==='XX'||country==='T1');
        if(UNKNOWN||ASK.indexOf(country)>-1) box.hidden=false;
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

    return f"""<div class="capture">
  <div class="glow" aria-hidden="true"></div>
  <div class="inner" data-reveal>
  <h2>{head}</h2>
  <p class="why">{why}</p>
  {form}
</div></div>"""


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def shell(page_title: str, description: str, canonical: str, body: str,
          schema: dict | None = None, og_image: str | None = None,
          noindex: bool = False, body_class: str = "p-plain") -> str:
    schema_tag = ""
    if schema:
        schema_tag = ('<script type="application/ld+json">'
                      + json.dumps(schema, ensure_ascii=False) + "</script>")
    og = og_image or f"{BASE}/covers/blackbeard.jpg"
    # follow, not nofollow: we still want link equity flowing to the book pages
    # from anything held back from the index.
    robots_tag = ('<meta name="robots" content="noindex,follow">\n' if noindex else "")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(page_title)}</title>
<meta name="description" content="{esc(description)}">
{robots_tag}<link rel="canonical" href="{canonical}">
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
<body class="{body_class}">
<div class="grain" aria-hidden="true"></div>
<nav class="nav" aria-label="Main">
  <a class="logo" href="/" aria-label="Turbo History">{LOGO_NAV_SVG}</a>
  <span class="links"><a href="/#books">The Books</a><a href="/collections/">Collections</a><a href="{AMAZON_AUTHOR}">Amazon</a></span>
</nav>
<main id="content">
{body}
</main>
<footer><div class="wrap">
  <div class="links"><a href="/">Home</a><span>&middot;</span><a href="{AMAZON_AUTHOR}">Amazon Author Page</a><span>&middot;</span><a href="/privacy/">Privacy</a><span>&middot;</span><a href="#" onclick="thPrivacy();return false;">Your privacy choices</a><span>&middot;</span><a href="mailto:{EMAIL}">{EMAIL}</a></div>
  <div>&copy; Turbo History. All books available on Amazon and Kindle Unlimited.</div>
</div></footer>
{CONSENT_JS}
{MOTION_JS}
</body>
</html>
"""


def load_books() -> list[dict]:
    books = json.loads(CATALOGUE.read_text())
    out = []
    for b in books:
        if not b.get("asin"):
            continue  # blocked/unpublished: never link to a dead product page
        if b.get("blocked"):
            # 17 Aug 2026: Amazon took john-f-kennedy and rosa-parks off the
            # storefront with no explanation. The ASIN still exists but the
            # product page is dead, so the book leaves the site entirely -
            # grid, collection hubs, related rails and sitemap - until the
            # block is resolved. Clear the flag in catalogue.json to restore.
            continue
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


def tile(b: dict, alt: str | None = None) -> str:
    """One cover tile in a .grid."""
    return (f'<a href="/books/{b["slug"]}/"><span class="cov">'
            f'<img src="/covers/{b["slug"]}.jpg" alt="{esc(alt or b["title"])} book cover" '
            f'loading="lazy"></span><span class="t">{esc(b["name"])}</span></a>')


def scene(kind: str) -> str:
    """The lit stand-in scene behind a hero. Same layers as the mockups."""
    if kind == "book":
        return ('<div class="scene" aria-hidden="true"><div class="base"></div>'
                '<div class="drift"></div><div class="vignette"></div></div>')
    return ('<div class="scene" aria-hidden="true"><div class="base"></div>'
            '<div class="drift"></div><div class="drift2"></div><div class="streak"></div>'
            '<div class="table"></div><div class="vignette"></div></div>')


NUMWORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
            "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
            "sixteen", "seventeen", "eighteen", "nineteen", "twenty"]


def numword(n: int) -> str:
    """Spelled-out number, so headline copy cannot drift from the real count."""
    return NUMWORDS[n] if 0 <= n < len(NUMWORDS) else str(n)


def h1_lines(lines: list[str]) -> str:
    return "".join(f'<span class="line"><span>{ln}</span></span>' for ln in lines)


def h1_split(text: str, width: int = 30) -> str:
    """Break a headline into the mockup's authored <span class="line"> rows.

    Display type is set at line-height 1.06, which only reads as deliberate when the
    breaks are chosen rather than left to the wrap. Break after a colon first, then
    balance the rest into rows of about `width` characters. The accent word gets the
    gold italic, exactly as the specimen page does.
    """
    text = esc(text).replace("&#x27;", "’")
    head, rows = "", []
    if ":" in text:
        head, text = text.split(":", 1)
        rows.append(head.strip() + ":")
        text = text.strip()
    words, line = text.split(), ""
    for w in words:
        if line and len(line) + 1 + len(w) > width:
            rows.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    if line:
        rows.append(line)
    rows = [r.replace("Actually", "<em>Actually</em>") for r in rows]
    return h1_lines(rows)


# Which books to show as "More from the series" on each page.
#
# This used to be books[:6], i.e. the SAME six books on all 41 pages. That gave those six
# 40 inbound links each and left 34 pages with none, so most of the site was reachable only
# from the homepage. Two problems for search: link equity piled up on six arbitrary pages,
# and there was no topical signal at all connecting, say, the Tudor books to each other.
#
# Now: score by genuine overlap (shared themes, era, region, kind), then break ties by
# whichever candidate has been used least so far. The tie-break is what spreads the links,
# and it makes the picker order-dependent by design.
RELATED: dict[str, list[dict]] = {}


def _overlap(a: dict, b: dict) -> int:
    score = 3 * len(set(a.get("themes") or []) & set(b.get("themes") or []))
    if a.get("era") and a.get("era") == b.get("era"):
        score += 2
    if a.get("region") and a.get("region") == b.get("region"):
        score += 2
    if a.get("kind") and a.get("kind") == b.get("kind"):
        score += 1
    return score


def build_related(books: list[dict], n: int = 6) -> dict[str, list[dict]]:
    from collections import Counter
    used: Counter = Counter()
    out: dict[str, list[dict]] = {}
    for b in books:
        cands = [x for x in books if x["slug"] != b["slug"]]
        # highest overlap first, then least-used, then stable by slug
        cands.sort(key=lambda x: (-_overlap(b, x), used[x["slug"]], x["slug"]))
        picked = cands[:n]
        for x in picked:
            used[x["slug"]] += 1
        out[b["slug"]] = picked
    return out


def related_grid(slug: str, books: list[dict], heading: str,
                 sub: str = "One figure or one event per book. Under an hour each.",
                 exclude: set[str] | None = None) -> str:
    others = RELATED.get(slug) or [x for x in books if x["slug"] != slug][:6]
    if exclude:
        others = [o for o in others if o["slug"] not in exclude]
    rel = "".join(tile(o, alt=o["name"]) for o in others)
    return f"""<section class="wrap">
  <div class="sect-head" data-reveal>
    <h2>{esc(heading)}</h2>
    <p class="sub">{esc(sub)}</p>
    <div class="rule"></div>
  </div>
  <div class="grid" data-stagger>{rel}</div>
</section>"""


FAIR_WARNING = """<div class="warning">
  <div class="inner" data-reveal>
    <b>Fair warning</b>
    <p>These are not academic books. You will not find footnotes to chase, family trees to
    memorise, or ten pages on the logistics of a treaty. Every book ends with a page of
    proper ones to go to next if you want that depth. If you want the story and the big
    picture in an hour, you are home.</p>
  </div>
</div>"""


def book_page(b: dict, books: list[dict]) -> str:
    name, slug = b["name"], b["slug"]
    is_writer = slug in SEO_WRITERS
    # SEO title targets the money phrase: "<subject> book" / "best books about <subject>"
    title = (f"{name}: A Short Biography You Can Finish in an Hour | Turbo History"
             if is_writer else
             f"{name} Book: The Short Version, Read in Under an Hour | Turbo History")
    desc = (f"Want a book about {name} without the 600 pages? {b['title']} tells the "
            f"story in under an hour. The rise, the fall, why it still matters. "
            f"Free on Kindle Unlimited.")
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
    hook = f'<p class="tag">{esc(b["hook"])}</p>' if b.get("hook") else ""
    body = f"""
<header class="bhero">
  {scene('book')}
  <div class="inner">
    <nav class="crumbs" aria-label="Breadcrumb"><a href="/">Turbo History</a><span class="sep" aria-hidden="true">&rsaquo;</span><span aria-current="page">{esc(name)}</span></nav>
    <div class="bookhead">
      <div class="covwrap">
        <span class="halo" aria-hidden="true"></span>
        <img src="/covers/{slug}.jpg" alt="{esc(b['title'])} book cover">
      </div>
      <div class="meta">
        <h1>{h1_split(name)}</h1>
        {hook}
        <p class="partof label">{collection_line(b)}Turbo History #{b.get('series_n','')} &nbsp;&middot;&nbsp; {HG_INLINE}<b>Reads in under an hour</b></p>
        <div class="acts">
          <a class="btn" href="{b['amazon']}">Read It on Amazon</a>
          <a class="btn ghost" href="{AMAZON_AUTHOR}">All {len(books)} Books</a>
        </div>
      </div>
    </div>
  </div>
</header>

<section class="wrap">
  <div class="sect-head" data-reveal>
    <h2>What is in the book</h2>
    <div class="rule"></div>
  </div>
  <div class="blurb" data-reveal>{blurb_html(b['blurb'])}</div>
</section>

{FAIR_WARNING}
{capture(b)}
{related_grid(slug, books, "More from the series")}
"""
    return shell(title, desc, f"{BASE}/books/{slug}/", body, schema,
                 og_image=f"{BASE}/covers/{slug}.jpg", body_class="p-book")


CURATION_DIR = PROJECT / "seo" / "curation"
COLLECTIONS_FILE = PROJECT / "seo" / "collections.json"


# Collection membership is stored per book in catalogue.json (written by
# seo/apply_collections.py).
def collection_titles() -> dict[str, dict]:
    if not COLLECTIONS_FILE.exists():
        return {}
    return {c["slug"]: c for c in json.loads(COLLECTIONS_FILE.read_text())["collections"]}


COLLECTION_META = collection_titles()
HUB_MIN = 4

# The hubs are built now (site/collections/<slug>/), so the "Part of" links have real
# destinations again. This was False only because the URLs 404'd.
HUBS_LIVE = True


def collection_line(b: dict) -> str:
    """The 'Part of <collection>' fragment that opens a book page's byline."""
    cols = [COLLECTION_META[c] for c in (b.get("collections") or []) if c in COLLECTION_META]
    if not cols:
        return ""
    bits = []
    for c in cols:
        t = esc(c["title"])
        bits.append(f'<a href="/collections/{c["slug"]}/">{t}</a>'
                    if HUBS_LIVE else f"<span>{t}</span>")
    return "Part of " + " &middot; ".join(bits) + " &nbsp;&middot;&nbsp; "


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
            "<span class='m'>" + byline(p) + "</span></td>"
            "<td>" + esc(p["length"]) + "<br><span class='m'>" + esc(p["time"]) +
            "</span></td><td>" + esc(p["best_for"]) + "</td></tr>")
    rows = "".join(rows)

    detail = []
    for i, p in enumerate(items, 1):
        mine = p.get("is_ours")
        cls = "pick pick-ours" if mine else "pick"
        anchor = " id='ours'" if mine else ""
        tag = " <span class='ourstag'>ours</span>" if mine else ""
        cta = ("<p style='margin-top:24px'><a class='btn' href='" + b["amazon"]
               + "'>Read It on Amazon</a></p>" if mine else "")
        body_ps = "".join("<p>" + esc(x) + "</p>" for x in p["why"].split("\n\n"))
        detail.append(
            "<div class='" + cls + "'" + anchor + " data-reveal><p class='num'>" +
            f"{i:02d}" + "</p><h3>" + esc(p["title"]) + tag + "</h3><p class='byline'>" +
            byline(p) + " &middot; " + esc(p["length"]) + " &middot; " + esc(p["time"]) +
            " &middot; " + esc(p["best_for"]) + "</p>" + body_ps + cta + "</div>")
    detail = "".join(detail)

    faqs = "".join(
        f"<div class='pick' data-reveal><h3>{esc(f['q'])}</h3><p>{esc(f['a'])}</p></div>"
        for f in c["faq"])

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
<header class="bhero">
  {scene('book')}
  <div class="inner">
    <nav class="crumbs" aria-label="Breadcrumb"><a href="/">Turbo History</a><span class="sep" aria-hidden="true">&rsaquo;</span><span aria-current="page">{esc(b['name'])}</span></nav>
    <div class="bookhead">
      <div class="covwrap">
        <span class="halo" aria-hidden="true"></span>
        <img src="/covers/{slug}.jpg" alt="{esc(b['title'])} book cover">
      </div>
      <div class="meta">
        <h1>{h1_split(c['h1'])}</h1>
        <p class="partof label">{collection_line(b)}{HG_INLINE}<b>Ours reads in under an hour</b></p>
        <div class="acts">
          <a class="btn" href="{b['amazon']}">Read Ours on Amazon</a>
          <a class="btn ghost" href="#shortlist">See the Full List</a>
        </div>
      </div>
    </div>
  </div>
</header>

<section class="wrap">
  <div class="prose" data-reveal>
    <p class="lede">{esc(c['intro_answer'])}</p>
    <p class="note">{esc(c['note'])}</p>
  </div>
</section>

<section class="wrap" id="shortlist">
  <div class="sect-head" data-reveal>
    <h2>The short version</h2>
    <p class="sub">Sorted by what you want, not by what is most famous.</p>
    <div class="rule"></div>
  </div>
  <div class="tablewrap" data-reveal><table class="picks">
  <thead><tr><th>Book</th><th>Length</th><th>Best for</th></tr></thead>
  <tbody>{rows}</tbody></table></div>
</section>

<section class="wrap">
  <div class="sect-head" data-reveal>
    <h2>The picks, in detail</h2>
    <div class="rule"></div>
  </div>
  {detail}
</section>

<section class="wrap">
  <div class="sect-head" data-reveal>
    <h2>Questions people actually ask</h2>
    <div class="rule"></div>
  </div>
  <div class="prose">{faqs}</div>
</section>

{capture(b)}
{related_grid(slug, books, "More from the series")}
"""
    return shell(c["meta_title"], c["meta_description"], f"{BASE}/books/{slug}/",
                 body, schema, og_image=f"{BASE}/covers/{slug}.jpg", body_class="p-book")


# ============================================================================
# Collection hubs
#
# One page per collection in seo/collections.json, at /collections/<slug>/, built as
# an argued reading path rather than a grid: a gold spine down the page, numbered
# stations, and a sentence per station saying why the book sits at that position.
# Books are ordered chronologically by death_year; the four event/expedition books
# have no death year, so they carry an explicit end-of-story year below.
# ============================================================================
PATH_YEAR = {"american-civil-war": 1865, "world-war-i": 1918,
             "world-war-ii": 1945, "lewis-and-clark": 1806}

COLLECTION_COPY: dict[str, dict] = {
    "the-tudors": {
        "h1": [
            "Four books.",
            "One family that <em>rebuilt England</em>.",
        ],
        "meta_title": "The Tudors: Four Books, One Reading Order | Turbo History",
        "meta_description": "One family, two generations, and the marriage that took England out of the Roman church. Four Turbo History books in a curated order, an hour each.",
        "deck": "Four books on the family that turned a marriage problem into a national religion. <b>Read in this order and the century reads as cause and effect</b>, not a list of wives.",
        "intro": [
            "Most Tudor history is told as a parade of six wives, which puts the causation the wrong way round. Start instead with the woman who refused to be a mistress. Anne Boleyn held out for the best part of seven years, and the price of that refusal was the English church leaving Rome, eight hundred religious houses closed, and a queen executed with a sword in May 1536. Her daughter then held the throne for forty-four years and died leaving nobody behind. Four books, two generations, one continuous consequence.",
            "So Anne comes first, before the king she married. Henry VIII then reads as the man who had to break a thousand-year institution to get one annulment, and kept going long after he had it. Mary I comes third because she is the attempt to put it all back, five years of burnings that changed nothing permanent. Elizabeth I comes last because she is the result: a girl declared illegitimate at two, queen at twenty-five, left holding a country her parents had rearranged around a single wedding.",
            "Four books, an hour each, so about four hours in total. This is the story and the shape of it, not a scholarly account of the Reformation Parliament. If you want the statutes and the theology, each book closes with a page of proper histories to go to next.",
        ],
        "pathend": "Elizabeth dies childless in 1603 and the crown goes north to a Scottish king, which is where the Stuarts begin. For the longer view, the British Monarchs path picks the story up on either side of these three.",
        "capture_head": "Tudor books go free most weekends.",
        "stations": {
            "anne-boleyn": {
                "dateline": "c.1501–1536 · The French court to the Tower",
                "why": "<b>She goes first because the whole century starts with her saying no.</b> Years of refusal, an annulment England could not get from Rome, and a new church built to settle one marriage. Then a daughter instead of a son, a treason trial that took a morning, and a swordsman brought over from France for the job. Read her first and everything after it is consequence.",
            },
            "henry-viii": {
                "dateline": "1491–1547 · England and the break with Rome",
                "why": "<b>Second, because you now meet the king already knowing what he was willing to spend.</b> Six wives: two beheaded, two annulled, one dead after childbirth, one who outlived him. Around that, more than eight hundred religious houses closed and their land taken into the crown, the largest transfer of property in England since the Conquest. He began as a scholar-prince who spoke four languages and ended being carried between rooms.",
            },
            "mary-i": {
                "dateline": "1516–1558 · Five years, and a church dragged back",
                "why": "<b>Third, because she is the correction that did not hold.</b> Henry\u2019s eldest daughter, declared illegitimate at seventeen and shut out of the succession, was pushed aside again in 1553 for Lady Jane Grey and took the throne anyway within a fortnight. Then a Spanish marriage the country hated, papal authority restored by statute, and close to three hundred Protestants burned in five years. Two pregnancies turned out not to be pregnancies. She died in November 1558 with no child, and the whole settlement reverted to her half-sister inside a day.",
            },
            "elizabeth-i": {
                "dateline": "1533–1603 · The last of her family",
                "why": "<b>Last, because she is both what the first two books cost and what they bought.</b> Declared illegitimate at two, imprisoned in the Tower by her own half-sister, queen at twenty-five and then on the throne for forty-four years. She signed her cousin’s death warrant in 1587, saw off the Armada the year after, never married, and closed the dynasty herself by leaving no heir at all.",
            },
        },
    },
    "british-monarchs": {
        "h1": [
            "A thousand years.",
            "<em>Seven crowns</em>, in order.",
        ],
        "meta_title": "British Monarchs: Seven Books in Order | Turbo History",
        "meta_description": "Nine centuries of the British crown in seven short books, from the Conquest to the empire, an hour each, ordered so every reign explains the next.",
        "deck": "Seven reigns across nine centuries, picked because each one changed what the crown actually was. <b>The throne is not the same object at the end of this path as it was at the start.</b>",
        "intro": [
            "A monarchy is easier to follow as a set of arguments than as a family tree. Who owns the land. Who owns the church. Who decides the succession. Who pays for the wars. William settles the first question in a single afternoon in 1066 and audits the answer twenty years later in the Domesday Book. Henry VIII settles the second by inventing a church. By the time Victoria dies in 1901 the crown has given up nearly every practical power it started with and become the most recognised institution on earth.",
            "So the seven run in date order, because here the chronology is the argument. Each monarch inherits a crown the last one altered and hands on something different again. One of them lost thirteen colonies, one lost her head to a cousin, and the one who ended with the largest empire in history could not choose her own prime minister.",
            "Seven books, an hour each, so about seven hours for nine hundred years. That is less time than one decent biography of any single reign here. There are no genealogical tables and no constitutional theory, and each book ends with a short list of the fuller works if a reign catches you.",
        ],
        "pathend": "Nine centuries, six crowns, and a throne that finishes the path with almost no authority and extraordinary reach. Victoria’s grandchildren were sitting on or beside the thrones of Britain, Germany and Russia by 1914, which is roughly where the Wars and Events books begin.",
        "capture_head": "British Monarchs books go free most weekends.",
        "stations": {
            "william-the-conqueror": {
                "dateline": "c.1028–1087 · Normandy, then all of England",
                "why": "<b>He opens the path because he is the point at which English kingship is imported wholesale.</b> An illegitimate duke wins one battle on one October afternoon in 1066 and replaces the language of government, the owners of the land and the top of the church. Twenty years later the entire country is written down in the Domesday Book, shire by shire, down to the ploughs and the pigs.",
            },
            "henry-viii": {
                "dateline": "1491–1547 · The crown takes the church",
                "why": "<b>Second, for the moment the crown stops answering to anybody abroad.</b> To end one marriage Henry made himself supreme head of the church in England, and the wealth of eight hundred dissolved houses came with it. What that left behind was a power no earlier king had held: the right to define what his own subjects were required to believe, enforced as treason.",
            },
            "mary-i": {
                "dateline": "1516–1558 · The crown tries to give the church back",
                "why": "<b>Third, because she is the one ruler on this path who tried to reverse the previous reign and found the crown could not do it twice.</b> The first woman to hold England in her own right rather than through a husband, queen in 1553 on a wave of genuine support, married to the king of Spain the year after, and restoring papal authority by act of parliament within two. Close to three hundred burnings followed. Five years later the country was less Catholic than when she began, and the land taken from the monasteries was never going back.",
            },
            "mary-queen-of-scots": {
                "dateline": "1542–1587 · Scotland, France and nineteen years a prisoner",
                "why": "<b>Fourth, because she is the reign that shows what a crown is worth without the means to hold it.</b> Queen of Scotland at six days old, queen of France and widowed by eighteen, then a second husband murdered, an abdication forced on her at twenty-four, and nineteen years as her cousin’s prisoner in England. The axe at Fotheringhay in 1587 also settled who would inherit England, though not in the way anyone intended.",
            },
            "elizabeth-i": {
                "dateline": "1533–1603 · Forty-four years, no heir",
                "why": "<b>Fifth, and she inherits every earlier problem at once: a church her father invented, a restoration her sister attempted, and a cousin with a rival claim to her throne.</b> The second she settled with a signature. The first she never fully settled at all, and she refused for forty-four years to answer the only question her council really cared about, which was who came next. The succession was resolved in her final hours, and it went to the son of the woman she had executed.",
            },
            "george-iii": {
                "dateline": "1738–1820 · Britain loses thirteen colonies",
                "why": "<b>Sixth, because this is the reign where the crown finds the edge of its reach.</b> Fifty-nine years on the throne, longer than any British king before him, and the part everyone remembers is the thirteen colonies gone by 1783. He spent his last decade blind, deaf and confined at Windsor while his son governed as regent. The monarchy that came out the other side was a quieter and much more constitutional thing.",
            },
            "queen-victoria": {
                "dateline": "1819–1901 · Sixty-three years and an empire",
                "why": "<b>Last, because the crown now has barely any power left and more reach than it has ever had.</b> Eighteen when she acceded, sixty-three years on the throne, Empress of India from 1876, and forty years in black after Albert died in 1861. William took a country with an army and a fleet of ships. Victoria presided over close to a quarter of the world’s people with a signature, a title and a photograph.",
            },
        },
    },
    "american-presidents": {
        "h1": [
            "Eight men.",
            "One office, <em>eight ways</em> to hold it.",
        ],
        "meta_title": "American Presidents: Eight Books in Order | Turbo History",
        "meta_description": "Eight presidents, Washington to Reagan, in eight short books of an hour each, ordered to show how a deliberately weak office became the most powerful.",
        "deck": "Eight men, one office, and a job that changes shape under every one of them. <b>Read in order and you watch the presidency grow from an experiment into the most powerful post on earth.</b>",
        "intro": [
            "The American presidency was designed to be weak. The men who drafted it had just fought a war against a king and had no intention of building a second one. What these eight books show, taken end to end, is how it stopped being weak. Washington sets the limit by walking away after two terms. Lincoln discovers the office can suspend habeas corpus and turn a war into emancipation for four million people. Franklin Roosevelt wins four elections and rebuilds the state around the job. By Kennedy, one man in one room has minutes rather than months to decide how a crisis ends. By Reagan the job is largely televised, and being good on camera is most of it.",
            "So the order is chronological, because the accumulation is the whole point. Each book stands on its own and assumes nothing, but together they make a single argument about power collecting in one office and never dispersing again. Two of these eight were shot dead in post and a third was shot and back at his desk within a fortnight. One was a general who had been written off as a drunk. One could not walk and kept the extent of it out of sight for twelve years.",
            "Eight books, an hour each, so a long working day in total for two hundred years of the office. These are lives rather than policy histories, and no attempt is made at a balanced verdict on any of them. Every book ends with a short list of the fuller biographies if one of the seven grabs you.",
        ],
        "pathend": "From a president who argued his way out of a royal-sounding title to one who had spent his first career in front of a camera and treated the office as the bigger role. For the wars underneath half of this path, the Wars and Events books cover the ground these men stood on.",
        "capture_head": "American Presidents books go free most weekends.",
        "stations": {
            "george-washington": {
                "dateline": "1732–1799 · Virginia to the first presidency",
                "why": "<b>First, because he had no model to copy and everything he did became one.</b> He won a war in which he lost most of the battles, then did the unexpected thing twice: handed his commission back to Congress in 1783, and walked out of the presidency in 1797 after two terms. No law required either. The second decision held for the next century and a half on nothing but his example.",
            },
            "thomas-jefferson": {
                "dateline": "1743–1826 · Monticello and the Louisiana Purchase",
                "why": "<b>Second, because the contradiction at the centre of the country is easiest to see inside one man.</b> He wrote that all men are created equal, and he enslaved more than six hundred people over the course of his life. He also doubled the size of the United States in 1803 for about fifteen million dollars, using a presidential power he had spent his whole career insisting did not exist.",
            },
            "abraham-lincoln": {
                "dateline": "1809–1865 · A country at war with itself",
                "why": "<b>Third, because the union the first two built comes apart here, and the office swells to hold it together.</b> A one-term congressman with roughly a year of formal schooling in total, elected in 1860 without carrying a single southern state, and by 1865 slavery is finished and the presidency has taken wartime powers it never entirely handed back. He was shot five days after the surrender at Appomattox.",
            },
            "ulysses-s.-grant": {
                "dateline": "1822–1885 · The Union army, then the White House",
                "why": "<b>Fourth, because Lincoln’s war needed somebody to actually win it and nobody expected it to be this man.</b> He had failed at farming, at business and, by reputation, at staying sober, and was selling firewood on a street corner before the war. Then Vicksburg, Appomattox, two terms in the White House and eight years spent trying to defend Black voters in the South. He finished his memoirs days before throat cancer killed him, to clear his family’s debts.",
            },
            "theodore-roosevelt": {
                "dateline": "1858–1919 · The office becomes a platform",
                "why": "<b>Fifth, because he is the first president to treat the job as a stage rather than an administration.</b> The youngest ever at forty-two, put there by an assassin’s bullet rather than a vote. He broke up trusts, took the ground for the Panama Canal, placed something like two hundred and thirty million acres under federal protection, and won the Nobel Peace Prize in 1906 for ending somebody else’s war between Russia and Japan.",
            },
            "franklin-d.-roosevelt": {
                "dateline": "1882–1945 · Depression, then a world war",
                "why": "<b>Sixth, because the office finally becomes the centre of American daily life and never leaves.</b> Elected four times, twelve years in post, and a state rebuilt around banking rules, public works and old-age pensions that are still there. He had been paralysed from the waist down since 1921 and was almost never photographed in the chair. He died in April 1945, weeks before the German surrender he had spent his last term arranging.",
            },
            "john-f-kennedy": {
                "dateline": "1917–1963 · A thousand days",
                "why": "<b>Seventh, because this is the presidency at maximum power with the smallest margin for error anyone had yet faced.</b> Just over a thousand days in office, a botched invasion of Cuba in his first months, then thirteen days in October 1962 spent overruling most of the senior advisers pressing him for air strikes. Thirteen months after that, an open car in Dallas, and the office he had made glamorous became something the country watched being taken apart.",
            },
            "ronald-reagan": {
                "dateline": "1911\u20132004 \u00b7 Hollywood, California, then the end of the Cold War",
                "why": "<b>Last, because the job has now become mostly performance, and he is the first president who had trained for that part.</b> A film actor and screen actors\u2019 union president who changed parties in middle age, governor of California, and sworn in at sixty-nine, the oldest to that point. Shot in the chest in March 1981 and back at work inside a fortnight. Then tax cuts, a national debt close to tripled, and an arms treaty signed in 1987 with the leader of a country he had called an evil empire four years earlier. He announced his own Alzheimer\u2019s in a handwritten letter in 1994 and was not seen in public again.",
            },
        },
    },
    "the-ancient-world": {
        "h1": [
            "Five lives.",
            "Where the <em>ancient world</em> turned.",
        ],
        "meta_title": "The Ancient World: Five Books in Order | Turbo History",
        "meta_description": "Macedon, Carthage, Rome and Egypt in five short books of about an hour each, ordered so four centuries read as one story rather than five famous names.",
        "deck": "Five lives that between them cover the rise of Rome, seen mostly from outside it. <b>Rome is the thread: the model it copied, the enemies who nearly broke it, and the man who broke the republic himself.</b>",
        "intro": [
            "Rome runs through all five of these books, and for most of them Rome is not the narrator. Alexander comes first because he is the standard the Romans measured themselves against and never stopped talking about. Hannibal second, because he is the closest Rome came to dying young. Spartacus third, because the whole system ran on slavery and once, for two years, the slaves were winning. Caesar fourth, because the republic ends in his hands. Cleopatra last, because the world that existed before Rome finishes with her in 30 BC and nothing like it returns.",
            "Read in date order, the five stop being separate famous names and acquire a shape. An idea of empire arrives from Macedon, is tested nearly to destruction by Carthage, cracks from the inside under the people it enslaved, is seized by one ambitious man, and finally swallows the last Hellenistic kingdom whole. Each book starts from nothing, so no prior reading is assumed anywhere in the path.",
            "Five books, an hour each, five hours for four centuries. These are short lives written for people who want the shape of the ancient world rather than the sources it survives in. The evidence is thin and heavily contested in places, and where it is, the books say so rather than picking the best story.",
        ],
        "pathend": "Egypt becomes a Roman province in 30 BC, and the republic that took it had already been dead for a generation. If you would rather follow the conquering instinct forward than stay in the ancient world, three of these five continue into the Conquerors path.",
        "capture_head": "Ancient World books go free most weekends.",
        "stations": {
            "alexander-the-great": {
                "dateline": "356–323 BC · Macedon to the Indus",
                "why": "<b>First, because he is the benchmark everyone else in this collection is measured against, usually by their own choice.</b> Eleven years of campaigning without losing a battle, an empire running from Greece to the Punjab, then dead at thirty-two in Babylon with no succession arranged and no heir old enough to matter. The Hellenistic world his generals carved up is the world the remaining four books take place inside.",
            },
            "hannibal": {
                "dateline": "247–183 BC · Carthage, the Alps, and years stranded in Italy",
                "why": "<b>Second, because Rome only gets interesting once you have seen how nearly it did not survive.</b> He brought an army and elephants over the Alps, destroyed a much larger Roman force at Cannae in 216 BC in a single afternoon, and then spent fifteen years camped in Italy while Rome simply declined to negotiate. Losing that slowly, and refusing to stop, is what taught Rome how to win everything afterwards.",
            },
            "spartacus": {
                "dateline": "died 71 BC · Capua to the Appian Way",
                "why": "<b>Third, because the ancient world makes no sense without the people it was built on, and this is the one occasion they nearly took it apart.</b> A gladiator breaks out of a training school at Capua with about seventy others and ends up commanding tens of thousands, beating consular armies for two years. Crassus finished it, and six thousand survivors were crucified along the road to Rome as a notice to everybody else.",
            },
            "julius-caesar": {
                "dateline": "100–44 BC · Gaul, then Rome itself",
                "why": "<b>Fourth, because the republic that survived Hannibal and Spartacus does not survive him.</b> Eight years conquering Gaul, an account of it he wrote himself and had circulated at home, then the Rubicon, a civil war against his own side, and the title of dictator for life. Around sixty senators decided that was the end of the discussion and stabbed him in a hall beside Pompey’s theatre in March 44 BC.",
            },
            "cleopatra": {
                "dateline": "69–30 BC · The last of the Ptolemies",
                "why": "<b>Last, because she is the closing of the world the other four lived in.</b> A Macedonian Greek ruling Egypt nearly three hundred years after one of Alexander’s generals took it, and reputedly the only one of her line who troubled to learn Egyptian. She backed Caesar, then Antony, lost at Actium in 31 BC, and with her death the following year Egypt became a province and the Hellenistic age was finished.",
            },
        },
    },
    "conquerors": {
        "h1": [
            "Six conquerors.",
            "One <em>reading order</em>.",
        ],
        "meta_title": "Conquerors: Six Books, One Reading Order | Turbo History",
        "meta_description": "The men who took more of the map than anyone thought possible, and what it cost. Six Turbo History books in a curated reading order, an hour each.",
        "deck": "The men who took more of the map than anyone thought possible, and what it cost. <b>Read in this order and the six books argue with each other</b> — each one inherits the last man’s playbook and finds out where it breaks.",
        "intro": [
            "Conquest is the one subject school gets backwards. You get the battles and the dates, and never the thing that actually explains them: every conqueror on this list was copying somebody. Alexander wrote the manual. Hannibal used it against Rome. Rome learned from Hannibal and handed the lesson to Caesar, who used it on Rome itself. William proved the whole thing could be done in a single afternoon if you picked the right afternoon. Genghis Khan built the same machine from outside the classical world entirely and made it bigger than all of them. Napoleon tried it one last time with modern armies and found the ceiling.",
            "So the six run in date order, which turns out to be the order the argument wants anyway. Read straight through and you watch one idea — move faster than anyone can react, then govern what you took — get picked up, sharpened, compressed into a single day, scaled up to a continent, and finally broken. Each book stands alone and starts from nothing, so you can begin anywhere. The order is where the collection pays.",
            "Six books, an hour each, roughly six hours end to end. That is one long train ride, or a week of commutes, for two thousand years of empire. Reading times are honest estimates from word count at roughly 250 words per minute, and none of these books pretends to be the last word on anything.",
        ],
        "pathend": "Six men, two thousand years, and the same discovery every time: taking the map is the quick half. Only a couple left an institution standing. For the view from the other end of an army, the Ancient World and France paths overlap with this one.",
        "capture_head": "Conquerors books go free most weekends.",
        "stations": {
            "alexander-the-great": {
                "dateline": "356–323 BC · Macedon to the Indus",
                "why": "<b>Start here because everyone after him is working from this template.</b> Eleven years, no defeat, an empire from Greece to the Punjab, dead at thirty-two with no plan for what came next. It gives you the whole pattern in its purest form: speed as a weapon, a father’s army inherited and improved, and the part nobody warns you about, which is that conquering is the easy half.",
            },
            "hannibal": {
                "dateline": "247–183 BC · Carthage against Rome",
                "why": "<b>Second, because Hannibal is Alexander’s method aimed at a state that refuses to lose.</b> Cannae is still taught in war colleges and it still did not win him the war. Read after Alexander and the contrast does the work for you: the same genius, the same speed, a very different enemy, and fifteen years stranded in Italy waiting for a surrender that never came.",
            },
            "julius-caesar": {
                "dateline": "100–44 BC · Gaul, then Rome itself",
                "why": "<b>Third, because this is the state that beat Hannibal turning the weapon on itself.</b> Caesar conquers Gaul, writes his own press coverage while doing it, then marches the army home. He is the first man on this list to prove that the real prize was never foreign territory, and the first to find out what a republic does to someone who works that out loud.",
            },
            "william-the-conqueror": {
                "dateline": "c.1028–1087 · Normandy to England",
                "why": "<b>Fourth, for scale. This is the smallest conquest on the list and the one you are still living inside.</b> One battle, one afternoon, and a country’s language, landholding, aristocracy and law rebuilt from the ground up, then audited in the Domesday Book. Put straight after Caesar it looks like a footnote. Nine centuries later it is the only conquest here that never came undone.",
            },
            "genghis-khan": {
                "dateline": "c.1162–1227 · The largest land empire ever assembled",
                "why": "<b>Fifth, because the Mediterranean is not the world, and this is the point where the collection has to admit it.</b> An outcast child eating roots on the steppe builds an empire more than twice the size of Alexander’s, and the seed of the largest land empire ever assembled, with a postal relay system, a written law and religious tolerance bolted on, and a death toll that still shows up in population estimates. Everything the first four did on a peninsula or an island, done across a continent.",
            },
            "napoleon": {
                "dateline": "1769–1821 · Corsica to Saint Helena",
                "why": "<b>Finish here, because Napoleon is the last man to try all of it at once and the only one whose paperwork outlived his empire.</b> He read Alexander and Caesar and said so. He moved faster than anyone in Europe could react, exactly as they had. Then the ceiling: Russia, a catastrophic retreat, an island in the South Atlantic. What survived was the boring half he built between campaigns — the Code, the prefects, the bank, the baccalaureate — still running under the law of several countries.",
            },
        },
    },
    "queens-and-empresses": {
        "h1": [
            "Eight women.",
            "Thrones held, and <em>heads lost</em>.",
        ],
        "meta_title": "Queens and Empresses: Eight Books in Order | Turbo History",
        "meta_description": "Eight women who ruled, or died getting close to a throne, in short books of about an hour each, read in an order that makes the pattern impossible to miss.",
        "deck": "Eight women and two very different outcomes: rule in your own name, or get close to a throne and pay for it. <b>Three of these eight were executed.</b>",
        "intro": [
            "There is a pattern across these eight lives that has very little to do with ability. The women who held power in their own name — Cleopatra, Mary I, Elizabeth, Catherine, Victoria — died with the throne still theirs. The women whose power came through a husband, or through a claim they had no army to defend — Anne Boleyn, Mary Stuart, Marie Antoinette — died on a scaffold, all three of them after trials that were decided before they opened. Read across nineteen centuries in date order, the division is impossible to look away from. Two of them are half-sisters who ended up on opposite sides of it only by outliving the danger.",
            "So the order runs by date, and the collection is deliberately not a list of winners. One of the eight was queen at six days old and had lost her kingdom by twenty-five. One was a minor German princess who made herself empress of Russia and kept it for thirty-four years. One reigned longer than any British monarch before her and had almost no power left to use. The comparison only works if you read them together.",
            "Eight books, an hour each, so around eight hours for nineteen centuries. These are lives, not an argument about gender and power, though the pattern is difficult to ignore once you have seen it. Every book ends with a page of fuller biographies for anyone who wants the scholarship behind the story.",
        ],
        "pathend": "Eight reigns, three scaffolds, and a queen at the end who outlived the idea that a woman on a throne needed explaining. Four of these eight also appear in the British Monarchs path, where they read as reigns rather than as lives.",
        "capture_head": "Queens and Empresses books go free most weekends.",
        "stations": {
            "cleopatra": {
                "dateline": "69–30 BC · Alexandria and the end of a dynasty",
                "why": "<b>She opens the collection because she is the last of the classical Mediterranean's great female rulers, and the one every queen after her gets measured against.</b> Co-ruler at eighteen, pushed out by her own brother, back inside two years, then the sole authority over the richest kingdom in the Mediterranean. Almost everything written about her afterwards was written by the men who beat her, which is a problem this entire path keeps running into.",
            },
            "anne-boleyn": {
                "dateline": "c.1501–1536 · Roughly a thousand days as queen",
                "why": "<b>Second, and she is the counter-example: all of the influence, none of the title that protects you.</b> She changed the religion of a country without ever holding authority in her own right, and when she failed to produce a son the same machinery that crowned her convicted her in one morning. Under three years as queen, and a daughter who would outlive every single one of her accusers.",
            },
            "mary-i": {
                "dateline": "1516\u20131558 \u00b7 England\u2019s first queen regnant",
                "why": "<b>Third, because she is the first woman to hold the English crown in her own name, and she had to fight for it before she could wear it.</b> Declared illegitimate as a teenager, then pushed aside in 1553 for Lady Jane Grey, she raised her own support in East Anglia and was queen within a fortnight. What followed was a Spanish marriage the country never accepted, two pregnancies that were not pregnancies, and five years of burnings that fixed her in English memory under a nickname. She died with the throne still hers, which on this path is not a small thing.",
            },
            "mary-queen-of-scots": {
                "dateline": "1542–1587 · Queen at six days old",
                "why": "<b>Fourth, because she had the strongest claim of anybody in this collection and it was worth nothing without soldiers behind it.</b> Crowned before she could sit up, raised at the French court, widowed at seventeen, then home to a Scotland that had changed religion while she was away. A murdered husband, a forced abdication, and nineteen years of English captivity ending in a warrant her cousin signed and then insisted she had not meant to send.",
            },
            "elizabeth-i": {
                "dateline": "1533–1603 · The queen who would not marry",
                "why": "<b>Fifth, because she watched her mother and her cousin die and drew the obvious conclusion about marriage.</b> Every European negotiation for her hand was a way of not answering. She kept the succession open for forty-four years, used the mere possibility of a husband as a diplomatic instrument, and built her entire public image out of the absence of a king. It cost her the dynasty and it kept her the crown.",
            },
            "marie-antoinette": {
                "dateline": "1755–1793 · Vienna to the Place de la Révolution",
                "why": "<b>Sixth, and she is the one punished hardest for the least actual power.</b> Married into France at fourteen, never a ruler in her own right, blamed for a national bankruptcy that predated her by decades, and wrecked by a jewellery fraud she had no part in. She never said the line about cake. She was tried over two days, on charges that included one so grotesque it embarrassed the court, and guillotined nine months after her husband.",
            },
            "catherine-the-great": {
                "dateline": "1729–1796 · A German princess takes Russia",
                "why": "<b>Seventh, because she is the answer to everything the previous two books show going wrong.</b> A minor princess from a small German house, married to an emperor she despised, who took the throne herself in a coup in 1762 and then held it alone for thirty-four years. She annexed Crimea, took a large share of Poland, corresponded with the philosophers of the Enlightenment, and conceded no power to anyone. Most of what people think they know about her death was invented by her enemies.",
            },
            "queen-victoria": {
                "dateline": "1819–1901 · Sixty-three years and a quarter of the world",
                "why": "<b>Last, because by her reign a queen no longer has to seize anything, and that turns out to carry its own cost.</b> Eighteen at her accession, nine children, forty years in black after Albert died, Empress of India from 1876. Her authority was constitutional rather than personal, and more territory was attached to her name than to all seven of them put together, and she spent much of the reign discovering the difference.",
            },
        },
    },
    "scientists-and-inventors": {
        "h1": [
            "Five minds.",
            "The <em>rules rewritten</em>, five times.",
        ],
        "meta_title": "Scientists and Inventors: Five Books | Turbo History",
        "meta_description": "Leonardo to Einstein in five short books, an hour each, ordered so you watch science stop being a private obsession and turn into an organised enterprise.",
        "deck": "Five people who changed what was known, and were mostly difficult company while they did it. <b>Read in order and you watch science stop being a private hobby and become an industry.</b>",
        "intro": [
            "Leonardo worked alone, sold his services to whoever was paying, and published nothing. Newton wrote the most important book of his century, and only because a friend nagged him into it and then paid the printer. Curie processed ore by hand in a converted shed and won Nobel Prizes in two different sciences. Tesla had the physics right and the commercial instincts of a man who died in a hotel room owing money. Einstein published four papers in one year that broke physics open, then spent decades arguing with what followed. Five centuries, five temperaments, one steadily more organised enterprise.",
            "The order is chronological, and it is also the order in which the work becomes impossible to do alone. By Curie the equipment costs real money and the material is quietly killing the person handling it. By Einstein an idea needs journals, conferences and an eclipse expedition on the other side of the world before anyone will accept it. Each book is a life rather than a physics lesson, but that shift is unmissable once the five are read together.",
            "Five books, an hour each, so roughly five hours. There are no equations in any of them, and none will teach you relativity or radioactivity properly. What they will do is tell you who these people actually were, and each one ends with the fuller books if you want the science itself done at length.",
        ],
        "pathend": "Five lives, five hundred years, and a straight line from notebooks nobody read to a surname that became a synonym for genius. Leonardo also sits in the Artists path, where the same unfinished work reads as an entirely different problem.",
        "capture_head": "Scientists and Inventors books go free most weekends.",
        "stations": {
            "leonardo-da-vinci": {
                "dateline": "1452–1519 · Florence, Milan and a French château",
                "why": "<b>He starts the path because he is what curiosity looks like before there is a method to attach it to.</b> Thousands of notebook pages on anatomy, water, flight and gearing, written in mirror script and left unpublished, so almost none of it reached anybody for centuries. Fewer than twenty finished paintings. He dissected around thirty human bodies and drew the workings of the heart valves better than anyone would manage for four hundred years.",
            },
            "isaac-newton": {
                "dateline": "1642–1727 · Cambridge, the Mint, and a great many feuds",
                "why": "<b>Second, because he is the first man here whose work is published, checked and built on, which is the entire difference.</b> The Principia in 1687 gave the world gravity, the laws of motion and the mathematics for both. He also spent more of his life on alchemy and biblical chronology than on physics, ran the Royal Mint and had counterfeiters hanged, and pursued Hooke and Leibniz with a spite that outlasted both men.",
            },
            "marie-curie": {
                "dateline": "1867–1934 · A Paris shed and two Nobel Prizes",
                "why": "<b>Third, because this is where the work starts costing the person doing it.</b> Shut out of university in Poland, she studied in secret classes, then boiled tonnes of pitchblende by hand in an unheated shed to isolate radium. The Nobel Prize in Physics came in 1903 and one in Chemistry in 1911, and she remains the only person to win in two different sciences. She died of aplastic anaemia, and her notebooks are still too radioactive to handle unprotected.",
            },
            "nikola-tesla": {
                "dateline": "1856–1943 · Alternating current and an empty hotel room",
                "why": "<b>Fourth, because being right and being paid turn out to be unrelated, and he is the clearest proof of it.</b> The alternating-current system carrying electricity into your house is largely his, and he tore up the royalty agreement that would have made him one of the richest men alive. Around three hundred patents, a remote-controlled boat demonstrated in 1898 that nobody knew what to do with, and a death in a New York hotel in 1943 surrounded by debts and pigeons.",
            },
            "albert-einstein": {
                "dateline": "1879–1955 · Bern, Berlin, Princeton",
                "why": "<b>Last, because he closes the collection the way Leonardo opens it: one person thinking, except now the whole apparatus of modern science exists to check the answer.</b> Four papers in 1905, written around a day job in a patent office. General relativity in 1915, confirmed by an eclipse expedition in 1919, which is the exact moment a physicist becomes a household name. The Nobel arrived in 1921, and not for relativity.",
            },
        },
    },
    "writers": {
        "h1": [
            "Four writers.",
            "Lives stranger than the <em>books</em>.",
        ],
        "meta_title": "Writers: Four Books, One Reading Order | Turbo History",
        "meta_description": "Shakespeare, Austen, Poe and Mary Shelley in four short books, an hour each, read in an order that becomes a history of what writing was worth.",
        "deck": "Four writers whose lives are stranger, and in two cases far shorter, than anything they published. <b>Two of the four put their best-known book into the world with no name on the title page.</b>",
        "intro": [
            "The books came first for all four of these people, and the lives were whatever happened around them, usually badly. Shakespeare left an enormous body of work and almost no personal trace, which is why people still argue about who he was. Austen published four novels without her name on them and died at forty-one. Poe invented the detective story and could not make it pay. Mary Shelley wrote the first science fiction novel at eighteen, on a washed-out holiday by a lake, and buried nearly everyone she loved before she was thirty.",
            "Read in date order the collection quietly turns into a history of what writing was worth. Shakespeare held a share in his own theatre and retired comfortable. Austen wrote in a family sitting room on a tiny allowance and earned a few hundred pounds in her lifetime. Poe was paid by the line and died broke at forty. Shelley wrote to keep herself and a son. The work outlasted every one of those arrangements, which is the only consolation on offer here.",
            "Four books, an hour each, so about four hours in total. These are lives rather than literary criticism, and there is no close reading of the texts anywhere in them. If you want the writing itself, each book ends with a short list of where to start and which of the long biographies is worth the time.",
        ],
        "pathend": "Four writers, two and a half centuries, and not one of them with any idea what the work would eventually be worth. If you want more lives that ended badly and became famous for it, the Artists path is the same proposition with paint.",
        "capture_head": "Writers books go free most weekends.",
        "stations": {
            "william-shakespeare": {
                "dateline": "1564–1616 · Stratford, the Globe, and very few documents",
                "why": "<b>He opens the path because he is the largest body of work and the smallest quantity of biography in the collection.</b> Around thirty-eight plays and a hundred and fifty-four sonnets, against six surviving signatures and not one manuscript in his hand. He was a businessman as much as a writer, held a share in his company and its theatre, and left his wife the second-best bed. Roughly half the plays would have disappeared without a collection two colleagues printed seven years after he died.",
            },
            "jane-austen": {
                "dateline": "1775–1817 · Hampshire, and a very small writing table",
                "why": "<b>Second, because she is the first person here writing for a market rather than a patron, and having to do it without a name attached.</b> Four books published while she was alive, credited only to a Lady. By family account she wrote in a sitting room with a creaking door, which gave her warning enough to cover the pages. She made a few hundred pounds in total and died at forty-one, months before the last two novels appeared with her name on them at last.",
            },
            "edgar-allan-poe": {
                "dateline": "1809–1849 · Richmond, Baltimore, and the magazine trade",
                "why": "<b>Third, because he shows what happens when a writer depends entirely on periodicals for a living.</b> He invented the detective story in 1841 and built the modern horror tale beside it, and was paid around nine dollars for the most famous poem in America. His wife died of tuberculosis at twenty-four. He was found delirious on a Baltimore street in clothes that were not his and died four days later at forty, with no agreed cause and no reliable account of the missing week.",
            },
            "mary-shelley": {
                "dateline": "1797–1851 · Lake Geneva, then a long widowhood",
                "why": "<b>Last, because a teenager on a rained-off holiday invented a genre and then spent thirty years being described as somebody’s widow.</b> The ghost-story competition at the Villa Diodati in 1816 produced two books that lasted, and the one everybody remembers is hers. Published anonymously when she was twenty, widowed at twenty-four, three of her four children dead before she turned thirty, and a long later career of novels and editing that almost nobody reads now.",
            },
        },
    },
    "france": {
        "h1": [
            "Four lives.",
            "<em>France</em>, from Orléans to Waterloo.",
        ],
        "meta_title": "France: Four Books, One Reading Order | Turbo History",
        "meta_description": "Joan of Arc, Louis XIV, Marie Antoinette and Napoleon in four short books, an hour each, ordered so four centuries of France read as one long argument.",
        "deck": "Four lives running from a besieged city in 1429 to a rock in the South Atlantic. <b>One was burned, one was guillotined, and one died a British prisoner.</b>",
        "intro": [
            "France spends four hundred years asking the same question in different costumes: who is entitled to speak for the country. In 1429 the answer is a teenage farmer’s daughter who says God told her, and it works, right up to the point where the people she saved let her burn. Under Louis XIV the answer is one man in one palace, permanently and by design. In 1793 it is a crowd, and it takes the head off a queen. By 1804 it is a Corsican artillery officer putting a crown on himself in front of the Pope.",
            "So these four are read in date order because each one is a response to the failure of the last. Absolute monarchy is Louis XIV’s answer to a childhood spent fleeing noble revolt. The Revolution is the bill for what absolutism cost, presented to the family that inherited it. Napoleon is the Revolution deciding it wants one man after all. Four books, four answers, and a country that has never entirely stopped arguing about which of them was right.",
            "Four books, an hour each, so about four hours for four centuries. These are lives, not a history of France, and the gaps between them are enormous: no Capetians, no Dreyfus, no world wars. Each book ends with a short list of the fuller histories if you want the connective tissue rather than the four peaks.",
        ],
        "pathend": "From Orléans to Saint Helena, and a country that has worked through more than a dozen constitutions since 1791. Two of these four turn up elsewhere as well: Napoleon closes the Conquerors path, and Marie Antoinette sits among the Queens and Empresses.",
        "capture_head": "France books go free most weekends.",
        "stations": {
            "joan-of-arc": {
                "dateline": "c.1412–1431 · Domrémy, Orléans, Rouen",
                "why": "<b>She opens the path because France as an idea, rather than a collection of feudal holdings, more or less begins with her.</b> An illiterate farmer’s daughter talks her way to a disinherited prince, breaks the siege of Orléans in days, and has him crowned at Reims inside three months. Captured the following year, sold to the English, tried by French churchmen and burned at nineteen. Twenty-five years later the same church declared that trial a fraud.",
            },
            "louis-xiv": {
                "dateline": "1638–1715 · Seventy-two years and one palace",
                "why": "<b>Second, because he is the opposite solution entirely: not a voice from outside, but a state engineered so that no outside voice can be heard.</b> King at four, seventy-two years on the throne, the longest reign of any sovereign in European history. He moved the nobility into Versailles and gave them ceremonial duties so they could not conspire at home, governed for over fifty years without a chief minister, and left the country exhausted by war and buried in debt.",
            },
            "marie-antoinette": {
                "dateline": "1755–1793 · Versailles to the scaffold",
                "why": "<b>Third, because the bill for the previous book arrives here, and she is the one handed it.</b> An Austrian teenager married into a court she did not understand, who became the face of a system perfected a lifetime before she reached it. The debt was mostly war debt, a good deal of it run up funding the American revolution. She was tried over two days and guillotined in October 1793, nine months after the husband whose crown she had never wanted.",
            },
            "napoleon": {
                "dateline": "1769–1821 · Corsica to Saint Helena",
                "why": "<b>Last, because he is the Revolution deciding it wants an emperor, and the only figure here who left more behind on paper than on the map.</b> A Corsican who spoke French with an accent his whole life, first consul at thirty, emperor at thirty-five, master of most of Europe until Russia in 1812 ended it. The empire lasted about a decade. The Civil Code, the prefects, the Bank of France and the baccalaureate are all still running.",
            },
        },
    },
    "wars-and-events": {
        "h1": [
            "Not a person.",
            "A <em>moment</em>.",
        ],
        "meta_title": "Wars and Events: Three Books in Order | Turbo History",
        "meta_description": "Three Turbo History books on the wars that redrew the map, from 1861 to 1945, in the order that shows how each one produced the next. An hour each.",
        "deck": "Most of this series follows one life at a time. These three follow the moments too big for any single life to hold, and <b>read in order they behave like one long argument about the industrial age</b>.",
        "intro": [
            "Three books, and the shortest path in the series. The American Civil War is where warfare stops being a matter of lines of men and starts being a matter of railways, telegraphs, factories and casualty lists nobody had budgeted for. The First World War is that discovery applied to an entire continent by professionals who had read the wrong lessons. The Second is what happens when the settlement from the first is left unpaid and the machinery has had twenty years to improve. Read straight through and the century stops looking like three disasters and starts looking like one, compounding.",
            "The order is simply chronological, because in this case chronology is the argument. Each war is fought by people who remember the last one and draw the wrong conclusion from it. Every book stands alone and assumes you know nothing, so there is no penalty for starting at the end. But the first book explains why the second was possible, and the second explains why the third was almost inevitable.",
            "Three books, an hour each, about three hours in total. That is short for eighty-four years and a great many dead, and it is meant to be: these are orientation, not scholarship. If you want unit-level detail, campaign maps or a historiographical fight, this is not the shelf for you.",
        ],
        "pathend": "Three books is a short path, and honestly stated: this collection is small because events are harder to do well in an hour than lives are. More are being written. The people who fought these wars have their own collections.",
        "capture_head": "Wars and Events books go free most weekends.",
        "stations": {
            "american-civil-war": {
                "dateline": "1861–1865 · The United States against itself",
                "why": "<b>Start here because this is where war becomes industrial, and everything after it inherits that.</b> Four years, roughly 620,000 dead by the traditional count and probably more, and a country that had to invent conscription, income tax and national cemeteries as it went. It also settles the question the founding generation had deliberately left open, at the price of the bloodiest event in American history.",
            },
            "world-war-i": {
                "dateline": "1914–1918 · Europe and its empires",
                "why": "<b>Second, because Europe spent 1914 making mistakes the Americans had already paid for.</b> A single shooting in Sarajevo, six weeks of diplomacy, and then four years of men walking into machine guns because the tactics had not caught up with the tools. Four empires gone by the end: Russian, German, Austro-Hungarian, Ottoman. The map of the modern Middle East and Eastern Europe is drawn in the wreckage.",
            },
            "world-war-ii": {
                "dateline": "1939–1945 · Six continents",
                "why": "<b>Finish here, because this war is the unfinished business of the last one, fought with better machines.</b> Somewhere between seventy and eighty-five million dead, most of them civilians. The Holocaust, the bombing of cities as policy, and two atomic weapons used on people. It ends with the map, the alliances and the anxieties that the world still operates under, which is the honest reason to read all three in a row.",
            },
        },
    },
    "russia": {
        "h1": [
            "Tsars, an empress,",
            "and a <em>mad monk</em>.",
        ],
        "meta_title": "Russia: Four Books, One Reading Order | Turbo History",
        "meta_description": "Four Turbo History books on the Russian throne, from the first tsar to the last, read in the order that explains how it kept collapsing. An hour each.",
        "intro": [
            "Russia is a country that has never quite solved the problem of what happens when one man holds everything. Ivan invents the office of tsar and then demonstrates, at length, what an unchecked one can do to his own nobility and his own city. Catherine takes the same absolute power two centuries later, applies it with genuine intelligence, expands the empire enormously, and still cannot touch the thing underneath it, which is serfdom. Rasputin shows how a court that answers to nobody can be captured by one persuasive outsider. Nicholas inherits all of it and drops it.",
            "So the sequence is chronological, and it is also a slow demolition. Each book widens the crack in the same wall. You can read any of them cold, and the Rasputin book in particular works fine as a standalone curiosity, but the last two are far better read together: Rasputin is the symptom and Nicholas is the patient, and the diagnosis arrives in 1917.",
            "Four books, an hour each, roughly four hours for four hundred years. Some of this is grim without relief, particularly the fate of the last imperial family, and it is told plainly rather than dramatically. If you want the Soviet century, it is not here yet.",
        ],
        "deck": "Four hundred years of absolute power in one country, from the first man crowned tsar to the man who lost the throne. <b>The empire in these books never reforms, it only breaks.</b>",
        "pathend": "The path stops in 1918 with the end of the Romanovs, which is where most people expect Russian history to get started. What follows the last tsar belongs to a collection that does not exist yet.",
        "capture_head": "Russia books go free most weekends.",
        "stations": {
            "ivan-the-terrible": {
                "dateline": "1530–1584 · Moscow and the first tsardom",
                "why": "<b>Start here because Ivan invents the job every other person in this collection inherits.</b> The first Russian ruler crowned tsar, in 1547, he expands Russia east and south, then turns the state inward with the oprichnina, a personal terror apparatus that gutted the nobility and sacked Novgorod. He also killed his own heir in a rage in 1581, which is how the dynasty ran out.",
            },
            "catherine-the-great": {
                "dateline": "1729–1796 · A German princess on the Russian throne",
                "why": "<b>Second, for the strongest possible case that absolutism can be done well, and the point where that case fails.</b> Born in Prussia, married into the Romanovs, she deposed her own husband in 1762 and ruled for thirty-four years. She corresponded with the philosophes, founded schools and hospitals, and enlarged the empire hugely. She also left serfdom intact and harder, which is the crack the fourth book falls through.",
            },
            "grigori-rasputin": {
                "dateline": "1869–1916 · Siberia to the Winter Palace",
                "why": "<b>Third, because he is the clearest evidence that by the dynasty's last years nobody was actually running the place.</b> A Siberian peasant with no office and no education ends up advising the imperial family, because he could apparently ease the heir's haemophilia when doctors could not. The story of his killing in December 1916 has been embroidered for a century; the book separates what is documented from what is legend.",
            },
            "nicholas-ii": {
                "dateline": "1868–1918 · The end of three hundred years",
                "why": "<b>Finish here, because everything the first three books set up collapses on this one man's watch.</b> He inherited absolute power without the temperament for it, took personal command of the army in 1915 and personal blame with it, abdicated in March 1917, and was shot with his wife, four daughters and son at Yekaterinburg in July 1918. Three centuries of Romanov rule ended in a cellar.",
            },
        },
    },
    "outlaws-and-villains": {
        "h1": [
            "Three men.",
            "Three <em>legends that ate them</em>.",
        ],
        "meta_title": "Outlaws and Villains: Three Short Books | Turbo History",
        "meta_description": "Three Turbo History books about men who became stories before they were dead: Vlad the Impaler, Blackbeard and Mussolini. Under an hour each, and no myth left standing.",
        "deck": "A deliberately short path with a single question behind it: what happens to a real man once he is more useful as a monster? <b>All three were flesh and blood before they were a brand.</b>",
        "intro": [
            "Three books is a small collection, so here is the honest version: these are the subjects in the series where the legend has almost entirely replaced the person, and putting them side by side is the point. Vlad III of Wallachia was a real prince fighting a real war against the Ottomans, and four hundred years later a novelist borrowed his father's byname for a vampire. Edward Teach ran a pirate career of roughly two years and built the terrifying image himself, on purpose, because a reputation that frightening meant fewer ships had to be fought at all. Mussolini did the same trick with a country attached.",
            "Read Vlad first and Blackbeard second, and the difference does the work. One man had his myth applied to him by other people, mostly hostile pamphleteers and later a Victorian author. The other man manufactured his own and used it as a weapon. Mussolini comes last because he is the industrial version of the second case: the same manufacture run by a state, on a whole population, for twenty-one years. Between them you get a fairly complete account of how a reputation actually gets made, and how little any of the three would recognise the version we have now.",
            "Three books, an hour each, so about three hours. Vlad's story involves mass impalement and is described factually, without relish; if that is not what you want, skip to the pirate. None of the three is a debunking exercise for its own sake, but none of them leaves the myth standing where the record does not support it.",
        ],
        "pathend": "Three books, and no pretence that this is a full shelf. It is the start of one. More tyrants and more pirates are being written; the men who did their damage from a throne have their own collections already.",
        "capture_head": "Outlaws and Villains books go free most weekends.",
        "stations": {
            "vlad-the-impaler": {
                "dateline": "1431–1476 · Wallachia, between two empires",
                "why": "<b>Start here because Vlad shows a reputation being built by other people, mostly his enemies.</b> A Wallachian prince held hostage by the Ottomans as a boy, ruling a small territory squeezed between Hungary and the Sultan, who used mass impalement as terror and as policy. German pamphlets made him a monster in print within his own century. Bram Stoker took the name Dracula in 1897 and the man disappeared behind it.",
            },
            "blackbeard": {
                "dateline": "c.1680–1718 · The Caribbean and the Carolinas",
                "why": "<b>Second, for the opposite case: a man who designed his own legend and knew exactly what it was for.</b> Edward Teach was at large for around two years. He blockaded Charleston harbour in 1718 and took the town's hostages for a chest of medicine. The smoking beard and the terrifying appearance were deliberate stagecraft, and there is little evidence he ever killed anyone before the fight at Ocracoke that killed him in November 1718.",
            },
            "benito-mussolini": {
                "dateline": "1883\u20131945 \u00b7 Italy, and an image that governed for twenty-one years",
                "why": "<b>Finish here with the case where the invented man took over a country.</b> A socialist newspaper editor who changed sides, marched on Rome in 1922 and was handed the government without having to fight for it, then spent two decades as a manufactured picture: the jaw, the balcony, the staged photographs, the trains that did not in fact run on time. Behind the picture were an opposition deputy murdered in 1924, a colonial war in Ethiopia fought with poison gas, race laws in 1938 and an alliance that finished him. Partisans shot him in April 1945 and the body was strung up at a Milan petrol station, where the crowd went for the image rather than the man.",
            },
        },
    },
    "civil-rights": {
        "h1": [
            "Four lives.",
            "One <em>unfinished fight</em>.",
        ],
        "meta_title": "Civil Rights: Four Books, in Reading Order | Turbo History",
        "meta_description": "Four Turbo History books on the American fight for equality, from slavery to the bus boycott, in an order that makes it one continuous story. An hour each.",
        "deck": "From a man born into slavery to a woman who lived to see the century turn. <b>Read in this order, the four books stop being four biographies and become one argument that never finished.</b>",
        "intro": [
            "The usual way this history is taught puts a century of silence between abolition and the movement, as though nothing connected them. These four lives make that hard to believe. Douglass, born into slavery in Maryland, proves in print that the entire justification for the system is a lie. Tubman, born into slavery a few counties away, does the same thing with her feet and a pistol. Then King and Parks take the fight into a country where slavery is gone and the arrangement it was built to serve is not. Two Marylanders, an Alabamian and a Georgian, and the same argument in all four mouths.",
            "So the order follows when each life ends, which puts Rosa Parks last even though her arrest in December 1955 is what put Martin Luther King in front of a crowd. That is deliberate. Parks lived until 2005, decades past the movement's headline years, and reading her last means finishing with the long aftermath rather than the famous speech. Every book stands alone. Read in sequence, the century between book two and book three becomes the loudest thing on the page.",
            "Four books, an hour each, about four hours in all. These are introductions to lives, not a history of American slavery or of the movement, and slavery and racial violence are described directly rather than softened. If you already know this ground well, you will find it brisk.",
        ],
        "pathend": "Four books, and none of them ends with the problem solved. Lincoln and the Civil War sit alongside these in the American shelves, and are the obvious next step if you want the political machinery that the first two books were pushing against.",
        "capture_head": "Civil Rights books go free most weekends.",
        "stations": {
            "frederick-douglass": {
                "dateline": "c.1818–1895 · Maryland to Washington",
                "why": "<b>Start here because Douglass is the first of the four to make the case in public, and he makes it with his own life.</b> Born into slavery on the Eastern Shore, taught to read against the law, escaped north in 1838 and published his account in 1845. He then had to leave the country for two years because the book named names and made him recapturable. He spent the rest of a long life arguing, editing and refusing to let the argument close.",
            },
            "harriet-tubman": {
                "dateline": "c.1822–1913 · The Underground Railroad",
                "why": "<b>Second, because Tubman answers Douglass in the only other language available: she went back.</b> Having escaped in 1849, she returned to Maryland roughly thirteen times and brought out around seventy people, and never lost one. During the war she scouted for the Union and helped lead the Combahee River raid in 1863, which freed more than seven hundred. She waited decades for the pension the government owed her.",
            },
            "martin-luther-king-jr": {
                "dateline": "1929–1968 · Montgomery to Memphis",
                "why": "<b>Third, and the shock of the jump is the point: a century has passed and the argument has barely moved.</b> A twenty-six-year-old minister is handed the Montgomery bus boycott in 1955, and twelve years later he has a Nobel Prize, two federal Acts and a bullet on a motel balcony in Memphis. The book keeps the last year in view, when he turned to poverty and to Vietnam and lost a good deal of his support for it.",
            },
            "rosa-parks": {
                "dateline": "1913–2005 · Montgomery, and fifty years after",
                "why": "<b>Finish here, because Parks lived longest into the aftermath and knew best how the story got flattened.</b> She was not a tired seamstress who happened to sit down; she had been secretary of the Montgomery NAACP for twelve years and had trained for exactly this. Her arrest on 1 December 1955 started the boycott that started book three. She then lost her job, left Alabama, and spent another five decades at it in Detroit.",
            },
        },
    },
    "artists": {
        "h1": [
            "Four painters.",
            "One <em>expensive obsession</em>.",
        ],
        "meta_title": "Artists: Four Books, One Reading Order | Turbo History",
        "meta_description": "Four Turbo History books on Leonardo, Michelangelo, Van Gogh and Frida Kahlo, in an order that traces who paid for art and why. An hour each.",
        "deck": "Two Florentines with wealthy patrons, then two painters with almost nobody. <b>The order tracks a single change: who art is made for, and what it costs the person making it.</b>",
        "intro": [
            "Art history usually gets sold as a parade of masterpieces. These four books are about the arrangement behind the masterpieces, which is money. Leonardo and Michelangelo worked for popes, dukes and republics, on commission, to a brief, with the patron's politics baked into the contract. Van Gogh worked for no one, sold almost nothing, and was kept alive by his brother's wages. Kahlo painted mostly herself, in a body that had been wrecked at eighteen, and had to be dead a long time before the world caught up. Read in order, that shift is the through line.",
            "Chronology and argument agree here, so the order is simply the order they died in. Leonardo and Michelangelo are best read as a pair, since they were rivals in the same city and were briefly set to paint competing murals in the same hall. Van Gogh then lands harder for having read them: a decade of work, roughly 2,100 pieces, and no market at all. Every book starts from nothing, so you can enter anywhere.",
            "Four books, an hour each, about four hours end to end. These are lives rather than criticism, so you will get the workshops, the patrons and the injuries rather than close readings of individual canvases. Van Gogh's and Kahlo's books both deal with mental and physical suffering directly.",
        ],
        "pathend": "Four books, and between them about five hundred years of the same bargain being renegotiated. Leonardo also sits in the Scientists and Inventors collection, where the notebooks matter more than the paintings, and reads as a different man entirely.",
        "capture_head": "Artists books go free most weekends.",
        "stations": {
            "leonardo-da-vinci": {
                "dateline": "1452–1519 · Florence, Milan, France",
                "why": "<b>Start here because Leonardo sets the terms: a working craftsman on commission who could not stop thinking sideways.</b> An illegitimate notary's son apprenticed in a Florentine workshop, he finished perhaps fifteen to twenty paintings in a career of nearly fifty years, and filled thousands of notebook pages with anatomy, water and flying machines that nobody saw for centuries. He died in France, having carried the Mona Lisa with him and never handed it over.",
            },
            "michelangelo": {
                "dateline": "1475–1564 · Florence and Rome",
                "why": "<b>Second, because he is the same system with the opposite temperament, and the two men could not stand each other.</b> He took a block of marble other sculptors had abandoned and produced the David between 1501 and 1504. He spent four years on the Sistine ceiling insisting he was a sculptor being made to paint. He lived to eighty-eight, outlasted a string of popes, and ran the building of St Peter's without pay.",
            },
            "vincent-van-gogh": {
                "dateline": "1853–1890 · The Netherlands to Provence",
                "why": "<b>Third, and the floor falls out: this is what the same obsession looks like with no patron underneath it.</b> He came to painting in his late twenties and had about a decade, producing roughly 2,100 works including some 860 oils, while living on money from his brother Theo. He sold vanishingly little in his lifetime. He died at thirty-seven in July 1890, and the letters to Theo are the reason we know the interior of any of it.",
            },
            "frida-kahlo": {
                "dateline": "1907–1954 · Mexico City",
                "why": "<b>Finish here, because Kahlo turns the whole arrangement round and makes herself the commission.</b> A bus accident at eighteen broke her spine, pelvis and right foot, and the surgeries never stopped; she painted lying down, in a mirror, and fifty-five of her 143 paintings are self-portraits. Better known in her lifetime as a Mexican Communist and a painter's wife, she had one solo show at home, in 1953, a year before she died.",
            },
        },
    },
    "great-explorers": {
        "h1": [
            "Four departures.",
            "Three <em>returns</em>.",
        ],
        "meta_title": "Great Explorers: Four Books in Order | Turbo History",
        "meta_description": "Four Turbo History books on Marco Polo, Columbus, Lewis and Clark, and Amelia Earhart, in the order that shows the map closing. An hour each.",
        "deck": "The people who went first, and what the going cost, from a Venetian on the Silk Road to a pilot over the Pacific. <b>One of these four did not come back.</b>",
        "intro": [
            "Exploration is usually told as a story of courage, which it is, and almost never as a story of blank space running out, which it also is. Marco Polo goes east when Europe knows nothing whatever about China, and comes home to be disbelieved. Columbus goes west with a wrong number for the size of the earth and dies still insisting he had reached Asia. Lewis and Clark walk into the last unmapped interior of a continent that is not empty and never was. Earhart goes last, when the coastlines are all drawn and the only frontier left is the air.",
            "Chronological, and the shrinking is the argument. Each expedition has less unknown to work with than the one before it and takes correspondingly greater personal risk to find any. The books stand alone, but reading Polo before Columbus is worth doing, because Polo's east is the one Columbus went looking for. His own heavily annotated copy survives in Seville, though he only acquired it after the first crossing; what sent him west was the picture Polo had already put in Europe's head.",
            "Four books, an hour each, roughly four hours. Two of these expeditions were catastrophic for the people already living where they arrived, and the books say so rather than skirting it. Earhart's disappearance is treated with the evidence available, without picking a favourite theory.",
        ],
        "pathend": "Four books, ending mid-Pacific in 1937 with nothing found. The obvious continuation is the Conquerors collection, which is the same appetite for other people's territory with an army attached instead of a ship.",
        "capture_head": "Great Explorers books go free most weekends.",
        "stations": {
            "marco-polo": {
                "dateline": "1254–1324 · Venice to Xanadu and back",
                "why": "<b>Start here because Polo is the first European to describe China at length, and the one who put it in everybody else's head.</b> He left Venice as a teenager, spent around seventeen years in the service of Kublai Khan, and was away twenty-four in total. The book was dictated to a romance writer while both were prisoners in Genoa, which is precisely why it was doubted for centuries and still is in parts.",
            },
            "christopher-columbus": {
                "dateline": "1451–1506 · Four crossings of the Atlantic",
                "why": "<b>Second, because Columbus sails on Polo's book and a badly wrong estimate of the earth's circumference.</b> Every educated person already knew the world was round; the argument was distance, and his critics had the maths right. He made four voyages from 1492, governed Hispaniola so brutally that the Crown sent him home in chains in 1500, and went to his grave maintaining he had found Asia. The consequences for the Caribbean were annihilating.",
            },
            "lewis-and-clark": {
                "dateline": "1804–1806 · St Louis to the Pacific",
                "why": "<b>Third, because this is exploration as state paperwork, and it is far more effective for it.</b> Jefferson bought Louisiana in 1803 and sent the Corps of Discovery to walk it, some 8,000 miles out and back in two years and four months, with one death in the whole party. They mapped rivers, catalogued species, and depended on the Shoshone woman Sacagawea and on dozens of Native nations who could have stopped them and did not.",
            },
            "amelia-earhart": {
                "dateline": "1897–1937 · The last blank space is the sky",
                "why": "<b>Finish here, because by 1937 the coastlines are drawn and the only unmapped route left runs over the ocean.</b> First woman to fly the Atlantic solo, in 1932, in fifteen hours from Newfoundland to a field in Northern Ireland. Five years later she and Fred Noonan vanished heading for Howland Island, a target two miles long in the open Pacific, with about 22,000 miles already behind them and 7,000 still to fly. No wreck has ever been confirmed.",
            },
        },
    },
    "the-american-revolution": {
        "h1": [
            "One rebellion,",
            "told from <em>both sides</em>.",
        ],
        "meta_title": "The American Revolution: Four Books | Turbo History",
        "meta_description": "Four Turbo History books on Washington, Hamilton, George III and Jefferson: the revolution from both sides of the Atlantic, an hour each, in reading order.",
        "deck": "Three men who made the break and one who was on the receiving end of it. <b>The king is in this collection on purpose, and reading him third changes the other three.</b>",
        "intro": [
            "Thirteen colonies with no army, no navy, no treasury and no country took on the leading power in the world and won, and the standard account of how tends to leave out both the money and the losing side. So this path runs Washington for the war, Hamilton for the machinery that paid for it, George III for the view from London, and Jefferson for the words and the enormous contradiction underneath them. Four books, four vantage points, one event that none of the four saw whole.",
            "The order runs by when each man's story ends, which happens to be a good argument too. Washington first because without an army in the field nothing else matters. Hamilton second because he is the one who works out that independence is an accounting problem. George III third, once you have seen what he was up against, because a mad tyrant is a poor explanation for losing a war. Jefferson last, because his sentence about equality is the promise the whole thing is measured against, and he owned people while writing it.",
            "Four books, an hour each, roughly four hours. This is not a military history: you will get Yorktown in outline, not in order of battle. Slavery is not treated as a footnote to the founding, particularly in the fourth book, and George III's illness is described as the medical uncertainty it remains.",
        ],
        "pathend": "The path ends in 1826, with Jefferson dying on the fiftieth anniversary of the Declaration. Where it goes next is the American Presidents collection, which picks up the office these men invented and follows it to the twentieth century.",
        "capture_head": "American Revolution books go free most weekends.",
        "stations": {
            "george-washington": {
                "dateline": "1732–1799 · Virginia to Yorktown to Mount Vernon",
                "why": "<b>Start here because the rebellion survives eight years mainly by not losing, and that is Washington's particular skill.</b> He lost a great many battles, kept an unpaid army in existence through Valley Forge, and won at Yorktown in 1781 with a French fleet doing half the work. Then the decisive act: he handed his commission back in 1783 and went home, and later left the presidency after two terms when nobody was making him.",
            },
            "alexander-hamilton": {
                "dateline": "c.1755–1804 · Nevis to the Treasury",
                "why": "<b>Second, because independence was won on credit and Hamilton is the one who understood that.</b> Born illegitimate on Nevis and orphaned, he came to New York as a student, served as Washington's aide, and led a bayonet charge at Yorktown. As the first Treasury Secretary he assumed the states' war debts, founded a national bank and made the new country creditworthy. He died in 1804 from a wound taken in a duel with the sitting vice president.",
            },
            "george-iii": {
                "dateline": "1738–1820 · London, and the war seen from the losing end",
                "why": "<b>Third, because the revolution reads very differently once you have the other party in the room.</b> He reigned for fifty-nine years, longer than any king before him, and his American war was one crisis among many: France, Ireland, India, and a Parliament he did not simply command. The recurrent madness that produced the Regency in 1811 came mostly after the colonies were lost, and its cause is still argued over rather than settled.",
            },
            "thomas-jefferson": {
                "dateline": "1743–1826 · Monticello and the Declaration",
                "why": "<b>Finish here, because Jefferson wrote the promise the other three books are judged against and did not keep it.</b> He drafted the Declaration at thirty-three, doubled the country with the Louisiana Purchase in 1803, and founded a university. He also enslaved more than six hundred people across his life and freed almost none of them. He died on 4 July 1826, fifty years to the day after the document, hours before John Adams.",
            },
        },
    },
    "the-second-world-war": {
        "h1": [
            "The war,",
            "then the <em>four men inside it</em>.",
        ],
        "meta_title": "The Second World War: Five Books in Order | Turbo History",
        "meta_description": "Five Turbo History books on the Second World War: the whole war first, then Roosevelt, Mussolini, MacArthur and Churchill. An hour each, in a reading order that builds.",
        "deck": "One book for the war itself, then four for the men who had to make decisions inside it. <b>Take the overview first and the three lives stop being anecdotes.</b>",
        "intro": [
            "This collection is built differently from the others in the series, because one of its five books is an event and the other four are people. That is deliberate. Read the war first and you get the frame: the scale, the fronts, the chronology, the industrial arithmetic and the civilian dead. Then the three lives sit inside that frame rather than floating free. Roosevelt is the production and the alliance, Mussolini is the Axis seen from the inside, MacArthur is the Pacific, and Churchill is the year Britain spent alone with nothing much beyond a refusal to negotiate.",
            "After the overview the order runs by when each life ends, which is close enough to useful. Roosevelt second, because American factories decide the outcome long before American infantry do. Mussolini third, since he died sixteen days after Roosevelt and because the Axis is easier to understand from its weakest founder than from its strongest one. MacArthur fourth, because the Pacific war has almost nothing in common with the European one and needs its own guide. Churchill last, because reading him after the full sweep makes 1940 look less like destiny and more like the narrow thing it was. Every book stands alone.",
            "Five books, an hour each, about five hours for the largest war in history. The overview does not soften the Holocaust, the bombing of cities or the atomic weapons, and none of the four men is presented as a hero, or as a monster, without the record attached. For depth on any single campaign, this is the wrong length of book.",
        ],
        "pathend": "The path ends with two of the four dead before the war was, and two who outlived their moment by twenty years. The Wars and Events collection puts this war back in sequence with the two that produced it, which is the shortest way to see why it happened at all.",
        "capture_head": "Second World War books go free most weekends.",
        "stations": {
            "world-war-ii": {
                "dateline": "1939–1945 · Six continents and every ocean",
                "why": "<b>Start here because the four lives that follow are unreadable without the shape of the war around them.</b> Six years, somewhere between seventy and eighty-five million dead, the majority of them civilians, and roughly six million murdered in the Holocaust. This book does the whole thing at altitude: how it began, why the Eastern Front dwarfs everything else, and what the two atomic weapons in August 1945 settled and started.",
            },
            "franklin-d.-roosevelt": {
                "dateline": "1882–1945 · Washington, and the arsenal behind the war",
                "why": "<b>Second, because the war is decided in factories some time before it is decided in the field, and that is his doing.</b> Paralysed from the waist down since 1921 and rarely photographed in the chair, he won four presidential elections, pushed Lend-Lease through a neutral country in 1941, and held an alliance together with Stalin and Churchill in it. He died on 12 April 1945, less than a month before Germany surrendered.",
            },
            "benito-mussolini": {
                "dateline": "1883\u20131945 \u00b7 Rome, and the alliance that consumed him",
                "why": "<b>Third, because the Axis needs a face on it, and his is the one that shows how thin the thing actually was.</b> He built fascism as a system of government and Hitler copied it, then spent the war as the junior partner in his own idea: an invasion of Greece in 1940 that Germany had to come and finish, an army lost in North Africa, and his own Grand Council voting him out in July 1943. German commandos took him off a mountain and installed him over a puppet republic in the north. Partisans caught him near Lake Como in April 1945, two days before Hitler shot himself in Berlin.",
            },
            "douglas-macarthur": {
                "dateline": "1880–1964 · The Philippines, Japan, then Korea",
                "why": "<b>Fourth, because the Pacific is effectively a separate war and he is the way into it.</b> Ordered out of the Philippines in 1942 leaving his men to captivity, he came back at Leyte in October 1944 and took the Japanese surrender aboard the Missouri in September 1945. He then governed occupied Japan for six years and wrote much of its constitution, before being sacked in 1951 for arguing publicly with his own president.",
            },
            "winston-churchill": {
                "dateline": "1874–1965 · Britain, from the wilderness to Downing Street",
                "why": "<b>Finish here, because after the full sweep of the war his one indispensable year looks far more precarious than the legend allows.</b> Written off through the 1930s and carrying Gallipoli and a gold standard disaster behind him, he became prime minister in May 1940 as France fell. The book keeps in what the statue leaves out, including the Bengal famine, and the fact that the country voted him out weeks after victory in Europe.",
            },
        },
    },
}


def collection_members(c: dict, by_slug: dict[str, dict]) -> list[dict]:
    ms = [by_slug[s] for s in c["members"] if s in by_slug]
    ms.sort(key=lambda b: b.get("death_year")
            if b.get("death_year") is not None else PATH_YEAR.get(b["slug"], 9999))
    return ms


def collection_page(c: dict, books: list[dict], by_slug: dict[str, dict]) -> str:
    slug = c["slug"]
    copy = COLLECTION_COPY[slug]
    members = collection_members(c, by_slug)
    n = len(members)
    url = f"{BASE}/collections/{slug}/"

    strip = "".join(
        f'<a href="#step-{i}" aria-label="{esc(b["name"])}, step {i}">'
        f'<img src="/covers/{b["slug"]}.jpg" alt="{esc(b["name"])} book cover"></a>'
        for i, b in enumerate(members, 1))

    steps = []
    for i, b in enumerate(members, 1):
        st = copy["stations"][b["slug"]]
        hook = b["title"].split(":", 1)[1].strip() if ":" in b["title"] else ""
        heading = (f'<a href="/books/{b["slug"]}/">{esc(b["name"])}</a>'
                   + (f" &mdash; {esc(hook)}" if hook else ""))
        steps.append(f"""<article class="step" id="step-{i}" data-reveal>
      <p class="num">{i:02d}</p>
      <a class="cov" href="/books/{b['slug']}/" aria-label="{esc(b['name'])} book page"><img src="/covers/{b['slug']}.jpg" alt="{esc(b['title'])} book cover" loading="lazy"></a>
      <div class="body">
        <h3>{heading}</h3>
        <p class="byline">{st['dateline']} &middot; <b>Under an hour</b></p>
        <p class="why">{st['why']}</p>
        <a class="go" href="/books/{b['slug']}/">Read the book<span class="arr" aria-hidden="true">&rsaquo;</span></a>
      </div>
    </article>""")
    steps = "\n".join(steps)

    intro = "".join(
        f'<p class="{cls}">{p}</p>'
        for cls, p in zip(["lede", "", "note"], copy["intro"]))

    hours = "about " + ("an hour" if n == 1 else f"{n} hours") + " end to end"
    members_slugs = {b["slug"] for b in members}

    schema = {"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "name": c["title"], "url": url,
         "description": copy["meta_description"],
         "isPartOf": {"@type": "WebSite", "name": "Turbo History", "url": BASE + "/"},
         "mainEntity": {"@type": "ItemList", "numberOfItems": n,
                        "itemListOrder": "https://schema.org/ItemListOrderAscending",
                        "itemListElement": [
                            {"@type": "ListItem", "position": i,
                             "url": f"{BASE}/books/{b['slug']}/", "name": b["title"]}
                            for i, b in enumerate(members, 1)]}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Turbo History",
             "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Collections",
             "item": BASE + "/collections/"},
            {"@type": "ListItem", "position": 3, "name": c["title"], "item": url}]}]}

    body = f"""
<header class="chero">
  {scene('collection')}
  <div class="inner">
    <nav class="crumbs" aria-label="Breadcrumb"><a href="/">Turbo History</a><span class="sep" aria-hidden="true">&rsaquo;</span><a href="/collections/">Collections</a><span class="sep" aria-hidden="true">&rsaquo;</span><span aria-current="page">{esc(c['title'])}</span></nav>
    <h1>{h1_lines(copy['h1'])}</h1>
    <p class="deck">{copy['deck']}</p>
    <p class="label stats"><b>{n} book{'' if n == 1 else 's'}</b> &nbsp;&middot;&nbsp; {HG_INLINE_LOOP}{hours} &nbsp;&middot;&nbsp; &pound;2.99 / $2.99 each &nbsp;&middot;&nbsp; free with Kindle Unlimited</p>
    <div class="acts">
      <a class="btn" href="#path">Start the Path</a>
      <a class="btn ghost" href="{AMAZON_AUTHOR}">See Them on Amazon</a>
    </div>
  </div>
  <div class="strip">{strip}</div>
</header>

<section class="wrap">
  <div class="prose" data-reveal>{intro}</div>
</section>

<section class="wrap" id="path">
  <div class="sect-head" data-reveal>
    <h2>The reading path</h2>
    <p class="sub">{n} book{'' if n == 1 else 's'}, in the order that makes each one hit harder than it would alone.</p>
    <div class="rule"></div>
  </div>
  <div class="path" id="thepath">
    <div class="spine" aria-hidden="true"></div>
    {steps}
    <div class="pathend" data-reveal>
      <b>End of the path</b>
      <p>{copy['pathend']}</p>
    </div>
  </div>
</section>

{FAIR_WARNING}
{capture(collection=dict(slug=slug, title=c["title"], capture_head=copy["capture_head"]))}
{related_grid(members[0]["slug"], books, "If you liked " + c["title"],
              "Same series, same hour, next to the ones you have just read.",
              exclude=members_slugs)}
"""
    return shell(copy["meta_title"], copy["meta_description"], url, body, schema,
                 og_image=f"{BASE}/covers/{members[0]['slug']}.jpg",
                 body_class="p-collection")


def collections_index(cols: list[dict], by_slug: dict[str, dict]) -> str:
    cards = []
    for c in cols:
        members = collection_members(c, by_slug)
        spines = "".join(
            f'<img src="/covers/{b["slug"]}.jpg" alt="" loading="lazy">'
            for b in members[:4])
        n = len(members)
        cards.append(f"""<a class="colcard" href="/collections/{c['slug']}/">
      <h3>{esc(c['title'])}</h3>
      <p>{esc(c['blurb'])}</p>
      <span class="spines" aria-hidden="true">{spines}</span>
      <span class="count">{n} book{'' if n == 1 else 's'} &middot; about {n} hour{'' if n == 1 else 's'} end to end</span>
    </a>""")
    cards = "\n".join(cards)
    total = len(cols)
    desc = ("Every Turbo History collection: curated reading orders through the Tudors, "
            "the conquerors, the presidents, the scientists and more. One hour per book.")
    schema = {"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "name": "Turbo History Collections",
         "url": f"{BASE}/collections/", "description": desc,
         "isPartOf": {"@type": "WebSite", "name": "Turbo History", "url": BASE + "/"},
         "mainEntity": {"@type": "ItemList", "numberOfItems": total,
                        "itemListElement": [
                            {"@type": "ListItem", "position": i,
                             "url": f"{BASE}/collections/{c['slug']}/", "name": c["title"]}
                            for i, c in enumerate(cols, 1)]}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Turbo History", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Collections",
             "item": f"{BASE}/collections/"}]}]}
    body = f"""
<header class="bhero">
  {scene('book')}
  <div class="inner">
    <nav class="crumbs" aria-label="Breadcrumb"><a href="/">Turbo History</a><span class="sep" aria-hidden="true">&rsaquo;</span><span aria-current="page">Collections</span></nav>
    <div class="pagehead">
      <h1>{h1_lines([numword(total).capitalize() + ' ways in.'])}</h1>
      <p class="tag" style="color:var(--muted);font-size:var(--t-lede);margin-top:26px">Every book stands alone and starts from nothing. Read a collection in order, though, and the books start arguing with each other: one idea picked up, sharpened, and broken by the next person who tried it.</p>
    </div>
  </div>
</header>

<section class="wrap">
  <div class="sect-head" data-reveal>
    <h2>All {total} collections</h2>
    <p class="sub">Each one is a reading order, not a shelf.</p>
    <div class="rule"></div>
  </div>
  <div class="cols" data-stagger>{cards}</div>
</section>

{capture()}
"""
    return shell("Collections: Curated Reading Orders | Turbo History", desc,
                 f"{BASE}/collections/", body, schema, body_class="p-plain")


def index_page(books: list[dict]) -> str:
    by_slug = {b["slug"]: b for b in books}
    featured = [by_slug[s] for s in FEATURED if s in by_slug] or books[:12]
    fg = "".join(tile(b) for b in featured)
    allg = "".join(tile(b) for b in books)
    n = len(books)
    desc = (f"Love history, but hate how it was taught at school? Turbo History: one figure "
            f"or one event per book, told in under an hour. {n} books. No filler, no "
            f"600-page epics. Free on Kindle Unlimited.")
    schema = {
        "@context": "https://schema.org", "@type": "BookSeries", "name": "Turbo History",
        "url": BASE + "/", "numberOfItems": n,
        "description": ("Short history books for casual history lovers. One figure or one "
                        "event per book, told in under an hour: the story, the turning "
                        "points, why it still matters. Not academic."),
        "author": {"@type": "Organization", "name": "Turbo History",
                   "email": EMAIL, "url": BASE + "/"},
        "genre": ["History", "Biography"], "sameAs": [AMAZON_AUTHOR],
    }
    ncol = len(COLLECTION_META)
    fan = [s for s in ("alexander-the-great", "genghis-khan", "napoleon") if s in by_slug]
    fanhtml = "".join(
        f'<a class="f{i}" href="/collections/conquerors/"><img src="/covers/{s}.jpg" '
        f'alt="{esc(by_slug[s]["name"])} book cover" loading="lazy"></a>'
        for i, s in enumerate(fan, 1))
    body = f"""
<header class="hero">
  {scene('home')}
  <div class="hero-inner">
    {HG_HERO}
    <h1>{h1_lines(['Love history,', 'but hate how it was', '<em>taught at school?</em>'])}</h1>
    <p class="deck">Same. School taught history like a memory test: names, dates, family trees, exam. <b>Turbo History is one figure or one event per book, told in under an hour.</b> The rise, the fall, the why-it-still-matters. Straight to the point, every time.</p>
    <div class="cta">
      <a class="btn" href="{AMAZON_AUTHOR}">Browse the Series on Amazon</a>
      <a class="btn ghost" href="#books">See All {n} Books</a>
    </div>
    <p class="label since"><b>{n} books and counting</b> &nbsp;&middot;&nbsp; &pound;2.99 / $2.99 each &nbsp;&middot;&nbsp; free with Kindle Unlimited</p>
  </div>
</header>

<section class="wrap">
  <div class="sect-head" data-reveal>
    <h2>Queens and conquerors.<br>Pirates and rebels.</h2>
    <p class="sub">Minds that changed everything, and the wars that changed everything else.</p>
    <div class="rule"></div>
  </div>
  <div class="grid" data-stagger>{fg}</div>
</section>

<div class="bill">
  <div class="glow" aria-hidden="true"></div>
  <div class="wrap inner">
    <div class="copy" data-reveal>
      <h2>{ncol} collections. {ncol} reading orders.</h2>
      <p>Every book stands alone, but they are grouped into curated paths: the Tudors, the conquerors, the presidents, the scientists, the people who went first. Read one in order and each book makes the next one hit harder.</p>
      <a class="btn ghost" href="/collections/">Browse the Collections</a>
    </div>
    <div class="fan" data-reveal>{fanhtml}</div>
  </div>
</div>

{FAIR_WARNING}
{capture()}

<section class="wrap" id="books">
  <div class="sect-head" data-reveal>
    <h2>Every book in the series</h2>
    <p class="sub">{n} and counting. Start anywhere. Finish everything.</p>
    <div class="rule"></div>
  </div>
  <div class="grid" data-stagger>{allg}</div>
</section>

<section class="wrap contact" id="contact">
  <div data-reveal>
    <h2>Contact</h2>
    <p class="sub muted" style="margin-top:14px">Questions, requests for who to cover next, or anything else.</p>
    <a class="mail" href="mailto:{EMAIL}">{EMAIL}</a>
    <p class="small">Turbo History is written and published by Turbo History.<br>Every book is available on Amazon and Kindle Unlimited.</p>
  </div>
</section>
"""
    return shell(
        "Turbo History | One-Hour History Books for People Who Hate How History Was Taught",
        desc, BASE + "/", body, schema, body_class="p-home")


PRIVACY_BODY = """
<header class="bhero">
  {scene}
  <div class="inner">
    <nav class="crumbs" aria-label="Breadcrumb"><a href="/">Turbo History</a><span class="sep" aria-hidden="true">&rsaquo;</span><span aria-current="page">Privacy</span></nav>
    <div class="pagehead"><h1><span class="line"><span>Privacy Policy</span></span></h1></div>
  </div>
</header>
<section class="wrap"><div class="blurb">
<p class="lede note">Last updated: {updated}. Short version: we run Google Analytics to see which
books people are interested in, and if you give us your email we use it to tell you when
books are free. We do not sell anything to anyone, ever.</p>

<h2>Who we are</h2>
<p>This site is run by Turbo History, an independent publisher of short history books.
Contact us about anything on this page at <a href="mailto:privacy@turbohistory.com">privacy@turbohistory.com</a>.</p>

<h2>What we collect</h2>
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

<h2>Legal basis</h2>
<p>Analytics: your consent, where consent is required. Email alerts: your consent, given when
you subscribe. Server logs: our legitimate interest in keeping the site up and secure.</p>

<h2>Who else sees it</h2>
<p>Google, for analytics, and only if you consented. That is the only third party involved.
Your email address is stored on our own server rather than handed to a mailing list company,
so nobody else touches it. If that ever changes we will say so here first. We never sell data.</p>

<h2>How long we keep it</h2>
<p>Analytics data: 14 months. Your email: until you unsubscribe or ask us to delete it.</p>

<h2>Your rights</h2>
<p>You can ask us for a copy of what we hold about you, ask us to correct it, or ask us to
delete it. Email <a href="mailto:privacy@turbohistory.com">privacy@turbohistory.com</a> and we
will sort it. If you are in the UK or EEA and think we have handled your data badly, you can
also complain to your national data protection authority.</p>

<h2>Cookies</h2>
<p>Only Google Analytics cookies, and only with consent where consent is required. No
advertising cookies, no tracking pixels, no third-party ad networks. You can change your
choice any time via "Your privacy choices" in the footer.</p>

<h2>Buying the books</h2>
<p>Our books are sold by Amazon, not by this website. We never see your payment details.
Amazon's own privacy policy covers anything you do on their site.</p>

<h2>Changes</h2>
<p>If we change this policy we will update the date at the top.</p>
</div></section>
"""


def privacy_page() -> str:
    from datetime import date as _d
    body = (PRIVACY_BODY.replace("{updated}", _d.today().strftime("%d %B %Y"))
                        .replace("{scene}", scene("book")))
    return shell("Privacy Policy | Turbo History",
                 "How Turbo History handles analytics, email sign-ups and cookies. Short "
                 "version: analytics to see which books people like, email only for free "
                 "book alerts, nothing sold to anyone.",
                 BASE + "/privacy/", body, body_class="p-plain")


def main() -> None:
    books = load_books()
    by_slug = {b["slug"]: b for b in books}
    RELATED.update(build_related(books))
    SITE.mkdir(parents=True, exist_ok=True)
    make_thumbs(books)

    (SITE / "index.html").write_text(index_page(books), encoding="utf-8")
    (SITE / "privacy").mkdir(exist_ok=True)
    (SITE / "privacy" / "index.html").write_text(privacy_page(), encoding="utf-8")

    books_dir = SITE / "books"
    if books_dir.exists():
        shutil.rmtree(books_dir)
    curated = 0
    for b in books:
        d = books_dir / b["slug"]
        d.mkdir(parents=True, exist_ok=True)
        cur = CURATION_DIR / f"{b['slug']}.json"
        if cur.exists():
            curated += 1
            d.joinpath("index.html").write_text(
                curated_page(json.loads(cur.read_text()), b, books), encoding="utf-8")
        else:
            d.joinpath("index.html").write_text(book_page(b, books), encoding="utf-8")

    cols_dir = SITE / "collections"
    if cols_dir.exists():
        shutil.rmtree(cols_dir)
    cols_dir.mkdir(parents=True, exist_ok=True)
    cols = [c for c in json.loads(COLLECTIONS_FILE.read_text())["collections"]
            if c["slug"] in COLLECTION_COPY and collection_members(c, by_slug)]
    for c in cols:
        d = cols_dir / c["slug"]
        d.mkdir(parents=True, exist_ok=True)
        d.joinpath("index.html").write_text(
            collection_page(c, books, by_slug), encoding="utf-8")
    (cols_dir / "index.html").write_text(
        collections_index(cols, by_slug), encoding="utf-8")

    today = date.today().isoformat()
    urls = ([(BASE + "/", "1.0")]
            + [(f"{BASE}/books/{b['slug']}/", "0.8") for b in books]
            + [(BASE + "/collections/", "0.6")]
            # thin collections (under HUB_MIN books) are real pages with real copy, but
            # they get a lower priority until they fill out.
            + [(f"{BASE}/collections/{c['slug']}/",
                "0.6" if len(collection_members(c, by_slug)) >= HUB_MIN else "0.4")
               for c in cols]
            + [(BASE + "/privacy/", "0.2")])
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{u}</loc><lastmod>{today}</lastmod>"
                  f"<priority>{p}</priority></url>\n" for u, p in urls)
        + "</urlset>\n", encoding="utf-8")
    (SITE / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n", encoding="utf-8")

    print(f"built {len(books)} book pages ({curated} curated, {len(books)-curated} standard)"
          f" + index")
    print(f"  collections: {len(cols)} hubs + /collections/ index")
    print(f"  sitemap: {len(urls)} urls")
    missing = [b["slug"] for b in books if not (SITE / "covers" / f"{b['slug']}.jpg").exists()]
    if missing:
        print(f"  WARNING missing covers: {missing}")


if __name__ == "__main__":
    main()
