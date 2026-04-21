#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from typing import Any


CLASS_LABELS = {
    "shared-core": "Shared Core",
    "shared-template": "Shared Template",
    "shared-dashboard": "Shared Dashboard",
    "standard-radar": "Standard Radar",
    "advanced-radar": "Advanced Radar",
}
MOTION_LABELS = {
    "infrastructure": "Infrastructure",
    "conversion": "Conversion",
    "intelligence": "Intelligence",
    "compliance-risk": "Compliance/Risk",
    "attention": "Attention",
}
GOVERNANCE_LABELS = {
    "shared": "Shared",
    "low": "Low",
    "medium": "Medium",
    "high": "High",
}
READINESS_LABELS = {
    "ready": "Ready",
    "watch": "Watch",
    "upgrade": "Upgrade",
}
LAYER_LABELS = {
    "official": "공식",
    "operational": "운영",
    "market": "시장",
    "community": "커뮤니티",
    "attention": "관심",
}
LAYER_ORDER = ["official", "operational", "market", "community", "attention"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render classification dashboard from classification.json")
    parser.add_argument("--data-path", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


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
    return (
        "<article class=\"panel\">"
        f"<h2>{escape(title)}</h2>"
        + "".join(rows)
        + "</article>"
    )


def layer_pills(available_layers: list[str], missing_layers: list[str]) -> str:
    available = set(available_layers)
    missing = set(missing_layers)
    pills = []
    for layer in LAYER_ORDER:
        if layer in available:
            pills.append(f"<span class=\"layer layer--on\">{LAYER_LABELS[layer]}</span>")
        elif layer in missing:
            pills.append(f"<span class=\"layer layer--off\">{LAYER_LABELS[layer]}</span>")
        else:
            pills.append(f"<span class=\"layer layer--na\">{LAYER_LABELS[layer]}</span>")
    return "".join(pills)


def quality_meter(score: int) -> str:
    width = max(4, min(score, 100))
    return (
        "<div class=\"quality\">"
        f"<div class=\"quality__bar\"><span style=\"width:{width}%\"></span></div>"
        f"<div class=\"quality__value\">{score}</div>"
        "</div>"
    )


def badge(kind: str, label: str) -> str:
    return f"<span class=\"badge badge--{escape(kind)}\">{escape(label)}</span>"


def render_repo_rows(rows: list[dict[str, Any]]) -> str:
    rendered = []
    for row in rows:
        readiness = row["readiness_status"]
        rendered.append(
            "<tr>"
            f"<td><div class=\"repo-name\">{escape(row['display_name'])}</div><div class=\"repo-id\">{escape(row['repo'])}</div></td>"
            f"<td>{badge('class', CLASS_LABELS.get(row['repo_class'], row['repo_class']))}</td>"
            f"<td>{badge('motion', MOTION_LABELS.get(row['primary_motion'], row['primary_motion']))}</td>"
            f"<td>{escape(row['domain_family'])}</td>"
            f"<td>{badge('gov', GOVERNANCE_LABELS.get(row['governance_profile'], row['governance_profile']))}</td>"
            f"<td>{escape(row['evidence_strategy'])}</td>"
            f"<td>{badge(readiness, READINESS_LABELS.get(readiness, readiness))}</td>"
            f"<td>{escape(row['source_status'])}</td>"
            f"<td>{layer_pills(row.get('available_layers') or [], row.get('missing_layers') or [])}</td>"
            f"<td>{escape(str(row.get('dashboard_status') or 'n/a'))}</td>"
            f"<td>{quality_meter(int(row.get('quality_score') or 0))}</td>"
            f"<td>{escape(str(row.get('next_step') or ''))}</td>"
            "</tr>"
        )
    return "\n".join(rendered)


def build_html(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    rows = list(payload["repos"])
    rows.sort(key=lambda row: (-int(row.get("priority_score", 0)), row["repo"]))

    top_priority = rows[:8]
    priority_items = "".join(
        "<li>"
        f"<strong>{escape(row['repo'])}</strong> · "
        f"{escape(READINESS_LABELS.get(row['readiness_status'], row['readiness_status']))} · "
        f"{escape(str(row['next_step']))}"
        "</li>"
        for row in top_priority
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Workspace Classification Audit</title>
  <style>
    :root {{
      --bg: #f4f6fb;
      --surface: #fff;
      --surface-2: #eef3ff;
      --text: #18202b;
      --muted: #617086;
      --line: #d7dfef;
      --accent: #1d4ed8;
      --accent-soft: #dbe8ff;
      --ok: #1d7f49;
      --ok-soft: #ddf5e5;
      --warn: #9a6700;
      --warn-soft: #fff1cc;
      --bad: #a23b3b;
      --bad-soft: #fde2e2;
      --shared: #5b4ab2;
      --shared-soft: #ece8ff;
      --shadow: 0 18px 50px rgba(24, 32, 43, 0.08);
      --max: 1460px;
      --radius: 20px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--text);
      font-family: "Pretendard Variable", "Pretendard", "Segoe UI", Arial, sans-serif;
      background:
        radial-gradient(circle at top left, rgba(29, 78, 216, 0.08), transparent 24rem),
        radial-gradient(circle at bottom right, rgba(29, 127, 73, 0.08), transparent 22rem),
        var(--bg);
    }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .page {{ max-width: var(--max); margin: 0 auto; padding: 28px 22px 56px; }}
    .hero {{
      background: linear-gradient(135deg, #0f1f3d, #1d4ed8);
      border-radius: 28px;
      color: #fff;
      padding: 34px;
      box-shadow: var(--shadow);
    }}
    .hero h1 {{ margin: 0 0 10px; font-size: clamp(2rem, 3vw, 3rem); letter-spacing: -0.04em; }}
    .hero p {{ margin: 0; max-width: 75ch; color: rgba(255,255,255,0.86); line-height: 1.6; }}
    .hero-meta {{ margin-top: 16px; color: rgba(255,255,255,0.75); font-size: 0.95rem; }}
    .hero-links {{ margin-top: 16px; display: flex; gap: 14px; flex-wrap: wrap; }}
    .hero-links a {{
      display: inline-flex; align-items: center; gap: 6px; padding: 10px 14px;
      border-radius: 999px; background: rgba(255,255,255,0.12); color: #fff;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
      margin-top: 24px;
    }}
    .stat {{
      background: rgba(255,255,255,0.12);
      border: 1px solid rgba(255,255,255,0.16);
      border-radius: 18px;
      padding: 16px;
    }}
    .stat__value {{ font-size: 2rem; font-weight: 700; letter-spacing: -0.04em; }}
    .stat__label {{ margin-top: 4px; color: rgba(255,255,255,0.78); }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
      margin-top: 22px;
    }}
    .panel {{
      background: var(--surface);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 22px;
    }}
    .panel h2 {{ margin: 0 0 14px; font-size: 1.15rem; }}
    .metric-row {{
      display: grid;
      grid-template-columns: 140px minmax(0, 1fr) 32px;
      gap: 10px;
      align-items: center;
      margin-top: 10px;
    }}
    .metric-row__label {{ color: var(--muted); font-size: 0.95rem; }}
    .metric-row__bar {{
      height: 10px; border-radius: 999px; background: var(--surface-2); overflow: hidden;
    }}
    .metric-row__bar span {{
      display: block; height: 100%; border-radius: 999px;
      background: linear-gradient(90deg, #2358d5, #1d7f49);
    }}
    .metric-row__value {{ text-align: right; font-weight: 700; }}
    .priority-list {{ margin: 0; padding-left: 18px; line-height: 1.7; }}
    .table-wrap {{
      margin-top: 22px; background: var(--surface); border-radius: var(--radius);
      box-shadow: var(--shadow); overflow: hidden;
    }}
    .table-header {{ padding: 22px 22px 0; }}
    .table-header h2 {{ margin: 0 0 10px; }}
    .table-header p {{ margin: 0 0 18px; color: var(--muted); line-height: 1.6; }}
    .table-scroll {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; min-width: 1340px; }}
    th, td {{ padding: 14px 16px; border-top: 1px solid var(--line); vertical-align: top; }}
    th {{ background: #f8faff; text-align: left; font-size: 0.9rem; color: var(--muted); }}
    .repo-name {{ font-weight: 700; }}
    .repo-id {{ margin-top: 4px; color: var(--muted); font-size: 0.85rem; }}
    .badge {{
      display: inline-flex; align-items: center; padding: 7px 10px; border-radius: 999px;
      font-size: 0.82rem; font-weight: 600;
    }}
    .badge--class {{ background: var(--shared-soft); color: var(--shared); }}
    .badge--motion {{ background: var(--accent-soft); color: var(--accent); }}
    .badge--gov {{ background: #eef6ff; color: #22598f; }}
    .badge--ready {{ background: var(--ok-soft); color: var(--ok); }}
    .badge--watch {{ background: var(--warn-soft); color: var(--warn); }}
    .badge--upgrade {{ background: var(--bad-soft); color: var(--bad); }}
    .layer {{
      display: inline-flex; align-items: center; justify-content: center;
      min-width: 40px; padding: 6px 8px; border-radius: 10px; margin: 2px 4px 2px 0;
      font-size: 0.78rem; font-weight: 600; border: 1px solid transparent;
    }}
    .layer--on {{ background: var(--accent-soft); color: var(--accent); }}
    .layer--off {{ background: #fff7e6; color: #9a6700; border-color: #f4d38c; }}
    .layer--na {{ background: #f1f3f7; color: #8a95a8; }}
    .quality {{ min-width: 120px; }}
    .quality__bar {{
      height: 10px; background: #edf1f8; border-radius: 999px; overflow: hidden;
    }}
    .quality__bar span {{
      display: block; height: 100%;
      background: linear-gradient(90deg, #c94c4c, #dc9f1d, #1d7f49);
    }}
    .quality__value {{ margin-top: 6px; color: var(--muted); font-size: 0.85rem; }}
    .footer {{ margin-top: 18px; color: var(--muted); font-size: 0.92rem; }}
    @media (max-width: 980px) {{
      .grid {{ grid-template-columns: 1fr; }}
      .metric-row {{ grid-template-columns: 110px minmax(0, 1fr) 28px; }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <h1>Workspace Classification Audit</h1>
      <p>모든 하위 프로젝트를 같은 공통 taxonomy로 재분류한 점검판입니다. 저장소 구조, 의사결정 용도, 소스 레이어, 거버넌스, 실행 준비도를 한 화면에서 확인할 수 있게 만들었습니다.</p>
      <div class="hero-meta">Generated from repo taxonomy audit · Framework: {escape(payload.get('framework_path', 'docs/harness/portfolio-taxonomy-framework.md'))}</div>
      <div class="hero-links">
        <a href="index.html">Main Dashboard</a>
        <a href="data-quality.html">Data Quality Audit</a>
        <a href="../docs/harness/repo-taxonomy-review.md">Markdown Review</a>
        <a href="../docs/harness/portfolio-taxonomy-framework.md">Framework Doc</a>
      </div>
      <div class="stats">
        <article class="stat"><div class="stat__value">{summary['repo_count']}</div><div class="stat__label">Tracked Repos</div></article>
        <article class="stat"><div class="stat__value">{summary['repo_class_counts'].get('advanced-radar', 0)}</div><div class="stat__label">Advanced Radars</div></article>
        <article class="stat"><div class="stat__value">{summary['governance_counts'].get('high', 0)}</div><div class="stat__label">High Governance</div></article>
        <article class="stat"><div class="stat__value">{summary['readiness_counts'].get('upgrade', 0)}</div><div class="stat__label">Upgrade Needed</div></article>
      </div>
    </section>

    <section class="grid">
      {render_count_group("Repo Class", summary["repo_class_counts"], CLASS_LABELS)}
      {render_count_group("Primary Motion", summary["primary_motion_counts"], MOTION_LABELS)}
      {render_count_group("Governance", summary["governance_counts"], GOVERNANCE_LABELS)}
      {render_count_group("Execution Readiness", summary["readiness_counts"], READINESS_LABELS)}
      {render_count_group("Evidence Strategy", summary["evidence_strategy_counts"], {})}
      <article class="panel">
        <h2>Priority Upgrades</h2>
        <ol class="priority-list">{priority_items}</ol>
      </article>
    </section>

    <section class="table-wrap">
      <div class="table-header">
        <h2>Classification Matrix</h2>
        <p>각 저장소를 `Repo Class`, `Primary Motion`, `Governance`, `Evidence Strategy`, `Readiness` 기준으로 정렬했습니다. `Layers`는 고도화한 분류체계의 5개 소스 계층 점검용 표시입니다.</p>
      </div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Repo</th>
              <th>Class</th>
              <th>Motion</th>
              <th>Domain</th>
              <th>Governance</th>
              <th>Evidence Strategy</th>
              <th>Readiness</th>
              <th>Source Status</th>
              <th>Layers</th>
              <th>Dashboard</th>
              <th>Quality</th>
              <th>Next Step</th>
            </tr>
          </thead>
          <tbody>
            {render_repo_rows(rows)}
          </tbody>
        </table>
      </div>
    </section>

    <footer class="footer">
      Canonical output: <code>radar-dashboard/classification.html</code> · Data source: <code>radar-dashboard/data/classification.json</code>
    </footer>
  </main>
</body>
</html>
"""


def main() -> int:
    args = parse_args()
    script_path = Path(__file__).resolve()
    workspace_root = script_path.parents[2]
    data_path = args.data_path.resolve() if args.data_path else workspace_root / "radar-dashboard" / "data" / "classification.json"
    output = args.output.resolve() if args.output else workspace_root / "radar-dashboard" / "classification.html"

    payload = json.loads(data_path.read_text(encoding="utf-8"))
    output.write_text(build_html(payload), encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
