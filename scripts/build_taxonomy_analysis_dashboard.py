#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from typing import Any


LAYER_ORDER = ["official", "operational", "market", "community", "attention"]
LAYER_LABELS = {
    "official": "Official",
    "operational": "Operational",
    "market": "Market",
    "community": "Community",
    "attention": "Attention",
}
FOCUS_LABELS = {
    "collector_repair": "Collector Repair",
    "freshness_coverage": "Freshness Coverage",
    "disabled_source_governance": "Disabled Source Governance",
    "taxonomy_enrichment": "Taxonomy Enrichment",
    "tracked_source_coverage": "Tracked Source Coverage",
    "stable": "Stable",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render taxonomy-analysis.html")
    parser.add_argument("--data-path", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def fmt_number(value: Any) -> str:
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.1f}"
    if value is None:
        return "n/a"
    return escape(str(value))


def fmt_percent(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.1f}%"
    return "n/a"


def bar(value: Any, max_value: float = 100.0, kind: str = "neutral") -> str:
    width = 0.0
    if isinstance(value, (int, float)) and max_value > 0:
        width = max(0.0, min(100.0, (float(value) / max_value) * 100.0))
    label = fmt_number(value)
    return (
        f"<div class=\"bar bar--{escape(kind)}\">"
        f"<span style=\"width:{width:.1f}%\"></span>"
        f"<strong>{label}</strong>"
        "</div>"
    )


def badge(kind: str, value: Any) -> str:
    label = "n/a" if value is None else str(value)
    css_kind = "".join(ch if ch.isalnum() else "-" for ch in label.lower())
    return f"<span class=\"badge badge--{escape(kind)} badge--{escape(css_kind)}\">{escape(label)}</span>"


def stat(label: str, value: Any, note: str | None = None) -> str:
    note_html = f"<span>{escape(note)}</span>" if note else ""
    return (
        "<article class=\"stat\">"
        f"<strong>{fmt_number(value)}</strong>"
        f"<em>{escape(label)}</em>"
        f"{note_html}"
        "</article>"
    )


def render_count_bars(title: str, counts: dict[str, int], labels: dict[str, str] | None = None) -> str:
    if not counts:
        return ""
    labels = labels or {}
    max_count = max(counts.values()) if counts else 1
    rows = []
    for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        rows.append(
            "<div class=\"count-row\">"
            f"<span>{escape(labels.get(key, key))}</span>"
            f"{bar(count, max_count)}"
            "</div>"
        )
    return f"<section class=\"panel\"><h2>{escape(title)}</h2>{''.join(rows)}</section>"


def render_group_table(title: str, rows: list[dict[str, Any]], key_label: str) -> str:
    body = []
    for row in rows:
        body.append(
            "<tr>"
            f"<td>{escape(str(row['key']))}</td>"
            f"<td>{fmt_number(row['project_count'])}</td>"
            f"<td>{fmt_percent(row.get('match_rate'))}</td>"
            f"<td>{fmt_number(row['collection_errors'])}</td>"
            f"<td>{fmt_number(row['freshness_gap'])}</td>"
            f"<td>{fmt_number(row['disabled_sources'])}</td>"
            f"<td>{bar(row['average_risk_score'], 100, 'risk')}</td>"
            f"<td>{fmt_number(row['p0_count'])}</td>"
            f"<td>{fmt_number(row['t1_count'])}</td>"
            "</tr>"
        )
    return (
        "<section class=\"panel panel--wide\">"
        f"<h2>{escape(title)}</h2>"
        "<div class=\"table-scroll\"><table>"
        "<thead><tr>"
        f"<th>{escape(key_label)}</th><th>Projects</th><th>Match</th><th>Errors</th>"
        "<th>Freshness Gap</th><th>Disabled</th><th>Avg Risk</th><th>P0</th><th>T1</th>"
        "</tr></thead>"
        f"<tbody>{''.join(body)}</tbody>"
        "</table></div></section>"
    )


def layer_strip(available: list[str], missing: list[str]) -> str:
    available_set = set(available)
    missing_set = set(missing)
    cells = []
    for layer in LAYER_ORDER:
        state = "on" if layer in available_set else "gap" if layer in missing_set else "off"
        cells.append(
            f"<span class=\"layer layer--{state}\" title=\"{escape(layer)}\">"
            f"{escape(LAYER_LABELS[layer])}"
            "</span>"
        )
    return "<div class=\"layers\">" + "".join(cells) + "</div>"


def render_focus_queue(rows: list[dict[str, Any]]) -> str:
    selected = rows[:12]
    items = []
    for row in selected:
        items.append(
            "<article class=\"queue-item\">"
            "<div>"
            f"<strong>{escape(row['repo'])}</strong>"
            f"<span>{escape(FOCUS_LABELS.get(row['focus_area'], row['focus_area']))}</span>"
            "</div>"
            f"{bar(row['risk_score'], 100, 'risk')}"
            f"<p>{escape(str(row.get('next_step') or 'No next step recorded.'))}</p>"
            "</article>"
        )
    return "<section class=\"queue\">" + "".join(items) + "</section>"


def render_repo_matrix(rows: list[dict[str, Any]]) -> str:
    body = []
    for row in rows:
        body.append(
            "<tr>"
            f"<td><strong>{escape(row['repo'])}</strong><span>{escape(str(row.get('domain_family') or ''))}</span></td>"
            f"<td>{badge('motion', row.get('primary_motion'))}</td>"
            f"<td>{badge('gov', row.get('governance_profile'))}</td>"
            f"<td>{badge('readiness', row.get('readiness_status'))}</td>"
            f"<td>{badge('op', row.get('operational_priority'))} {badge('tax', row.get('taxonomy_priority'))}</td>"
            f"<td>{fmt_percent(row.get('match_rate'))}</td>"
            f"<td>{fmt_number(row['collection_errors'])}</td>"
            f"<td>{fmt_number(row['freshness_gap'])}</td>"
            f"<td>{fmt_number(row['disabled_sources'])}</td>"
            f"<td>{fmt_percent(row.get('tracked_coverage_pct'))}</td>"
            f"<td>{layer_strip(row.get('available_layers') or [], row.get('missing_layers') or [])}</td>"
            f"<td>{bar(row['risk_score'], 100, 'risk')}</td>"
            "</tr>"
        )
    return (
        "<section class=\"panel panel--full\">"
        "<h2>Project Matrix</h2>"
        "<div class=\"table-scroll\"><table>"
        "<thead><tr>"
        "<th>Project</th><th>Motion</th><th>Governance</th><th>Readiness</th>"
        "<th>Priority</th><th>Match</th><th>Errors</th><th>Freshness Gap</th>"
        "<th>Disabled</th><th>Tracked Coverage</th><th>Evidence Layers</th><th>Risk</th>"
        "</tr></thead>"
        f"<tbody>{''.join(body)}</tbody>"
        "</table></div></section>"
    )


def build_html(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    groups = payload["groups"]
    rows = payload["repos"]
    top_rows = sorted(rows, key=lambda row: (-row["risk_score"], row["repo"]))

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Taxonomy Analysis</title>
  <style>
    :root {{
      --bg: #f6f8f7;
      --surface: #ffffff;
      --surface-alt: #edf3f1;
      --text: #18231f;
      --muted: #5c6b65;
      --line: #d9e2df;
      --teal: #0f766e;
      --green: #2f855a;
      --coral: #d94841;
      --amber: #b7791f;
      --ink: #26352f;
      --shadow: 0 16px 36px rgba(24, 35, 31, 0.08);
      --radius: 8px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--text);
      background: var(--bg);
      font-family: "Segoe UI", Arial, sans-serif;
      font-size: 16px;
      letter-spacing: 0;
    }}
    a {{ color: var(--teal); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .page {{ max-width: 1540px; margin: 0 auto; padding: 28px 22px 52px; }}
    .masthead {{
      display: grid;
      grid-template-columns: minmax(0, 1.4fr) minmax(320px, 0.6fr);
      gap: 20px;
      align-items: end;
      padding: 24px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
    }}
    .masthead h1 {{ margin: 0 0 10px; font-size: 2.2rem; line-height: 1.15; }}
    .masthead p {{ margin: 0; color: var(--muted); line-height: 1.6; max-width: 82ch; }}
    .nav {{ display: flex; flex-wrap: wrap; gap: 10px; justify-content: flex-end; }}
    .nav a {{
      display: inline-flex;
      padding: 9px 12px;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      color: var(--ink);
      background: var(--surface-alt);
      font-weight: 700;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 12px;
      margin-top: 16px;
    }}
    .stat {{
      min-height: 112px;
      padding: 16px;
      border-radius: var(--radius);
      background: var(--surface);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
    }}
    .stat strong {{ display: block; font-size: 1.8rem; line-height: 1; }}
    .stat em {{ display: block; margin-top: 10px; color: var(--muted); font-style: normal; }}
    .stat span {{ display: block; margin-top: 8px; color: var(--teal); font-size: 0.9rem; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
      margin-top: 16px;
    }}
    .panel {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 18px;
    }}
    .panel--wide {{ grid-column: span 2; }}
    .panel--full {{ grid-column: 1 / -1; }}
    h2 {{ margin: 0 0 14px; font-size: 1.15rem; }}
    .count-row {{
      display: grid;
      grid-template-columns: 150px minmax(0, 1fr);
      gap: 10px;
      align-items: center;
      margin-top: 10px;
    }}
    .count-row > span {{ color: var(--muted); }}
    .bar {{
      position: relative;
      height: 24px;
      background: var(--surface-alt);
      border-radius: var(--radius);
      overflow: hidden;
    }}
    .bar span {{
      display: block;
      height: 100%;
      background: var(--teal);
    }}
    .bar--risk span {{ background: linear-gradient(90deg, var(--green), var(--amber), var(--coral)); }}
    .bar strong {{
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: flex-end;
      padding: 0 8px;
      color: var(--ink);
      font-size: 0.85rem;
    }}
    .queue {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-top: 16px;
    }}
    .queue-item {{
      min-height: 148px;
      padding: 14px;
      border-radius: var(--radius);
      background: var(--surface);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
    }}
    .queue-item div:first-child {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: start;
      margin-bottom: 12px;
    }}
    .queue-item span {{ color: var(--muted); font-size: 0.88rem; text-align: right; }}
    .queue-item p {{ margin: 12px 0 0; color: var(--muted); line-height: 1.45; font-size: 0.92rem; }}
    .table-scroll {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; min-width: 1020px; }}
    th, td {{
      padding: 12px 10px;
      border-top: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      font-size: 0.92rem;
    }}
    th {{ color: var(--muted); font-weight: 700; background: #f8faf9; }}
    td > span:first-child:not(.badge):not(.layer) {{
      display: block;
      margin-top: 4px;
      color: var(--muted);
      font-size: 0.82rem;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      padding: 5px 8px;
      margin: 0 4px 4px 0;
      border-radius: var(--radius);
      background: var(--surface-alt);
      color: var(--ink);
      font-weight: 700;
      font-size: 0.8rem;
    }}
    .badge--p0, .badge--t1, .badge--watch {{ background: #fde8e7; color: var(--coral); }}
    .badge--p1, .badge--t2 {{ background: #fff2d6; color: var(--amber); }}
    .badge--p2, .badge--t3, .badge--ready {{ background: #e2f4ea; color: var(--green); }}
    .layers {{ display: flex; flex-wrap: wrap; gap: 4px; min-width: 250px; }}
    .layer {{
      display: inline-flex;
      min-width: 78px;
      justify-content: center;
      padding: 5px 7px;
      border-radius: var(--radius);
      border: 1px solid var(--line);
      color: var(--muted);
      background: #f5f7f6;
      font-size: 0.78rem;
      font-weight: 700;
    }}
    .layer--on {{ color: var(--teal); background: #e2f4f1; border-color: #c8e4df; }}
    .layer--gap {{ color: var(--coral); background: #fde8e7; border-color: #f4c6c3; }}
    .layer--off {{ color: #87928e; }}
    .footer {{ margin-top: 16px; color: var(--muted); text-align: right; }}
    @media (max-width: 1180px) {{
      .masthead {{ grid-template-columns: 1fr; }}
      .nav {{ justify-content: flex-start; }}
      .stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .grid {{ grid-template-columns: 1fr; }}
      .panel--wide {{ grid-column: span 1; }}
      .queue {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    @media (max-width: 720px) {{
      .stats {{ grid-template-columns: 1fr; }}
      .queue {{ grid-template-columns: 1fr; }}
      .masthead h1 {{ font-size: 1.8rem; }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="masthead">
      <div>
        <h1>Taxonomy Analysis</h1>
        <p>All dashboard-visible Radar projects joined with portfolio taxonomy, source-layer balance, collection quality, freshness, disabled-source backlog, and operational risk.</p>
      </div>
      <nav class="nav">
        <a href="index.html">Main</a>
        <a href="classification.html">Classification</a>
        <a href="data-quality.html">Quality</a>
        <a href="daily-collection.html">Daily Collection</a>
      </nav>
    </section>

    <section class="stats">
      {stat("Projects", summary["project_count"], f"taxonomy rows {summary['taxonomy_repo_count']}")}
      {stat("Overall Match Rate", fmt_percent(summary["overall_match_rate"]))}
      {stat("Collection Errors", summary["collection_error_total"], f"{summary['repos_with_errors']} repos")}
      {stat("Freshness Gaps", summary["freshness_gap_total"], f"{summary['repos_with_freshness_gap']} repos")}
      {stat("Disabled Sources", summary["disabled_source_total"], f"{summary['repos_with_disabled_sources']} repos")}
      {stat("Average Risk", summary["average_risk_score"])}
    </section>

    {render_focus_queue(top_rows)}

    <section class="grid">
      {render_count_bars("Operational Priority", summary["operational_priority_counts"])}
      {render_count_bars("Taxonomy Priority", summary["taxonomy_priority_counts"])}
      {render_count_bars("Focus Area", summary["focus_area_counts"], FOCUS_LABELS)}
      {render_group_table("Primary Motion x Quality", groups["primary_motion"], "Primary Motion")}
      {render_group_table("Governance x Quality", groups["governance_profile"], "Governance")}
      {render_group_table("Evidence Strategy x Quality", groups["evidence_strategy"], "Evidence Strategy")}
      {render_group_table("Readiness x Quality", groups["readiness_status"], "Readiness")}
      {render_repo_matrix(rows)}
    </section>

    <footer class="footer">
      Data source: <code>radar-dashboard/data/taxonomy-analysis.json</code>
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
        else workspace_root / "radar-dashboard" / "data" / "taxonomy-analysis.json"
    )
    output = (
        args.output.resolve()
        if args.output
        else workspace_root / "radar-dashboard" / "taxonomy-analysis.html"
    )
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    output.write_text(build_html(payload), encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
