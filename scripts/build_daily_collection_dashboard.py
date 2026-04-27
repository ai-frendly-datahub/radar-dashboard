#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from typing import Any


STATUS_LABELS = {
    "ok": "OK",
    "partial": "Partial",
    "not_applicable": "N/A",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render daily collection dashboard from daily-collection.json"
    )
    parser.add_argument("--data-path", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def badge(status: str) -> str:
    label = STATUS_LABELS.get(status, status)
    return f"<span class=\"badge badge--{escape(status)}\">{escape(label)}</span>"


def render_check_list(checks: dict[str, Any]) -> str:
    if not checks:
        return "<span class=\"muted\">Shared repo</span>"
    items = []
    for key, value in sorted(checks.items()):
        state = "yes" if value else "no"
        items.append(
            f"<span class=\"check check--{state}\">{escape(key)}: {escape(str(bool(value)).lower())}</span>"
        )
    return "<div class=\"checks\">" + "".join(items) + "</div>"


def render_repo_rows(rows: list[dict[str, Any]]) -> str:
    rendered = []
    for row in rows:
        missing = ", ".join(str(item) for item in row.get("missing_required") or []) or "-"
        notes = "; ".join(str(item) for item in row.get("notes") or []) or "-"
        rendered.append(
            "<tr>"
            f"<td><div class=\"repo-name\">{escape(str(row.get('repo') or 'unknown'))}</div>"
            f"<div class=\"repo-meta\">{escape(str(row.get('repo_type') or 'n/a'))}</div></td>"
            f"<td>{badge(str(row.get('status') or 'partial'))}</td>"
            f"<td>{escape(missing)}</td>"
            f"<td>{render_check_list(row.get('checks') or {})}</td>"
            f"<td>{escape(notes)}</td>"
            "</tr>"
        )
    return "\n".join(rendered)


def render_status_counts(summary: dict[str, Any]) -> str:
    cards = []
    for status in ("ok", "partial", "not_applicable"):
        cards.append(
            "<article class=\"stat\">"
            f"<div class=\"stat__value\">{escape(str(summary.get(status, 0)))}</div>"
            f"<div class=\"stat__label\">{escape(STATUS_LABELS[status])}</div>"
            "</article>"
        )
    return "".join(cards)


def build_html(payload: dict[str, Any]) -> str:
    contract = payload.get("contract") or {}
    summary = payload.get("summary") or {}
    repos = list(payload.get("repos") or [])
    repos.sort(key=lambda row: (str(row.get("status") or ""), str(row.get("repo") or "")))
    accepted_snapshots = ", ".join(
        f"<code>{escape(str(path))}</code>" for path in contract.get("accepted_snapshot_paths") or []
    )
    required_checks = ", ".join(
        f"<code>{escape(str(check))}</code>" for check in contract.get("required_checks") or []
    )

    return f"""<!DOCTYPE html>
<html lang="ko" data-visual-system="radar-unified-v2" data-visual-surface="portfolio" data-visual-page="daily-collection">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Daily Collection Contract</title>
  <style>
    :root {{
      --vs-bg-0: #f7f8fa;
      --vs-bg-1: #eef2f0;
      --vs-surface-0: #ffffff;
      --vs-surface-1: #eef2f0;
      --vs-text: #1f2424;
      --vs-text-muted: #66706d;
      --vs-line: #d9e0dd;
      --vs-brand: #126c55;
      --vs-brand-strong: #167046;
      --vs-accent: #9b5f00;
      --vs-danger: #a13b36;
      --vs-shadow: 0 18px 40px rgba(31, 36, 36, 0.08);
      --vs-radius: 8px;
      --vs-max: 1420px;
      --vs-font-sans: "Pretendard Variable", "Pretendard", "Segoe UI", Arial, sans-serif;

      --bg: var(--vs-bg-0);
      --surface: var(--vs-surface-0);
      --surface-alt: var(--vs-surface-1);
      --text: var(--vs-text);
      --muted: var(--vs-text-muted);
      --line: var(--vs-line);
      --accent: var(--vs-brand);
      --accent-2: #9b5f00;
      --ok: var(--vs-brand-strong);
      --ok-soft: #dff4e8;
      --warn: #9b5f00;
      --warn-soft: #fff0cf;
      --bad: var(--vs-danger);
      --bad-soft: #ffe2dd;
      --max: var(--vs-max);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--text);
      font-family: var(--vs-font-sans);
      background: var(--bg);
    }}
    a {{ color: var(--accent); text-decoration: none; font-weight: 700; }}
    a:hover {{ text-decoration: underline; }}
    code {{ background: var(--surface-alt); padding: 2px 6px; border-radius: 6px; }}
    .page {{ max-width: var(--max); margin: 0 auto; padding: 28px 22px 56px; }}
    .hero {{
      background: linear-gradient(135deg, #fdfefe, #e9f2ee);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 28px;
    }}
    .hero h1 {{ margin: 0 0 10px; font-size: clamp(2rem, 3vw, 3.2rem); }}
    .hero p {{ margin: 0; max-width: 82ch; color: var(--muted); line-height: 1.6; }}
    .hero-meta {{ margin-top: 14px; color: var(--muted); }}
    .hero-links {{ margin-top: 18px; display: flex; flex-wrap: wrap; gap: 10px; }}
    .hero-links a {{
      display: inline-flex;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 9px 12px;
      background: var(--surface);
    }}
    .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-top: 18px; }}
    .stat {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      padding: 16px;
    }}
    .stat__value {{ font-size: 2rem; font-weight: 800; }}
    .stat__label {{ margin-top: 5px; color: var(--muted); }}
    .contract {{
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }}
    .panel {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      padding: 18px;
    }}
    .panel h2 {{ margin: 0 0 10px; font-size: 1.1rem; }}
    .panel p {{ margin: 0; color: var(--muted); line-height: 1.55; }}
    .table-wrap {{
      margin-top: 18px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      overflow: hidden;
    }}
    .table-header {{ padding: 18px 18px 8px; }}
    .table-header h2 {{ margin: 0 0 8px; }}
    .table-header p {{ margin: 0; color: var(--muted); line-height: 1.55; }}
    .table-scroll {{ overflow-x: auto; padding: 8px 10px 14px; }}
    table {{ width: 100%; border-collapse: collapse; min-width: 1180px; }}
    th, td {{ padding: 13px 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; font-size: 0.94rem; }}
    th {{ color: var(--muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }}
    .repo-name {{ font-weight: 800; }}
    .repo-meta {{ margin-top: 4px; color: var(--muted); font-size: 0.84rem; }}
    .badge, .check {{
      display: inline-flex;
      align-items: center;
      border-radius: 8px;
      padding: 6px 9px;
      font-size: 0.82rem;
      font-weight: 800;
      margin: 0 6px 6px 0;
    }}
    .badge--ok, .check--yes {{ background: var(--ok-soft); color: var(--ok); }}
    .badge--partial, .check--no {{ background: var(--warn-soft); color: var(--warn); }}
    .badge--not_applicable {{ background: var(--surface-alt); color: var(--muted); }}
    .checks {{ display: flex; flex-wrap: wrap; gap: 2px; }}
    .muted {{ color: var(--muted); }}
    .footer {{ margin-top: 16px; color: var(--muted); text-align: right; font-size: 0.9rem; }}
    @media (max-width: 900px) {{
      .contract {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <h1>Daily Collection Contract</h1>
      <p>매일 실행, 날짜별 raw 기록, 날짜별 DuckDB snapshot, retention CLI가 전 Radar 저장소에 적용되어 있는지 점검합니다.</p>
      <div class="hero-meta">Generated at {escape(str(payload.get('generated_at') or 'n/a'))}</div>
      <div class="hero-links">
        <a href="index.html">Main Dashboard</a>
        <a href="data-quality.html">Data Quality Audit</a>
        <a href="classification.html">Classification Audit</a>
        <a href="taxonomy-analysis.html">Taxonomy Analysis</a>
        <a href="storage.html">Storage Footprint</a>
        <a href="event-model.html">Event Model Coverage</a>
        <a href="../docs/harness/daily-collection-review.md">Markdown Review</a>
      </div>
      <div class="stats">{render_status_counts(summary)}</div>
    </section>

    <section class="contract">
      <article class="panel">
        <h2>Snapshot Paths</h2>
        <p>{accepted_snapshots or "No snapshot path contract configured."}</p>
      </article>
      <article class="panel">
        <h2>Required Checks</h2>
        <p>{required_checks or "No required checks configured."}</p>
      </article>
    </section>

    <section class="table-wrap">
      <div class="table-header">
        <h2>Repository Status</h2>
        <p>Collecting repos must be OK. Shared infrastructure repos are marked N/A.</p>
      </div>
      <div class="table-scroll">
        <table>
          <thead><tr><th>Repo</th><th>Status</th><th>Missing</th><th>Checks</th><th>Notes</th></tr></thead>
          <tbody>{render_repo_rows(repos)}</tbody>
        </table>
      </div>
    </section>

    <footer class="footer">
      Canonical output: <code>radar-dashboard/daily-collection.html</code> · Data source: <code>radar-dashboard/data/daily-collection.json</code>
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
        else workspace_root / "radar-dashboard" / "data" / "daily-collection.json"
    )
    output = (
        args.output.resolve()
        if args.output
        else workspace_root / "radar-dashboard" / "daily-collection.html"
    )

    payload = json.loads(data_path.read_text(encoding="utf-8"))
    output.write_text(build_html(payload), encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
