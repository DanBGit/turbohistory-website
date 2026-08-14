# 01 — Cinematic Archive

## Direction thesis

Turbo History is sold as *prestige documentary*, not as a bookshop: a near-black ink
ground, one monumental lit scene, and a display serif set at title-sequence scale, so
the first thing a visitor feels is the opening ten seconds of a film rather than a
product grid. Gold (`#c9a24b`) is the only saturated colour on the page and it is
rationed — it lights the accent word in a headline, the CTA, the hairline rules, and
nothing else — while everything structural is stated in parchment on ink with a
permanent film-grain overlay so the pages never read as flat AI output. Motion is
slow and atmospheric rather than snappy: gradients drift for minutes, one authored
title moment plays on load, and everything else rises 44px into place on scroll.

## Templates

| File | Template | Specimen |
|---|---|---|
| `index.html` | Homepage | — |
| `book.html` | Book page | Napoleon |
| `collection.html` | Collection hub | Conquerors (6 books, curated reading order) |

`collection.html` is built as an argued reading **path**, not a grid: a gold spine
draws itself down the page on scroll, six numbered stations hang off it, and each
station carries a cover, a dateline/region/reading-time byline, and a lead sentence
that says *why it sits at that position* (Alexander writes the manual → Hannibal aims
it at Rome → Rome hands it to Caesar → Genghis does it on a continent → William does
it in an afternoon → Napoleon finds the ceiling). Napoleon is the terminal station and
is the one entry rendered on a raised gold-tinted ground, linking through to
`book.html`.

## Tokens as built

### Colour

| Token | Value | Use |
|---|---|---|
| `--ink` | `#0d0b08` | page ground |
| `--ink-2` | `#131009` | billboard / capture bands |
| `--ink-3` | `#060504` | "fair warning" interlude, scene floor |
| `--parchment` | `#e9ddc6` | body + headline text (14.1:1 on `--ink`) |
| `--muted` | `#a39781` | decks, bylines, fineprint (7.4:1 on `--ink`) |
| `--gold` | `#c9a24b` | THE accent — links, CTA, rules, numerals (8.0:1 on `--ink`) |
| `--line` | `rgba(233,221,198,.14)` | nav border, input border |
| `--hairline` | `rgba(233,221,198,.09)` | section dividers |

One accent, brand default, no second hue anywhere. Every text colour clears 4.5:1.

### Type

Serif ground (`Georgia`) for everything readable; sans (`Futura` / `Avenir Next`) only
for labels, buttons and nav. Five steps, extremes-only, nothing filling the middle:

| Token | Value | Rendered range | Use |
|---|---|---|---|
| `--t-label` | `.75rem` | 12px | labels, bylines, buttons, nav, fineprint |
| `--t-body` | `1.0625rem` | 17px | prose (measure capped 60–68ch) |
| `--t-lede` | `1.375rem` | 22px | decks, h3, interlude |
| `--t-h2` | `clamp(1.9rem,3.6vw,2.6rem)` | 30–42px | h2, path numerals, book numerals |
| `--t-display` | `clamp(2.7rem,7vw,6rem)` / `8.6vw,7.4rem` on index | 43–118px | h1 |

Step ratios at a 1280px viewport: 1.42 / 1.29 / 1.38 / 1.42 — all above the 1.25 floor,
7.5:1 across the whole scale on the homepage.

### Motion

Ease is `cubic-bezier(.16,1,.3,1)` everywhere; only `transform`, `opacity` and `filter`
animate. Reveals are 44px rise + fade, 950ms, staggered 60ms per child to a 540ms cap,
with the hidden `.pre` class applied **by JS only** so a no-JS visitor sees the finished
page. Hover intent is 200–250ms on every interactive element. One authored moment per
page: homepage = headline lines rising out of overflow masks over a 2.2s atmosphere
fade-up; book = the projector halo breathing behind the cover; collection = the same
headline rise followed by the six spines dealing in left-to-right at 80ms intervals,
then the gold spine drawing itself down the path on its own IntersectionObserver.
`prefers-reduced-motion: reduce` kills all animation and transition globally.

## Hero assets — Gemini generation prompts

Every hero currently ships a CSS-only stand-in (layered radial gradients + a drifting
light haze + a horizon streak + a table falloff + vignette) that occupies the exact
final space. Drop the generated image in behind `.scene .base` as a `background-image`
and keep `.drift` / `.drift2` / `.vignette` on top — they are what stops a still image
from looking dead.

### 1. Homepage hero — `hero-archive.jpg` (the monumental one)

> A dark cinematic still life of historical objects arranged on a worn oak table in a
> vast unlit archive: a folded campaign map with a bent corner, a tarnished brass
> sextant, a stack of leather-bound ledgers, a broken wax seal, a single spent musket
> ball, a cracked marble bust turned three-quarters away in deep shadow at the right.
> Single hard key light raking in low from the lower right at roughly 15 degrees, like
> a projector beam through dust, falling off to near-black within a metre; heavy
> airborne dust motes catching the beam. Palette strictly near-black brown-blacks
> (#0d0b08 to #1c150c) with warm antique-gold highlights (#c9a24b) and one small
> parchment-cream highlight; absolutely no blue, green, teal or magenta anywhere.
> Shot on 35mm anamorphic, 40mm lens, f/2.0, shallow depth of field with the bust
> falling out of focus, subtle film halation on the brightest gold specular, fine
> 35mm grain. Composition: all objects sit in the lower two-thirds, the upper-left
> third is empty near-black negative space reserved for a headline. Prestige
> documentary title card. No text, no lettering, no watermark, no people, no modern
> objects.
>
> Aspect ratio **16:9** (also export a **4:5** crop for mobile).
> Target: JPEG q78 progressive, 2400×1350, **under 320 KB**; plus a WebP twin at
> ~200 KB and a 24px-wide blurred LQIP inlined as a data URI.
> *Video variant:* same prompt plus "seamless loop, 8 seconds, no camera cut — only
> dust drifting through the beam and a barely perceptible 2% push-in", delivered as
> H.264 MP4 + VP9 WebM, **under 2.5 MB**, `muted playsinline loop`, poster = the JPEG.

### 2. Book page hero — `hero-book-plinth.jpg`

> A single closed book standing upright on a dark stone plinth in an empty near-black
> room, three-quarter view, edges catching a thin gold rim light. A soft circular pool
> of warm light behind it on the back wall, like a slide projector left running.
> Palette #0d0b08 ground, #c9a24b rim and pool, parchment #e9ddc6 on the page edges
> only. 50mm lens, f/2.8, eye level, slight vignette, fine grain, no reflections on
> the floor. Empty space to the right for a headline. No text on the book, no title
> lettering, no hands, no people.
>
> Aspect ratio **16:9**. JPEG q78, 2000×1125, **under 240 KB**.
> Sits behind the existing `.bookhead .halo`, which stays as the live glow.

### 3. Collection hero — `hero-conquerors.jpg`

> A vast dark campaign table seen from a low three-quarter angle: a huge worn military
> map of Europe and Asia unrolled and weighted at the corners by a helmet, a sword
> pommel and two brass weights, with faint route lines drawn on it. Six unlit candle
> stubs in a rough line across the map. Single low warm key light from the far right
> at a raking angle, the rest of the room swallowed in black; long shadows running
> left. Palette near-black #0d0b08 with antique gold #c9a24b highlights and one
> parchment #e9ddc6 note on the map; no blue, no green. Shot on 35mm anamorphic, 35mm
> lens, f/2.0, heavy falloff, dust in the beam, fine grain. Upper-left third empty and
> near-black for a headline; lower band deliberately dark so cover thumbnails can sit
> over it. No text, no legible place names, no flags, no people, no modern objects.
>
> Aspect ratio **16:9** (plus a **4:5** mobile crop).
> JPEG q78, 2400×1350, **under 300 KB**; WebP twin ~190 KB.

General rules for all three: no legible text of any kind in the image (it will be
wrong and it will date), no people or faces, no cool hues at all, and everything must
survive being crushed to near-black in the lower 26% where the `.table` gradient
takes over.

## Detector status

`npx impeccable detect mockups/01-cinematic-archive/*.html` — **36 → 3 findings.**

Fixed for real (across all three pages):

- **wide-tracking** (×12) — `.pick .byline`, `.step .byline` and the footer were at
  .05–.06em on running text; pulled back to .04em. Wide tracking now lives only on
  nav links, buttons and the logo, which are short uppercase labels.
- **all-caps-body** (×3) — the `.label` meta lines ("55 books and counting · £2.99 …",
  "Part of Conquerors · France · …", the collection stats line) were 61–90 characters
  of tracked uppercase, i.e. sentences, not labels. `.label` is now mixed-case sans at
  .04em with the gold `<b>` retained. Uppercase is reserved for nav, buttons and the
  logo.
- **hero-eyebrow-chip** (×1) — the crumbs above the collection H1 read as an eyebrow
  chip. Now a real `<nav aria-label="Breadcrumb">` with `aria-current="page"`, in
  mixed case at .04em, so it reads as navigation rather than a kicker. Applied to
  `book.html` too for consistency.
- **cramped-padding** (×1) — `index.html`'s `.bill` band carried its border while the
  padding lived on the inner flex row; padding moved onto the bordered element itself.
  No visual change.
- **numbered-section-labels** (×8) — `book.html`'s ranked picks used tiny 12px tracked
  "01…08" chips beside each h3, which is exactly the AI-scaffolding shape. The numerals
  are now a deliberate typographic element: serif, `--t-h2`, gold, set above the
  heading — the same treatment as the collection path's station numerals, so the two
  pages now share one numbering language.

Classified, not fixed — **3 remaining, one per page**:

- **flat-type-hierarchy** — "Sizes: 12px, 17px, 22px (ratio 1.8:1)". This is a
  false positive caused by `clamp()`: the detector resolves `var()` and `rem` but not
  `clamp()`, so it never sees the two largest steps. Verified in a real browser at a
  617px-wide viewport, the rendered scale is **12 / 17 / 22 / 30.4 / 43.2px** (ratios
  1.42, 1.29, 1.38, 1.42; 3.6:1 across the scale, rising to 7.5:1 on a desktop
  homepage where the H1 hits ~118px). Confirmed by substituting static `rem` tokens in
  a throwaway copy — the finding disappears with no other change — so the only way to
  clear it in place is to give up fluid display type, which is not a trade this
  direction should make.

## build.py

One change: `render_collection_hub()` gains an ordered `path` array per collection in
`seo/collections.json` — each entry `{slug, position, dateline, why}` — and the
existing book loop emits `<article class="step">` stations instead of grid cells;
everything else (nav, footer, capture, grain, motion script) moves into the shared
`base_page()` head/foot the three templates already share verbatim.
