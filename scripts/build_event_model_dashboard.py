#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from html import escape
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render event-model.html from event-model-rollout.json")
    parser.add_argument("--data-path", type=Path, default=None)
    parser.add_argument("--storage-facts-path", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def fmt_number(value: Any) -> str:
    if isinstance(value, bool):
        return "—"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.1f}"
    if value is None:
        return "—"
    return escape(str(value))


def fmt_percent(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.1f}%"
    return "—"


def stat_card(value: Any, label: str) -> str:
    return (
        "<article class=\"stat\">"
        f"<div class=\"stat__value\">{fmt_number(value)}</div>"
        f"<div class=\"stat__label\">{escape(label)}</div>"
        "</article>"
    )


def render_event_model_rows(rows: list[dict[str, Any]]) -> str:
    rendered = []
    for row in sorted(
        rows,
        key=lambda r: (
            -int(r.get("repo_count") or 0),
            -float(r.get("avg_match_rate") or 0.0),
            str(r.get("event_model_id") or ""),
        ),
    ):
        rendered.append(
            "<tr>"
            f"<td><div class=\"event-id\">{escape(str(row.get('event_model_id') or '—'))}</div>"
            f"<div class=\"event-meta\">{escape(str(row.get('event_model_namespace') or 'unknown'))}</div></td>"
            f"<td>{escape(str(row.get('coverage_source') or '—'))}</td>"
            f"<td>{fmt_number(row.get('repo_count'))}</td>"
            f"<td>{fmt_number(row.get('event_model_record_total'))}</td>"
            f"<td>{fmt_number(row.get('article_total'))}</td>"
            f"<td>{fmt_number(row.get('matched_total'))}</td>"
            f"<td>{fmt_percent(row.get('avg_match_rate'))}</td>"
            f"<td>{fmt_number(row.get('avg_tracked_sources'))}</td>"
            "</tr>"
        )
    return "\n".join(rendered)


def _coverage_bucket(ratio: float) -> str:
    if ratio >= 0.95:
        return "full"
    if ratio >= 0.7:
        return "high"
    if ratio >= 0.3:
        return "mid"
    if ratio > 0:
        return "low"
    return "empty"


def render_coverage_progression_panel(storage_rows: list[dict[str, Any]]) -> str:
    if not storage_rows:
        return ""

    progression: list[tuple[str, float, int, int, bool]] = []
    for row in storage_rows:
        ontology_rows = int(row.get("duckdb_ontology_row_count") or 0)
        event_records = int(row.get("duckdb_event_model_record_count") or 0)
        capable = bool(row.get("articles_ontology_capable"))
        if not capable and ontology_rows == 0:
            continue
        ratio = (event_records / ontology_rows) if ontology_rows else 0.0
        progression.append(
            (
                str(row.get("repo") or ""),
                ratio,
                event_records,
                ontology_rows,
                capable,
            )
        )

    progression.sort(key=lambda item: (-item[1], item[0]))
    if not progression:
        return ""

    bucket_counts: dict[str, int] = {"full": 0, "high": 0, "mid": 0, "low": 0, "empty": 0}
    for _, ratio, _, _, _ in progression:
        bucket_counts[_coverage_bucket(ratio)] += 1

    summary_html = (
        "<div class=\"coverage-summary\">"
        f"<span class=\"coverage-bucket coverage-bucket--full\">{bucket_counts['full']} at 100% (&ge; 95)</span>"
        f"<span class=\"coverage-bucket coverage-bucket--high\">{bucket_counts['high']} high (70-94)</span>"
        f"<span class=\"coverage-bucket coverage-bucket--mid\">{bucket_counts['mid']} mid (30-69)</span>"
        f"<span class=\"coverage-bucket coverage-bucket--low\">{bucket_counts['low']} low (1-29)</span>"
        f"<span class=\"coverage-bucket coverage-bucket--empty\">{bucket_counts['empty']} empty (0)</span>"
        "</div>"
    )

    rows_html: list[str] = []
    for repo, ratio, events, ontology_rows, _ in progression:
        bucket = _coverage_bucket(ratio)
        width = max(2.0, ratio * 100.0) if ratio else 2.0
        rows_html.append(
            "<div class=\"progression-row\">"
            f"<span class=\"progression-row__repo\">{escape(repo)}</span>"
            f"<div class=\"progression-row__bar progression-row__bar--{escape(bucket)}\">"
            f"<span style=\"width:{width:.1f}%\"></span></div>"
            f"<span class=\"progression-row__value\">{ratio:.1%}</span>"
            f"<span class=\"progression-row__counts\">{events:,} / {ontology_rows:,}</span>"
            "</div>"
        )

    return (
        "<section class=\"table-wrap\">"
        "<div class=\"table-header\">"
        "<h2>Event Model Coverage Progression</h2>"
        "<p>각 repo 의 DuckDB 에서 event_model_id 로 채워진 article 비율 (event_model_record_count / ontology_row_count). "
        "100% 에 가까울수록 contract 매핑이 mart 단계까지 충실히 이어진 상태입니다. "
        "non-articles schema repo 와 ontology 비어 있는 repo 는 자동 제외됩니다.</p>"
        f"{summary_html}"
        "</div>"
        "<div class=\"progression-list\">"
        f"{''.join(rows_html)}"
        "</div>"
        "</section>"
    )


def render_namespace_panel(rows: list[dict[str, Any]]) -> str:
    grouped: dict[str, dict[str, int]] = defaultdict(lambda: {"models": 0, "repos": 0, "duckdb_models": 0, "summary_models": 0})
    for row in rows:
        namespace = str(row.get("event_model_namespace") or "unknown")
        bucket = grouped[namespace]
        bucket["models"] += 1
        bucket["repos"] += int(row.get("repo_count") or 0)
        source = str(row.get("coverage_source") or "")
        if source == "duckdb_storage":
            bucket["duckdb_models"] += 1
        elif source == "summary":
            bucket["summary_models"] += 1
    if not grouped:
        return ""

    items = []
    for namespace, stats in sorted(grouped.items(), key=lambda kv: (-kv[1]["models"], kv[0])):
        items.append(
            "<tr>"
            f"<td>{escape(namespace)}</td>"
            f"<td>{fmt_number(stats['models'])}</td>"
            f"<td>{fmt_number(stats['summary_models'])}</td>"
            f"<td>{fmt_number(stats['duckdb_models'])}</td>"
            f"<td>{fmt_number(stats['repos'])}</td>"
            "</tr>"
        )
    return (
        "<section class=\"table-wrap\">"
        "<div class=\"table-header\"><h2>Namespace Coverage</h2>"
        "<p>각 namespace 가 몇 개의 event model 을 담당하는지, 그리고 그 모델이 summary ontology adoption 에서 잡혔는지 DuckDB raw payload 에서 잡혔는지 분리해 보여줍니다.</p></div>"
        "<div class=\"table-scroll\">"
        "<table>"
        "<thead><tr><th>Namespace</th><th>Models</th><th>Summary Source</th><th>DuckDB Source</th><th>Repo Coverage</th></tr></thead>"
        f"<tbody>{''.join(items)}</tbody>"
        "</table></div></section>"
    )


def render_coverage_grid(coverage_rows: list[dict[str, Any]]) -> str:
    if not coverage_rows:
        return ""
    repo_index: dict[str, dict[str, Any]] = {}
    namespaces: dict[str, set[str]] = defaultdict(set)
    cells: dict[tuple[str, str], dict[str, Any]] = {}
    for row in coverage_rows:
        repo = str(row.get("repo") or "")
        namespace = str(row.get("event_model_namespace") or "unknown")
        if not repo:
            continue
        repo_index.setdefault(
            repo,
            {
                "category": str(row.get("category") or "n/a"),
                "primary_motion": str(row.get("primary_motion") or "n/a"),
            },
        )
        namespaces[namespace].add(repo)
        cell = cells.setdefault(
            (repo, namespace),
            {
                "models": 0,
                "records": 0,
                "match_rate": None,
                "match_rate_count": 0,
                "match_rate_total": 0.0,
                "duckdb_models": 0,
                "summary_models": 0,
            },
        )
        cell["models"] += 1
        cell["records"] += int(row.get("event_model_record_count") or 0)
        match_rate = row.get("match_rate")
        if isinstance(match_rate, (int, float)):
            cell["match_rate_total"] += float(match_rate)
            cell["match_rate_count"] += 1
        ontology_source = str(row.get("ontology_source") or "")
        if ontology_source == "duckdb_storage":
            cell["duckdb_models"] += 1
        elif ontology_source == "summary":
            cell["summary_models"] += 1

    sorted_namespaces = sorted(namespaces.keys())
    sorted_repos = sorted(repo_index.keys())

    header_cells = "".join(f"<th>{escape(ns)}</th>" for ns in sorted_namespaces)
    body_rows: list[str] = []
    for repo in sorted_repos:
        meta = repo_index[repo]
        cells_html: list[str] = []
        for namespace in sorted_namespaces:
            cell = cells.get((repo, namespace))
            if not cell or cell["models"] == 0:
                cells_html.append(
                    "<td class=\"coverage-cell coverage-cell--empty\"><span class=\"muted\">·</span></td>"
                )
                continue
            avg_rate = (
                cell["match_rate_total"] / cell["match_rate_count"]
                if cell["match_rate_count"]
                else 0.0
            )
            level = "high" if avg_rate >= 95 else "mid" if avg_rate >= 80 else "low"
            duckdb_chip = (
                f"<span class=\"coverage-source coverage-source--duckdb\" title=\"duckdb-emitted models\">{cell['duckdb_models']}d</span>"
                if cell["duckdb_models"]
                else ""
            )
            summary_chip = (
                f"<span class=\"coverage-source coverage-source--summary\" title=\"summary-emitted models\">{cell['summary_models']}s</span>"
                if cell["summary_models"]
                else ""
            )
            tooltip = (
                f"{repo} · {namespace}: {cell['models']} models, "
                f"{cell['records']} records, avg match {avg_rate:.1f}%"
            )
            cells_html.append(
                f"<td class=\"coverage-cell coverage-cell--{level}\" title=\"{escape(tooltip)}\">"
                f"<div class=\"coverage-models\">{cell['models']}</div>"
                f"<div class=\"coverage-meta\">{summary_chip}{duckdb_chip}</div>"
                "</td>"
            )
        body_rows.append(
            "<tr>"
            f"<td class=\"coverage-repo\"><div class=\"repo-name\">{escape(repo)}</div>"
            f"<div class=\"repo-meta\">{escape(meta['category'])} · {escape(meta['primary_motion'])}</div></td>"
            f"{''.join(cells_html)}"
            "</tr>"
        )
    return (
        "<section class=\"table-wrap\">"
        "<div class=\"table-header\"><h2>Namespace × Repo Coverage Grid</h2>"
        "<p>각 셀은 (repo, namespace) 교차로 채워진 event model 수를 보여줍니다. 셀 색은 평균 match rate (≥95% high, ≥80% mid, 그 외 low) 이며, `s` 와 `d` 칩은 summary / duckdb_storage 어느 source 가 그 셀을 채웠는지 표시합니다. 빈 셀은 해당 repo 의 ontology 가 그 namespace 를 cover 하지 않는다는 뜻입니다.</p></div>"
        "<div class=\"table-scroll\">"
        "<table class=\"coverage-grid\">"
        f"<thead><tr><th>Repo</th>{header_cells}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table></div></section>"
    )


def render_coverage_rows(rows: list[dict[str, Any]]) -> str:
    rendered = []
    sorted_rows = sorted(
        rows,
        key=lambda r: (
            str(r.get("event_model_namespace") or ""),
            str(r.get("event_model_id") or ""),
            str(r.get("repo") or ""),
        ),
    )
    for row in sorted_rows:
        rendered.append(
            "<tr>"
            f"<td>{escape(str(row.get('event_model_id') or '—'))}</td>"
            f"<td>{escape(str(row.get('event_model_namespace') or '—'))}</td>"
            f"<td><div class=\"repo-name\">{escape(str(row.get('repo') or '—'))}</div>"
            f"<div class=\"repo-meta\">{escape(str(row.get('category') or 'n/a'))} · {escape(str(row.get('primary_motion') or 'n/a'))}</div></td>"
            f"<td>{escape(str(row.get('ontology_source') or '—'))}</td>"
            f"<td>{fmt_number(row.get('event_model_record_count'))}</td>"
            f"<td>{fmt_number(row.get('article_count'))}</td>"
            f"<td>{fmt_number(row.get('matched_count'))}</td>"
            f"<td>{fmt_percent(row.get('match_rate'))}</td>"
            f"<td>{fmt_number(row.get('gap_count'))}</td>"
            "</tr>"
        )
    return "\n".join(rendered)


def build_html(
    payload: dict[str, Any],
    storage_payload: dict[str, Any] | None = None,
) -> str:
    summary = payload.get("summary") or {}
    rows = list(payload.get("rows") or [])
    coverage_rows = list(payload.get("coverage_rows") or [])
    coverage_source_counts = summary.get("coverage_source_counts") or {}
    summary_count = coverage_source_counts.get("summary", 0)
    duckdb_count = coverage_source_counts.get("duckdb_storage", 0)

    return f"""<!DOCTYPE html>
<html lang="ko" data-visual-system="radar-unified-v2" data-visual-surface="portfolio" data-visual-page="event-model-coverage">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Workspace Event Model Coverage</title>
  <style>
    :root {{
      --bg: #f4f7fb;
      --surface: #ffffff;
      --surface-2: #eef2fa;
      --text: #131c2b;
      --muted: #5d6a82;
      --line: #d8e0ee;
      --accent: #1f5edc;
      --shadow: 0 14px 38px rgba(15, 23, 42, 0.08);
      --radius: 20px;
      --max: 1480px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--text);
      font-family: "Pretendard Variable", "Segoe UI", Arial, sans-serif;
      background: var(--bg);
    }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .page {{ max-width: var(--max); margin: 0 auto; padding: 30px 22px 56px; }}
    .hero {{
      background: linear-gradient(135deg, #1c3146, #6f3edc);
      color: #fff;
      border-radius: 28px;
      padding: 32px;
      box-shadow: var(--shadow);
    }}
    .hero h1 {{ margin: 0 0 10px; font-size: clamp(2rem, 3vw, 3rem); letter-spacing: -0.04em; }}
    .hero p {{ margin: 0; max-width: 78ch; line-height: 1.65; color: rgba(255,255,255,0.84); }}
    .hero-links {{ margin-top: 18px; display: flex; gap: 12px; flex-wrap: wrap; }}
    .hero-links a {{
      display: inline-flex; padding: 10px 14px; border-radius: 999px;
      background: rgba(255,255,255,0.16); color: #fff; font-weight: 700;
    }}
    .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px; margin-top: 22px; }}
    .stat {{
      background: rgba(255,255,255,0.14);
      border: 1px solid rgba(255,255,255,0.2);
      border-radius: 18px; padding: 16px;
    }}
    .stat__value {{ font-size: 1.9rem; font-weight: 800; letter-spacing: -0.04em; }}
    .stat__label {{ margin-top: 6px; color: rgba(255,255,255,0.75); }}
    .table-wrap {{ margin-top: 22px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; }}
    .table-header {{ padding: 22px 24px 8px; }}
    .table-header h2 {{ margin: 0 0 8px; }}
    .table-header p {{ margin: 0; color: var(--muted); line-height: 1.6; }}
    .table-scroll {{ overflow-x: auto; padding: 8px 12px 16px; }}
    table {{ width: 100%; border-collapse: collapse; min-width: 1200px; }}
    th, td {{ padding: 12px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; font-size: 0.9rem; }}
    th {{ color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em; }}
    tr:hover td {{ background: #f7faff; }}
    .event-id {{ font-weight: 700; font-family: "Source Code Pro", ui-monospace, SFMono-Regular, monospace; }}
    .event-meta {{ color: var(--muted); font-size: 0.82rem; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.04em; }}
    .repo-name {{ font-weight: 700; }}
    .repo-meta {{ color: var(--muted); font-size: 0.82rem; margin-top: 4px; }}
    .coverage-grid {{ min-width: 1100px; }}
    .coverage-grid th {{ position: sticky; top: 0; background: var(--surface); }}
    .coverage-cell {{ text-align: center; min-width: 64px; padding: 10px 6px; vertical-align: middle; }}
    .coverage-cell--empty {{ background: #fafbff; }}
    .coverage-cell--high {{ background: #d8efe1; color: #0f5b32; }}
    .coverage-cell--mid {{ background: #fff1cd; color: #5a4500; }}
    .coverage-cell--low {{ background: #fbe1dc; color: #8a2818; }}
    .progression-list {{ padding: 8px 24px 22px; display: flex; flex-direction: column; gap: 8px; }}
    .progression-row {{ display: grid; grid-template-columns: 200px 1fr 70px 130px; gap: 12px; align-items: center; }}
    .progression-row__repo {{ font-weight: 700; }}
    .progression-row__bar {{ height: 14px; background: var(--surface-2); border-radius: 999px; overflow: hidden; }}
    .progression-row__bar span {{ display: block; height: 100%; border-radius: 999px; }}
    .progression-row__bar--full span {{ background: linear-gradient(90deg, #0f5b32, #1e8a52); }}
    .progression-row__bar--high span {{ background: linear-gradient(90deg, #1e8a52, #6dbb84); }}
    .progression-row__bar--mid span {{ background: linear-gradient(90deg, #c98a00, #f3c357); }}
    .progression-row__bar--low span {{ background: linear-gradient(90deg, #b23a2c, #d96f5b); }}
    .progression-row__bar--empty span {{ background: #e0e4f0; }}
    .progression-row__value {{ text-align: right; font-weight: 800; }}
    .progression-row__counts {{ color: var(--muted); font-size: 0.85rem; font-family: ui-monospace, monospace; }}
    .coverage-summary {{ margin-top: 14px; display: flex; flex-wrap: wrap; gap: 8px; }}
    .coverage-bucket {{ display: inline-flex; padding: 4px 10px; border-radius: 999px; font-size: 0.78rem; font-weight: 700; }}
    .coverage-bucket--full {{ background: #d8efe1; color: #0f5b32; }}
    .coverage-bucket--high {{ background: #e8f3eb; color: #1e8a52; }}
    .coverage-bucket--mid {{ background: #fff1cd; color: #5a4500; }}
    .coverage-bucket--low {{ background: #fbe1dc; color: #8a2818; }}
    .coverage-bucket--empty {{ background: #eef0f7; color: #4a5468; }}
    @media (max-width: 980px) {{ .progression-row {{ grid-template-columns: 130px 1fr 60px; }} .progression-row__counts {{ display: none; }} }}
    .coverage-cell .coverage-models {{ font-weight: 800; font-size: 0.95rem; }}
    .coverage-cell .coverage-meta {{ font-size: 0.7rem; margin-top: 3px; display: flex; justify-content: center; gap: 4px; }}
    .coverage-source {{ display: inline-flex; padding: 1px 5px; border-radius: 999px; font-weight: 700; }}
    .coverage-source--summary {{ background: rgba(31, 94, 220, 0.14); color: #1f5edc; }}
    .coverage-source--duckdb {{ background: rgba(111, 62, 220, 0.18); color: #4a1eaf; }}
    .coverage-repo {{ background: var(--surface); position: sticky; left: 0; }}
    .muted {{ color: var(--muted); }}
    .footer {{ margin-top: 18px; color: var(--muted); font-size: 0.9rem; text-align: right; }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <h1>Workspace Event Model Coverage</h1>
      <p>radar-ontology event 모델이 어느 namespace 에서 어떤 source 로 채워지는지 모은 페이지입니다. 모델 단위 rollup, namespace × source 분포, repo × event_model coverage 행을 한 페이지에서 비교합니다.</p>
      <div class="hero-links">
        <a href="index.html">Main Dashboard</a>
        <a href="classification.html">Classification Audit</a>
        <a href="data-quality.html">Data Quality Audit</a>
        <a href="daily-collection.html">Daily Collection</a>
        <a href="taxonomy-analysis.html">Taxonomy Analysis</a>
        <a href="storage.html">Storage Footprint</a>
      </div>
      <div class="stats">
        {stat_card(summary.get("coverage_row_count"), "Coverage Rows")}
        {stat_card(summary.get("unique_event_model_count"), "Unique Event Models")}
        {stat_card(summary.get("namespace_count"), "Namespaces")}
        {stat_card(summary_count, "Summary Source Models")}
        {stat_card(duckdb_count, "DuckDB Source Models")}
      </div>
    </section>

    {render_namespace_panel(rows)}

    {render_coverage_progression_panel((storage_payload or {}).get("repo_rows") or [])}

    {render_coverage_grid(coverage_rows)}

    <section class="table-wrap">
      <div class="table-header">
        <h2>Event Model Rollup</h2>
        <p>각 event model 이 몇 개의 repo 에 매핑돼 있는지, summary 마트로 집계됐는지 DuckDB raw payload 에서 잡혔는지를 표시합니다. avg match rate 와 tracked sources 는 해당 모델을 채우는 repo 들의 평균값입니다.</p>
      </div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Event Model</th>
              <th>Source</th>
              <th>Repo Count</th>
              <th>Records</th>
              <th>Articles</th>
              <th>Matched</th>
              <th>Avg Match Rate</th>
              <th>Avg Tracked Sources</th>
            </tr>
          </thead>
          <tbody>{render_event_model_rows(rows)}</tbody>
        </table>
      </div>
    </section>

    <section class="table-wrap">
      <div class="table-header">
        <h2>Repo × Event Model Coverage</h2>
        <p>각 repo 가 어떤 event model 을 cover 하고 어디서 gap 이 나는지 행 단위로 보여줍니다. ontology_source 컬럼은 summary 어댑션 / DuckDB raw 적재 중 어느 경로에서 모델이 채워졌는지 구분합니다.</p>
      </div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Event Model</th>
              <th>Namespace</th>
              <th>Repo</th>
              <th>Source</th>
              <th>Records</th>
              <th>Articles</th>
              <th>Matched</th>
              <th>Match Rate</th>
              <th>Gap</th>
            </tr>
          </thead>
          <tbody>{render_coverage_rows(coverage_rows)}</tbody>
        </table>
      </div>
    </section>

    <footer class="footer">
      Canonical output: <code>radar-dashboard/event-model.html</code> · Data source: <code>radar-dashboard/data/event-model-rollout.json</code>
    </footer>
  </main>
</body>
</html>
"""


def main() -> int:
    args = parse_args()
    script_path = Path(__file__).resolve()
    workspace_root = script_path.parents[2]
    data_path = (
        args.data_path.resolve()
        if args.data_path
        else workspace_root / "radar-dashboard" / "data" / "event-model-rollout.json"
    )
    output = (
        args.output.resolve()
        if args.output
        else workspace_root / "radar-dashboard" / "event-model.html"
    )
    storage_facts_path = (
        args.storage_facts_path.resolve()
        if args.storage_facts_path
        else workspace_root / "radar-dashboard" / "data" / "storage-facts.json"
    )

    payload = json.loads(data_path.read_text(encoding="utf-8"))
    storage_payload: dict[str, Any] | None = None
    if storage_facts_path.is_file():
        storage_payload = json.loads(storage_facts_path.read_text(encoding="utf-8"))
    output.write_text(build_html(payload, storage_payload), encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
