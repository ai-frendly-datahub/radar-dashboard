#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


INFRA_REPOS = {"radar-core", "Radar-Template", "radar-dashboard"}
RADAR_DATA_RE = re.compile(r"const\s+RADAR_DATA\s*=\s*(\{.*?\})\s*;", re.DOTALL)
JS_KEY_RE = re.compile(r'([{\[,]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:)')
TREND_UPDATED_RE = re.compile(r"최종 업데이트:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})")
TREND_GENERATED_RE = re.compile(r"자동 생성됨\s*[·|]\s*([0-9:\-\s]{16})")
TREND_LINK_RE = re.compile(r'<a href="([^"]+)" class="report-link">')
SUMMARY_DATE_TOKEN_RE = re.compile(r"([0-9]{8})")


@dataclass(slots=True)
class QualityInfo:
    origin: str | None
    summary: dict[str, Any]
    warnings: list[str]


@dataclass(slots=True)
class ProjectRecord:
    repo: str
    display_name: str
    category: str | None
    status: str
    pipeline_kind: str
    has_summary_json: bool
    article_count: int | None
    matched_count: int | None
    source_count: int | None
    match_rate: float | None
    last_updated: str | None
    generated_at: str | None
    total_reports: int | None
    report_index_path: str | None
    latest_report_path: str | None
    data_origin: str | None
    quality_origin: str | None
    quality_summary: dict[str, Any]
    top_entities: list[dict[str, Any]]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo": self.repo,
            "display_name": self.display_name,
            "category": self.category,
            "status": self.status,
            "pipeline_kind": self.pipeline_kind,
            "has_summary_json": self.has_summary_json,
            "article_count": self.article_count,
            "matched_count": self.matched_count,
            "source_count": self.source_count,
            "match_rate": self.match_rate,
            "last_updated": self.last_updated,
            "generated_at": self.generated_at,
            "total_reports": self.total_reports,
            "report_index_path": self.report_index_path,
            "latest_report_path": self.latest_report_path,
            "data_origin": self.data_origin,
            "quality_origin": self.quality_origin,
            "quality_summary": self.quality_summary,
            "top_entities": self.top_entities,
            "warnings": self.warnings,
        }


def discover_radar_repos(workspace_root: Path) -> list[Path]:
    repos: list[Path] = []
    for child in workspace_root.iterdir():
        if not child.is_dir() or child.name in INFRA_REPOS:
            continue
        if not (child / ".git").exists():
            continue
        if child.name.endswith("Radar"):
            repos.append(child)
    return sorted(repos, key=lambda p: p.name.lower())


def display_name_from_repo(repo_name: str) -> str:
    if repo_name.endswith("Radar"):
        return repo_name[:-5]
    return repo_name


def relative_path(path: Path, start: Path) -> str:
    return str(path.relative_to(start)).replace("\\", "/")


def latest_summary_file(repo_path: Path) -> Path | None:
    summary_files = list((repo_path / "reports").glob("*_summary.json"))
    if not summary_files:
        return None
    return max(summary_files, key=_summary_sort_key)


def latest_quality_file(repo_path: Path) -> Path | None:
    quality_files = list((repo_path / "reports").glob("*_quality.json"))
    if not quality_files:
        return None
    return max(quality_files, key=lambda path: (path.stat().st_mtime, path.name))


def load_quality_info(repo_path: Path, workspace_root: Path) -> QualityInfo:
    quality_path = latest_quality_file(repo_path)
    if quality_path is None:
        return QualityInfo(origin=None, summary={}, warnings=[])

    try:
        with quality_path.open(encoding="utf-8") as fp:
            data = json.load(fp)
    except (OSError, json.JSONDecodeError):
        return QualityInfo(
            origin=relative_path(quality_path, workspace_root),
            summary={},
            warnings=["quality report exists but could not be parsed"],
        )

    summary = data.get("summary")
    summary_map = summary if isinstance(summary, dict) else {}
    return QualityInfo(
        origin=relative_path(quality_path, workspace_root),
        summary=summary_map,
        warnings=_quality_warnings(summary_map),
    )


def parse_summary_repo(repo_path: Path, workspace_root: Path) -> ProjectRecord | None:
    summary_path = latest_summary_file(repo_path)
    if summary_path is None:
        return None

    with summary_path.open(encoding="utf-8") as fp:
        data = json.load(fp)

    article_count = _to_int(data.get("article_count"))
    matched_count = _to_int(data.get("matched_count"))
    source_count = _to_int(data.get("source_count"))
    match_rate = None
    if article_count and matched_count is not None:
        match_rate = round((matched_count / article_count) * 100, 1)
    elif article_count == 0 and matched_count == 0:
        match_rate = 0.0

    top_entities = data.get("top_entities")
    if not isinstance(top_entities, list):
        top_entities = []

    repo_name = repo_path.name
    report_index = repo_path / "reports" / "index.html"
    quality = load_quality_info(repo_path, workspace_root)
    warnings = _summary_warnings(data) + quality.warnings
    return ProjectRecord(
        repo=repo_name,
        display_name=display_name_from_repo(repo_name),
        category=_to_str(data.get("category")),
        status="active",
        pipeline_kind="summary_json",
        has_summary_json=True,
        article_count=article_count,
        matched_count=matched_count,
        source_count=source_count,
        match_rate=match_rate,
        last_updated=_to_str(data.get("date")),
        generated_at=_to_str(data.get("generated_at")),
        total_reports=len(list((repo_path / "reports").glob("*_summary.json"))),
        report_index_path=relative_path(report_index, workspace_root) if report_index.exists() else None,
        latest_report_path=relative_path(report_index, workspace_root) if report_index.exists() else None,
        data_origin=relative_path(summary_path, workspace_root),
        quality_origin=quality.origin,
        quality_summary=quality.summary,
        top_entities=top_entities[:5],
        warnings=warnings,
    )


def _summary_warnings(data: dict[str, Any]) -> list[str]:
    raw_warnings = data.get("warnings")
    if not isinstance(raw_warnings, list):
        return []
    return [str(warning) for warning in raw_warnings if str(warning).strip()]


def _quality_warnings(summary: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    error_count = _to_int(summary.get("collection_error_count")) or 0
    stale_sources = _to_int(summary.get("stale_sources")) or 0
    missing_sources = _to_int(summary.get("missing_sources")) or 0
    unknown_event_date_sources = _to_int(summary.get("unknown_event_date_sources")) or 0
    disabled_sources = _to_int(summary.get("skipped_disabled_sources")) or 0

    if error_count:
        warnings.append(f"quality report has {error_count} collection error(s)")
    if stale_sources or missing_sources or unknown_event_date_sources:
        warnings.append(
            "quality freshness gaps: "
            f"stale={stale_sources}, "
            f"missing={missing_sources}, "
            f"unknown_event_date={unknown_event_date_sources}"
        )
    if disabled_sources:
        warnings.append(f"quality report has {disabled_sources} disabled source(s)")
    return warnings


def parse_radar_data_index(repo_path: Path, workspace_root: Path) -> ProjectRecord | None:
    index_path = repo_path / "reports" / "index.html"
    if not index_path.exists():
        return None

    html = index_path.read_text(encoding="utf-8")
    match = RADAR_DATA_RE.search(html)
    if not match:
        return None

    payload = _load_js_object_literal(match.group(1))
    reports = payload.get("reports") if isinstance(payload, dict) else None
    summaries = payload.get("summaries") if isinstance(payload, dict) else None

    latest_report_path = None
    total_reports = len(reports) if isinstance(reports, list) else None
    last_updated = None
    if isinstance(reports, list) and reports:
        latest_report = None
        dated_reports = [item for item in reports if isinstance(item, dict) and item.get("date")]
        if dated_reports:
            latest_report = max(dated_reports, key=lambda item: str(item.get("date")))
            last_updated = _to_str(latest_report.get("date"))
        else:
            latest_report = reports[-1] if isinstance(reports[-1], dict) else None
        if isinstance(latest_report, dict):
            filename = _to_str(latest_report.get("filename"))
            if filename:
                latest_report_path = relative_path(index_path.parent / filename, workspace_root)

    summary_entry: dict[str, Any] | None = None
    if isinstance(summaries, list) and summaries:
        dated_summaries = [item for item in summaries if isinstance(item, dict) and item.get("date")]
        if dated_summaries:
            summary_entry = max(dated_summaries, key=lambda item: str(item.get("date")))
        elif isinstance(summaries[-1], dict):
            summary_entry = summaries[-1]

    article_count = _to_int(summary_entry.get("article_count")) if summary_entry else None
    matched_count = _to_int(summary_entry.get("matched_count")) if summary_entry else None
    source_count = _to_int(summary_entry.get("source_count")) if summary_entry else None
    match_rate = None
    if article_count and matched_count is not None:
        match_rate = round((matched_count / article_count) * 100, 1)
    elif article_count == 0 and matched_count == 0 and source_count == 0:
        match_rate = 0.0

    warnings = [
        "summary JSON not found; metrics derived from reports/index.html fallback",
    ]
    if summary_entry and article_count == 0 and matched_count == 0 and source_count == 0:
        warnings.append("fallback summary reports zero metrics; verify upstream pipeline output")

    repo_name = repo_path.name
    quality = load_quality_info(repo_path, workspace_root)
    warnings.extend(quality.warnings)
    return ProjectRecord(
        repo=repo_name,
        display_name=display_name_from_repo(repo_name),
        category=_to_str(summary_entry.get("category")) if summary_entry else None,
        status="partial",
        pipeline_kind="html_index_radar_data",
        has_summary_json=False,
        article_count=article_count,
        matched_count=matched_count,
        source_count=source_count,
        match_rate=match_rate,
        last_updated=last_updated,
        generated_at=_to_str(payload.get("generatedAt")) if isinstance(payload, dict) else None,
        total_reports=total_reports,
        report_index_path=relative_path(index_path, workspace_root),
        latest_report_path=latest_report_path,
        data_origin=relative_path(index_path, workspace_root),
        quality_origin=quality.origin,
        quality_summary=quality.summary,
        top_entities=(summary_entry.get("top_entities") if isinstance(summary_entry, dict) else [])[:5]
        if isinstance(summary_entry, dict)
        else [],
        warnings=warnings,
    )


def parse_minimal_index(repo_path: Path, workspace_root: Path) -> ProjectRecord | None:
    index_path = repo_path / "reports" / "index.html"
    if not index_path.exists():
        return None

    html = index_path.read_text(encoding="utf-8")
    updated_match = TREND_UPDATED_RE.search(html)
    generated_match = TREND_GENERATED_RE.search(html)
    link_match = TREND_LINK_RE.search(html)

    latest_report_path = None
    if link_match:
        latest_report_path = relative_path(index_path.parent / link_match.group(1), workspace_root)

    repo_name = repo_path.name
    quality = load_quality_info(repo_path, workspace_root)
    return ProjectRecord(
        repo=repo_name,
        display_name=display_name_from_repo(repo_name),
        category=display_name_from_repo(repo_name).lower(),
        status="partial",
        pipeline_kind="html_index_minimal",
        has_summary_json=False,
        article_count=None,
        matched_count=None,
        source_count=None,
        match_rate=None,
        last_updated=updated_match.group(1) if updated_match else None,
        generated_at=_normalize_generated_at(generated_match.group(1)) if generated_match else None,
        total_reports=1 if latest_report_path else None,
        report_index_path=relative_path(index_path, workspace_root),
        latest_report_path=latest_report_path,
        data_origin=relative_path(index_path, workspace_root),
        quality_origin=quality.origin,
        quality_summary=quality.summary,
        top_entities=[],
        warnings=[
            "summary JSON not found; only minimal metadata extracted from reports/index.html",
        ]
        + quality.warnings,
    )


def collect_project_record(repo_path: Path, workspace_root: Path) -> ProjectRecord:
    for parser in (parse_summary_repo, parse_radar_data_index, parse_minimal_index):
        result = parser(repo_path, workspace_root)
        if result is not None:
            return result

    repo_name = repo_path.name
    quality = load_quality_info(repo_path, workspace_root)
    return ProjectRecord(
        repo=repo_name,
        display_name=display_name_from_repo(repo_name),
        category=None,
        status="missing_reports",
        pipeline_kind="none",
        has_summary_json=False,
        article_count=None,
        matched_count=None,
        source_count=None,
        match_rate=None,
        last_updated=None,
        generated_at=None,
        total_reports=None,
        report_index_path=None,
        latest_report_path=None,
        data_origin=None,
        quality_origin=quality.origin,
        quality_summary=quality.summary,
        top_entities=[],
        warnings=["no dashboard-readable report artifacts found"] + quality.warnings,
    )


def build_summary(records: list[ProjectRecord], workspace_root: Path) -> dict[str, Any]:
    full_metrics = [r for r in records if r.pipeline_kind == "summary_json"]
    partial_metrics = [r for r in records if r.status == "partial"]
    article_total = sum(r.article_count or 0 for r in full_metrics)
    matched_total = sum(r.matched_count or 0 for r in full_metrics)
    overall_match_rate = round((matched_total / article_total) * 100, 1) if article_total else None

    warnings: list[str] = []
    for record in records:
        for warning in record.warnings:
            warnings.append(f"{record.repo}: {warning}")

    latest_updates = [
        {
            "repo": record.repo,
            "display_name": record.display_name,
            "last_updated": record.last_updated,
            "status": record.status,
        }
        for record in sorted(
            [r for r in records if r.last_updated],
            key=lambda item: str(item.last_updated),
            reverse=True,
        )[:10]
    ]

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "workspace_root": str(workspace_root),
        "projects_scanned": len(records),
        "active_projects": len([r for r in records if r.status in {"active", "partial"}]),
        "projects_with_full_metrics": len(full_metrics),
        "projects_with_partial_metrics": len(partial_metrics),
        "projects_missing_metrics": len([r for r in records if r.status == "missing_reports"]),
        "article_total": article_total,
        "matched_total": matched_total,
        "overall_match_rate": overall_match_rate,
        "latest_updates": latest_updates,
        "warnings": warnings,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build radar-dashboard JSON dataset from sibling Radar repos")
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=None,
        help="Workspace root containing sibling Radar repositories",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory where projects.json and summary.json will be written",
    )
    return parser.parse_args()


def resolve_workspace_root(script_path: Path, explicit_workspace_root: Path | None) -> Path:
    if explicit_workspace_root is not None:
        return explicit_workspace_root.resolve()
    return script_path.resolve().parents[2]


def resolve_output_dir(script_path: Path, explicit_output_dir: Path | None) -> Path:
    if explicit_output_dir is not None:
        return explicit_output_dir.resolve()
    return script_path.resolve().parents[1] / "data"


def _to_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _to_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _normalize_generated_at(value: str) -> str:
    return value.replace(" ", "T")


def _load_js_object_literal(source: str) -> dict[str, Any]:
    normalized = JS_KEY_RE.sub(r'\1"\2"\3', source)
    return json.loads(normalized)


def _summary_sort_key(path: Path) -> tuple[str, str]:
    match = SUMMARY_DATE_TOKEN_RE.search(path.stem)
    token = match.group(1) if match else ""
    return (token, path.name)


def main() -> int:
    args = parse_args()
    script_path = Path(__file__)
    workspace_root = resolve_workspace_root(script_path, args.workspace_root)
    output_dir = resolve_output_dir(script_path, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    records = [collect_project_record(repo_path, workspace_root) for repo_path in discover_radar_repos(workspace_root)]
    records.sort(key=lambda record: record.repo.lower())

    projects_payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "workspace_root": str(workspace_root),
        "projects": [record.to_dict() for record in records],
    }
    summary_payload = build_summary(records, workspace_root)

    (output_dir / "projects.json").write_text(
        json.dumps(projects_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {output_dir / 'projects.json'}")
    print(f"Wrote {output_dir / 'summary.json'}")
    print(
        "Scanned "
        f"{summary_payload['projects_scanned']} projects "
        f"({summary_payload['projects_with_full_metrics']} full, "
        f"{summary_payload['projects_with_partial_metrics']} partial)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
