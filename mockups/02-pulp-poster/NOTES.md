# 02 — Pulp Poster

## Direction thesis

A dime-store paperback rack photographed on an ink-black table: condensed all-caps
display type at poster scale, covers pinned at slight angles like stickers, gold
starbursts and rubber-stamp labels doing the shouting. Every panel of running text is
a parchment card dropped onto that dark ground with a hard offset shadow — no blur,
no glow, no gradient softness anywhere. The energy is meant to match the subtitles
("The Drunk They Wrote Off Who Won the War"), so the page sells before it explains.

## Tokens as built (identical across all three templates)

**Colour**

| Token | Value | Role |
| --- | --- | --- |
| `--ink` | `#171310` | page ground |
| `--ink2` | `#0d0a07` | text on gold/parchment, shadow ground |
| `--parch` | `#e9ddc6` | body text on ink; panel surface |
| `--parch2` | `#f2e9d4` | input fields inside panels |
| `--gold` | `#c9a24b` | the single accent — bursts, stamps, rules, buttons |
| `--mut` | `#b5a78d` | secondary text on ink (7.4:1) |
| `--mutp` | `#5d5140` | secondary text on parchment (6.0:1) |

Single accent, brand gold. No second hue anywhere; the covers are the only colour
that is not ink/parchment/gold.

**Type**

- `--cond` — `Arial Narrow, Avenir Next Condensed, Helvetica Neue Condensed, …` —
  every display line, label, button, stamp. All-caps for labels and headings only.
- `--serif` — `Georgia, Times New Roman` — all running text, 1.65 leading, measure
  capped at 66–70ch.
- Scale (5 steps, ratio ≥1.25 between each): `--fs0 13px` · `--fs1 17px` ·
  `--fs2 27px` · `--fs3 clamp(34,4.6vw,46)` · `--fs4 clamp(58,10.5vw,138)`.
  Nothing lives between 17px and 27px — labels are tiny, display is huge.
- Ease `cubic-bezier(.16,1,.3,1)` everywhere; hover intent 180–200ms; reveals 750ms.

**Motion (Tier 1, per page)**

- Authored moment: `[data-drop]` elements start at `translateY(-64px) rotate(−8°) scale(1.1)`
  and land in place, staggered 105–130ms apart. Homepage = stickers hit the poster;
  book page = the cover and its burst drop in; collection = the six covers deal onto
  the table like a hand of cards.
- IntersectionObserver reveals: 44px rise + fade, `[data-rv]` singles and `[data-rvg]`
  groups (45ms per child, capped at 600ms). Hidden state is added by JS only.
- `prefers-reduced-motion: reduce` returns early from the script *and* kills all
  transitions in CSS.

## Hero-asset generation prompts (Gemini / AI image)

The CSS stand-ins are the gold starburst fields behind the cover collages
(`.collage::before`, `.coverblock::before` — inline SVG rays, radially masked). Each
can be replaced by a generated plate at the same position with no layout change.

**1. Homepage hero backdrop — `hero-rack.jpg`**
> A 1960s dime-store paperback rack photographed from slightly above on a scuffed
> dark walnut table, empty of readable titles: blank pulp paperbacks stacked and
> fanned, one open notebook, a brass desk lamp just out of frame. Single warm
> tungsten key light from upper right raking across the grain, deep falloff to near
> black at the edges. Palette strictly warm black, aged parchment cream and antique
> gold — no blue, no green, no red. Shot on 50mm at f/2.8, slight film grain, no
> text, no faces, no logos. Aspect ratio 3:2.
> Target: 1800×1200 JPEG (quality 78), under 260 KB. WebP fallback at 180 KB.

**2. Book-page cover plate — `napoleon-plate.jpg`**
> An overhead still life on black-stained wood: a folded 19th-century military map,
> a brass compass, a single guttering candle and a torn playing card, arranged around
> an empty rectangular space in the centre where a book cover will sit. Hard low-angle
> tungsten light from the left throwing long crisp shadows. Warm black, parchment
> cream and antique gold only. Macro-ish 85mm, f/4, visible paper fibre and dust.
> No text, no portraits, no heraldry. Aspect ratio 4:5 (portrait).
> Target: 1200×1500 JPEG (quality 78), under 220 KB.

**3. Collection-hub backdrop — `conquerors-map.jpg`**
> A weathered parchment world map lying flat on a dark table, edges burned and
> curling, creased into eight panels, with six blank pale rectangles laid across it
> in a rough diagonal line as if paperbacks had been dropped there. Warm single-source
> lamp from top-left, strong vignette to near black. Aged parchment, warm black and
> antique gold only. 35mm, f/5.6, straight-down camera, heavy grain. No borders,
> no country names, no text of any kind. Aspect ratio 16:9.
> Target: 1920×1080 JPEG (quality 76), under 280 KB.

**4. Optional starburst plate — `burst.png`**
> Flat vector-style 24-ray sunburst, antique gold `#c9a24b` on transparent, rays of
> uneven width, slightly hand-cut edges as if screen-printed, 6% ink misregistration.
> Square, 1200×1200 PNG-24 with alpha, under 60 KB.

Every generated asset must be checked at 390px width — the composition has to survive
being cropped to a 4:5 slice of its centre.

## Detector status

`npx impeccable detect mockups/02-pulp-poster/*.html` → **3 findings**, all
brand-intentional and listed below. `book.html` is clean.

Real findings fixed during the pass (all three pages): gold-on-gold button text inside
parchment panels (2.7:1 → `.panel .btn` now ink on gold, 8.9:1); the footer rule and
the collection fact-bar rule rebuilt as drawn rules instead of 3px one-side borders;
the starburst atmosphere and the reading-path dashes rebuilt as inline SVG instead of
repeating gradients; and all-caps removed from every run of *sentence-length* text set
in the condensed face (fineprint, bylines, breadcrumbs, opt-in labels, table titles,
section subs, footers, the reading-path connectives). Uppercase is now reserved for
labels, stamps, buttons and headings, which is what it was for.

**Classified as brand-intentional**

1. `all-caps-body` — 34 chars, `index.html`. This is the hero tagline
   `<p class="display">Start anywhere. Finish everything.</p>` — display typography set
   at 27px in the poster face, not body copy. The rule is tag-based and cannot tell a
   display line from a paragraph; the same string inside an `<h2>` is not flagged. The
   equivalent line on `collection.html` was tightened to 30 characters and now passes,
   which is the only difference between them.
2. `clipped-overflow-container` — `index.html`, `collection.html`. `body` carries
   `overflow-x: hidden` as a horizontal-scroll guard, because the collage covers,
   stamps and rotated panels deliberately sit a few pixels outside the grid. The rule
   exists to protect escaping tooltips, menus and popovers; these pages have none —
   there is no layer on any of the three templates that needs to leave the viewport.
   Removing the guard would trade a theoretical problem for a real horizontal scrollbar
   at several widths.

One further note for the record: an earlier pass showed `tight-leading` at "0.59x" on
the collection tagline. That measurement resolves the unitless `line-height` against
the inherited 17px body size rather than the element's own 27px — the actual leading
is 25px on 27px type. It no longer fires, but if it reappears on another page the
number should not be read literally.

## build.py, in one line

`curated_page()` already renders collection hubs, so this direction needs the shared
`shell()` CSS block swapped for these tokens plus a `reading_order` list (and a
one-sentence `reason` per book) added to `seo/collections.json`, which
`collection_line()`/`curated_page()` then walk in order instead of emitting an
unordered related-books grid.
