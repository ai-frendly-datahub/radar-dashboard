#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


LAYER_ORDER = ["official", "operational", "market", "community", "attention"]
GROUP_FIELDS = [
    "repo_class",
    "primary_motion",
    "governance_profile",
    "evidence_strategy",
    "readiness_status",
    "source_status",
]
SHARED_CLASSES = {"shared-core", "shared-template", "shared-dashboard"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an integrated taxonomy and data-quality analysis dataset"
    )
    parser.add_argument("--workspace-root", type=Path, default=None)
    parser.add_argument("--projects-json", type=Path, default=None)
    parser.add_argument("--summary-json", type=Path, default=None)
    parser.add_argument("--classification-json", type=Path, default=None)
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


def number(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def integer(value: Any, default: int = 0) -> int:
    return int(number(value, float(default)))


def percent(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return round((numerator / denominator) * 100, 1)


def quality_counts(summary: dict[str, Any]) -> dict[str, int]:
    stale = integer(summary.get("stale_sources"))
    missing = integer(summary.get("missing_sources"))
    unknown = integer(summary.get("unknown_event_date_sources"))
    disabled = integer(summary.get("skipped_disabled_sources"))
    errors = integer(summary.get("collection_error_count"))
    total = integer(summary.get("total_sources"))
    enabled = integer(summary.get("enabled_sources"))
    if not enabled and total:
        enabled = max(0, total - disabled)
    tracked = integer(summary.get("tracked_sources"))
    if tracked > enabled:
        enabled = tracked
    fresh = integer(summary.get("fresh_sources"))
    not_tracked = integer(summary.get("not_tracked_sources"))
    return {
        "collection_errors": errors,
        "freshness_gap": stale + missing + unknown,
        "stale_sources": stale,
        "missing_sources": missing,
        "unknown_event_date_sources": unknown,
        "disabled_sources": disabled,
        "total_sources": total,
        "enabled_sources": enabled,
        "tracked_sources": tracked,
        "fresh_sources": fresh,
        "not_tracked_sources": not_tracked,
    }


def risk_score(row: dict[str, Any]) -> int:
    score = 0.0
    score += row["collection_errors"] * 6.5
    score += row["freshness_gap"] * 1.6
    score += row["disabled_sources"] * 0.9
    if row["missing_layers"]:
        score += 12 + (len(row["missing_layers"]) * 3)
    if row["readiness_status"] == "watch":
        score += 10
    match_rate = row.get("match_rate")
    if isinstance(match_rate, (int, float)) and row["article_count"] > 0:
        score += max(0.0, 100.0 - float(match_rate)) * 0.45
    tracked_coverage = row.get("tracked_coverage_pct")
    if isinstance(tracked_coverage, (int, float)):
        score += max(0.0, 40.0 - float(tracked_coverage)) * 0.3
    if row["article_count"] == 0 and row["repo_class"] not in SHARED_CLASSES:
        score += 8
    return min(100, round(score))


def operational_priority(row: dict[str, Any]) -> str:
    match_rate = row.get("match_rate")
    low_match = isinstance(match_rate, (int, float)) and row["article_count"] > 0 and match_rate < 90
    if row["collection_errors"] >= 4 or (row["collection_errors"] > 0 and row["freshness_gap"] >= 5) or low_match:
        return "P0"
    if row["freshness_gap"] >= 5 or row["disabled_sources"] >= 10:
        return "P1"
    if row["freshness_gap"] > 0 or row["disabled_sources"] > 0 or row["collection_errors"] > 0:
        return "P2"
    return "P3"


def taxonomy_priority(row: dict[str, Any]) -> str:
    if row["repo_class"] in SHARED_CLASSES:
        return "shared"
    if row["missing_layers"] or row["readiness_status"] == "watch":
        return "T1"
    if row["source_status"] and row["source_status"] != "강함":
        return "T2"
    return "T3"


def focus_area(row: dict[str, Any]) -> str:
    if row["operational_priority"] == "P0":
        return "collector_repair"
    if row["freshness_gap"] >= 5:
        return "freshness_coverage"
    if row["disabled_sources"] >= 5:
        return "disabled_source_governance"
    if row["taxonomy_priority"] in {"T1", "T2"}:
        return "taxonomy_enrichment"
    if row["tracked_coverage_pct"] is not None and row["tracked_coverage_pct"] < 40:
        return "tracked_source_coverage"
    return "stable"


def build_repo_rows(
    projects: list[dict[str, Any]],
    taxonomy_rows: list[dict[str, Any]],
    disabled_classification: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    taxonomy_by_repo = {row["repo"]: row for row in taxonomy_rows}
    disabled_by_repo = (disabled_classification or {}).get("by_repo") or {}
    rows: list[dict[str, Any]] = []
    for project in projects:
        repo = project["repo"]
        taxonomy = taxonomy_by_repo.get(repo, {})
        quality = quality_counts(project.get("quality_summary") or {})
        tracked = quality["tracked_sources"]
        enabled = quality["enabled_sources"]
        fresh = quality["fresh_sources"]
        article_count = integer(project.get("article_count"))
        matched_count = integer(project.get("matched_count"))
        match_rate = project.get("match_rate")
        repo_disabled = disabled_by_repo.get(repo) or {}
        row = {
            "repo": repo,
            "display_name": taxonomy.get("display_name") or project.get("display_name") or repo,
            "category": project.get("category"),
            "repo_class": taxonomy.get("repo_class") or "unclassified",
            "domain_family": taxonomy.get("domain_family") or project.get("category") or "unclassified",
            "primary_motion": taxonomy.get("primary_motion") or "unclassified",
            "governance_profile": taxonomy.get("governance_profile") or "unclassified",
            "evidence_strategy": taxonomy.get("evidence_strategy") or "unclassified",
            "readiness_status": taxonomy.get("readiness_status") or "unclassified",
            "source_status": taxonomy.get("source_status") or "unclassified",
            "available_layers": list(taxonomy.get("available_layers") or []),
            "missing_layers": list(taxonomy.get("missing_layers") or []),
            "layer_counts": taxonomy.get("layer_counts") or {},
            "next_step": taxonomy.get("next_step"),
            "quality_score": integer(taxonomy.get("quality_score")),
            "taxonomy_priority_score": integer(taxonomy.get("priority_score")),
            "article_count": article_count,
            "matched_count": matched_count,
            "match_rate": match_rate if isinstance(match_rate, (int, float)) else None,
            "source_count": integer(project.get("source_count")),
            "dashboard_status": project.get("status"),
            "last_updated": project.get("last_updated"),
            "warnings": list(project.get("warnings") or []),
            "warning_count": len(project.get("warnings") or []),
            "quality_origin": project.get("quality_origin"),
            "data_origin": project.get("data_origin"),
            "tracked_coverage_pct": percent(tracked, enabled) if enabled else None,
            "freshness_coverage_pct": percent(fresh, tracked) if tracked else None,
            "disabled_source_classification": dict(repo_disabled.get("bucket_counts") or {}),
            "disabled_source_classification_total": int(
                repo_disabled.get("total_disabled_count", 0) or 0
            ),
            **quality,
        }
        row["operational_priority"] = operational_priority(row)
        row["taxonomy_priority"] = taxonomy_priority(row)
        row["risk_score"] = risk_score(row)
        row["focus_area"] = focus_area(row)
        rows.append(row)
    return rows


def aggregate_rows(rows: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "key": "",
            "project_count": 0,
            "article_count": 0,
            "matched_count": 0,
            "collection_errors": 0,
            "freshness_gap": 0,
            "disabled_sources": 0,
            "risk_score_total": 0,
            "watch_count": 0,
            "p0_count": 0,
            "t1_count": 0,
            "missing_layer_counts": Counter(),
        }
    )
    for row in rows:
        key = str(row.get(field) or "unclassified")
        bucket = grouped[key]
        bucket["key"] = key
        bucket["project_count"] += 1
        bucket["article_count"] += row["article_count"]
        bucket["matched_count"] += row["matched_count"]
        bucket["collection_errors"] += row["collection_errors"]
        bucket["freshness_gap"] += row["freshness_gap"]
        bucket["disabled_sources"] += row["disabled_sources"]
        bucket["risk_score_total"] += row["risk_score"]
        if row["readiness_status"] == "watch":
            bucket["watch_count"] += 1
        if row["operational_priority"] == "P0":
            bucket["p0_count"] += 1
        if row["taxonomy_priority"] == "T1":
            bucket["t1_count"] += 1
        for layer in row["missing_layers"]:
            bucket["missing_layer_counts"][layer] += 1

    output = []
    for bucket in grouped.values():
        project_count = bucket["project_count"]
        output.append(
            {
                "key": bucket["key"],
                "project_count": project_count,
                "article_count": bucket["article_count"],
                "matched_count": bucket["matched_count"],
                "match_rate": percent(bucket["matched_count"], bucket["article_count"]),
                "collection_errors": bucket["collection_errors"],
                "freshness_gap": bucket["freshness_gap"],
                "disabled_sources": bucket["disabled_sources"],
                "average_risk_score": round(bucket["risk_score_total"] / project_count, 1)
                if project_count
                else 0,
                "watch_count": bucket["watch_count"],
                "p0_count": bucket["p0_count"],
                "t1_count": bucket["t1_count"],
                "missing_layer_counts": dict(bucket["missing_layer_counts"]),
            }
        )
    return sorted(output, key=lambda item: (-item["average_risk_score"], item["key"]))


def count_values(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(Counter(str(row.get(field) or "unclassified") for row in rows))


def build_payload(
    workspace_root: Path,
    projects_path: Path,
    summary_path: Path,
    classification_path: Path,
    disabled_classification_path: Path | None = None,
) -> dict[str, Any]:
    projects_payload = json.loads(projects_path.read_text(encoding="utf-8"))
    dashboard_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    classification_payload = json.loads(classification_path.read_text(encoding="utf-8"))
    disabled_classification = (
        _load_disabled_classification(disabled_classification_path)
        if disabled_classification_path
        else {"summary": {}, "by_repo": {}}
    )
    projects = list(projects_payload.get("projects") or [])
    taxonomy_rows = list(classification_payload.get("repos") or [])
    rows = build_repo_rows(projects, taxonomy_rows, disabled_classification)
    rows.sort(key=lambda row: (-row["risk_score"], row["repo"]))

    taxonomy_by_repo = {row["repo"]: row for row in taxonomy_rows}
    unmatched_projects = [row["repo"] for row in rows if row["repo"] not in taxonomy_by_repo]
    shared_taxonomy_repos = [
        row["repo"] for row in taxonomy_rows if row.get("repo_class") in SHARED_CLASSES
    ]
    layer_gap_counts = Counter()
    for row in rows:
        for layer in row["missing_layers"]:
            layer_gap_counts[layer] += 1

    summary = {
        "project_count": len(rows),
        "taxonomy_repo_count": len(taxonomy_rows),
        "shared_taxonomy_repo_count": len(shared_taxonomy_repos),
        "unmatched_project_count": len(unmatched_projects),
        "unmatched_projects": unmatched_projects,
        "article_total": sum(row["article_count"] for row in rows),
        "matched_total": sum(row["matched_count"] for row in rows),
        "overall_match_rate": percent(
            sum(row["matched_count"] for row in rows),
            sum(row["article_count"] for row in rows),
        ),
        "dashboard_generated_at": dashboard_summary.get("generated_at"),
        "project_data_generated_at": projects_payload.get("generated_at"),
        "classification_generated_at": classification_payload.get("generated_at"),
        "collection_error_total": sum(row["collection_errors"] for row in rows),
        "freshness_gap_total": sum(row["freshness_gap"] for row in rows),
        "disabled_source_total": sum(row["disabled_sources"] for row in rows),
        "disabled_source_classification_summary": dict(
            disabled_classification.get("summary") or {}
        ),
        "repos_with_errors": sum(1 for row in rows if row["collection_errors"] > 0),
        "repos_with_freshness_gap": sum(1 for row in rows if row["freshness_gap"] > 0),
        "repos_with_disabled_sources": sum(1 for row in rows if row["disabled_sources"] > 0),
        "average_risk_score": round(sum(row["risk_score"] for row in rows) / len(rows), 1)
        if rows
        else 0,
        "operational_priority_counts": count_values(rows, "operational_priority"),
        "taxonomy_priority_counts": count_values(rows, "taxonomy_priority"),
        "focus_area_counts": count_values(rows, "focus_area"),
        "primary_motion_counts": count_values(rows, "primary_motion"),
        "governance_counts": count_values(rows, "governance_profile"),
        "readiness_counts": count_values(rows, "readiness_status"),
        "source_status_counts": count_values(rows, "source_status"),
        "evidence_strategy_counts": count_values(rows, "evidence_strategy"),
        "layer_gap_counts": dict(layer_gap_counts),
        "top_risk_repos": [row["repo"] for row in rows[:10]],
        "top_taxonomy_repos": [
            row["repo"]
            for row in sorted(
                rows,
                key=lambda item: (
                    item["taxonomy_priority"] != "T1",
                    -item["taxonomy_priority_score"],
                    -len(item["missing_layers"]),
                    item["repo"],
                ),
            )[:12]
        ],
    }

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "workspace_root": str(workspace_root),
        "inputs": {
            "projects_json": str(projects_path.relative_to(workspace_root)),
            "summary_json": str(summary_path.relative_to(workspace_root)),
            "classification_json": str(classification_path.relative_to(workspace_root)),
        },
        "summary": summary,
        "groups": {field: aggregate_rows(rows, field) for field in GROUP_FIELDS},
        "repos": rows,
    }


def main() -> int:
    args = parse_args()
    script_path = Path(__file__).resolve()
    workspace_root = args.workspace_root.resolve() if args.workspace_root else script_path.parents[2]
    dashboard_data = workspace_root / "radar-dashboard" / "data"
    projects_path = args.projects_json.resolve() if args.projects_json else dashboard_data / "projects.json"
    summary_path = args.summary_json.resolve() if args.summary_json else dashboard_data / "summary.json"
    classification_path = (
        args.classification_json.resolve()
        if args.classification_json
        else dashboard_data / "classification.json"
    )
    disabled_classification_path = (
        args.disabled_classification_json.resolve()
        if args.disabled_classification_json
        else workspace_root
        / "radar-analysis"
        / "data"
        / "exports"
        / "disabled_source_classification.json"
    )
    output = args.output.resolve() if args.output else dashboard_data / "taxonomy-analysis.json"

    payload = build_payload(
        workspace_root,
        projects_path,
        summary_path,
        classification_path,
        disabled_classification_path,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
