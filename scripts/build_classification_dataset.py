#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Copy workspace taxonomy audit into radar-dashboard data")
    parser.add_argument("--workspace-root", type=Path, default=None)
    parser.add_argument("--taxonomy-json", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    script_path = Path(__file__).resolve()
    workspace_root = args.workspace_root.resolve() if args.workspace_root else script_path.parents[2]
    taxonomy_json = (
        args.taxonomy_json.resolve()
        if args.taxonomy_json
        else workspace_root / "docs" / "harness" / "repo-taxonomy.json"
    )
    output = (
        args.output.resolve()
        if args.output
        else workspace_root / "radar-dashboard" / "data" / "classification.json"
    )

    payload = json.loads(taxonomy_json.read_text(encoding="utf-8"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
