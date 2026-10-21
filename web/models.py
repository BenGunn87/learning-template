"""Read-only API contract; FastAPI generates /openapi.json from these models."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class Node(BaseModel):
    id: str
    title: str
    type: Literal["area", "topic", "concept"]
    summary: str | None = None
    status: Literal["active", "deprecated"] = "active"


class Edge(BaseModel):
    source: str
    target: str
    type: Literal["part-of", "prerequisite", "related"]


class Mastery(BaseModel):
    recall: Literal["failed", "hard", "good", "easy"] | None = None
    understanding: Literal["failed", "hard", "good", "easy"] | None = None
    application: Literal["failed", "hard", "good", "easy"] | None = None


class Review(BaseModel):
    last: date | None = None
    due: date | None = None
    interval_days: int | None = None
    repetitions: int | None = None


class Progress(BaseModel):
    status: Literal["learning", "practice", "verified"]
    mastery: Mastery = Field(default_factory=Mastery)
    attempts: int | None = None
    last_attempt: datetime | None = None
    review: Review | None = None
    review_overdue_days: int | None = Field(
        default=None, description="Days since Review became due, from the engine's due-review list; null when not due"
    )


class Gap(BaseModel):
    id: str
    node: str
    dimension: Literal["recall", "understanding", "application"]
    status: Literal["detected", "confirmed"]
    scope: str
    routing_impact: str


class Unit(BaseModel):
    id: str
    title: str
    goal: str | None = None
    nodes: list[str]
    kind: Literal["initialized", "planned"]
    in_frontier: bool
    progress: Progress | None = None


class Envelope(BaseModel):
    mode: Literal["repository", "demo"]
    repository_state: Literal["uninitialized", "partial", "initialized"]
    warnings: list[str] = Field(default_factory=list)


class MapResponse(Envelope):
    nodes: list[Node]
    edges: list[Edge]


class NodeResponse(Envelope):
    node: Node
    parents: list[Node]
    children: list[Node]
    related_nodes: list[Node]
    edges: list[Edge]
    units: list[Unit]
    gaps: list[Gap]


class UnitResponse(Envelope):
    unit: Unit
    nodes: list[Node]
    gaps: list[Gap]


class ErrorResponse(BaseModel):
    detail: str
