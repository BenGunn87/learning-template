# Local Knowledge Map

A local, read-only viewer. All implementation and synthetic data live here;
the learning engine and real repository data are unchanged.

## Install and run

From the repository root, using Python 3.10+ and Node.js 22.12+:

```bash
make web-install
make web
```

Open <http://127.0.0.1:8000>. Stop with Ctrl+C. `web-install` creates `.venv`
if needed and installs both dependency sets. After installation, only `make web`
is needed; it builds the frontend before starting the backend.
Use `make web PORT=8001` if port 8000 is occupied.

Explicit demo mode:

```bash
make web-demo
```

The DEMO label confirms that only `web/fixtures/demo/` is being read. Ordinary
mode always reads this checkout's root, even when it is uninitialized.
The viewer does not generate or modify fixtures on startup.

For frontend development, keep the backend on port 8000 and, in another terminal:

```bash
make web-dev
```

Open the Local URL printed by Vite. It proxies `/api` to the backend.
The production build needs no Node.js process at runtime and no external fonts
or services. API docs: <http://127.0.0.1:8000/docs>.

`make web-build` only builds the frontend; `make help` lists all commands.
To start the backend directly without rebuilding, use `.venv/bin/python -m web`
(add `--demo` for fixtures). Vite's development proxy expects backend port 8000.

## Architecture and files

| Files | Purpose |
| --- | --- |
| `__main__.py`, `__init__.py`, `requirements.txt` | Python entry point and optional dependencies |
| `app.py` | Three GET API routes, no-store headers, built SPA and direct-link hosting |
| `data.py` | One new Snapshot per request using Repository graph/state, read_progress, list_gaps and existing YAML readers; no writes or derived-state rebuilds |
| `models.py`, `API.md`, `openapi.json`, `export_openapi.py` | Typed response contract and documented semantics; OpenAPI exported from FastAPI with `python -m web.export_openapi` and served at `/openapi.json` |
| `src/main.jsx` | Map, search, Node inspector, Unit page, loading/error/empty states |
| `src/hierarchy.js` | Display occurrences, source-component detection, cycle markers, expand/collapse, search paths and layout; no learning logic |
| `src/style.css` | Responsive styling and accessible focus states |
| `index.html`, `vite.config.js`, `package.json`, `package-lock.json`, `.gitignore` | Frontend entry, development proxy, reproducible installation and build configuration |
| `fixtures/demo/` | Synthetic graph and learning records, physically separate from real data |
| `fixtures/build_demo.py` | Fixture authoring via existing engine methods in an isolated temporary directory; never used by the server |

The root `Makefile` provides installation, build and launch commands.
`README.md`, `docs/SPEC.md` and `docs/web-ui.md` in the repository root describe
installation and current product requirements.

The frontend unfolds `part-of` paths into visual occurrences, each with its own
display ID; all occurrences refer to one original Node and its canonical URL.
Source strongly connected components ensure rootless cycles have an entry point.
A repeated Node in a branch becomes a non-expanding cycle link. `part-of`
arrows retain the original child → parent direction. Extra edges use one visible
occurrence per endpoint; expand the endpoints to see their connections.

Missing optional records yield warnings rather than invented values. The viewer
never rebuilds stale derived files: update them with the existing learning CLI
when needed. Each request reads files afresh; it is not an atomic snapshot across
concurrent writes to several files. Refresh again after the writer finishes.

## Manual verification

No automated tests are required to run the viewer. Use these browser scenarios:

1. Start ordinary mode in this uninitialized template. Confirm the initialization
   message and absence of DEMO or substituted fixture data.
2. Start `--demo`. Expand Data Systems → Indexing and Query Planning. B-tree
   appears under both. Both copies open `/nodes/btree` and the same details.
3. Confirm Latency is a root despite being a Concept, and has an explicit missing
   description message. Rootless Cycle A has a separate entry point. Expand its
   branch and the Hierarchy Loop under Indexing until a cycle link appears;
   it must not expand indefinitely. Cycle Leaf remains reachable.
4. Search for `B-tree`, `Cycle Leaf`, and `Isolation`. Selecting a result expands
   ancestors and centers the map. Search is case insensitive. A nonsense query
   shows no matches. Directly open and refresh `/nodes/isolation`, then use Back.
5. Show B-tree and Isolation, then enable `prerequisite`; enable `related` with
   Indexing and Query Planning visible. Check edge labels and arrows. No false
   links to collapsed ancestors should appear.
6. Select Data Systems: no Units or active Gaps are inherited from descendants.
   Select Indexing: Indexing Basics appears once as an initialized Unit, marked
   as also in Frontier. Its Progress is `practice`; its application Gap is active.
7. Open `/units/indexing-basics`, `/units/transactions-basics`, and
   `/units/cache-basics`: inspect `practice`, `learning`, and `verified` with their
   stored dimension results. Open `/units/btree-cost`: no Progress. Open
   `/units/transaction-isolation`: Planned, no Progress, linked Nodes and direct
   active Gaps. Follow Node links back to the map.
8. Open an unknown Node/Unit ID: an error with a route back to the map. Narrow the
   browser to phone width: search, controls, Node details and Unit links remain
   usable. Tab to links and expand buttons; Enter activates them.
9. Edit a demo Node's title/summary locally, refresh, and verify the new value
   without restarting the backend; restore the fixture afterwards. A malformed
   optional YAML file should show a warning while readable data remains usable.
   Unknown API IDs return 404; an invalid graph returns 503. `/docs` lists GET
   operations only. Browser requests carry no-store cache headers.
10. After the planned rebase, repeat ordinary-mode checks on `education_branch`
    with its real learning records, including direct links and Progress values.

The committed fixture's Units, Evidence, Assessments, Gaps and Progress were
created through existing Repository operations. To author a fresh fixture in an
empty fixture directory, use `python -m web.fixtures.build_demo`; this refuses to
replace differing existing records. It is not a routine startup step.

Implementation references: [React Flow providers](https://reactflow.dev/api-reference/react-flow-provider),
[FastAPI response models](https://fastapi.tiangolo.com/tutorial/response-model/),
[Vite setup](https://vite.dev/guide/).
