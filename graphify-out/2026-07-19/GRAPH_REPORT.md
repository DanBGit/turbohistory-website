# Graph Report - turbohistory-website  (2026-07-19)

## Corpus Check
- 3 files · ~101,395 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 16 nodes · 34 edges · 4 communities
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `58e35d3e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- build.py
- book_page
- esc
- curated_page

## God Nodes (most connected - your core abstractions)
1. `curated_page()` - 7 edges
2. `main()` - 7 edges
3. `capture()` - 6 edges
4. `esc()` - 6 edges
5. `shell()` - 6 edges
6. `book_page()` - 6 edges
7. `index_page()` - 5 edges
8. `blurb_html()` - 3 edges
9. `privacy_page()` - 3 edges
10. `load_books()` - 2 edges

## Surprising Connections (you probably didn't know these)
- `book_page()` --calls--> `capture()`  [EXTRACTED]
  build.py → build.py  _Bridges community 2 → community 1_
- `curated_page()` --calls--> `capture()`  [EXTRACTED]
  build.py → build.py  _Bridges community 2 → community 3_
- `privacy_page()` --calls--> `shell()`  [EXTRACTED]
  build.py → build.py  _Bridges community 2 → community 0_
- `main()` --calls--> `book_page()`  [EXTRACTED]
  build.py → build.py  _Bridges community 1 → community 0_
- `main()` --calls--> `curated_page()`  [EXTRACTED]
  build.py → build.py  _Bridges community 3 → community 0_

## Import Cycles
- None detected.

## Communities (4 total, 0 thin omitted)

### Community 0 - "build.py"
Cohesion: 0.70
Nodes (4): load_books(), main(), make_thumbs(), privacy_page()

### Community 1 - "book_page"
Cohesion: 0.67
Nodes (3): blurb_html(), book_page(), Pipeline blurbs are plain text with bullet lines. Render as real HTML.

### Community 2 - "esc"
Cohesion: 0.60
Nodes (5): capture(), esc(), index_page(), Email capture. Honest hook: the books really are free most weekends., shell()

### Community 3 - "curated_page"
Cohesion: 0.67
Nodes (3): curated_page(), Curated-list page. Beats the incumbents by being more useful: honest picks,, Curated-list page. Beats the incumbents by being more useful: honest picks,

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `curated_page()` connect `curated_page` to `build.py`, `esc`?**
  _High betweenness centrality (0.270) - this node is a cross-community bridge._
- **Why does `capture()` connect `esc` to `build.py`, `book_page`, `curated_page`?**
  _High betweenness centrality (0.147) - this node is a cross-community bridge._
- **Why does `blurb_html()` connect `book_page` to `build.py`?**
  _High betweenness centrality (0.133) - this node is a cross-community bridge._