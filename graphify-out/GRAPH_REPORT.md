# Graph Report - turbohistory-website  (2026-07-19)

## Corpus Check
- 3 files · ~94,521 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 15 nodes · 33 edges · 3 communities
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `285b3218`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- build.py
- book_page
- esc

## God Nodes (most connected - your core abstractions)
1. `main()` - 7 edges
2. `capture()` - 6 edges
3. `esc()` - 6 edges
4. `shell()` - 6 edges
5. `book_page()` - 6 edges
6. `curated_page()` - 6 edges
7. `index_page()` - 5 edges
8. `blurb_html()` - 3 edges
9. `privacy_page()` - 3 edges
10. `load_books()` - 2 edges

## Surprising Connections (you probably didn't know these)
- `book_page()` --calls--> `capture()`  [EXTRACTED]
  build.py → build.py  _Bridges community 2 → community 1_
- `privacy_page()` --calls--> `shell()`  [EXTRACTED]
  build.py → build.py  _Bridges community 2 → community 0_
- `main()` --calls--> `book_page()`  [EXTRACTED]
  build.py → build.py  _Bridges community 1 → community 0_

## Import Cycles
- None detected.

## Communities (3 total, 0 thin omitted)

### Community 0 - "build.py"
Cohesion: 0.70
Nodes (4): load_books(), main(), make_thumbs(), privacy_page()

### Community 1 - "book_page"
Cohesion: 0.67
Nodes (3): blurb_html(), book_page(), Pipeline blurbs are plain text with bullet lines. Render as real HTML.

### Community 2 - "esc"
Cohesion: 0.48
Nodes (7): capture(), curated_page(), esc(), index_page(), Email capture. Honest hook: the books really are free most weekends., Curated-list page. Beats the incumbents by being more useful: honest picks,, shell()

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `curated_page()` connect `esc` to `build.py`?**
  _High betweenness centrality (0.158) - this node is a cross-community bridge._
- **Why does `capture()` connect `esc` to `build.py`, `book_page`?**
  _High betweenness centrality (0.154) - this node is a cross-community bridge._
- **Why does `blurb_html()` connect `book_page` to `build.py`?**
  _High betweenness centrality (0.143) - this node is a cross-community bridge._