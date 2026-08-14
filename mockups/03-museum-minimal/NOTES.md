# 03 — Museum Minimal

## Direction thesis

Turbo History is hung like a national museum that decided wall text should be
readable: parchment ground, clinical whitespace, giant Georgia display type with a
ghosted first line, and covers matted and framed as exhibits rather than stacked as
product cards. Gold appears only where a museum would use brass — thin section
rules and the one CTA — so the page reads as authority rather than as a shop. The
collection page extends that into a curated gallery route: a floor plan across the
top, then six numbered wall labels in a deliberate chronological argument, which is
the thing the live site cannot currently express.

## Tokens as built

Colour (identical across all three pages):

| token | value | role |
| --- | --- | --- |
| `--paper` | `#f5efe2` | page ground (parchment) |
| `--paper-deep` | `#eee6d3` | reserved deeper ground |
| `--mat` | `#fbf7ed` | exhibit mat inside every frame |
| `--ink` | `#181410` | body + display text (13.9:1 on paper) |
| `--muted` | `#5f5644` | labels, secondary prose (6.4:1 on paper) |
| `--line` | `#d8cdb4` | hairlines, non-text only |
| `--gold` | `#c9a24b` | THE accent — section rules, underlines, CTA fill only. Never used as text colour on paper (fails AA at 2.1:1) |

Type — two families, five sizes, ratio ≥1.25:

- `--serif` Georgia / Times New Roman — everything structural and readable.
- `--mono` ui-monospace / SF Mono — labels only.
- Scale: 12px mono label (0.22em tracking, uppercase) → 17px body → 24–30px
  sub-heads → 34px H2 → `clamp(52px, 8.4vw, 112px)` H1. Nothing between 34 and 52.
- `.label.sentence` (13px, 0.02em, no uppercase) is the escape hatch for label-toned
  strings longer than ~35 characters — crumbs, plaque lines, bylines, fineprint.
  Added while clearing the `all-caps-body` detector finding; the tiny uppercase
  label survives everywhere it is genuinely a label.
- Prose measure 62–66ch.

Motion (Tier 1, all three pages): hidden state applied only under `html.js`, so
no-JS renders complete. IntersectionObserver adds `.in` to `[data-rv]` (44px rise +
fade, `--d` stagger at 80ms). Hover intent 180–220ms on every link, button, frame
and route stop. Everything eases on `cubic-bezier(0.16,1,0.3,1)`; only transform,
opacity and filter animate. `prefers-reduced-motion: reduce` removes the whole
block.

Authored hero moment per page — index: headline ghost/ink stagger plus the relic
rising into rotation. book: cover frame rises, then the head block staggers.
collection: the gold floor-plan rule **draws itself** left to right (`scaleX 0→1`,
1.25s) and the six route stops arrive along it in sequence — the museum equivalent
of a route lighting up.

## Hero assets — Gemini generation prompts

All three are the same object family (broken classical stone on white) so the site
reads as one exhibition. Each replaces a CSS stand-in already occupying the exact
space.

**1. index.html — `.relic` (diagonal marble shard, right of headline)**

> Photoreal studio still life: a fractured fragment of a white Carrara marble
> portrait bust — jaw, cheek and part of a laurel wreath, cleanly broken, fine grey
> veining and chipped edges. Suspended against a seamless warm off-white parchment
> backdrop (#f5efe2). Single large softbox from upper left, one subtle bounce from
> the right, soft directional shadow falling down-right; no rim light, no glow.
> Palette strictly warm neutrals — bone, chalk, sand, faint ochre in the shadow.
> 85mm lens, f/8, eye level, object rotated ~8° clockwise, filling the frame
> vertically with air around it. Museum-catalogue photography, no props, no text,
> no people.
> Aspect ratio 2:3 (portrait). Deliver 1160×1740 → export **WebP q78, ≤180 KB**,
> plus JPEG q76 fallback ≤240 KB. Transparent-background PNG variant welcome if the
> generator can cut it cleanly.

**2. collection.html — `.relic` (broken sword, right of headline)**

> Photoreal studio still life: an ancient bronze-and-iron sword broken just below
> the crossguard, blade heavily patinated with green-brown corrosion, pitted edge,
> the two fragments resting slightly apart as if just laid down. Seamless warm
> off-white parchment backdrop (#f5efe2). One large softbox upper left, soft
> falloff, a single believable contact shadow down-right. Palette warm neutrals plus
> muted verdigris — no saturated colour, no gold highlights. 85mm lens, f/8,
> straight-on, object tilted ~9° anticlockwise, running diagonally out of frame at
> top and bottom. Archaeological catalogue photography, no background objects, no
> text.
> Aspect ratio 2:3 (portrait). 1120×1680 → **WebP q78, ≤180 KB**, JPEG q76 fallback.

**3. book.html — optional plate above the picks table (not yet placed)**

> Photoreal overhead flat-lay: a closed antique leather-bound volume, a folded
> campaign map and a pair of dividers arranged on warm off-white parchment paper.
> Even diffuse overhead light, shallow shadows, no glare. Warm neutral palette,
> single muted gold detail on the book's spine tooling. 50mm lens, f/5.6, directly
> top-down. Museum catalogue plate, no text, no hands.
> Aspect ratio 3:2 (landscape). 1800×1200 → **WebP q78, ≤200 KB**.

Video note: if any of these later becomes a loop, request "seamless loop, 6s, static
camera, only a slow dust drift in the light beam, no cuts" and deliver as muted
`<video>` WebM ≤1.2 MB with the still as poster.

## Detector status

`npx impeccable detect mockups/03-museum-minimal/*.html` → **3 findings, all
`cream-palette`, one per page. Classified brand-intentional.**

Justification: `#f5efe2` is not a default warm off-white reached for by reflex — it
is the specified ground for this direction in MOCKUP-BRIEF.md ("Near-white gallery.
Parchment-paper ground (#f5efe2 family)"), it is the whole premise of the museum
read, and it is the deliberate contrast against direction 01's near-black. Changing
it would delete the direction.

Everything else was fixed rather than classified: gold-as-text (`low-contrast`,
2.1:1) was removed from the route numerals and floor plan so gold now appears only
on rules and CTA fills; long uppercase label strings across all three pages moved to
`.label.sentence`; the decorative `repeating-linear-gradient` marble veining on the
relic stand-ins was dropped in favour of the SVG turbulence layer already present.
One advisory remains (`em-dash-overuse`, index.html, 18 em-dashes) — that is live
converting copy carried over per the brief, and advisories are not counted as
failures.

## build.py

Adds one template — `collection.html`, rendered once per `collection` value with an
ordered `books` list plus two new per-book fields (`route_position` and a
`wall_label` paragraph pair) sourced from the catalogue, and a `collections/` index
route; the existing book and home templates only need the new `.label.sentence`
class applied to their long label strings.
