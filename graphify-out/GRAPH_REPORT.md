# Graph Report - turbohistory-website  (2026-07-19)

## Corpus Check
- 3 files · ~92,027 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 13 nodes · 27 edges · 3 communities
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4d6359c5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- build.py
- book_page
- esc

## God Nodes (most connected - your core abstractions)
1. `book_page()` - 6 edges
2. `main()` - 6 edges
3. `capture()` - 5 edges
4. `esc()` - 5 edges
5. `shell()` - 5 edges
6. `index_page()` - 5 edges
7. `blurb_html()` - 3 edges
8. `privacy_page()` - 3 edges
9. `load_books()` - 2 edges
10. `make_thumbs()` - 2 edges

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
Cohesion: 0.60
Nodes (5): capture(), esc(), index_page(), Email capture. Honest hook: the books really are free most weekends., shell()

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `capture()` connect `esc` to `build.py`, `book_page`?**
  _High betweenness centrality (0.170) - this node is a cross-community bridge._
- **Why does `blurb_html()` connect `book_page` to `build.py`?**
  _High betweenness centrality (0.167) - this node is a cross-community bridge._
- **Why does `book_page()` connect `book_page` to `build.py`, `esc`?**
  _High betweenness centrality (0.102) - this node is a cross-community bridge._