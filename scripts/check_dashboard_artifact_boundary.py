#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable


ALLOWED_DATA_JSON = {
    "classification.json",
    "daily-collection.json",
    "data-quality-panel.json",
    "data-quality.json",
    "event-model-rollout.json",
    "projects.json",
    "source-reliability.json",
    "storage-facts.json",
    "summary.json",
    "taxonomy-analysis.json",
}

ALLOWED_HTML = {
    "classification.html",
    "daily-collection.html",
    "dashboard.html",
    "data-quality-panel.html",
    "data-quality.html",
    "event-model.html",
    "index.html",
    "source-reliability.html",
    "storage.html",
    "taxonomy-analysis.html",
}

LEGACY_STATIC_ASSETS = {
    "entity_distribution.png",
    "overview_dashboard.png",
    "source_analysis.png",
    "trend_analysis.png",
}


@dataclass(frozen=True)
class HtmlArtifact:
    output_name: str
    renderer: str
    payload_names: tuple[str, ...]


HTML_ARTIFACTS = (
    HtmlArtifact("index.html", "build_dashboard_html", ("projects.json", "summary.json")),
    HtmlArtifact("dashboard.html", "build_dashboard_html", ()),
    HtmlArtifact("classification.html", "build_classification_dashboard", ("classification.json",)),
    HtmlArtifact("data-quality.html", "build_data_quality_dashboard", ("data-quality.json",)),
    HtmlArtifact("daily-collection.html", "build_daily_collection_dashboard", ("daily-collection.json",)),
    HtmlArtifact("taxonomy-analysis.html", "build_taxonomy_analysis_dashboard", ("taxonomy-analysis.json",)),
    HtmlArtifact("storage.html", "build_storage_dashboard", ("storage-facts.json",)),
    HtmlArtifact("event-model.html", "build_event_model_dashboard", ("event-model-rollout.json", "storage-facts.json")),
    HtmlArtifact("data-quality-panel.html", "build_data_quality_panel_html", ("data-quality-panel.json",)),
    HtmlArtifact("source-reliability.html", "build_source_reliability_html", ("source-reliability.json",)),
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(scripts_dir: Path, module_name: str) -> Any:
    module_path = scripts_dir / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load dashboard renderer: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def tracked_paths(repo_root: Path, runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> set[str]:
    result = runner(
        ["git", "-C", str(repo_root), "ls-files", "-z"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return {path for path in result.stdout.split("\0") if path}


def boundary_rows(paths: set[str]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    failures: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    data_json = {Path(path).name for path in paths if path.startswith("data/") and path.endswith(".json")}
    html = {Path(path).name for path in paths if "/" not in path and path.endswith(".html")}
    png = {Path(path).name for path in paths if "/" not in path and path.endswith(".png")}

    for name in sorted(ALLOWED_DATA_JSON - data_json):
        failures.append({"code": "missing_committed_dashboard_dataset", "path": f"data/{name}"})
    for name in sorted(data_json - ALLOWED_DATA_JSON):
        failures.append({"code": "unexpected_committed_dashboard_dataset", "path": f"data/{name}"})

    for name in sorted(ALLOWED_HTML - html):
        failures.append({"code": "missing_committed_dashboard_html", "path": name})
    for name in sorted(html - ALLOWED_HTML):
        failures.append({"code": "unexpected_committed_dashboard_html", "path": name})

    for name in sorted(png - LEGACY_STATIC_ASSETS):
        failures.append({"code": "unexpected_committed_dashboard_png", "path": name})
    for name in sorted(png & LEGACY_STATIC_ASSETS):
        warnings.append({"code": "legacy_committed_dashboard_png", "path": name})

    return failures, warnings


def expected_html(repo_root: Path, artifact: HtmlArtifact) -> str:
    data_dir = repo_root / "data"
    scripts_dir = repo_root / "scripts"
    module = load_module(scripts_dir, artifact.renderer)

    if artifact.output_name == "index.html":
        return module.build_index_html(
            load_json(data_dir / "projects.json"),
            load_json(data_dir / "summary.json"),
            load_json(data_dir / "classification.json"),
            load_json(data_dir / "data-quality.json"),
            load_json(data_dir / "daily-collection.json"),
            load_json(data_dir / "taxonomy-analysis.json"),
            load_json(data_dir / "storage-facts.json"),
            load_json(data_dir / "event-model-rollout.json"),
        )
    if artifact.output_name == "dashboard.html":
        return module.build_redirect_html()
    if artifact.output_name == "event-model.html":
        return module.build_html(
            load_json(data_dir / "event-model-rollout.json"),
            load_json(data_dir / "storage-facts.json"),
        )
    if artifact.renderer in {"build_data_quality_panel_html", "build_source_reliability_html"}:
        return module.render(load_json(data_dir / artifact.payload_names[0]))
    return module.build_html(load_json(data_dir / artifact.payload_names[0]))


def reproducibility_rows(repo_root: Path) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for artifact in HTML_ARTIFACTS:
        output_path = repo_root / artifact.output_name
        if not output_path.is_file():
            failures.append({"code": "missing_dashboard_html_file", "path": artifact.output_name})
            continue
        expected = expected_html(repo_root, artifact)
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            failures.append({"code": "dashboard_html_not_reproducible", "path": artifact.output_name})
    return failures


def build_report(repo_root: Path) -> dict[str, Any]:
    paths = tracked_paths(repo_root)
    failures, warnings = boundary_rows(paths)
    repro_failures = reproducibility_rows(repo_root)
    failures.extend(repro_failures)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "repo_root": str(repo_root),
        "summary": {
            "status": "pass" if not failures else "fail",
            "failure_count": len(failures),
            "warning_count": len(warnings),
            "tracked_dataset_count": len(ALLOWED_DATA_JSON),
            "tracked_html_count": len(ALLOWED_HTML),
            "html_reproducibility_checked": len(HTML_ARTIFACTS),
        },
        "policy": {
            "allowed_data_json": sorted(ALLOWED_DATA_JSON),
            "allowed_html": sorted(ALLOWED_HTML),
            "legacy_static_assets": sorted(LEGACY_STATIC_ASSETS),
        },
        "failures": failures,
        "warnings": warnings,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Dashboard Artifact Boundary",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Status: **{summary['status']}**",
        f"- Failures: `{summary['failure_count']}`",
        f"- Warnings: `{summary['warning_count']}`",
        f"- HTML reproducibility checked: `{summary['html_reproducibility_checked']}`",
        "",
    ]
    if report["failures"]:
        lines.extend(["## Failures", ""])
        for row in report["failures"]:
            lines.append(f"- `{row['path']}`: {row['code']}")
        lines.append("")
    if report["warnings"]:
        lines.extend(["## Warnings", ""])
        for row in report["warnings"]:
            lines.append(f"- `{row['path']}`: {row['code']}")
        lines.append("")
    lines.extend(["## Allowed Data JSON", ""])
    for name in report["policy"]["allowed_data_json"]:
        lines.append(f"- `data/{name}`")
    lines.extend(["", "## Allowed HTML", ""])
    for name in report["policy"]["allowed_html"]:
        lines.append(f"- `{name}`")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate radar-dashboard committed generated artifact boundary.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--md-output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args.repo_root.resolve())
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.md_output:
        args.md_output.parent.mkdir(parents=True, exist_ok=True)
        args.md_output.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
