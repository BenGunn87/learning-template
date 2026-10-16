# Local read-only API

The contract is defined by `models.py` and the routes in `app.py`. FastAPI
generates OpenAPI at `/openapi.json` and interactive documentation at `/docs`.
The committed `openapi.json` is exported from those definitions with
`.venv/bin/python -m web.export_openapi`; regenerate it after API changes.
No authentication, writes, external services, or database are involved.

| Request | Result |
| --- | --- |
| `GET /api/map` | Repository state, mode, warnings, Graph Nodes and edges |
| `GET /api/nodes/{node_id}` | Node, immediate parents/children, directly related Nodes and edges, direct Units and active Gaps |
| `GET /api/units/{unit_id}` | Initialized or planned Unit, its Nodes, direct active Gaps |

IDs are original, stable repository IDs. Edges expose `source`, `target`,
`type`; `part-of` always points **child → parent**. Display occurrences belong
to the frontend and do not change these IDs or directions.

All successful responses include `mode` (`repository` or `demo`),
`repository_state`, and `warnings`. Each request reads files again. Responses
use `Cache-Control: no-store`; there is no server-side data cache.

An uninitialized repository returns `200` from `/api/map` with empty lists and
`repository_state: uninitialized`. Missing optional data is an empty list or
`null`, never an inferred grade. Malformed optional records are omitted with
warnings. A partial repository can still return readable graph data, with
warnings. An unreadable or invalid graph returns `503 {"detail": "…"}`.
Unknown Node/Unit IDs return `404 {"detail": "…"}`. Unsupported write methods
return `405`. No request rebuilds Progress or Frontier.

Units are deduplicated by ID: initialized records take precedence over
Frontier records, including their Node associations. A Frontier-only Unit has
`kind: planned` and `progress: null`, even if an orphaned Progress entry exists.
Initialized Units without Progress also have `progress: null`.
Only Gaps with status `detected` or `confirmed` are returned. Node relations
use exact IDs; no descendant aggregation or assessment is performed.

Example: `/api/nodes/data-systems` in demo mode has no Units or Gaps, even
though descendant Nodes have them. `/api/units/indexing-basics` is initialized
and also in Frontier; `/api/units/transaction-isolation` is planned.

Browser routes `/nodes/{node_id}` and `/units/{unit_id}` serve the SPA, including
on a direct visit or refresh. Vite development mode proxies `/api` to port 8000.
