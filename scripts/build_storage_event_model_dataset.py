#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy radar-analysis storage_facts and event_model_rollout exports into radar-dashboard data"
    )
    parser.add_argument("--workspace-root", type=Path, default=None)
    parser.add_argument("--storage-facts-json", type=Path, default=None)
    parser.add_argument("--event-model-rollout-json", type=Path, default=None)
    parser.add_argument("--storage-output", type=Path, default=None)
    parser.add_argument("--event-model-output", type=Path, default=None)
    return parser.parse_args()


def copy_payload(source: Path, destination: Path) -> None:
    payload = json.loads(source.read_text(encoding="utf-8"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {destination}")


def main() -> int:
    args = parse_args()
    script_path = Path(__file__).resolve()
    workspace_root = args.workspace_root.resolve() if args.workspace_root else script_path.parents[2]
    analysis_exports = workspace_root / "radar-analysis" / "data" / "exports"
    dashboard_data = workspace_root / "radar-dashboard" / "data"

    storage_source = (
        args.storage_facts_json.resolve()
        if args.storage_facts_json
        else analysis_exports / "storage_facts.json"
    )
    event_source = (
        args.event_model_rollout_json.resolve()
        if args.event_model_rollout_json
        else analysis_exports / "event_model_rollout.json"
    )
    storage_destination = (
        args.storage_output.resolve()
        if args.storage_output
        else dashboard_data / "storage-facts.json"
    )
    event_destination = (
        args.event_model_output.resolve()
        if args.event_model_output
        else dashboard_data / "event-model-rollout.json"
    )

    copy_payload(storage_source, storage_destination)
    copy_payload(event_source, event_destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
