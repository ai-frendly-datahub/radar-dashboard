#!/usr/bin/env python3
"""Build a data-quality panel dataset for the dashboard.

Reads ``data/projects.json`` and the per-repo ``reports/*_summary.json``
artifacts already produced by each Radar to compute a small 5-dimension
quality scorecard per repo (and a workspace-wide rollup):

- completeness : matched_count / article_count
- timeliness   : 1 - min(staleness_days / 14, 1)
- volume       : log10(article_count + 1) scaled to 0..1
- diversity    : source_count / target_source_count (capped at 1.0)
- consistency  : 1 - abs(article_count - rolling_median) / rolling_median

The output JSON is consumed by ``data-quality.html`` (existing) and the new
``build_data_quality_panel_html.py`` builder.
"""

from __future__ import annotations

import json
import math
import statistics
from datetime import UTC, datetime
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_ROOT = WORKSPACE_ROOT / "radar-dashboard"
DATA_DIR = DASHBOARD_ROOT / "data"
OUT_PATH = DATA_DIR / "data-quality-panel.json"

TARGET_SOURCES_PER_REPO = 8


def _load_projects() -> list[dict]:
    with (DATA_DIR / "projects.json").open() as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        data = data.get("projects", [])
    return list(data)


def _staleness_days(generated_at: str | None) -> float:
    if not generated_at:
        return float("inf")
    try:
        dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError:
        return float("inf")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    delta = (datetime.now(UTC) - dt).total_seconds() / 86400.0
    return max(0.0, delta)


def _completeness(p: dict) -> float:
    article = int(p.get("article_count", 0) or 0)
    matched = int(p.get("matched_count", 0) or 0)
    if article <= 0:
        return 0.0
    return min(1.0, matched / article)


def _volume(p: dict) -> float:
    article = int(p.get("article_count", 0) or 0)
    # log scale: 1 article -> ~0, 100 -> 1.0
    return min(1.0, math.log10(article + 1) / 2.0)


def _diversity(p: dict) -> float:
    sources = int(p.get("source_count", 0) or 0)
    return min(1.0, sources / TARGET_SOURCES_PER_REPO)


def _consistency(p: dict, median: float) -> float:
    article = int(p.get("article_count", 0) or 0)
    if median <= 0:
        return 0.0
    return max(0.0, 1.0 - abs(article - median) / median)


def _timeliness(p: dict) -> float:
    stale = _staleness_days(p.get("generated_at"))
    if stale == float("inf"):
        return 0.0
    return max(0.0, 1.0 - min(stale, 14.0) / 14.0)


def build_panel(projects: list[dict]) -> dict:
    article_counts = [int(p.get("article_count", 0) or 0) for p in projects if p.get("article_count")]
    median = statistics.median(article_counts) if article_counts else 0.0

    rows: list[dict] = []
    for p in projects:
        completeness = _completeness(p)
        timeliness = _timeliness(p)
        volume = _volume(p)
        diversity = _diversity(p)
        consistency = _consistency(p, median)
        score = round(
            100 * (
                0.30 * completeness
                + 0.20 * timeliness
                + 0.15 * volume
                + 0.15 * diversity
                + 0.20 * consistency
            ),
            1,
        )
        rows.append(
            {
                "repo": p.get("repo"),
                "article_count": int(p.get("article_count", 0) or 0),
                "matched_count": int(p.get("matched_count", 0) or 0),
                "source_count": int(p.get("source_count", 0) or 0),
                "match_rate": float(p.get("match_rate", 0) or 0),
                "completeness": round(completeness, 4),
                "timeliness": round(timeliness, 4),
                "volume": round(volume, 4),
                "diversity": round(diversity, 4),
                "consistency": round(consistency, 4),
                "score": score,
            }
        )

    rows.sort(key=lambda r: r["score"], reverse=True)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "median_article_count": median,
        "target_sources_per_repo": TARGET_SOURCES_PER_REPO,
        "rows": rows,
        "summary": {
            "repo_count": len(rows),
            "avg_score": round(sum(r["score"] for r in rows) / max(1, len(rows)), 2),
            "p50_score": (
                statistics.median([r["score"] for r in rows]) if rows else 0
            ),
            "low_score_count": sum(1 for r in rows if r["score"] < 70),
        },
    }


def main() -> None:
    projects = _load_projects()
    payload = build_panel(projects)
    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Wrote {OUT_PATH}  repos={payload['summary']['repo_count']} avg_score={payload['summary']['avg_score']}")


if __name__ == "__main__":
    main()
