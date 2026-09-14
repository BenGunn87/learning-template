"""Validation issue shared by repository operation modules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Issue:
    file: str
    message: str
    path: str = ""

    def render(self) -> str:
        location = f" at {self.path}" if self.path else ""
        return f"{self.file}{location}: {self.message}"
