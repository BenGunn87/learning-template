"""Opaque, editable Markdown for a course's reusable working knowledge."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from .issues import Issue
from .remediation import RemediationRepositoryMixin
from .yaml_io import YamlFileError, create_text


class ReferenceRepositoryMixin(RemediationRepositoryMixin):
    """Manage opaque files and new Reference metadata; Markdown meaning belongs to AI."""

    def create_evidence(self, data: Any) -> Path:
        # Reading historical permission-only metadata remains valid. New writes
        # must explicitly distinguish permission from actual consultation.
        policies = data.get("reference") if isinstance(data, dict) else None
        if isinstance(policies, list):
            for policy in policies:
                if isinstance(policy, dict) and "used" not in policy:
                    raise ValueError("new Evidence Reference metadata requires used for every dimension")
        return super().create_evidence(data)

    def _reference_path(self, relative: str) -> Path:
        if not isinstance(relative, str) or "\\" in relative or any(ord(c) < 32 for c in relative):
            raise ValueError("invalid Reference path")
        parts = relative.split("/")
        if len(parts) < 2 or parts[0] != "reference" or any(part in {"", ".", ".."} for part in parts):
            raise ValueError("Reference paths must stay inside reference/")
        path = self.root.joinpath(*parts)
        if path.suffix != ".md":
            raise ValueError("Reference files must be Markdown (.md)")
        current = self.root
        for part in parts:
            current = current / part
            if current.is_symlink():
                raise ValueError("Reference paths must not contain symlinks")
        if not path.resolve().is_relative_to(self.root / "reference"):
            raise ValueError("Reference paths must stay inside reference/")
        return path

    @staticmethod
    def _read_reference_text(path: Path) -> str:
        try:
            if not path.is_file():
                raise ValueError(f"Reference path is not a readable regular file: {path}")
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ValueError(f"cannot read Reference file {path}: {exc}") from exc

    @staticmethod
    def _check_reference_content(content: str) -> None:
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Reference content must not be empty")
        try:
            content.encode("utf-8")
        except UnicodeError as exc:
            raise ValueError("Reference content must be valid UTF-8") from exc

    def ensure_reference(self) -> Path:
        index = self._reference_path("reference/index.md")
        try:
            index.parent.mkdir(parents=True, exist_ok=True)
            if not index.exists():
                try:
                    create_text(index, "# Reference\n")
                except YamlFileError:
                    if not index.is_file():
                        raise
            self._read_reference_text(index)
        except OSError as exc:
            raise ValueError(f"cannot initialize Reference: {exc}") from exc
        return index

    def list_reference_files(self) -> list[str]:
        self.ensure_reference()
        self._raise_issues(self.validate_reference())
        return sorted(path.relative_to(self.root).as_posix() for path in self.path("reference").rglob("*.md"))

    def read_reference(self, relative: str = "reference/index.md") -> str:
        path = self._reference_path(relative)
        self.ensure_reference()
        return self._read_reference_text(path)

    def create_reference(self, relative: str, content: str) -> Path:
        path = self._reference_path(relative)
        self._check_reference_content(content)
        if relative != "reference/index.md":
            self.ensure_reference()
        try:
            create_text(path, content)
        except OSError as exc:
            raise ValueError(f"cannot create Reference {relative}: {exc}") from exc
        return path

    def update_reference(self, relative: str, content: str, expected_content: str) -> Path:
        path = self._reference_path(relative)
        self._check_reference_content(content)
        self.ensure_reference()
        if self._read_reference_text(path) != expected_content:
            raise ValueError("Reference changed since it was read; read it again before updating")
        temporary = None
        try:
            descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
            temporary = Path(name)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            # Check immediately before replacement, after preparing the new file.
            path = self._reference_path(relative)
            if self._read_reference_text(path) != expected_content:
                raise ValueError("Reference changed since it was read; read it again before updating")
            os.replace(temporary, path)
        except OSError as exc:
            raise ValueError(f"cannot update Reference {relative}: {exc}") from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return path

    def validate_reference(self) -> list[Issue]:
        """Read-only validation; absent Reference is valid and remains absent."""
        directory = self.path("reference")
        if not directory.exists() and not directory.is_symlink():
            return []
        if directory.is_symlink() or not directory.is_dir():
            return [Issue("reference", "Reference must be a directory, not a symlink")]
        issues = []
        if not (directory / "index.md").exists():
            issues.append(Issue("reference/index.md", "Reference index is missing"))
        for path in sorted(directory.rglob("*")):
            relative = path.relative_to(self.root).as_posix()
            if path.is_symlink():
                issues.append(Issue(relative, "Reference paths must not contain symlinks"))
            elif path.suffix == ".md":
                try:
                    self._read_reference_text(self._reference_path(relative))
                except ValueError as exc:
                    issues.append(Issue(relative, str(exc)))
        return issues

    @staticmethod
    def validate_reference_permissions(permissions: Any, relative: str, location: str) -> list[Issue]:
        """Schemas check types; prevent conflicting policies for one dimension."""
        if not isinstance(permissions, list):
            return []
        issues = []
        seen = set()
        for index, policy in enumerate(permissions):
            dimension = policy.get("dimension") if isinstance(policy, dict) else None
            if not isinstance(dimension, str):
                continue
            if dimension in seen:
                issues.append(Issue(relative, "duplicate Reference dimension", f"{location}[{index}].dimension"))
            seen.add(dimension)
        return issues
