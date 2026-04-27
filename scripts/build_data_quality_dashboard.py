#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from typing import Any


PRIORITY_LABELS = {"P0": "P0", "P1": "P1", "P2": "P2", "P3": "P3"}
DIMENSION_LABELS = {
    "authority": "권위성",
    "operational_depth": "운영 깊이",
    "freshness": "신선도",
    "actionability": "행동 가능성",
    "verification": "교차 검증",
    "traceability": "추적성",
}
DIMENSION_ORDER = [
    "authority",
    "operational_depth",
    "freshness",
    "actionability",
    "verification",
    "traceability",
]
DISABLED_BUCKET_LABELS = {
    "awaiting_url_replacement": "Awaiting URL replacement",
    "awaiting_secret": "Awaiting secret",
    "awaiting_smoke_test": "Awaiting smoke test",
    "upstream_section_missing": "Upstream section missing",
    "awaiting_partnership_review": "Awaiting partnership review",
    "accepted_backlog": "Accepted backlog",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render data quality dashboard from data-quality.json")
    parser.add_argument("--data-path", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def badge(kind: str, label: str) -> str:
    return f"<span class=\"badge badge--{escape(kind)}\">{escape(label)}</span>"


def score_bar(score: int, class_name: str = "score") -> str:
    width = max(4, min(score, 100))
    return (
        f"<div class=\"{escape(class_name)}\">"
        f"<div class=\"{escape(class_name)}__bar\"><span style=\"width:{width}%\"></span></div>"
        f"<div class=\"{escape(class_name)}__value\">{score}</div>"
        "</div>"
    )


def render_count_group(title: str, counts: dict[str, int], labels: dict[str, str]) -> str:
    if not counts:
        return ""
    max_count = max(counts.values())
    rows = []
    for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        width = max(12, round((count / max_count) * 100))
        rows.append(
            "<div class=\"metric-row\">"
            f"<div class=\"metric-row__label\">{escape(labels.get(key, key))}</div>"
            f"<div class=\"metric-row__bar\"><span style=\"width:{width}%\"></span></div>"
            f"<div class=\"metric-row__value\">{count}</div>"
            "</div>"
        )
    return "<article class=\"panel\">" f"<h2>{escape(title)}</h2>" + "".join(rows) + "</article>"


def render_issue_list(items: list[str], limit: int = 2) -> str:
    if not items:
        return "<span class=\"muted\">No blocking issue</span>"
    return "<ul class=\"mini-list\">" + "".join(f"<li>{escape(item)}</li>" for item in items[:limit]) + "</ul>"


def render_dimension_cells(dimensions: dict[str, int]) -> str:
    cells = []
    for dimension in DIMENSION_ORDER:
        cells.append(f"<td>{score_bar(int(dimensions.get(dimension) or 0), 'mini-score')}</td>")
    return "".join(cells)


def render_action_pack(row: dict[str, Any]) -> str:
    action_pack = row.get("action_pack") or {}
    next_actions = action_pack.get("next_actions") or row.get("recommendations") or []
    return render_issue_list([str(item) for item in next_actions], limit=3)


def render_disabled_chips(row: dict[str, Any]) -> str:
    total = int(row.get("disabled_source_classification_total") or 0)
    if total <= 0:
        return "<span class=\"muted\">0 disabled</span>"
    bucket_counts = row.get("disabled_source_classification") or {}
    nonzero = [(key, int(count or 0)) for key, count in bucket_counts.items() if int(count or 0) > 0]
    nonzero.sort(key=lambda item: (-item[1], item[0]))
    chips = "".join(
        f"<span class=\"disabled-chip\">{count} {escape(DISABLED_BUCKET_LABELS.get(key, key))}</span>"
        for key, count in nonzero
    )
    return (
        f"<div class=\"disabled-total\">{total} disabled</div>"
        f"<div class=\"disabled-chips\">{chips}</div>"
    )


def render_priority_rows(rows: list[dict[str, Any]], priority: str) -> str:
    rendered = []
    for row in rows:
        if row.get("priority") != priority:
            continue
        rendered.append(
            "<tr>"
            f"<td><div class=\"repo-name\">{escape(str(row['repo']))}</div>"
            f"<div class=\"repo-meta\">{escape(str(row['governance_profile']))} · {escape(str(row['primary_motion']))}</div></td>"
            f"<td>{score_bar(int(row.get('risk_score') or 0), 'risk')}</td>"
            f"<td>{score_bar(int(row.get('data_quality_score') or 0))}</td>"
            f"<td>{escape(DIMENSION_LABELS.get(str(row.get('weakest_dimension')), str(row.get('weakest_dimension'))))}</td>"
            f"<td>{render_disabled_chips(row)}</td>"
            f"<td>{render_issue_list([str(item) for item in row.get('issues') or []])}</td>"
            f"<td>{render_action_pack(row)}</td>"
            "</tr>"
        )
    return "\n".join(rendered)


def render_matrix_rows(rows: list[dict[str, Any]]) -> str:
    rendered = []
    for row in rows:
        priority = str(row.get("priority") or "P3")
        rendered.append(
            "<tr>"
            f"<td>{badge(priority.lower(), priority)}</td>"
            f"<td><div class=\"repo-name\">{escape(str(row['repo']))}</div>"
            f"<div class=\"repo-meta\">{escape(str(row['source_status']))} · {escape(str(row['readiness_status']))}</div></td>"
            f"<td>{escape(str(row.get('governance_profile') or 'n/a'))}</td>"
            f"<td>{escape(str(row.get('primary_motion') or 'n/a'))}</td>"
            f"<td>{score_bar(int(row.get('risk_score') or 0), 'risk')}</td>"
            f"<td>{score_bar(int(row.get('data_quality_score') or 0))}</td>"
            + render_dimension_cells(row.get("dimensions") or {})
            + f"<td>{render_disabled_chips(row)}</td>"
            + f"<td>{render_issue_list([str(item) for item in row.get('recommendations') or []], limit=1)}</td>"
            "</tr>"
        )
    return "\n".join(rendered)


def build_html(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    rows = list(payload["repos"])
    rows.sort(key=lambda row: (str(row.get("priority") or "P3"), -int(row.get("risk_score") or 0), row["repo"]))
    p0_count = int((summary.get("priority_counts") or {}).get("P0", 0))
    p1_count = int((summary.get("priority_counts") or {}).get("P1", 0))
    p2_count = int((summary.get("priority_counts") or {}).get("P2", 0))
    average_score = summary.get("average_data_quality_score")
    top_priority = ", ".join(str(value) for value in summary.get("top_priority_repos", [])[:6])
    disabled_classification = summary.get("disabled_source_classification_summary") or {}
    disabled_bucket_totals = dict(disabled_classification.get("bucket_totals") or {})
    disabled_total = int(disabled_classification.get("total_disabled_count", 0) or 0)
    disabled_repo_count = int(disabled_classification.get("repo_count_with_disabled_sources", 0) or 0)
    disabled_panel_html = render_count_group(
        "Disabled Source Classification", disabled_bucket_totals, DISABLED_BUCKET_LABELS
    )

    return f"""<!DOCTYPE html>
<html lang="ko" data-visual-system="radar-unified-v2" data-visual-surface="portfolio" data-visual-page="data-quality-audit">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Workspace Data Quality Audit</title>
  <style>
    :root {{
      --vs-bg-0: #f5f1e8;
      --vs-bg-1: #f3eee4;
      --vs-surface-0: #fffdf8;
      --vs-surface-1: #f4ead8;
      --vs-text: #241f19;
      --vs-text-muted: #756956;
      --vs-line: #e1d2bb;
      --vs-brand: #9a4f18;
      --vs-brand-strong: #21734f;
      --vs-accent: #12332b;
      --vs-danger: #a43d2a;
      --vs-shadow: 0 18px 50px rgba(36, 31, 25, 0.10);
      --vs-radius: 22px;
      --vs-max: 1520px;
      --vs-font-sans: "IBM Plex Sans KR", "Pretendard Variable", "Segoe UI", Arial, sans-serif;

      --bg: var(--vs-bg-0);
      --surface: var(--vs-surface-0);
      --surface-2: var(--vs-surface-1);
      --text: var(--vs-text);
      --muted: var(--vs-text-muted);
      --line: var(--vs-line);
      --accent: var(--vs-brand);
      --accent-soft: #ffe2bf;
      --ink: var(--vs-accent);
      --ok: var(--vs-brand-strong);
      --ok-soft: #ddf4df;
      --warn: #a26000;
      --warn-soft: #fff0c7;
      --bad: var(--vs-danger);
      --bad-soft: #ffe0d7;
      --shadow: var(--vs-shadow);
      --radius: var(--vs-radius);
      --max: var(--vs-max);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--text);
      font-family: var(--vs-font-sans);
      background:
        radial-gradient(circle at 12% 8%, rgba(154, 79, 24, 0.14), transparent 24rem),
        radial-gradient(circle at 88% 12%, rgba(18, 51, 43, 0.12), transparent 22rem),
        linear-gradient(135deg, #f9f3e8, #f3eee4 52%, #ebe3d3);
    }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .page {{ max-width: var(--max); margin: 0 auto; padding: 30px 22px 58px; }}
    .hero {{
      background:
        linear-gradient(135deg, rgba(18, 51, 43, 0.96), rgba(154, 79, 24, 0.92)),
        repeating-linear-gradient(45deg, rgba(255,255,255,0.06) 0 1px, transparent 1px 14px);
      border-radius: 30px;
      color: #fffaf0;
      padding: 34px;
      box-shadow: var(--shadow);
    }}
    .hero h1 {{ margin: 0 0 10px; font-size: clamp(2.1rem, 3.2vw, 3.5rem); letter-spacing: -0.05em; }}
    .hero p {{ margin: 0; max-width: 82ch; color: rgba(255,250,240,0.84); line-height: 1.65; }}
    .hero-meta {{ margin-top: 16px; color: rgba(255,250,240,0.72); font-size: 0.94rem; }}
    .hero-links {{ margin-top: 18px; display: flex; gap: 12px; flex-wrap: wrap; }}
    .hero-links a {{
      display: inline-flex; padding: 10px 14px; border-radius: 999px;
      background: rgba(255,255,255,0.14); color: #fffaf0; font-weight: 700;
    }}
    .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px; margin-top: 24px; }}
    .stat {{
      background: rgba(255,255,255,0.13);
      border: 1px solid rgba(255,255,255,0.18);
      border-radius: 18px;
      padding: 16px;
    }}
    .stat__value {{ font-size: 2rem; font-weight: 800; letter-spacing: -0.05em; }}
    .stat__label {{ margin-top: 6px; color: rgba(255,250,240,0.76); }}
    .grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-top: 22px; }}
    .panel {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 22px;
      box-shadow: var(--shadow);
    }}
    .panel h2 {{ margin: 0 0 14px; font-size: 1.12rem; }}
    .metric-row {{ display: grid; grid-template-columns: 130px minmax(0, 1fr) 34px; gap: 10px; align-items: center; margin-top: 10px; }}
    .metric-row__label {{ color: var(--muted); font-size: 0.95rem; }}
    .metric-row__bar {{ height: 10px; border-radius: 999px; background: var(--surface-2); overflow: hidden; }}
    .metric-row__bar span {{ display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--accent), var(--ink)); }}
    .metric-row__value {{ text-align: right; font-weight: 800; }}
    .table-wrap {{ margin-top: 22px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; }}
    .table-header {{ padding: 22px 24px 8px; }}
    .table-header h2 {{ margin: 0 0 8px; }}
    .table-header p {{ margin: 0; color: var(--muted); line-height: 1.6; }}
    .table-scroll {{ overflow-x: auto; padding: 8px 12px 16px; }}
    table {{ width: 100%; border-collapse: collapse; min-width: 1480px; }}
    th, td {{ padding: 14px 12px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; font-size: 0.93rem; }}
    th {{ color: var(--muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.06em; }}
    tr:hover td {{ background: #fff8eb; }}
    .repo-name {{ font-weight: 800; }}
    .repo-meta {{ color: var(--muted); font-size: 0.84rem; margin-top: 4px; }}
    .badge {{ display: inline-flex; align-items: center; padding: 7px 10px; border-radius: 999px; font-size: 0.78rem; font-weight: 800; }}
    .badge--p0 {{ background: var(--bad-soft); color: var(--bad); }}
    .badge--p1 {{ background: var(--warn-soft); color: var(--warn); }}
    .badge--p2, .badge--p3 {{ background: var(--ok-soft); color: var(--ok); }}
    .score, .risk, .mini-score {{ min-width: 96px; }}
    .score__bar, .risk__bar, .mini-score__bar {{ height: 10px; background: var(--surface-2); border-radius: 999px; overflow: hidden; }}
    .score__bar span, .mini-score__bar span {{ display: block; height: 100%; background: linear-gradient(90deg, var(--bad), var(--warn), var(--ok)); border-radius: 999px; }}
    .risk__bar span {{ display: block; height: 100%; background: linear-gradient(90deg, var(--ok), var(--warn), var(--bad)); border-radius: 999px; }}
    .score__value, .risk__value, .mini-score__value {{ margin-top: 5px; color: var(--muted); font-size: 0.82rem; }}
    .mini-score {{ min-width: 74px; }}
    .mini-list {{ margin: 0; padding-left: 17px; color: var(--muted); line-height: 1.45; }}
    .muted {{ color: var(--muted); }}
    .disabled-total {{ font-weight: 800; font-size: 0.86rem; margin-bottom: 4px; }}
    .disabled-chips {{ display: flex; flex-wrap: wrap; gap: 4px; }}
    .disabled-chip {{
      display: inline-flex; padding: 4px 8px; border-radius: 999px;
      background: var(--accent-soft); color: var(--bad);
      font-size: 0.74rem; font-weight: 600; white-space: nowrap;
    }}
    .footer {{ margin-top: 18px; color: var(--muted); font-size: 0.9rem; text-align: right; }}
    @media (max-width: 1080px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <h1>Workspace Data Quality Audit</h1>
      <p>전 Radar 저장소의 source portfolio와 taxonomy audit를 결합해 품질 축별 약점을 점검하는 실행판입니다. 우선순위, risk, weakest dimension, 다음 action을 같은 화면에서 확인합니다.</p>
      <div class="hero-meta">Generated from data-quality audit · Top queue: {escape(top_priority)}</div>
      <div class="hero-links">
        <a href="index.html">Main Dashboard</a>
        <a href="classification.html">Classification Audit</a>
        <a href="taxonomy-analysis.html">Taxonomy Analysis</a>
        <a href="storage.html">Storage Footprint</a>
        <a href="event-model.html">Event Model Coverage</a>
        <a href="../docs/harness/data-quality-review.md">Markdown Review</a>
      </div>
      <div class="stats">
        <article class="stat"><div class="stat__value">{summary['repo_count']}</div><div class="stat__label">Tracked Repos</div></article>
        <article class="stat"><div class="stat__value">{average_score}</div><div class="stat__label">Average Quality</div></article>
        <article class="stat"><div class="stat__value">{p0_count}</div><div class="stat__label">P0 Execution Queue</div></article>
        <article class="stat"><div class="stat__value">{p1_count}</div><div class="stat__label">P1 Execution Queue</div></article>
        <article class="stat"><div class="stat__value">{p2_count}</div><div class="stat__label">P2 Backlog</div></article>
        <article class="stat"><div class="stat__value">{disabled_total}</div><div class="stat__label">Disabled Sources ({disabled_repo_count} repos)</div></article>
      </div>
    </section>

    <section class="grid">
      {render_count_group("Priority", summary.get("priority_counts") or {}, PRIORITY_LABELS)}
      {render_count_group("Weakest Dimension", summary.get("weakest_dimension_counts") or {}, DIMENSION_LABELS)}
      {render_count_group("Governance", summary.get("governance_counts") or {}, {})}
      {disabled_panel_html}
    </section>

    <section class="table-wrap">
      <div class="table-header">
        <h2>P0 Execution Queue</h2>
        <p>고거버넌스/고리스크 저장소의 즉시 실행 대기열입니다. Risk는 높을수록 먼저 처리합니다.</p>
      </div>
      <div class="table-scroll">
        <table>
          <thead><tr><th>Repo</th><th>Risk</th><th>Quality</th><th>Weakest</th><th>Disabled</th><th>Issues</th><th>Next Actions</th></tr></thead>
          <tbody>{render_priority_rows(rows, "P0")}</tbody>
        </table>
      </div>
    </section>

    <section class="table-wrap">
      <div class="table-header">
        <h2>P1 Execution Queue</h2>
        <p>P0 이후 바로 이어갈 중간 우선순위 저장소입니다. attention, commerce, mobility, event 등 전환/운영 신호 보강이 핵심입니다.</p>
      </div>
      <div class="table-scroll">
        <table>
          <thead><tr><th>Repo</th><th>Risk</th><th>Quality</th><th>Weakest</th><th>Disabled</th><th>Issues</th><th>Next Actions</th></tr></thead>
          <tbody>{render_priority_rows(rows, "P1")}</tbody>
        </table>
      </div>
    </section>

    <section class="table-wrap">
      <div class="table-header">
        <h2>P2 Backlog</h2>
        <p>전체 커버리지를 완성하기 위한 후순위 저장소입니다. risk가 낮아도 canonical key, 운영 신호, 검증 축을 명시해 다음 구현 단위로 유지합니다.</p>
      </div>
      <div class="table-scroll">
        <table>
          <thead><tr><th>Repo</th><th>Risk</th><th>Quality</th><th>Weakest</th><th>Disabled</th><th>Issues</th><th>Next Actions</th></tr></thead>
          <tbody>{render_priority_rows(rows, "P2")}</tbody>
        </table>
      </div>
    </section>

    <section class="table-wrap">
      <div class="table-header">
        <h2>Quality Matrix</h2>
        <p>6개 품질 축을 전체 저장소에 대해 비교합니다. 낮은 점수의 dimension이 다음 source/config 보강의 기준입니다.</p>
      </div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Priority</th><th>Repo</th><th>Governance</th><th>Motion</th><th>Risk</th><th>Quality</th>
              <th>Authority</th><th>Operational</th><th>Freshness</th><th>Actionability</th><th>Verification</th><th>Traceability</th><th>Disabled</th><th>Next</th>
            </tr>
          </thead>
          <tbody>{render_matrix_rows(rows)}</tbody>
        </table>
      </div>
    </section>

    <footer class="footer">
      Canonical output: <code>radar-dashboard/data-quality.html</code> · Data source: <code>radar-dashboard/data/data-quality.json</code>
    </footer>
  </main>
</body>
</html>
"""


def main() -> int:
    args = parse_args()
    script_path = Path(__file__).resolve()
    workspace_root = script_path.parents[2]
    data_path = args.data_path.resolve() if args.data_path else workspace_root / "radar-dashboard" / "data" / "data-quality.json"
    output = args.output.resolve() if args.output else workspace_root / "radar-dashboard" / "data-quality.html"

    payload = json.loads(data_path.read_text(encoding="utf-8"))
    output.write_text(build_html(payload), encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
