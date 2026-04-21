#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any


DATA_QUALITY_DIMENSION_LABELS = {
    "authority": "권위성",
    "operational_depth": "운영 깊이",
    "freshness": "신선도",
    "actionability": "행동 가능성",
    "verification": "교차 검증",
    "traceability": "추적성",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render radar-dashboard index.html from JSON dataset")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Directory containing projects.json and summary.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory where index.html and dashboard.html will be written",
    )
    return parser.parse_args()


def resolve_paths(script_path: Path, args: argparse.Namespace) -> tuple[Path, Path]:
    dashboard_root = script_path.resolve().parents[1]
    data_dir = args.data_dir.resolve() if args.data_dir else dashboard_root / "data"
    output_dir = args.output_dir.resolve() if args.output_dir else dashboard_root
    return data_dir, output_dir


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return load_json(path)


def dashboard_href(path_value: str | None) -> str | None:
    if not path_value:
        return None
    return f"../{path_value}"


def badge_class(status: str) -> str:
    if status == "active":
        return "badge badge--active"
    if status == "partial":
        return "badge badge--partial"
    return "badge badge--missing"


def badge_label(status: str) -> str:
    if status == "active":
        return "Full"
    if status == "partial":
        return "Partial"
    return "Missing"


def format_number(value: Any) -> str:
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.1f}"
    return "—"


def format_percent(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.1f}%"
    return "—"


def format_timestamp(value: str | None) -> str:
    if not value:
        return "—"
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return value


def render_warning_list(warnings: list[str]) -> str:
    if not warnings:
        return '<p class="empty-state">No warnings. All projects expose dashboard-readable metrics.</p>'
    items = "\n".join(f"<li>{escape(item)}</li>" for item in warnings)
    return f"<ul class=\"warning-list\">\n{items}\n</ul>"


def render_latest_updates(items: list[dict[str, Any]]) -> str:
    if not items:
        return '<p class="empty-state">No update metadata available.</p>'
    rows = []
    for item in items:
        rows.append(
            "<li class=\"update-item\">"
            f"<span class=\"update-item__name\">{escape(str(item.get('display_name') or item.get('repo') or 'Unknown'))}</span>"
            f"<span class=\"update-item__date\">{escape(str(item.get('last_updated') or '—'))}</span>"
            f"<span class=\"{badge_class(str(item.get('status') or 'missing'))}\">{badge_label(str(item.get('status') or 'missing'))}</span>"
            "</li>"
        )
    return "<ul class=\"update-list\">\n" + "\n".join(rows) + "\n</ul>"


def render_top_entities(entities: list[dict[str, Any]]) -> str:
    if not entities:
        return '<span class="entity-chip entity-chip--muted">No entity data</span>'
    chips = []
    for entity in entities[:4]:
        name = escape(str(entity.get("name") or "unknown"))
        count = escape(str(entity.get("count") or 0))
        chips.append(f"<span class=\"entity-chip\">{name} <strong>{count}</strong></span>")
    return "".join(chips)


def render_project_rows(projects: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    for project in projects:
        status = str(project.get("status") or "missing")
        index_href = dashboard_href(project.get("report_index_path"))
        latest_href = dashboard_href(project.get("latest_report_path"))
        repo = escape(str(project.get("repo") or "Unknown"))
        display_name = escape(str(project.get("display_name") or repo))
        category = escape(str(project.get("category") or "—"))
        link = ""
        if index_href:
            link = f"<a href=\"{escape(index_href)}\">{display_name}</a>"
        else:
            link = display_name

        report_links: list[str] = []
        if index_href:
            report_links.append(f"<a href=\"{escape(index_href)}\">index</a>")
        if latest_href and latest_href != index_href:
            report_links.append(f"<a href=\"{escape(latest_href)}\">latest</a>")
        report_links_html = " · ".join(report_links) if report_links else "—"

        rows.append(
            "<tr>"
            f"<td><div class=\"project-name\">{link}</div><div class=\"project-repo\">{repo}</div></td>"
            f"<td>{category}</td>"
            f"<td><span class=\"{badge_class(status)}\">{badge_label(status)}</span></td>"
            f"<td>{format_number(project.get('article_count'))}</td>"
            f"<td>{format_number(project.get('matched_count'))}</td>"
            f"<td>{format_percent(project.get('match_rate'))}</td>"
            f"<td>{format_number(project.get('source_count'))}</td>"
            f"<td>{escape(str(project.get('last_updated') or '—'))}</td>"
            f"<td>{render_top_entities(project.get('top_entities') or [])}</td>"
            f"<td>{report_links_html}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def render_taxonomy_teaser(classification_payload: dict[str, Any] | None) -> str:
    if not classification_payload:
        return ""

    summary = classification_payload.get("summary") or {}
    repo_count = summary.get("repo_count")
    upgrade_needed = (summary.get("readiness_counts") or {}).get("upgrade", 0)
    high_governance = (summary.get("governance_counts") or {}).get("high", 0)
    advanced_radars = (summary.get("repo_class_counts") or {}).get("advanced-radar", 0)
    return (
        "<section class=\"taxonomy-banner\">"
        "<div>"
        "<h2>Portfolio Taxonomy Audit</h2>"
        "<p>전 저장소를 공통 taxonomy로 재분류한 별도 감사 페이지를 추가했습니다. "
        "저장소 구조, 의사결정 용도, 거버넌스, 소스 레이어 공백을 한 번에 점검할 수 있습니다.</p>"
        "</div>"
        "<div class=\"taxonomy-banner__meta\">"
        f"<span>{format_number(repo_count)} repos</span>"
        f"<span>{format_number(advanced_radars)} advanced</span>"
        f"<span>{format_number(high_governance)} high-governance</span>"
        f"<span>{format_number(upgrade_needed)} upgrade-needed</span>"
        "<a href=\"classification.html\">Open classification audit</a>"
        "</div>"
        "</section>"
    )


def render_data_quality_teaser(data_quality_payload: dict[str, Any] | None) -> str:
    if not data_quality_payload:
        return ""

    summary = data_quality_payload.get("summary") or {}
    priority_counts = summary.get("priority_counts") or {}
    weakest_counts = summary.get("weakest_dimension_counts") or {}
    p0_count = priority_counts.get("P0", 0)
    p1_count = priority_counts.get("P1", 0)
    average_score = summary.get("average_data_quality_score")
    weakest = "n/a"
    if weakest_counts:
        weakest = max(weakest_counts.items(), key=lambda item: item[1])[0]
        weakest = DATA_QUALITY_DIMENSION_LABELS.get(str(weakest), str(weakest))
    return (
        "<section class=\"taxonomy-banner\">"
        "<div>"
        "<h2>Data Quality Audit</h2>"
        "<p>전 저장소의 데이터 품질 축을 별도 점검판으로 추가했습니다. "
        "P0/P1 실행 큐, weakest dimension, source 보강 next action을 한 화면에서 확인할 수 있습니다.</p>"
        "</div>"
        "<div class=\"taxonomy-banner__meta\">"
        f"<span>avg quality {format_number(average_score)}</span>"
        f"<span>{format_number(p0_count)} P0</span>"
        f"<span>{format_number(p1_count)} P1</span>"
        f"<span>weakest {escape(str(weakest))}</span>"
        "<a href=\"data-quality.html\">Open quality audit</a>"
        "</div>"
        "</section>"
    )


def render_daily_collection_teaser(daily_payload: dict[str, Any] | None) -> str:
    if not daily_payload:
        return ""

    summary = daily_payload.get("summary") or {}
    ok_count = summary.get("ok", 0)
    partial_count = summary.get("partial", 0)
    not_applicable_count = summary.get("not_applicable", 0)
    contract = daily_payload.get("contract") or {}
    snapshot_paths = contract.get("accepted_snapshot_paths") or []
    snapshot_label = " / ".join(str(path) for path in snapshot_paths[:2]) or "date-addressable DuckDB"
    return (
        "<section class=\"taxonomy-banner\">"
        "<div>"
        "<h2>Daily Collection Contract</h2>"
        "<p>전 저장소의 daily schedule, date-partitioned raw records, DuckDB snapshot, retention CLI 적용 상태를 점검합니다.</p>"
        "</div>"
        "<div class=\"taxonomy-banner__meta\">"
        f"<span>{format_number(ok_count)} ok</span>"
        f"<span>{format_number(partial_count)} partial</span>"
        f"<span>{format_number(not_applicable_count)} n/a</span>"
        f"<span>{escape(snapshot_label)}</span>"
        "<a href=\"daily-collection.html\">Open daily contract</a>"
        "</div>"
        "</section>"
    )


def render_taxonomy_analysis_teaser(analysis_payload: dict[str, Any] | None) -> str:
    if not analysis_payload:
        return ""

    summary = analysis_payload.get("summary") or {}
    project_count = summary.get("project_count")
    error_total = summary.get("collection_error_total")
    freshness_gap_total = summary.get("freshness_gap_total")
    disabled_total = summary.get("disabled_source_total")
    average_risk = summary.get("average_risk_score")
    return (
        "<section class=\"taxonomy-banner\">"
        "<div>"
        "<h2>Taxonomy Analysis</h2>"
        "<p>Classification, evidence layers, collection errors, freshness gaps, and disabled-source backlog are joined into one portfolio analysis queue.</p>"
        "</div>"
        "<div class=\"taxonomy-banner__meta\">"
        f"<span>{format_number(project_count)} projects</span>"
        f"<span>{format_number(error_total)} errors</span>"
        f"<span>{format_number(freshness_gap_total)} freshness gaps</span>"
        f"<span>{format_number(disabled_total)} disabled</span>"
        f"<span>risk {format_number(average_risk)}</span>"
        "<a href=\"taxonomy-analysis.html\">Open taxonomy analysis</a>"
        "</div>"
        "</section>"
    )


def build_index_html(
    projects_payload: dict[str, Any],
    summary_payload: dict[str, Any],
    classification_payload: dict[str, Any] | None = None,
    data_quality_payload: dict[str, Any] | None = None,
    daily_collection_payload: dict[str, Any] | None = None,
    taxonomy_analysis_payload: dict[str, Any] | None = None,
) -> str:
    projects = list(projects_payload.get("projects") or [])
    projects.sort(
        key=lambda item: (
            0 if item.get("status") == "active" else 1 if item.get("status") == "partial" else 2,
            str(item.get("last_updated") or ""),
            str(item.get("repo") or ""),
        ),
        reverse=False,
    )
    projects.sort(key=lambda item: str(item.get("last_updated") or ""), reverse=True)

    active_projects = summary_payload.get("active_projects")
    full_projects = summary_payload.get("projects_with_full_metrics")
    partial_projects = summary_payload.get("projects_with_partial_metrics")
    article_total = summary_payload.get("article_total")
    matched_total = summary_payload.get("matched_total")
    overall_match_rate = summary_payload.get("overall_match_rate")
    generated_at = format_timestamp(summary_payload.get("generated_at"))
    warnings = list(summary_payload.get("warnings") or [])
    latest_updates = list(summary_payload.get("latest_updates") or [])
    taxonomy_teaser = render_taxonomy_teaser(classification_payload)
    data_quality_teaser = render_data_quality_teaser(data_quality_payload)
    daily_collection_teaser = render_daily_collection_teaser(daily_collection_payload)
    taxonomy_analysis_teaser = render_taxonomy_analysis_teaser(taxonomy_analysis_payload)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Radar Projects Dashboard</title>
  <style>
    :root {{
      --bg: #f4f6fb;
      --surface: #ffffff;
      --surface-alt: #eef3ff;
      --text: #18202b;
      --muted: #617086;
      --line: #d7dfef;
      --accent: #2358d5;
      --accent-soft: #dce7ff;
      --ok: #1e8e5a;
      --ok-soft: #daf4e7;
      --warn: #a96b00;
      --warn-soft: #fff1cd;
      --bad: #a23b3b;
      --bad-soft: #fde2e2;
      --shadow: 0 18px 50px rgba(24, 32, 43, 0.08);
      --radius: 18px;
      --radius-sm: 999px;
      --max: 1380px;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      font-family: "Pretendard Variable", "Pretendard", "Segoe UI", Arial, sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(35, 88, 213, 0.08), transparent 24rem),
        radial-gradient(circle at bottom right, rgba(30, 142, 90, 0.06), transparent 24rem),
        var(--bg);
    }}

    a {{
      color: var(--accent);
      text-decoration: none;
    }}

    a:hover {{
      text-decoration: underline;
    }}

    .page {{
      max-width: var(--max);
      margin: 0 auto;
      padding: 32px 24px 56px;
    }}

    .hero {{
      background: linear-gradient(135deg, #13203d, #2358d5);
      color: white;
      border-radius: 28px;
      padding: 32px;
      box-shadow: var(--shadow);
    }}

    .hero h1 {{
      margin: 0 0 12px;
      font-size: clamp(2rem, 3vw, 3rem);
      letter-spacing: -0.04em;
    }}

    .hero p {{
      margin: 0;
      max-width: 68ch;
      line-height: 1.6;
      color: rgba(255,255,255,0.84);
    }}

    .hero-meta {{
      margin-top: 18px;
      font-size: 0.95rem;
      color: rgba(255,255,255,0.78);
    }}

    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
      margin-top: 24px;
    }}

    .stat-card {{
      background: rgba(255,255,255,0.14);
      border: 1px solid rgba(255,255,255,0.18);
      border-radius: var(--radius);
      padding: 18px 20px;
      backdrop-filter: blur(8px);
    }}

    .stat-card__value {{
      font-size: 1.9rem;
      font-weight: 700;
      letter-spacing: -0.03em;
    }}

    .stat-card__label {{
      margin-top: 8px;
      color: rgba(255,255,255,0.72);
      font-size: 0.92rem;
    }}

    .section-grid {{
      display: grid;
      grid-template-columns: 1.4fr 1fr;
      gap: 20px;
      margin-top: 24px;
    }}

    .taxonomy-banner {{
      margin-top: 24px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 22px 24px;
      box-shadow: var(--shadow);
      display: grid;
      gap: 16px;
      grid-template-columns: minmax(0, 1.7fr) minmax(280px, 1fr);
      align-items: center;
    }}

    .taxonomy-banner h2 {{
      margin: 0 0 8px;
      font-size: 1.2rem;
      letter-spacing: -0.02em;
    }}

    .taxonomy-banner p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.6;
    }}

    .taxonomy-banner__meta {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
      justify-content: flex-end;
    }}

    .taxonomy-banner__meta span,
    .taxonomy-banner__meta a {{
      display: inline-flex;
      align-items: center;
      padding: 8px 12px;
      border-radius: var(--radius-sm);
      background: var(--surface-alt);
      color: var(--text);
      font-size: 0.9rem;
      white-space: nowrap;
    }}

    .taxonomy-banner__meta a {{
      background: var(--accent);
      color: white;
      font-weight: 700;
    }}

    @media (max-width: 980px) {{
      .section-grid {{
        grid-template-columns: 1fr;
      }}

      .taxonomy-banner {{
        grid-template-columns: 1fr;
      }}

      .taxonomy-banner__meta {{
        justify-content: flex-start;
      }}
    }}

    .panel {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 24px;
      box-shadow: var(--shadow);
    }}

    .panel h2 {{
      margin: 0 0 12px;
      font-size: 1.2rem;
      letter-spacing: -0.02em;
    }}

    .panel p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.6;
    }}

    .warning-list,
    .update-list {{
      margin: 14px 0 0;
      padding-left: 18px;
      color: var(--muted);
    }}

    .warning-list li {{
      margin: 10px 0;
      line-height: 1.5;
    }}

    .update-list {{
      list-style: none;
      padding: 0;
    }}

    .update-item {{
      display: grid;
      grid-template-columns: 1fr auto auto;
      gap: 12px;
      align-items: center;
      padding: 12px 0;
      border-top: 1px solid var(--line);
    }}

    .update-item:first-child {{
      border-top: none;
      padding-top: 0;
    }}

    .update-item__name {{
      font-weight: 600;
    }}

    .update-item__date {{
      color: var(--muted);
      font-size: 0.92rem;
      white-space: nowrap;
    }}

    .table-wrap {{
      margin-top: 24px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }}

    .table-header {{
      padding: 22px 24px 8px;
    }}

    .table-header h2 {{
      margin: 0;
      font-size: 1.2rem;
      letter-spacing: -0.02em;
    }}

    .table-header p {{
      margin: 8px 0 0;
      color: var(--muted);
      line-height: 1.6;
    }}

    .table-scroll {{
      overflow-x: auto;
      padding: 8px 12px 16px;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 1120px;
    }}

    th, td {{
      padding: 14px 12px;
      text-align: left;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
      font-size: 0.95rem;
    }}

    th {{
      color: var(--muted);
      font-weight: 600;
      font-size: 0.82rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }}

    tr:hover td {{
      background: #f9fbff;
    }}

    .project-name {{
      font-weight: 700;
      margin-bottom: 4px;
    }}

    .project-repo {{
      color: var(--muted);
      font-size: 0.86rem;
    }}

    .badge {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: var(--radius-sm);
      padding: 6px 10px;
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}

    .badge--active {{
      background: var(--ok-soft);
      color: var(--ok);
    }}

    .badge--partial {{
      background: var(--warn-soft);
      color: var(--warn);
    }}

    .badge--missing {{
      background: var(--bad-soft);
      color: var(--bad);
    }}

    .entity-chip {{
      display: inline-flex;
      gap: 6px;
      align-items: center;
      padding: 5px 10px;
      margin: 0 6px 6px 0;
      background: var(--surface-alt);
      border-radius: var(--radius-sm);
      color: #3a4a64;
      font-size: 0.82rem;
      white-space: nowrap;
    }}

    .entity-chip--muted {{
      color: var(--muted);
      background: #f1f3f8;
    }}

    .empty-state {{
      margin-top: 14px;
      color: var(--muted);
    }}

    .footer {{
      margin-top: 20px;
      color: var(--muted);
      font-size: 0.9rem;
      text-align: right;
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <h1>Radar Projects Dashboard</h1>
      <p>각 Radar 저장소의 `summary JSON`과 리포트 인덱스를 읽어 워크스페이스 전체 상태를 집계한 canonical 대시보드입니다. 현재는 full metrics 우선, 부족한 저장소는 partial fallback으로 표시합니다.</p>
      <div class="hero-meta">Generated at {escape(generated_at)} · Workspace scan source: sibling Radar repositories</div>
      <div class="stats">
        <article class="stat-card">
          <div class="stat-card__value">{format_number(active_projects)}</div>
          <div class="stat-card__label">Active Projects</div>
        </article>
        <article class="stat-card">
          <div class="stat-card__value">{format_number(full_projects)}</div>
          <div class="stat-card__label">Projects With Full Metrics</div>
        </article>
        <article class="stat-card">
          <div class="stat-card__value">{format_number(partial_projects)}</div>
          <div class="stat-card__label">Projects Using Fallback</div>
        </article>
        <article class="stat-card">
          <div class="stat-card__value">{format_number(article_total)}</div>
          <div class="stat-card__label">Articles From Full Metrics</div>
        </article>
        <article class="stat-card">
          <div class="stat-card__value">{format_number(matched_total)}</div>
          <div class="stat-card__label">Matched Articles</div>
        </article>
        <article class="stat-card">
          <div class="stat-card__value">{format_percent(overall_match_rate)}</div>
          <div class="stat-card__label">Overall Match Rate</div>
        </article>
      </div>
    </section>

    <section class="section-grid">
      <article class="panel">
        <h2>Coverage Warnings</h2>
        <p>Summary JSON이 없는 저장소는 HTML fallback으로 읽었고, 그 결과는 partial로 표시됩니다.</p>
        {render_warning_list(warnings)}
      </article>
      <article class="panel">
        <h2>Latest Updates</h2>
        <p>가장 최근 업데이트된 저장소 순으로 집계했습니다.</p>
        {render_latest_updates(latest_updates)}
      </article>
    </section>

    {taxonomy_teaser}

    {data_quality_teaser}

    {taxonomy_analysis_teaser}

    {daily_collection_teaser}

    <section class="table-wrap">
      <div class="table-header">
        <h2>Project Status</h2>
        <p>각 행은 저장소별 최신 상태입니다. `index`는 보고서 인덱스, `latest`는 최신 리포트 링크입니다. partial 저장소는 metrics가 비어 있거나 fallback으로 읽은 상태입니다.</p>
      </div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Project</th>
              <th>Category</th>
              <th>Status</th>
              <th>Articles</th>
              <th>Matched</th>
              <th>Match Rate</th>
              <th>Sources</th>
              <th>Last Updated</th>
              <th>Top Entities</th>
              <th>Reports</th>
            </tr>
          </thead>
          <tbody>
            {render_project_rows(projects)}
          </tbody>
        </table>
      </div>
    </section>

    <footer class="footer">
      Canonical output: <code>radar-dashboard/index.html</code> · Redirect alias: <code>radar-dashboard/dashboard.html</code>
    </footer>
  </main>
</body>
</html>
"""


def build_redirect_html() -> str:
    return """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="0; url=index.html">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Redirecting to dashboard</title>
</head>
<body>
  <p>Dashboard moved to <a href="index.html">index.html</a>.</p>
</body>
</html>
"""


def main() -> int:
    args = parse_args()
    script_path = Path(__file__)
    data_dir, output_dir = resolve_paths(script_path, args)

    projects_payload = load_json(data_dir / "projects.json")
    summary_payload = load_json(data_dir / "summary.json")
    classification_payload = load_optional_json(data_dir / "classification.json")
    data_quality_payload = load_optional_json(data_dir / "data-quality.json")
    daily_collection_payload = load_optional_json(data_dir / "daily-collection.json")
    taxonomy_analysis_payload = load_optional_json(data_dir / "taxonomy-analysis.json")

    index_html = build_index_html(
        projects_payload,
        summary_payload,
        classification_payload,
        data_quality_payload,
        daily_collection_payload,
        taxonomy_analysis_payload,
    )
    redirect_html = build_redirect_html()

    (output_dir / "index.html").write_text(index_html, encoding="utf-8")
    (output_dir / "dashboard.html").write_text(redirect_html, encoding="utf-8")

    print(f"Wrote {(output_dir / 'index.html')}")
    print(f"Wrote {(output_dir / 'dashboard.html')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
