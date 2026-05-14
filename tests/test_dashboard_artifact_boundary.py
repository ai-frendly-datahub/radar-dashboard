from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_dashboard_artifact_boundary.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_dashboard_artifact_boundary", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_current_dashboard_artifact_boundary_passes() -> None:
    checker = _load_checker()
    report = checker.build_report(REPO_ROOT)

    assert report["summary"]["status"] == "pass"
    assert report["summary"]["failure_count"] == 0
    assert report["summary"]["tracked_dataset_count"] == 10
    assert report["summary"]["tracked_html_count"] == 10
    assert report["summary"]["html_reproducibility_checked"] == 10


def test_boundary_rows_flag_unexpected_committed_generated_files() -> None:
    checker = _load_checker()
    paths = {f"data/{name}" for name in checker.ALLOWED_DATA_JSON}
    paths.update(checker.ALLOWED_HTML)
    paths.update({"data/experimental.json", "experimental.html", "experimental.png"})

    failures, warnings = checker.boundary_rows(paths)

    assert warnings == []
    assert {"code": "unexpected_committed_dashboard_dataset", "path": "data/experimental.json"} in failures
    assert {"code": "unexpected_committed_dashboard_html", "path": "experimental.html"} in failures
    assert {"code": "unexpected_committed_dashboard_png", "path": "experimental.png"} in failures


def test_boundary_rows_treat_legacy_png_as_warning() -> None:
    checker = _load_checker()
    paths = {f"data/{name}" for name in checker.ALLOWED_DATA_JSON}
    paths.update(checker.ALLOWED_HTML)
    paths.add("overview_dashboard.png")

    failures, warnings = checker.boundary_rows(paths)

    assert failures == []
    assert warnings == [{"code": "legacy_committed_dashboard_png", "path": "overview_dashboard.png"}]
