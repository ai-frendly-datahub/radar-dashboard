#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render storage.html from storage-facts.json")
    parser.add_argument("--data-path", type=Path, default=None)
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


def stat_card(value: Any, label: str) -> str:
    return (
        "<article class=\"stat\">"
        f"<div class=\"stat__value\">{fmt_number(value)}</div>"
        f"<div class=\"stat__label\">{escape(label)}</div>"
        "</article>"
    )


def render_repo_rows(rows: list[dict[str, Any]]) -> str:
    rendered = []
    for row in rows:
        gaps: list[str] = []
        if not row.get("latest_raw_record_count"):
            gaps.append("raw=0")
        if not row.get("duckdb_table_count"):
            gaps.append("duckdb=0")
        elif not row.get("signal_table_count"):
            gaps.append("signal=0")
        if row.get("latest_raw_event_model_record_count") in (0, None) and row.get(
            "duckdb_event_model_record_count"
        ) in (0, None):
            gaps.append("event_model=0")
        gap_html = (
            "".join(f"<span class=\"chip chip--bad\">{escape(value)}</span>" for value in gaps)
            if gaps
            else "<span class=\"chip chip--ok\">healthy</span>"
        )
        rendered.append(
            "<tr>"
            f"<td><div class=\"repo-name\">{escape(str(row.get('display_name') or row.get('repo') or '—'))}</div>"
            f"<div class=\"repo-meta\">{escape(str(row.get('repo') or ''))} · {escape(str(row.get('repo_class') or 'unclassified'))}</div></td>"
            f"<td>{escape(str(row.get('latest_raw_date') or '—'))}</td>"
            f"<td>{fmt_number(row.get('latest_raw_file_count'))}</td>"
            f"<td>{fmt_number(row.get('latest_raw_record_count'))}</td>"
            f"<td>{fmt_number(row.get('latest_raw_source_count'))}</td>"
            f"<td>{fmt_number(row.get('duckdb_file_count'))}</td>"
            f"<td>{fmt_number(row.get('duckdb_table_count'))}</td>"
            f"<td>{fmt_number(row.get('signal_table_count'))}</td>"
            f"<td>{fmt_number(row.get('signal_row_total'))}</td>"
            f"<td>{fmt_number(row.get('latest_raw_ontology_record_count'))}</td>"
            f"<td>{fmt_number(row.get('duckdb_ontology_row_count'))}</td>"
            f"<td>{fmt_number(row.get('latest_raw_event_model_record_count'))}</td>"
            f"<td>{fmt_number(row.get('duckdb_event_model_record_count'))}</td>"
            f"<td>{gap_html}</td>"
            "</tr>"
        )
    return "\n".join(rendered)


def render_gap_panel(rows: list[dict[str, Any]]) -> str:
    no_raw = [r for r in rows if not r.get("latest_raw_record_count")]
    no_signal = [r for r in rows if not r.get("signal_table_count")]
    no_event = [
        r
        for r in rows
        if not r.get("latest_raw_event_model_record_count")
        and not r.get("duckdb_event_model_record_count")
    ]
    no_ontology = [
        r
        for r in rows
        if not r.get("latest_raw_ontology_record_count")
        and not r.get("duckdb_ontology_row_count")
    ]

    def listing(items: list[dict[str, Any]]) -> str:
        if not items:
            return "<span class=\"muted\">없음</span>"
        chips = "".join(
            f"<span class=\"chip chip--neutral\">{escape(str(it.get('repo') or '—'))}</span>"
            for it in sorted(items, key=lambda r: str(r.get("repo") or ""))
        )
        return f"<div class=\"chip-row\">{chips}</div>"

    return (
        "<section class=\"grid\">"
        "<article class=\"panel\">"
        f"<h2>Raw record = 0 ({len(no_raw)} repos)</h2>"
        f"{listing(no_raw)}"
        "</article>"
        "<article class=\"panel\">"
        f"<h2>Signal table = 0 ({len(no_signal)} repos)</h2>"
        f"{listing(no_signal)}"
        "</article>"
        "<article class=\"panel\">"
        f"<h2>Raw + DuckDB ontology row = 0 ({len(no_ontology)} repos)</h2>"
        f"{listing(no_ontology)}"
        "</article>"
        "<article class=\"panel\">"
        f"<h2>Raw + DuckDB event_model record = 0 ({len(no_event)} repos)</h2>"
        f"{listing(no_event)}"
        "</article>"
        "</section>"
    )


def build_html(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    rows = list(payload.get("repo_rows") or [])
    rows.sort(key=lambda r: str(r.get("repo") or ""))
    gap_panel = render_gap_panel(rows)
    repo_table = render_repo_rows(rows)

    return f"""<!DOCTYPE html>
<html lang="ko" data-visual-system="radar-unified-v2" data-visual-surface="portfolio" data-visual-page="storage-footprint">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Workspace Storage Footprint</title>
  <style>
    :root {{
      --bg: #f4f7fb;
      --surface: #ffffff;
      --surface-2: #eef2fa;
      --text: #131c2b;
      --muted: #5d6a82;
      --line: #d8e0ee;
      --accent: #1f5edc;
      --ok: #1e8a52;
      --ok-soft: #d8efe1;
      --bad: #b23a2c;
      --bad-soft: #fbe1dc;
      --neutral-soft: #e8edf7;
      --shadow: 0 14px 38px rgba(15, 23, 42, 0.08);
      --radius: 20px;
      --max: 1520px;
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
      background: linear-gradient(135deg, #16243d, #1f5edc);
      color: #ffffff;
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
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-top: 22px; }}
    .panel {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 22px;
      box-shadow: var(--shadow);
    }}
    .panel h2 {{ margin: 0 0 12px; font-size: 1.05rem; }}
    .chip-row {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .chip {{
      display: inline-flex; padding: 5px 10px; border-radius: 999px;
      font-size: 0.78rem; font-weight: 600;
    }}
    .chip--ok {{ background: var(--ok-soft); color: var(--ok); }}
    .chip--bad {{ background: var(--bad-soft); color: var(--bad); }}
    .chip--neutral {{ background: var(--neutral-soft); color: var(--text); }}
    .muted {{ color: var(--muted); }}
    .table-wrap {{ margin-top: 24px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; }}
    .table-header {{ padding: 22px 24px 8px; }}
    .table-header h2 {{ margin: 0 0 8px; }}
    .table-header p {{ margin: 0; color: var(--muted); line-height: 1.6; }}
    .table-scroll {{ overflow-x: auto; padding: 8px 12px 16px; }}
    table {{ width: 100%; border-collapse: collapse; min-width: 1500px; }}
    th, td {{ padding: 12px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; font-size: 0.9rem; }}
    th {{ color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em; }}
    tr:hover td {{ background: #f7faff; }}
    .repo-name {{ font-weight: 800; }}
    .repo-meta {{ color: var(--muted); font-size: 0.82rem; margin-top: 4px; }}
    .footer {{ margin-top: 18px; color: var(--muted); font-size: 0.9rem; text-align: right; }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <h1>Workspace Storage Footprint</h1>
      <p>각 Radar 저장소의 최신 raw JSONL snapshot, DuckDB 테이블, signal 테이블, ontology / event_model 적재 상태를 직접 집계한 페이지입니다. 마트가 비어 있는 repo와 ontology / event_model 적재 공백을 한 화면에서 점검합니다.</p>
      <div class="hero-links">
        <a href="index.html">Main Dashboard</a>
        <a href="classification.html">Classification Audit</a>
        <a href="data-quality.html">Data Quality Audit</a>
        <a href="daily-collection.html">Daily Collection</a>
        <a href="taxonomy-analysis.html">Taxonomy Analysis</a>
        <a href="event-model.html">Event Model Coverage</a>
      </div>
      <div class="stats">
        {stat_card(summary.get("repo_count"), "Repos")}
        {stat_card(summary.get("repos_with_raw_records"), "Repos with Raw Records")}
        {stat_card(summary.get("raw_file_count"), "Raw Files")}
        {stat_card(summary.get("raw_record_count"), "Raw Records")}
        {stat_card(summary.get("duckdb_table_count"), "DuckDB Tables")}
        {stat_card(summary.get("signal_table_count"), "Signal Tables")}
      </div>
    </section>

    {gap_panel}

    <section class="table-wrap">
      <div class="table-header">
        <h2>Repo Storage Matrix</h2>
        <p>raw / DuckDB / signal / ontology / event_model 카운트를 한 줄에 모아 줍니다. Gap 컬럼은 각 행에서 `0`으로 비어 있는 신호를 chip 으로 표시합니다.</p>
      </div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Repo</th>
              <th>Latest Raw</th>
              <th>Raw Files</th>
              <th>Raw Records</th>
              <th>Raw Sources</th>
              <th>DB Files</th>
              <th>DB Tables</th>
              <th>Signal Tables</th>
              <th>Signal Rows</th>
              <th>Raw Ontology</th>
              <th>DB Ontology</th>
              <th>Raw Event Model</th>
              <th>DB Event Model</th>
              <th>Gaps</th>
            </tr>
          </thead>
          <tbody>{repo_table}</tbody>
        </table>
      </div>
    </section>

    <footer class="footer">
      Canonical output: <code>radar-dashboard/storage.html</code> · Data source: <code>radar-dashboard/data/storage-facts.json</code>
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
        else workspace_root / "radar-dashboard" / "data" / "storage-facts.json"
    )
    output = (
        args.output.resolve()
        if args.output
        else workspace_root / "radar-dashboard" / "storage.html"
    )

    payload = json.loads(data_path.read_text(encoding="utf-8"))
    output.write_text(build_html(payload), encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
