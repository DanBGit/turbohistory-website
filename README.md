# turbohistory-website

Static one-page brand site for the Turbo History book series (41+ one-hour history
ebooks on Amazon KDP). Live at https://turbohistory.com.

## What it is

- `site/index.html` — single self-contained page (embedded CSS, no JS): brand copy,
  12-cover grid linking to Amazon product pages, contact email, BookSeries JSON-LD.
- `site/covers/*.jpg` — 480px cover thumbnails generated from the KDP source covers
  (source of truth: the kindle-create pipeline's `~/Downloads/turbo-history-ready/<slug>/cover.jpg`).
- `Dockerfile` — nginx:alpine serving `site/`.

## Deploy

Coolify app on abm-stars-bizops (Hetzner, 89.167.109.218), Dockerfile build pack,
domain `https://turbohistory.com` (Traefik + Let's Encrypt). Push to `main` → redeploy
via Coolify.

## Purpose / roadmap

1. Goodreads Author Program verification (requires contact@turbohistory.com visible on
   an official site — see Contact section).
2. Brand link hub for Reddit/creator outreach.
3. Later: MailerLite email capture ("one free history book every weekend"), per-book
   SEO pages, Goodreads link.

No secrets in this repo — static content only. Brand copy canonical version lives in
the kindle project's memory (reddit-distribution-playbook.md).
