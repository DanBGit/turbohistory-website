# Graph Report - turbohistory-website  (2026-07-19)

## Corpus Check
- 5 files · ~110,418 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 29 nodes · 51 edges · 8 communities (6 shown, 2 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cc7a4c1f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- build.py
- book_page
- esc
- curated_page
- app.py
- db
- rate_limited
- deploy.sh

## God Nodes (most connected - your core abstractions)
1. `curated_page()` - 7 edges
2. `main()` - 7 edges
3. `capture()` - 6 edges
4. `esc()` - 6 edges
5. `shell()` - 6 edges
6. `book_page()` - 6 edges
7. `db()` - 5 edges
8. `index_page()` - 5 edges
9. `subscribe()` - 4 edges
10. `rate_limited()` - 3 edges

## Surprising Connections (you probably didn't know these)
- `db()` --references--> `Connection`  [EXTRACTED]
  api/app.py →   _Bridges community 5 → community 6_
- `subscribe()` --calls--> `db()`  [EXTRACTED]
  api/app.py → api/app.py  _Bridges community 5 → community 4_
- `subscribe()` --calls--> `rate_limited()`  [EXTRACTED]
  api/app.py → api/app.py  _Bridges community 6 → community 4_
- `book_page()` --calls--> `capture()`  [EXTRACTED]
  build.py → build.py  _Bridges community 2 → community 1_
- `curated_page()` --calls--> `capture()`  [EXTRACTED]
  build.py → build.py  _Bridges community 2 → community 3_

## Import Cycles
- None detected.

## Communities (8 total, 2 thin omitted)

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

### Community 4 - "app.py"
Cohesion: 0.50
Nodes (3): client_ip(), Turbo History email capture.  Deliberately small: one endpoint, one SQLite file,, subscribe()

### Community 5 - "db"
Cohesion: 0.50
Nodes (4): count(), db(), export(), CSV export, ready to paste into MailerLite when there are enough to bother.

## Knowledge Gaps
- **1 isolated node(s):** `deploy.sh script`
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `curated_page()` connect `curated_page` to `build.py`, `esc`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Why does `capture()` connect `esc` to `build.py`, `book_page`, `curated_page`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `blurb_html()` connect `book_page` to `build.py`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **What connects `deploy.sh script` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._