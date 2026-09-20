"""Small, safe YAML helpers shared by deterministic repository operations."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import yaml


class YamlFileError(ValueError):
    """Raised when a repository YAML file cannot be read."""


class StringDatesSafeLoader(yaml.SafeLoader):
    """SafeLoader variant that keeps ISO-looking dates as strings.

    Repository schemas describe dates as strings. PyYAML otherwise resolves an
    unquoted value such as 2026-09-14 to ``datetime.date`` before validation.
    """


StringDatesSafeLoader.yaml_implicit_resolvers = {
    key: [
        (tag, regexp)
        for tag, regexp in resolvers
        if tag != "tag:yaml.org,2002:timestamp"
    ]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def load_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as stream:
            return yaml.load(stream, Loader=StringDatesSafeLoader)
    except FileNotFoundError as exc:
        raise YamlFileError(f"missing file: {path}") from exc
    except (OSError, yaml.YAMLError) as exc:
        raise YamlFileError(f"cannot read {path}: {exc}") from exc


def dump_yaml(data: Any) -> str:
    return yaml.safe_dump(
        data,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )


def load_yaml_text(text: str) -> Any:
    """Load YAML supplied as text while preserving date-looking strings."""

    try:
        return yaml.load(text, Loader=StringDatesSafeLoader)
    except yaml.YAMLError as exc:
        raise YamlFileError(f"cannot parse YAML: {exc}") from exc


def _write_temporary_yaml(path: Path, data: Any) -> Path:
    """Write and fsync a complete YAML document beside its destination."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(dump_yaml(data))
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return temporary


def create_yaml(path: Path, data: Any) -> None:
    """Atomically create a YAML file, refusing to replace existing data."""

    temporary = _write_temporary_yaml(path, data)
    try:
        os.link(temporary, path)
    except FileExistsError:
        raise YamlFileError(f"refusing to overwrite existing file: {path}") from None
    except OSError as exc:
        raise YamlFileError(f"cannot create {path}: {exc}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def create_text(path: Path, content: str) -> None:
    """Atomically create a UTF-8 text file, refusing to replace existing data."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            raise YamlFileError(f"refusing to overwrite existing file: {path}") from None
        except OSError as exc:
            raise YamlFileError(f"cannot create {path}: {exc}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def replace_yaml(path: Path, data: Any) -> None:
    """Atomically replace a derived document or a validated mutable state file."""

    temporary = _write_temporary_yaml(path, data)
    try:
        os.replace(temporary, path)
    except OSError as exc:
        raise YamlFileError(f"cannot replace {path}: {exc}") from exc
    finally:
        temporary.unlink(missing_ok=True)
