#!/usr/bin/env python3
"""Render the source reliability scoreboard as a standalone HTML page.

Consumes ``data/source-reliability.json`` written by the radar-analysis
``build_source_reliability_mart.py`` script. Writes
``source-reliability.html``.
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "source-reliability.json"
OUT = ROOT / "source-reliability.html"


def _tier(score: float) -> str:
    if score >= 85:
        return "ok"
    if score >= 70:
        return "warn"
    return "low"


def _format_source_row(repo: str, source: dict) -> str:
    tier = _tier(source["score"])
    last_seen = source.get("last_seen") or "—"
    staleness = source.get("staleness_days")
    staleness_text = f"{staleness:.1f}d" if isinstance(staleness, (int, float)) else "∞"
    return (
        "<tr>"
        f"<td><code>{escape(repo)}</code></td>"
        f"<td>{escape(source['source'])}</td>"
        f"<td class='num'>{source['article_count']}</td>"
        f"<td class='num'>{source['success_rate'] * 100:.1f}%</td>"
        f"<td class='num'>{staleness_text}</td>"
        f"<td class='num'>{escape(last_seen[:10])}</td>"
        f"<td class='score {tier}'>{source['score']:.1f}</td>"
        "</tr>"
    )


def render(payload: dict) -> str:
    rows: list[str] = []
    for repo_entry in payload["repos"]:
        repo = repo_entry["repo"]
        for source in repo_entry["sources"]:
            rows.append(_format_source_row(repo, source))

    all_scores = [
        s["score"]
        for repo_entry in payload["repos"]
        for s in repo_entry["sources"]
    ]
    overall_avg = sum(all_scores) / max(1, len(all_scores))
    low = sum(1 for s in all_scores if s < 70)

    return f"""<!doctype html>
<html lang="en" data-visual-system="radar-unified-v2" data-visual-surface="dashboard">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Workspace · Source Reliability</title>
  <style>
    body {{ font-family: system-ui, -apple-system, sans-serif; background:#0b0b0f; color:#e9e9ef; margin:0; padding:24px; }}
    h1 {{ margin: 0 0 8px; }}
    .meta {{ opacity:.72; margin-bottom: 24px; font-size: .9rem; }}
    .summary-cards {{ display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); margin-bottom: 24px; }}
    .card {{ background: rgba(28,26,34,.74); border: 1px solid rgba(244,244,247,.14); border-radius: 8px; padding: 16px; }}
    .card .label {{ opacity:.65; font-size:.85rem; }}
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
  <h1>Source Reliability</h1>
  <p class="meta">Generated {payload['generated_at']} · {payload['window_days']}-day window · {payload['repo_count']} repos</p>
  <section class="summary-cards">
    <div class="card"><div class="label">Sources tracked</div><div class="value">{len(all_scores)}</div></div>
    <div class="card"><div class="label">Avg score</div><div class="value">{overall_avg:.1f}</div></div>
    <div class="card"><div class="label">Sources &lt;70</div><div class="value">{low}</div></div>
  </section>
  <section>
    <table>
      <thead>
        <tr>
          <th>Repo</th><th>Source</th><th>Articles</th><th>Success</th><th>Stale</th><th>Last seen</th><th>Score</th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </section>
</body>
</html>
"""


def main() -> None:
    payload = json.loads(DATA.read_text())
    OUT.write_text(render(payload), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
