from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _load_module():
    path = SCRIPTS_DIR / "build_data_quality_panel_dataset.py"
    spec = importlib.util.spec_from_file_location("build_data_quality_panel_dataset", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_repo_family_classification() -> None:
    mod = _load_module()
    assert mod._repo_family("ArtRadar") == "standard"
    assert mod._repo_family("KoreanNLPMCPRadar") == "mcp"
    assert mod._repo_family("HomeRadar") == "dict_pattern"
    assert mod._repo_family("PriceRadar") == "dict_pattern"
    assert mod._repo_family("CommerceRadar") == "non_standard"
    assert mod._repo_family("") == "standard"


def test_consistency_full_credit_within_tolerance_band() -> None:
    mod = _load_module()
    # Within 2x of family median -> capped at 1.0
    assert mod._consistency({"article_count": 6}, 6.0) == 1.0
    assert mod._consistency({"article_count": 12}, 6.0) == 1.0
    assert mod._consistency({"article_count": 3}, 6.0) == 1.0
    assert mod._consistency({"article_count": 200}, 173.0) == 1.0


def test_consistency_proportional_outside_band() -> None:
    mod = _load_module()
    # 2 vs median 6 -> ratio=0.333 -> 0.667
    assert mod._consistency({"article_count": 2}, 6.0) == 0.6667
    # 13 vs median 6 -> ratio=0.461 -> 0.923
    assert mod._consistency({"article_count": 13}, 6.0) == 0.9231


def test_consistency_handles_zero_inputs() -> None:
    mod = _load_module()
    assert mod._consistency({"article_count": 0}, 6.0) == 0.0
    assert mod._consistency({"article_count": 6}, 0.0) == 0.0


def test_build_panel_uses_family_medians_not_global_median() -> None:
    mod = _load_module()
    projects = [
        {"repo": "ArtRadar", "article_count": 200, "matched_count": 200, "source_count": 8, "match_rate": 100.0},
        {"repo": "BookRadar", "article_count": 173, "matched_count": 173, "source_count": 8, "match_rate": 100.0},
        {"repo": "FoodRadar", "article_count": 150, "matched_count": 150, "source_count": 8, "match_rate": 100.0},
        {"repo": "TravelMCPRadar", "article_count": 6, "matched_count": 6, "source_count": 1, "match_rate": 100.0},
        {"repo": "WeatherMCPRadar", "article_count": 6, "matched_count": 6, "source_count": 1, "match_rate": 100.0},
        {"repo": "PublicDataMCPRadar", "article_count": 8, "matched_count": 8, "source_count": 1, "match_rate": 100.0},
    ]
    panel = mod.build_panel(projects)
    medians = panel["family_median_article_counts"]
    assert medians["standard"] == 173.0
    assert medians["mcp"] == 6.0

    rows = {r["repo"]: r for r in panel["rows"]}
    # MCPRadar consistency should be 1.0 (within family band), not penalized by 173-median.
    assert rows["TravelMCPRadar"]["consistency"] == 1.0
    assert rows["WeatherMCPRadar"]["consistency"] == 1.0
    # Standard repos also pass when near their family median.
    assert rows["BookRadar"]["consistency"] == 1.0
