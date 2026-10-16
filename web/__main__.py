"""Run from the repository root: python -m web [--demo]."""

import argparse

import uvicorn

from .app import create_app


def main():
    parser = argparse.ArgumentParser(description="Локальная карта знаний (только чтение)")
    parser.add_argument("--demo", action="store_true", help="читать только web/fixtures/demo/")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    print(f"Knowledge Map: http://127.0.0.1:{args.port} ({'DEMO' if args.demo else 'repository'})")
    uvicorn.run(create_app(demo=args.demo), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
