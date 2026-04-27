#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Copy workspace data quality audit into radar-dashboard data")
    parser.add_argument("--workspace-root", type=Path, default=None)
    parser.add_argument("--data-quality-json", type=Path, default=None)
    parser.add_argument("--disabled-classification-json", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def _load_disabled_classification(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"summary": {}, "by_repo": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"summary": {}, "by_repo": {}}
    rows = payload.get("rows") or []
    by_repo: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        repo = str(row.get("repo") or "")
        if not repo:
            continue
        by_repo[repo] = {
            "total_disabled_count": int(row.get("total_disabled_count", 0) or 0),
            "bucket_counts": dict(row.get("bucket_counts") or {}),
        }
    return {"summary": dict(payload.get("summary") or {}), "by_repo": by_repo}


def _enrich_with_disabled_classification(
    payload: dict[str, Any], classification: dict[str, Any]
) -> dict[str, Any]:
    by_repo = classification.get("by_repo") or {}
    summary = payload.get("summary")
    if isinstance(summary, dict):
        summary["disabled_source_classification_summary"] = dict(
            classification.get("summary") or {}
        )
    repos = payload.get("repos")
    if isinstance(repos, list):
        for repo_row in repos:
            if not isinstance(repo_row, dict):
                continue
            repo_name = str(repo_row.get("repo") or "")
            repo_buckets = by_repo.get(repo_name) or {}
            repo_row["disabled_source_classification"] = dict(
                repo_buckets.get("bucket_counts") or {}
            )
            repo_row["disabled_source_classification_total"] = int(
                repo_buckets.get("total_disabled_count", 0) or 0
            )
    return payload


def main() -> int:
    args = parse_args()
    script_path = Path(__file__).resolve()
    workspace_root = args.workspace_root.resolve() if args.workspace_root else script_path.parents[2]
    data_quality_json = (
        args.data_quality_json.resolve()
        if args.data_quality_json
        else workspace_root / "docs" / "harness" / "data-quality.json"
    )
    disabled_classification_json = (
        args.disabled_classification_json.resolve()
        if args.disabled_classification_json
        else workspace_root
        / "radar-analysis"
        / "data"
        / "exports"
        / "disabled_source_classification.json"
    )
    output = (
        args.output.resolve()
        if args.output
        else workspace_root / "radar-dashboard" / "data" / "data-quality.json"
    )

    payload = json.loads(data_quality_json.read_text(encoding="utf-8"))
    classification = _load_disabled_classification(disabled_classification_json)
    payload = _enrich_with_disabled_classification(payload, classification)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
