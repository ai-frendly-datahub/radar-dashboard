from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _load_module(name: str):
    path = SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_json(name: str) -> dict:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def _assert_html_contract(html: str, surface: str, page: str) -> None:
    header = "\n".join(html.splitlines()[:3])
    assert 'data-visual-system="radar-unified-v2"' in header
    assert f'data-visual-surface="{surface}"' in header
    assert f'data-visual-page="{page}"' in header


def test_dashboard_index_and_redirect_emit_portfolio_contract() -> None:
    module = _load_module("build_dashboard_html")

    html = module.build_index_html(
        _load_json("projects.json"),
        _load_json("summary.json"),
        _load_json("classification.json"),
        _load_json("data-quality.json"),
        _load_json("daily-collection.json"),
        _load_json("taxonomy-analysis.json"),
        _load_json("storage-facts.json"),
        _load_json("event-model-rollout.json"),
    )
    redirect_html = module.build_redirect_html()

    _assert_html_contract(html, "portfolio", "portfolio-index")
    _assert_html_contract(redirect_html, "portfolio", "dashboard-redirect")
    assert "Storage Footprint" in html
    assert "Event Model Coverage" in html


def test_data_quality_dashboard_renders_disabled_bucket_panel() -> None:
    module = _load_module("build_data_quality_dashboard")
    html = module.build_html(_load_json("data-quality.json"))
    assert "Disabled Source Classification" in html
    assert "Awaiting URL replacement" in html


def test_classification_dashboard_emits_portfolio_contract() -> None:
    module = _load_module("build_classification_dashboard")
    html = module.build_html(_load_json("classification.json"))
    _assert_html_contract(html, "portfolio", "classification-audit")


def test_data_quality_dashboard_emits_portfolio_contract() -> None:
    module = _load_module("build_data_quality_dashboard")
    html = module.build_html(_load_json("data-quality.json"))
    _assert_html_contract(html, "portfolio", "data-quality-audit")


def test_daily_collection_dashboard_emits_portfolio_contract() -> None:
    module = _load_module("build_daily_collection_dashboard")
    html = module.build_html(_load_json("daily-collection.json"))
    _assert_html_contract(html, "portfolio", "daily-collection")


def test_taxonomy_analysis_dashboard_emits_portfolio_contract() -> None:
    module = _load_module("build_taxonomy_analysis_dashboard")
    html = module.build_html(_load_json("taxonomy-analysis.json"))
    _assert_html_contract(html, "portfolio", "taxonomy-analysis")


def test_storage_dashboard_emits_portfolio_contract() -> None:
    module = _load_module("build_storage_dashboard")
    html = module.build_html(_load_json("storage-facts.json"))
    _assert_html_contract(html, "portfolio", "storage-footprint")
    assert "Repo Storage Matrix" in html


def test_event_model_dashboard_emits_portfolio_contract() -> None:
    module = _load_module("build_event_model_dashboard")
    html = module.build_html(_load_json("event-model-rollout.json"))
    _assert_html_contract(html, "portfolio", "event-model-coverage")
    assert "Event Model Rollup" in html
    assert "Repo × Event Model Coverage" in html
