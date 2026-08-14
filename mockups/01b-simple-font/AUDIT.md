# Direction 01 — Cinematic Archive · audit

Run 14 Aug 2026 against `/impeccable audit` (v4.1.1) + `detect` + real-browser
measurement at 1440px and 375px. Fixes applied in the same pass are marked FIXED.

## Health score

| # | Dimension | Score | Key finding |
|---|---|---|---|
| 1 | Accessibility | 4 | 0 contrast failures / 244 elements; focus now themed |
| 2 | Performance | 4 | transform+opacity only, targeted will-change, 0 external requests |
| 3 | Responsive | 4 | pill nav clipped "AMAZON" at 375px — FIXED |
| 4 | Theming | 4 | full token system, single accent, browser surfaces themed |
| 5 | Implementation integrity | 3 | display voice is a system face (see P1 below) |
| **Total** | | **19/20** | Excellent — one real gap remains |

Detector: **0 findings** across all three pages.

## Verified, not assumed

- **Contrast:** computed every text node against its resolved ancestor background.
  244 elements, 0 below 4.5:1 (3:1 for large). 
- **Type scale:** 12 / 17 / 22 / 30.4–41.6 / 49.6–118.4px. Steps 1.42, 1.29, 1.38,
  1.63 — all above the 1.25 floor. The detector's earlier `flat-type-hierarchy`
  finding was a genuine false positive: it resolves `var()` and `rem` but not
  `clamp()`, so it never saw the top two steps.
- **Measure:** prose capped 46–68ch. Within the 65–75ch guidance.
- **Performance:** only transform/opacity/color/filter transitions; one blur(16px);
  5 keyframes; `will-change:transform` on exactly 3 animated elements; all 70 covers
  lazy-loaded; zero external requests.
- **Motion:** IntersectionObserver reveals with the hidden state applied via JS, so
  a JS failure leaves all content visible. `prefers-reduced-motion` honoured.

## Fixed in this pass

- **[P1] Nav clipped on mobile.** The floating pill kept its desktop width at 375px;
  "AMAZON" was cut off the right edge and unreachable. The 640px breakpoint tightened
  gaps but never constrained the pill. Now spans left/right 12px with reduced tracking.
- **[P1] `outline:none` on the email input.** Focus was signalled only by a border
  colour change. Replaced with a themed `:focus-visible` ring (2px gold, 3px offset)
  applied globally — previously no element had a themed focus ring at all, which the
  craft floor names as the check models skip most reliably.
- **[P2] No `<main>` landmark** on any page. Added.
- **[P2] Orphaned headline word.** "was" fell alone onto line 3 of the mobile H1.
  `text-wrap:balance` on headings, `pretty` on decks.
- **[P2] Hit areas.** Nav links were 20px tall, footer links 16px — below WCAG 2.5.8's
  24px minimum. Padded to 38px without changing visual position.
- **[P3] Caret unthemed.** `caret-color` now gold. `::selection` was already themed.

## Open — needs a decision

- **[P1] The display voice is a system face.** `--serif: Georgia` and
  `--sans: Futura, 'Avenir Next', 'Trebuchet MS', Arial`. The craft floor explicitly
  refuses a system face as the display voice of an own-world page: "the closest
  installed font is a failure, not a fallback." Two consequences:
  1. The identity is the same one every default-styled page has.
  2. Futura ships on almost no machine. Mac visitors get Avenir Next, Windows gets
     Trebuchet MS — the brand renders as three different faces depending on platform.
  This is the single biggest remaining lever on "does this look designed." Fix is to
  license and self-host one display serif + one grotesque, and set the tokens to them.
  Mockups were built self-contained by brief, so this was correctly out of scope then.

## Not applicable

- Dark/light theming: this is a committed dark world, not a themed surface.
