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

## Font + sand timer

### The two faces, self-hosted

`Futura` was the problem: it ships on macOS and almost nowhere else, so the brand's
sans was Futura for us and Trebuchet for most visitors. Both faces are now local
files under `mockups/fonts/` (symlinked in as `fonts/`), declared as `@font-face` at
the top of each page's `<style>` with `font-display:swap` and a variable weight range.
No third-party request anywhere: the pages still only reach for `fonts/` and `covers/`.

| | family | file | size | axis | licence |
|---|---|---|---|---|---|
| display + prose | **Source Serif 4** (Frank Grießhammer, Adobe) | `fonts/SourceSerif4-latin.woff2` | 119 KB | `wght` 200–900 | SIL OFL 1.1 |
| labels, nav, buttons | **Archivo** (Omnibus-Type) | `fonts/Archivo-latin.woff2` | 34 KB | `wght` 100–900 | SIL OFL 1.1 |

All latin subsets, all free for commercial use and self-hosting.
Tokens lead with the new families and keep the old stacks behind them, so a failed
font load still lands on Georgia/Futura rather than on Times.

The italic hero word, the `.note` paragraphs and the `.warning` pull-quote are set in
the real **`fonts/SourceSerif4-Italic-latin.woff2`** (127 KB, `wght` 200–900,
`font-style:italic`, same SIL OFL 1.1), declared alongside the roman on all three
pages — an early cut shipped roman-only and let the browser fake the slant. Confirmed
genuine rather than synthetic: the italic advance measures 929.9 against the roman's
968.1 for the same string, where a synthesised oblique would match exactly. Total
weight is now 280 KB across three latin subsets.

### What the swap forced

Not cosmetic. Two metric differences moved real layout, and both were retuned:

1. **`ch` collapsed.** Georgia's `0` is 0.614em; Source Serif 4's is 0.470em. Every
   `max-width:NNch` in the sheet therefore shrank by ~24% the moment the font
   applied — columns narrowed, and the hero H1's `12ch` box went from 872px to 668px
   and re-wrapped the headline from four rendered lines to five. Every `ch` measure
   was re-derived to hold the *physical* width the approved design had:
   headlines ×1.31 (index `12ch→15.7ch`, book `16ch→21ch`, collection `13ch→17ch`),
   prose and decks ×1.23 (`68ch→84ch`, `62ch→78ch`, `56ch→70ch`, `48ch→59ch`,
   `66ch→81ch`, `52ch→64ch`, `60ch→74ch`, `46ch→57ch`, `18ch→23ch`).
2. **x-height dropped 6%.** Measured: Georgia 0.481em, Source Serif 4 0.452em. Body
   went `1.0625rem → 1.125rem` (17→18px) and the lede `1.375rem → 1.4375rem` (22→23px),
   which lands Source Serif's x-height within 0.5% of Georgia's old rendered height.
   `line-height:1.68` was left alone — it reads correctly at the new size.

The nav was the thing to watch, and it came out fine: **Archivo is narrower than
Futura**, not wider (1173.8 vs 1214 advance units for the same 25-character string at
100px), and its larger x-height means the 12px tracked caps read *better* than Futura
did at the same size. No tracking or `--t-label` change was needed. Verified at
375×812 on all three pages: the pill spans 12→363px and all four items sit inside it —
logo `23→104`, THE BOOKS `114→188`, COLLECTIONS `200→290`, AMAZON `302→357`.
`document.documentElement.scrollWidth === 375` on every page, no horizontal overflow.

### The sand timer

The logo mark already contains an hourglass and the promise is "under an hour", so a
running one is the brand's own object rather than an ornament. One authored inline SVG
component, `.hg`, reused at three sizes — **and only three, one per page**:

- **index.html** — `.hg-hero`, `clamp(264px,28vw,396px)` of square box (a 152px-wide
  glass at desktop), a 26s cycle, absolutely placed in the empty right half of the
  hero beside the headline; below 1000px it goes static above the H1, where it becomes
  the first thing on the page. This is the load moment; the existing `rise2` entrance
  carries it in last.
- **book.html** — `.hg-inline`, 2.64em tall, set immediately before *"Ours reads in
  under an hour"* in the `.partof` line. One cycle only: an IntersectionObserver adds
  `.hg-run` at 60% visibility, `--hg-rep:1` and `animation-fill-mode:both` leave it
  resting fully drained.
- **collection.html** — `.hg-inline`, same size, one instance, sitting against *"about 5 hours
  end to end"* in the hero stats line. Loops at 18s.

Nothing on the book tiles, nothing on the path stations.

How it is built, all transform/opacity, no layout properties:

- **Authored geometry**, `viewBox 0 0 240 240`: a hairline parchment glass path with
  `vector-effect:non-scaling-stroke` (so the stroke stays 1.2px whether it is drawn at
  396px or 32px), two gold cap bars, and two gold sand paths — one per chamber. The
  drawing itself is 92×188 user units, centred on (120,120).
- **Draining and filling** are two `<clipPath>` rects translated on the Y axis:
  `hgDrain` slides the top chamber's mask down 86px so less and less of the upper sand
  path shows; `hgFill` slides the bottom mask up 88px so more and more of the lower one
  does. Pure `transform`, so both stay on the compositor.
- **The falling stream** is a column of gold `<circle>` motes clipped to the neck,
  translated down exactly one 9px period on a 0.5s linear loop, so the repeat is
  seamless; a separate `hgPour` keyframe fades it in at 5% and out at 86%.
- **The loop seam** is the nice part. The glass, the caps and the two sand paths are
  all 180°-rotationally symmetric about the centre. At 88% of the cycle — sand fully
  down, stream gone — `hgFlip` rotates the whole group 180° with the house
  `--ease`. At 100% the rotation snaps back to 0° and the sand resets to top-full,
  which is *pixel-identical to the flipped, bottom-full frame it just left*. It reads
  as somebody turning the glass over, and it never jumps.

**Why the viewBox is a 240 square** (this was a bug, caught and fixed): the first cut
drew the glass in a tight `0 0 120 200` box with `overflow:visible`. The end states
were fine, so it looked correct at rest — but the group's rotation *diagonal* is
√(92² + 188²) ≈ 209 user units, far wider than the 120-unit box, so every intermediate
angle painted outside the SVG. Measured on the index hero at 375px, the 90° frame was
138px wide in an 88px box and reached `left:-3`, bleeding off the left edge of the
page. The fix is geometric, not CSS: the same artwork, translated +60x/+20y into a
`0 0 240 240` square whose half-diagonal (104.7) fits with room to spare, plus
`transform-origin:120px 120px`, `overflow:hidden` as a belt-and-braces guard, and
**doubled CSS sizes so the glass keeps the exact size it had** — hero
`clamp(132px,14vw,198px) → clamp(264px,28vw,396px)`, inline `2.2em → 2.64em`
(the square box is 240 tall where the old one was 200, so the inline step is ×1.2).

The square carries 30.83% dead space each side and 10.83% top and bottom, so the
anchoring backs off by exactly that much to hold the old optical position: the hero's
`right`/`bottom` became `calc(22px - .25*var(--hgw))` / `calc(104px - .08333*var(--hgw))`,
and the inline instances took `margin:0 -.36em 0 -.61em` with `vertical-align:-1em`.
The one place that could not be fully compensated is the mobile hero: pulling the box
far enough left to align the glass with the 22px text margin would have put the 45°
sweep back at a negative x, so the box stops flush at `x:0` (`margin-left:-22px`) and
the mark now sits ~22px further in than before. Deliberate trade — nothing may cross
the viewport edge.

Painted-rect check, `.hg-rot` forced through 0/45/90/135/180° on all three pages at
1440 and 375, measured against the SVG's own CSS box:

| | box | 0°/180° | 45°/135° (worst) | 90° | min clearance |
|---|---|---|---|---|---|
| index hero @1440 | 396×396 | 151.8×310.2 | 326.7×326.7 | 310.2×151.8 | 34.7px all sides |
| index hero @375 | 176×176 | 67.5×137.9 | 145.2×145.2 | 137.9×67.5 | 15.4px all sides |
| book / collection inline | 31.7×31.7 | 12.1×24.8 | 26.1×26.1 | 24.8×12.1 | 2.8px all sides |

Every angle stays inside the box on every side, no negative left, nothing past the
viewport (`documentElement.scrollWidth` = 375 and 1425 respectively). Glass renders at
118.8×280.5 on the desktop hero and 9.5×22.4 inline — identical to the pre-fix numbers,
so the doubled box changed the footprint and not the drawing.

`prefers-reduced-motion: reduce` overrides the two mask transforms to a fixed
`translateY(48px)` / `translateY(40px)` — about 55% drained, sand in both chambers —
and pins the stream visible at `opacity:1`. No animation runs (the run rules live
inside a `no-preference` query, and book's observer never fires because that script
already returns early). Verified in-browser: `animation-name: none` on every part,
and the mark still reads as an hourglass rather than an empty one.

One H1 per page, the `<main>` landmark, the gold `:focus-visible` ring,
`text-wrap:balance` and `caret-color` are all untouched. `impeccable detect` on all
three pages: still **zero findings**.
