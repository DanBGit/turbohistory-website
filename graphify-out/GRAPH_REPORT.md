# Graph Report - turbohistory-website  (2026-07-20)

## Corpus Check
- 6 files · ~202,773 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 33 nodes · 60 edges · 7 communities (4 shown, 3 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ffdbf72a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- build.py
- book_page
- esc
- app.py
- db
- rate_limited
- deploy.sh

## God Nodes (most connected - your core abstractions)
1. `main()` - 8 edges
2. `esc()` - 7 edges
3. `book_page()` - 7 edges
4. `curated_page()` - 7 edges
5. `capture()` - 6 edges
6. `shell()` - 6 edges
7. `collection_line()` - 5 edges
8. `index_page()` - 5 edges
9. `db()` - 5 edges
10. `subscribe()` - 4 edges

## Surprising Connections (you probably didn't know these)
- `privacy_page()` --calls--> `shell()`  [EXTRACTED]
  build.py → build.py  _Bridges community 2 → community 0_
- `book_page()` --calls--> `blurb_html()`  [EXTRACTED]
  build.py → build.py  _Bridges community 1 → community 2_
- `db()` --references--> `Connection`  [EXTRACTED]
  api/app.py →   _Bridges community 5 → community 6_
- `subscribe()` --calls--> `db()`  [EXTRACTED]
  api/app.py → api/app.py  _Bridges community 5 → community 4_
- `subscribe()` --calls--> `rate_limited()`  [EXTRACTED]
  api/app.py → api/app.py  _Bridges community 6 → community 4_

## Import Cycles
- None detected.

## Communities (7 total, 3 thin omitted)

### Community 0 - "build.py"
Cohesion: 0.43
Nodes (6): build_related(), load_books(), main(), make_thumbs(), _overlap(), privacy_page()

### Community 2 - "esc"
Cohesion: 0.38
Nodes (10): book_page(), capture(), collection_line(), curated_page(), esc(), index_page(), Email capture. Honest hook: the books really are free most weekends., Small 'Part of' line under the book title. (+2 more)

### Community 4 - "app.py"
Cohesion: 0.50
Nodes (3): client_ip(), Turbo History email capture.  Deliberately small: one endpoint, one SQLite file,, subscribe()

### Community 5 - "db"
Cohesion: 0.50
Nodes (4): count(), db(), export(), CSV export, ready to paste into MailerLite when there are enough to bother.

## Knowledge Gaps
- **1 isolated node(s):** `deploy.sh script`
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `curated_page()` connect `esc` to `build.py`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Why does `capture()` connect `esc` to `build.py`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Why does `collection_line()` connect `esc` to `build.py`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **What connects `deploy.sh script` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._