#!/usr/bin/env python3
"""Render the 5-dimension data-quality panel as a static HTML page.

Consumes ``data/data-quality-panel.json`` produced by
``build_data_quality_panel_dataset.py`` and writes ``data-quality-panel.html``
next to the other dashboard pages.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "data-quality-panel.json"
OUT = ROOT / "data-quality-panel.html"


def render(payload: dict) -> str:
    rows = payload["rows"]
    summary = payload["summary"]
    generated_at = payload["generated_at"]

    def cell(value: float) -> str:
        return f'<td class="num" data-v="{value}">{value:.2f}</td>'

    def score_cell(score: float) -> str:
        tier = "ok" if score >= 80 else ("warn" if score >= 60 else "low")
        return f'<td class="score {tier}" data-v="{score}">{score:.1f}</td>'

    tbody = []
    for row in rows:
        tbody.append(
            "<tr>"
            f'<th scope="row"><code>{row["repo"]}</code></th>'
            f'<td class="num">{row["article_count"]}</td>'
            f'<td class="num">{row["matched_count"]}</td>'
            f'<td class="num">{row["source_count"]}</td>'
            f'<td class="num">{row["match_rate"]:.1f}%</td>'
            f"{cell(row['completeness'])}"
            f"{cell(row['timeliness'])}"
            f"{cell(row['volume'])}"
            f"{cell(row['diversity'])}"
            f"{cell(row['consistency'])}"
            f"{score_cell(row['score'])}"
            "</tr>"
        )

    return f"""<!doctype html>
<html lang="en" data-visual-system="radar-unified-v2" data-visual-surface="dashboard">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Workspace · Data Quality Panel</title>
  <style>
    body {{ font-family: system-ui, -apple-system, sans-serif; background: #0b0b0f; color: #e9e9ef; margin: 0; padding: 24px; }}
    h1 {{ margin: 0 0 8px; }}
    .meta {{ opacity: .72; margin-bottom: 24px; font-size: 0.9rem; }}
    .summary-cards {{ display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); margin-bottom: 24px; }}
    .card {{ background: rgba(28,26,34,.74); border: 1px solid rgba(244,244,247,.14); border-radius: 8px; padding: 16px; }}
    .card .label {{ opacity: .65; font-size: .85rem; }}
    .card .value {{ font-size: 1.6rem; font-weight: 600; margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid rgba(244,244,247,.10); padding: 6px 8px; text-align: left; }}
    th {{ background: rgba(28,26,34,.92); position: sticky; top: 0; }}
    td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    td.score {{ font-weight: 600; text-align: right; }}
    td.score.ok {{ color: #6ee7b7; }}
    td.score.warn {{ color: #fbbf24; }}
    td.score.low {{ color: #f87171; }}
    code {{ font-family: "JetBrains Mono", ui-monospace, monospace; font-size: .9rem; }}
  </style>
</head>
<body>
  <h1>Data Quality Panel</h1>
  <p class="meta">Generated {generated_at} · target sources/repo = {payload['target_sources_per_repo']} · median article count = {payload['median_article_count']:.0f}</p>
  <section class="summary-cards">
    <div class="card"><div class="label">Repos</div><div class="value">{summary['repo_count']}</div></div>
    <div class="card"><div class="label">Avg score</div><div class="value">{summary['avg_score']}</div></div>
    <div class="card"><div class="label">P50 score</div><div class="value">{summary['p50_score']:.1f}</div></div>
    <div class="card"><div class="label">Below 70</div><div class="value">{summary['low_score_count']}</div></div>
  </section>
  <section>
    <table>
      <thead>
        <tr>
          <th scope="col">Repo</th>
          <th scope="col">Articles</th>
          <th scope="col">Matched</th>
          <th scope="col">Sources</th>
          <th scope="col">Match %</th>
          <th scope="col">Completeness</th>
          <th scope="col">Timeliness</th>
          <th scope="col">Volume</th>
          <th scope="col">Diversity</th>
          <th scope="col">Consistency</th>
          <th scope="col">Score</th>
        </tr>
      </thead>
      <tbody>
        {''.join(tbody)}
      </tbody>
    </table>
  </section>
</body>
</html>
"""


def main() -> None:
    payload = json.loads(DATA.read_text())
    html = render(payload)
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
