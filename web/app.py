"""FastAPI endpoints and local SPA hosting; no learning write operations."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .data import PROJECT_ROOT, Snapshot
from .models import ErrorResponse, MapResponse, NodeResponse, UnitResponse


def create_app(*, demo: bool = False) -> FastAPI:
    app = FastAPI(
        title="Learning Knowledge Map",
        version="0.1.0",
        description="Local read-only repository viewer. Every request rereads files; no Progress or Frontier rebuilds.",
    )

    @app.middleware("http")
    async def no_cache(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    errors = {503: {"model": ErrorResponse, "description": "Graph cannot be read or validated"}}

    @app.get("/api/map", response_model=MapResponse, responses=errors)
    def knowledge_map():
        """Read the graph; an uninitialized repository returns empty lists."""
        snapshot = Snapshot(demo)
        return {**snapshot.envelope(), "nodes": list(snapshot.nodes.values()), "edges": snapshot.edges}

    details_errors = {**errors, 404: {"model": ErrorResponse, "description": "Unknown repository ID"}}

    @app.get("/api/nodes/{node_id}", response_model=NodeResponse, responses=details_errors)
    def node_details(node_id: str):
        """Read direct relationships only, without descendant aggregation."""
        return Snapshot(demo).node_details(node_id)

    @app.get("/api/units/{unit_id}", response_model=UnitResponse, responses=details_errors)
    def unit_details(unit_id: str):
        """Read initialized or planned Unit; missing Progress stays null."""
        return Snapshot(demo).unit_details(unit_id)

    distribution = PROJECT_ROOT / "web/dist"
    if (distribution / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=distribution / "assets"), name="assets")

    def spa():
        index = distribution / "index.html"
        if not index.is_file():
            raise HTTPException(503, "Сначала выполните npm --prefix web run build")
        return FileResponse(index)

    # Explicit browser routes keep unknown API paths and unsupported methods
    # from falling through to an HTML response.
    app.add_api_route("/", spa, include_in_schema=False)
    app.add_api_route("/nodes/{node_id}", lambda node_id: spa(), include_in_schema=False)
    app.add_api_route("/units/{unit_id}", lambda unit_id: spa(), include_in_schema=False)
    return app
