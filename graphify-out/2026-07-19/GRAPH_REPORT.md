# Graph Report - turbohistory-website  (2026-07-19)

## Corpus Check
- 3 files · ~80,087 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 10 nodes · 19 edges · 3 communities
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `69a0f1bd`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- build.py
- book_page
- esc

## God Nodes (most connected - your core abstractions)
1. `book_page()` - 5 edges
2. `main()` - 5 edges
3. `esc()` - 4 edges
4. `shell()` - 4 edges
5. `index_page()` - 4 edges
6. `blurb_html()` - 3 edges
7. `load_books()` - 2 edges
8. `make_thumbs()` - 2 edges
9. `Pipeline blurbs are plain text with bullet lines. Render as real HTML.` - 1 edges

## Surprising Connections (you probably didn't know these)
- `book_page()` --calls--> `esc()`  [EXTRACTED]
  build.py → build.py  _Bridges community 2 → community 1_
- `main()` --calls--> `book_page()`  [EXTRACTED]
  build.py → build.py  _Bridges community 1 → community 0_
- `main()` --calls--> `index_page()`  [EXTRACTED]
  build.py → build.py  _Bridges community 2 → community 0_

## Import Cycles
- None detected.

## Communities (3 total, 0 thin omitted)

### Community 0 - "build.py"
Cohesion: 0.83
Nodes (3): load_books(), main(), make_thumbs()

### Community 1 - "book_page"
Cohesion: 0.67
Nodes (3): blurb_html(), book_page(), Pipeline blurbs are plain text with bullet lines. Render as real HTML.

### Community 2 - "esc"
Cohesion: 1.00
Nodes (3): esc(), index_page(), shell()

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `blurb_html()` connect `book_page` to `build.py`?**
  _High betweenness centrality (0.222) - this node is a cross-community bridge._
- **Why does `book_page()` connect `book_page` to `build.py`, `esc`?**
  _High betweenness centrality (0.102) - this node is a cross-community bridge._
- **Why does `main()` connect `build.py` to `book_page`, `esc`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._