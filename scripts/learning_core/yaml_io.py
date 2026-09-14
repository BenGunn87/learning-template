"""Small, safe YAML helpers shared by the Stage 1 scripts."""

from __future__ import annotations

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

