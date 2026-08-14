# Turbo History website redesign — mockup brief (shared)

Three fully-committed design directions, each delivering the same 3 templates.
NEVER blend directions. Each direction lives in its own folder and must feel like
one designer with strong opinions built it.

## Templates per direction

1. `index.html` — homepage (hero, cover grid, "fair warning" positioning block,
   email capture, contact, footer)
2. `book.html` — book page, use **Napoleon** as the specimen. Real content source:
   `../../site/books/napoleon/index.html` (crumbs, cover+meta head, blurb, related
   books, capture). Keep the SEO skeleton: one H1, H2 sections.
3. `collection.html` — collection hub page (DOES NOT EXIST YET — you are designing
   it). Use **Conquerors** as the specimen: intro + the books in the collection as
   a curated, ordered reading path. Books with collection `conquerors`: Genghis Khan,
   Napoleon, Alexander the Great, William the Conqueror, Julius Caesar, Hannibal
   (covers exist for all).

## Assets & content

- Covers: reference as `covers/<slug>.jpg` (each direction folder gets a symlink;
  already handled — just use that relative path). Slugs = folder names in
  `../../site/books/`.
- Logo SVG: copy the inline SVG from `../../site/index.html` nav.
- Copy: reuse the live copy (it converts; don't rewrite wholesale) but you MAY
  tighten headlines to fit the direction. Fix the aphoristic-cadence detector
  finding: at most ONE "X. No Y." construction per page.
- Brand voice: pulpy, confident, anti-academic. "One figure or one event per book,
  told in under an hour."

## Hero assets — AI-generated, placeholder now

The owner will generate hero imagery with Gemini/AI tools. For every hero (or
monumental visual) you design:
1. Build a CSS-only stand-in that occupies the exact space (gradient/texture scene,
   clearly composed, not a grey box) so the mockup reads as a finished page.
2. Add to your NOTES.md the exact generation prompt (subject, lighting, palette,
   camera, aspect ratio, "seamless loop" if video) + target file size/format.

## Hard rules (Impeccable craft floor + MOTION.md — all directions)

- Palette: near-monochrome ground + ONE accent. Brand gold `#c9a24b` is the default
  accent; a direction may justify a different single accent in NOTES.md.
- Contrast >= 4.5:1 for body text. 65–75ch measure on prose.
- Type at extremes: huge display or small labels, little in between. A real type
  scale (>=1.25 ratio between steps, max ~5 sizes).
- BANNED: border-left side-tabs, gradient text, zero-offset glow shadows as
  decoration (glow allowed only as THE authored hero moment on dark ground),
  emoji-as-icons, eyebrow/kicker labels above headings, cards-as-page-structure,
  1px border + huge blurred shadow combos, `transition: all`.
- Shadows: real offset + blur, or none.
- Grain/noise overlay is encouraged (kills the flat-AI look). Inline SVG noise, no
  external requests. Page must be fully self-contained (embedded CSS/JS, local
  covers only).
- Motion Tier 1 (mandatory, vanilla JS + CSS):
  - IntersectionObserver scroll reveals: rise 40–45px + fade, staggered. Hidden
    state applied VIA JS only (no-JS users see everything).
  - Hover intent on every interactive element (150–250ms).
  - ONE authored hero moment per page (headline stagger, atmosphere fade-up, etc.).
  - Ease `cubic-bezier(0.16,1,0.3,1)`. Animate only transform/opacity/filter.
  - `prefers-reduced-motion: reduce` disables all of it.
- Keep the email-capture form markup functional in shape (email input + button +
  fineprint) but you may restyle freely. Skip the consent/GA scripts in mockups.
- Mobile: test-think at 390px; grids collapse gracefully.

## Deliverables per direction folder

- `index.html`, `book.html`, `collection.html`
- `NOTES.md`: the direction thesis (3 sentences), type/color tokens, hero-asset
  generation prompts, and what would need to change in build.py terms (one line).

## The three directions

### 01-cinematic-archive
Nickel-style dark cinema. Near-black ink ground (#0d0b08 family), ONE monumental
photoreal hero scene (AI asset: dark cinematic still-life of history objects —
slot for a future video loop), massive display serif headline over it, gold as the
only saturated element, floating dark pill nav, deep atmosphere (slow CSS drift,
grain). Feels: prestige documentary title sequence.

### 02-pulp-poster
Retro pulp-poster collage. Condensed all-caps display type (huge), covers scattered
at slight angles like stickers/paperbacks on a table, starburst/stamp/sticker
elements ("55 BOOKS", "READ IN 1 HOUR"), heavy grain, ink ground with parchment
panels, gold accent. Scroll-in: stickers/covers drop or rotate into place (stagger).
Feels: dime-store paperback rack meets modern fintech poster. Energy matches the
subtitles ("The Drunk They Wrote Off Who Won the War").

### 03-museum-minimal
Near-white gallery. Parchment-paper ground (#f5efe2 family), giant black serif type
with a ghosted first line (15% opacity), ONE photoreal object cutting the viewport
diagonally (AI asset: cracked marble bust / laurel wreath / broken sword on white),
tiny uppercase mono labels, clinical whitespace, gold only on CTAs and thin rules.
Covers displayed like framed exhibits with generous mats. Feels: museum catalogue.
