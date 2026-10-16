"""Export the API contract without starting a server or reading learning data."""

import json
from pathlib import Path

from .app import create_app


if __name__ == "__main__":
    destination = Path(__file__).with_name("openapi.json")
    destination.write_text(
        json.dumps(create_app().openapi(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Exported {destination}")
